"""Stdlib-only MLLP receiver, durable forwarder, and health server."""

from __future__ import annotations

import json
import logging
import os
import signal
import socketserver
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from edge.hl7 import HL7Error, MLLPFramer, build_ack, parse_header
from edge.normalize import normalize_mdc
from edge.queue import AppendOnlyQueue, QueueItem

LOG = logging.getLogger("predictrx.edge")


def _env_float(name: str, default: float, minimum: float = 0.0) -> float:
    value = float(os.getenv(name, str(default)))
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return value


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    value = int(os.getenv(name, str(default)))
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return value


@dataclass(frozen=True)
class Config:
    mllp_host: str
    mllp_port: int
    health_host: str
    health_port: int
    api_url: str
    integration_key: str
    queue_path: str
    connect_timeout: float
    request_timeout: float
    retry_initial: float
    retry_max: float
    poll_interval: float
    max_message_bytes: int

    @classmethod
    def from_env(cls) -> "Config":
        key = os.getenv("EDGE_INTEGRATION_KEY", "")
        if not key:
            raise ValueError("EDGE_INTEGRATION_KEY is required")
        initial = _env_float("EDGE_RETRY_INITIAL_SECONDS", 1.0, 0.01)
        maximum = _env_float("EDGE_RETRY_MAX_SECONDS", 60.0, initial)
        return cls(
            mllp_host=os.getenv("EDGE_MLLP_HOST", "0.0.0.0"),
            mllp_port=_env_int("EDGE_MLLP_PORT", 2575),
            health_host=os.getenv("EDGE_HEALTH_HOST", "0.0.0.0"),
            health_port=_env_int("EDGE_HEALTH_PORT", 8081),
            api_url=os.getenv("EDGE_API_URL", "http://api:8000").rstrip("/"),
            integration_key=key,
            queue_path=os.getenv("EDGE_QUEUE_PATH", "/var/lib/predictrx-edge/queue.jsonl"),
            connect_timeout=_env_float("EDGE_CONNECT_TIMEOUT_SECONDS", 3.0, 0.01),
            request_timeout=_env_float("EDGE_REQUEST_TIMEOUT_SECONDS", 10.0, 0.01),
            retry_initial=initial,
            retry_max=maximum,
            poll_interval=_env_float("EDGE_POLL_INTERVAL_SECONDS", 0.25, 0.01),
            max_message_bytes=_env_int("EDGE_MAX_MESSAGE_BYTES", 2 * 1024 * 1024),
        )


class Forwarder:
    def __init__(self, config: Config, queue: AppendOnlyQueue) -> None:
        self.config = config
        self.queue = queue
        self.stop_event = threading.Event()
        self.last_success_at: float | None = None
        self.last_error: str | None = None
        self.permanent_failures = 0

    def _post(self, item: QueueItem) -> int:
        request = urllib.request.Request(
            self.config.api_url + "/v1/integrations/hl7v2/oru",
            data=item.payload,
            method="POST",
            headers={
                "Content-Type": "application/hl7-v2; charset=utf-8",
                "X-Integration-Key": self.config.integration_key,
                "Idempotency-Key": item.idempotency_key,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.request_timeout) as response:
                response.read()
                return response.status
        except urllib.error.HTTPError as exc:
            exc.read()
            return exc.code

    def process(self, item: QueueItem) -> None:
        try:
            status = self._post(item)
            if 200 <= status < 300:
                self.queue.mark_delivered(item.item_id)
                self.last_success_at = time.time()
                self.last_error = None
                return
            if status not in {408, 425, 429} and status < 500:
                error = f"API rejected payload with HTTP {status}"
                self.queue.mark_failed(item.item_id, error)
                self.permanent_failures += 1
                self.last_error = error
                return
            error = f"retryable API response HTTP {status}"
        except (OSError, urllib.error.URLError) as exc:
            error = f"{type(exc).__name__}: {exc}"
        delay = min(self.config.retry_max, self.config.retry_initial * (2 ** min(item.attempts, 30)))
        self.queue.mark_retry(item.item_id, error, time.time() + delay)
        self.last_error = error

    def run(self) -> None:
        while not self.stop_event.is_set():
            items = self.queue.due(limit=20)
            if not items:
                self.stop_event.wait(self.config.poll_interval)
                continue
            for item in items:
                if self.stop_event.is_set():
                    return
                self.process(item)


class Gateway:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.queue = AppendOnlyQueue(config.queue_path)
        self.forwarder = Forwarder(config, self.queue)
        self.started_at = time.time()

    def accept(self, frame: bytes) -> bytes:
        try:
            header = parse_header(frame, require_oru=False)
        except HL7Error as exc:
            return build_ack(None, "AE", str(exc))
        if (header.message_type, header.trigger_event) != ("ORU", "R01"):
            return build_ack(
                header,
                "AE",
                f"unsupported message type {header.message_type}^{header.trigger_event}; expected ORU^R01",
            )
        try:
            self.queue.enqueue(normalize_mdc(frame), header.control_id)
        except OSError as exc:
            LOG.exception("Unable to durably queue HL7 message")
            return build_ack(header, "AE", f"edge queue unavailable: {exc}")
        return build_ack(header, "AA", "accepted by durable edge queue")

    def health(self) -> dict[str, object]:
        return {
            "status": "degraded" if self.forwarder.last_error else "ok",
            "uptime_seconds": round(time.time() - self.started_at, 3),
            "pending": self.queue.pending_count,
            "last_forward_success_at": self.forwarder.last_success_at,
            "last_error": self.forwarder.last_error,
            "permanent_failures": self.forwarder.permanent_failures,
        }


class _ReusableThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def _mllp_handler(gateway: Gateway):
    class Handler(socketserver.BaseRequestHandler):
        def handle(self) -> None:
            framer = MLLPFramer(gateway.config.max_message_bytes)
            while True:
                data = self.request.recv(65536)
                if not data:
                    return
                try:
                    frames = framer.feed(data)
                except HL7Error as exc:
                    self.request.sendall(build_ack(None, "AE", str(exc)))
                    return
                for frame in frames:
                    self.request.sendall(gateway.accept(frame))

    return Handler


def _health_handler(gateway: Gateway):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
            if self.path != "/health":
                self.send_error(404)
                return
            body = json.dumps(gateway.health(), separators=(",", ":")).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            LOG.debug(format, *args)

    return Handler


def run(config: Config) -> None:
    gateway = Gateway(config)
    mllp = _ReusableThreadingTCPServer((config.mllp_host, config.mllp_port), _mllp_handler(gateway))
    health = ThreadingHTTPServer((config.health_host, config.health_port), _health_handler(gateway))
    threads = [
        threading.Thread(target=gateway.forwarder.run, name="forwarder", daemon=True),
        threading.Thread(target=mllp.serve_forever, name="mllp", daemon=True),
        threading.Thread(target=health.serve_forever, name="health", daemon=True),
    ]
    for thread in threads:
        thread.start()
    LOG.info("MLLP listening on %s:%d", config.mllp_host, config.mllp_port)
    stopped = threading.Event()

    def stop(_signum: int, _frame: object) -> None:
        stopped.set()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    stopped.wait()
    gateway.forwarder.stop_event.set()
    mllp.shutdown()
    health.shutdown()
    mllp.server_close()
    health.server_close()


if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("EDGE_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    run(Config.from_env())

