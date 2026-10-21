from __future__ import annotations

import json
import threading
import time
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from edge.csv_lab import CSVLabError, parse_csv_lab
from edge.hl7 import CR, FS, VT, MLLPFramer, build_ack, parse_header
from edge.normalize import normalize_mdc
from edge.queue import AppendOnlyQueue
from edge.service import Config, Forwarder, Gateway


MESSAGE = (
    b"MSH|^~\\&|MONITOR|ICU|PREDICTRX|HOSP|20261018120000+0000||ORU^R01|MSG-42|P|2.5.1\r"
    b"PID|1||patient-1\r"
    b"OBX|1|NM|8867-4^Heart rate^LN||88|/min|||||F|||20261018120000+0000\r"
)


def config(tmp_path, api_url="http://127.0.0.1:1"):
    return Config(
        mllp_host="127.0.0.1", mllp_port=2575,
        health_host="127.0.0.1", health_port=8081,
        api_url=api_url, integration_key="feed.secret",
        queue_path=str(tmp_path / "queue.jsonl"),
        connect_timeout=0.2, request_timeout=1,
        retry_initial=2, retry_max=10, poll_interval=0.01,
        max_message_bytes=1024 * 1024,
    )


def test_mllp_framer_handles_fragmented_and_coalesced_frames():
    framed = VT + MESSAGE + FS + CR
    framer = MLLPFramer()
    assert framer.feed(framed[:7]) == []
    assert framer.feed(framed[7:] + framed) == [MESSAGE, MESSAGE]


def test_ack_uses_control_id_and_reverses_sender_receiver():
    header = parse_header(MESSAGE)
    ack = build_ack(header, "AA", "accepted")
    assert ack.startswith(VT) and ack.endswith(FS + CR)
    text = ack[1:-2].decode()
    assert "MSH|^~\\&|PREDICTRX|HOSP|MONITOR|ICU|" in text
    assert "\rMSA|AA|MSG-42|accepted\r" in text


def test_gateway_returns_ae_for_invalid_message_and_aa_after_durable_enqueue(tmp_path):
    gateway = Gateway(config(tmp_path))
    assert b"MSA|AE|UNKNOWN|" in gateway.accept(b"not-hl7")
    unsupported = MESSAGE.replace(b"ORU^R01", b"ADT^A01")
    assert b"MSA|AE|MSG-42|" in gateway.accept(unsupported)
    assert b"MSA|AA|MSG-42|" in gateway.accept(MESSAGE)
    assert gateway.queue.pending_count == 1
    assert AppendOnlyQueue(tmp_path / "queue.jsonl").pending_count == 1


def test_ieee_11073_symbolic_codes_are_normalized_before_forwarding(tmp_path):
    message = MESSAGE.replace(b"8867-4^Heart rate^LN", b"MDC_PULS_OXIM_PULS_RATE^Pulse^MDC")
    assert b"8867-4^Pulse^LN" in normalize_mdc(message)
    gateway = Gateway(config(tmp_path))
    gateway.accept(message)
    assert b"8867-4^Pulse^LN" in gateway.queue.due()[0].payload


def test_append_only_queue_rebuilds_pending_and_delivery_state(tmp_path):
    path = tmp_path / "queue.jsonl"
    queue = AppendOnlyQueue(path)
    first = queue.enqueue(b"one", "id-1")
    second = queue.enqueue(b"two", "id-2")
    original_size = path.stat().st_size
    queue.mark_retry(first.item_id, "offline", time.time() + 5)
    queue.mark_delivered(second.item_id)
    assert path.stat().st_size > original_size

    restored = AppendOnlyQueue(path)
    assert restored.pending_count == 1
    pending = restored.due(now=time.time() + 10)
    assert pending[0].payload == b"one"
    assert pending[0].attempts == 1
    assert pending[0].last_error == "offline"


def test_forwarder_posts_hl7_with_integration_and_idempotency_headers(tmp_path):
    received = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            received["path"] = self.path
            received["key"] = self.headers["X-Integration-Key"]
            received["idempotency"] = self.headers["Idempotency-Key"]
            received["body"] = self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        queue = AppendOnlyQueue(tmp_path / "queue.jsonl")
        item = queue.enqueue(MESSAGE, "MSG-42")
        forwarder = Forwarder(config(tmp_path, f"http://127.0.0.1:{server.server_port}"), queue)
        forwarder.process(item)
    finally:
        server.shutdown()
        server.server_close()

    assert queue.pending_count == 0
    assert received == {
        "path": "/v1/integrations/hl7v2/oru",
        "key": "feed.secret",
        "idempotency": "MSG-42",
        "body": MESSAGE,
    }


def test_forwarder_retries_with_bounded_exponential_backoff(tmp_path, monkeypatch):
    queue = AppendOnlyQueue(tmp_path / "queue.jsonl")
    item = queue.enqueue(MESSAGE, "MSG-42")
    forwarder = Forwarder(config(tmp_path), queue)

    def unavailable(_item):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(forwarder, "_post", unavailable)
    for attempt in range(5):
        due = queue.due(now=time.time() + 1000)[0]
        before = time.time()
        forwarder.process(due)
        updated = queue.due(now=time.time() + 1000)[0]
        expected = min(10, 2 * (2 ** attempt))
        assert expected - 0.2 <= updated.next_attempt - before <= expected + 0.2
    assert queue.pending_count == 1


def test_csv_parser_produces_native_observation_batch():
    result = parse_csv_lab(
        "patient_id,encounter_id,timestamp,code,value,unit,unit_id\n"
        "p1,e1,2026-10-18T12:00:00+00:00,Lactate,3.4,mmol/L,icu-a\n"
    )
    assert result == {"observations": [{
        "patient_id": "p1", "encounter_id": "e1",
        "timestamp": "2026-10-18T12:00:00+00:00", "code": "Lactate",
        "value": 3.4, "source": "csv_lab", "unit": "mmol/L", "unit_id": "icu-a",
    }]}


def test_csv_parser_rejects_bad_contract():
    with pytest.raises(CSVLabError, match="missing required"):
        parse_csv_lab("patient_id,value\np1,3.4\n")
    with pytest.raises(CSVLabError, match="numeric"):
        parse_csv_lab("patient_id,encounter_id,timestamp,code,value\np1,e1,2026-01-01T00:00:00Z,HR,nope\n")

