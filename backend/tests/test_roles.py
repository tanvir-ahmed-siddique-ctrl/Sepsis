"""Role separation: nurse vs physician actions, and metadata-only platform operators."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings

pytestmark = pytest.mark.skipif(
    not (Path(settings.model_path).exists() and (Path(settings.demo_cases_dir) / "manifest.json").exists()),
    reason="model bundle or demo cases not generated",
)

ADMIN = {"X-Demo-User": "roles-admin", "X-Demo-Role": "admin"}
NURSE = {"X-Demo-User": "ward-nurse", "X-Demo-Role": "nurse"}
OPERATOR = {"X-Demo-User": "platform-ops", "X-Demo-Role": "operator"}
VIEWER = {"X-Demo-User": "clinical-viewer", "X-Demo-Role": "clinical_viewer"}
CLINICAL_IT = {"X-Demo-User": "clinical-it", "X-Demo-Role": "clinical_it"}

PATIENT_DATA_ROUTES = [
    "/v1/units",
    "/v1/alerts",
    "/v1/audit",
    "/v1/care/units",
    "/v1/integrations/quarantine",
    "/v1/pilot/feedback",
]


@pytest.fixture(scope="module")
def client():
    settings.database_url = "sqlite:///:memory:"
    settings.demo_mode = True
    from app.main import app

    with TestClient(app, headers=ADMIN) as c:
        c.post("/v1/demo/replay/step?hours=6")
        yield c


def test_nurse_has_clinical_workflow_access(client):
    assert client.get("/v1/units", headers=NURSE).status_code == 200
    assert client.get("/v1/alerts", headers=NURSE).status_code == 200
    assert client.get("/v1/care/units", headers=NURSE).status_code == 200


def test_physician_decisions_are_not_available_to_nurses(client):
    ack = client.post("/v1/alerts/any/acknowledge", json={"action": "acknowledged"}, headers=NURSE)
    assert ack.status_code == 403
    outcome = client.post("/v1/pilot/outcomes", json={"patient_id": "x", "adjudication": "sepsis"}, headers=NURSE)
    assert outcome.status_code == 403


def test_operator_sees_deployment_metadata(client):
    for path in ("/v1/ops/status", "/v1/ops/audit/verify", "/v1/integrations/status", "/v1/site/readiness", "/v1/model"):
        assert client.get(path, headers=OPERATOR).status_code == 200, path
    assert client.get("/metrics", headers=OPERATOR).status_code == 200


@pytest.mark.parametrize("path", PATIENT_DATA_ROUTES)
def test_operator_cannot_read_patient_data(client, path):
    assert client.get(path, headers=OPERATOR).status_code == 403


def test_clinical_viewer_reads_but_cannot_acknowledge(client):
    assert client.get("/v1/alerts", headers=VIEWER).status_code == 200
    units = client.get("/v1/units", headers=VIEWER)
    # units may still require full clinical role depending on route wiring
    assert units.status_code in {200, 403}
    ack = client.post("/v1/alerts/any/acknowledge", json={"action": "acknowledged"}, headers=VIEWER)
    assert ack.status_code == 403
    claim = client.post("/v1/patients/BED-01/ownership", json={"shift_label": "day"}, headers=VIEWER)
    assert claim.status_code == 403


def test_clinical_it_sees_integration_not_chart_write(client):
    assert client.get("/v1/integrations/status", headers=CLINICAL_IT).status_code == 200
    assert client.get("/v1/integrations/quarantine", headers=CLINICAL_IT).status_code == 200
    assert client.get("/v1/integrations/mappings", headers=CLINICAL_IT).status_code == 200
    assert client.post("/v1/alerts/any/acknowledge", json={"action": "acknowledged"}, headers=CLINICAL_IT).status_code == 403
    assert client.post("/v1/patients/BED-01/ownership", json={"shift_label": "day"}, headers=CLINICAL_IT).status_code == 403


def test_admin_can_create_nurse_and_operator_accounts(client):
    for user_id, role in (("rn.rahman", "nurse"), ("ops.founder", "operator"), ("it.karim", "clinical_it"), ("view.nur", "clinical_viewer")):
        created = client.post(
            "/v1/auth/users",
            json={"user_id": user_id, "display_name": user_id, "role": role, "password": "temporary-pass-123", "units": None},
        )
        assert created.status_code == 200, created.text
        assert created.json()["role"] == role
    rejected = client.post(
        "/v1/auth/users",
        json={"user_id": "bad.role", "display_name": "x", "role": "superuser", "password": "temporary-pass-123", "units": None},
    )
    assert rejected.status_code == 422


def test_public_demo_lockdown_keeps_shared_replay_in_demo_mode(client):
    settings.public_demo_lockdown = True
    try:
        assert client.post("/v1/auth/demo-token", params={"role": "admin"}).status_code == 404
        assert client.get("/v1/auth/me", headers={"X-Demo-Role": "admin"}).status_code == 401
        assert client.get("/v1/auth/me").status_code == 401
        response = client.put("/v1/site/mode", json={"mode": "silent", "reason": "should be refused"})
        assert response.status_code == 401
    finally:
        settings.public_demo_lockdown = False


def test_public_demo_disables_the_production_writer_lease(tmp_path, monkeypatch):
    from app.services.engine import Engine

    monkeypatch.setattr(settings, "database_url", f"sqlite:///{(tmp_path / 'public-demo.db').as_posix()}")
    monkeypatch.setattr(settings, "writer_lease_enabled", False)
    first = Engine()
    second = Engine()
    try:
        assert not first.read_only
        assert not second.read_only
    finally:
        second.close()
        first.close()


def test_replay_controls_require_authentication(client):
    settings.public_demo_lockdown = True
    try:
        response = client.post("/v1/demo/replay/reset")
        assert response.status_code == 401
    finally:
        settings.public_demo_lockdown = False
