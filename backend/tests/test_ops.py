"""Operations: Prometheus metrics, audit verification, backup/restore, credential tooling."""

from __future__ import annotations

import gzip
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import IntegrationKey, settings
from app.observability import verify_audit_chain

pytestmark = pytest.mark.skipif(
    not (Path(settings.model_path).exists() and (Path(settings.demo_cases_dir) / "manifest.json").exists()),
    reason="model bundle or demo cases not generated",
)

ADMIN = {"X-Demo-User": "ops-admin", "X-Demo-Role": "admin"}
CLINICIAN = {"X-Demo-User": "bedside-rn", "X-Demo-Role": "clinician"}


@pytest.fixture(scope="module")
def client():
    settings.database_url = "sqlite:///:memory:"
    settings.demo_mode = True
    from app.main import app

    with TestClient(app, headers=ADMIN) as c:
        c.post("/v1/demo/replay/step?hours=6")
        yield c


def test_prometheus_metrics_require_admin_or_token(client, monkeypatch):
    body = client.get("/metrics")
    assert body.status_code == 200
    text = body.text
    for name in ("predictrx_http_requests_total", "predictrx_inference_total", "predictrx_audit_chain_valid 1",
                 "predictrx_feed_circuit_open", "predictrx_read_only 0", "predictrx_encounters{source=\"replay\"}"):
        assert name in text, name
    assert client.get("/metrics", headers=CLINICIAN).status_code == 403
    monkeypatch.setattr(settings, "metrics_token", "scrape-token-123")
    scraped = client.get("/metrics", headers={"Authorization": "Bearer scrape-token-123", "X-Demo-Role": "", "X-Demo-User": ""})
    assert scraped.status_code == 200
    monkeypatch.setattr(settings, "demo_mode", False)
    assert client.get("/metrics", headers={"Authorization": "Bearer wrong", "X-Demo-Role": "", "X-Demo-User": ""}).status_code == 401


def test_ops_status_and_audit_verification(client):
    status = client.get("/v1/ops/status").json()
    assert status["writer"]["read_only"] is False
    assert status["writer"]["lease"]["holder"] == status["writer"]["this_instance"]
    assert status["model"]["frozen"] is True and len(status["model"]["sha256"]) == 64
    assert status["audit"]["linkage_valid"] and status["audit"]["content_hash_mismatches"] == 0
    assert client.get("/v1/ops/status", headers=CLINICIAN).status_code == 403
    verified = client.get("/v1/ops/audit/verify").json()
    assert verified["events_verified"] >= status["audit"]["events_verified"]


def test_audit_tampering_is_detected(client):
    from app.services.engine import get_engine

    audit = [dict(event) for event in get_engine().audit]
    assert verify_audit_chain(audit)["content_hash_mismatches"] == 0
    target = next(index for index, event in enumerate(audit) if event["event"] == "replay_reset")
    audit[target]["event"] = "replay_reset_forged"
    tampered = verify_audit_chain(audit)
    assert tampered["content_hash_mismatches"] == 1 and tampered["first_content_mismatches"] == [target]
    removed = audit[:target] + audit[target + 1:]
    assert not verify_audit_chain(removed)["linkage_valid"]


def test_backup_restore_round_trip(tmp_path, monkeypatch):
    from app import ops_cli
    from app.schemas import ObservationIn
    from app.services.engine import Engine

    source_url = f"sqlite:///{(tmp_path / 'source.db').as_posix()}"
    target_url = f"sqlite:///{(tmp_path / 'target.db').as_posix()}"
    monkeypatch.setattr(settings, "database_url", source_url)
    engine = Engine()
    t0 = datetime(2026, 7, 1, tzinfo=timezone.utc)
    engine.ingest([
        ObservationIn(patient_id="backup-a", encounter_id="e1", unit_id="icu-b", timestamp=t0 + timedelta(hours=h),
                      code=code, value=value)
        for h in range(6) for code, value in (("HR", 95), ("MAP", 70), ("SBP", 110), ("O2Sat", 95))
    ])
    archive = tmp_path / "backup.json.gz"
    with pytest.raises(SystemExit, match="holds the lease"):
        ops_cli.backup(source_url, archive)
        ops_cli.restore(source_url, archive, force=True)
    engine.close()

    summary = ops_cli.backup(source_url, archive)
    assert summary["counts"]["prediction_records"] == 6 and summary["counts"]["audit_events"] > 0
    assert summary["active_writer_at_backup"] is None
    result = ops_cli.restore(target_url, archive)
    assert result["audit"]["linkage_valid"] and result["audit"]["content_hash_mismatches"] == 0
    with pytest.raises(SystemExit, match="already has"):
        ops_cli.restore(target_url, archive)
    assert ops_cli.restore(target_url, archive, force=True)["counts"] == summary["counts"]

    monkeypatch.setattr(settings, "database_url", target_url)
    restored = Engine()
    try:
        assert not restored.read_only
        patient = restored.resolve_patient("backup-a--e1")
        assert patient is not None and patient.unit_id == "icu-b" and len(patient.predictions) == 6
        assert ops_cli.verify(target_url)["linkage_valid"]
    finally:
        restored.close()

    payload = json.loads(gzip.decompress(archive.read_bytes()))
    payload["tables"]["outcome_records"].append({"outcome_id": "forged"})
    forged = tmp_path / "forged.json"
    forged.write_text(json.dumps(payload))
    with pytest.raises(SystemExit, match="checksum"):
        ops_cli.restore(f"sqlite:///{(tmp_path / 'other.db').as_posix()}", forged)


def test_new_integration_key_round_trips_through_auth(client, monkeypatch, capsys):
    from app import ops_cli

    assert ops_cli.main(["new-integration-key", "--key-id", "lab-feed", "--units", "icu-x", "--scopes", "ingest:json"]) == 0
    generated = json.loads(capsys.readouterr().out)
    header = generated["give_to_interface_engine"].split(": ", 1)[1]
    entry = generated["add_to_INTEGRATION_API_KEYS"]
    assert entry["sha256"] == hashlib.sha256(header.split(".", 1)[1].encode()).hexdigest()
    monkeypatch.setattr(settings, "integration_api_keys", [IntegrationKey(**entry)])
    response = client.post(
        "/v1/observations/batch",
        headers={"X-Integration-Key": header, "X-Demo-Role": "", "X-Demo-User": ""},
        json={"observations": [{"patient_id": "lab-1", "encounter_id": "e", "unit_id": "icu-x",
                                "timestamp": "2026-07-02T00:00:00+00:00", "code": "Lactate", "value": 2.1}]},
    )
    assert response.status_code == 200, response.text


def test_check_config_flags_unsafe_settings(monkeypatch, capsys):
    from app import ops_cli

    monkeypatch.setattr(settings, "demo_mode", False)
    assert ops_cli.main(["check-config"]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["problems"] and report["production_security_ready"] is False
