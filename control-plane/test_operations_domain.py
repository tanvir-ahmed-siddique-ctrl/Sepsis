"""Managed service records and non-destructive dual-approval offboarding."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent))
spec = importlib.util.spec_from_file_location("account_service_ops", Path(__file__).with_name("account_service.py"))
assert spec and spec.loader
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)


def auth(client, email, password):
    response = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def test_service_records_and_dual_approval(tmp_path):
    app = service.create_app(str(tmp_path / "accounts.db"))
    app.state.store.create_vendor("root@example.test", "Root", "root-password-123")
    client = TestClient(app)
    root = auth(client, "root@example.test", "root-password-123")
    for org in ("hospital-a", "hospital-b"):
        assert client.post("/v1/vendor/organizations", headers=root, json={"organization_id": org, "name": org}).status_code == 200
        assert client.post("/v1/vendor/sites", headers=root, json={"organization_id": org, "site_id": org + "-icu", "name": "ICU"}).status_code == 200
        assert client.post("/v1/vendor/customers", headers=root, json={"organization_id": org, "email": org + "@example.test", "display_name": org, "password": "customer-password-123"}).status_code == 200
    a = auth(client, "hospital-a@example.test", "customer-password-123")
    b = auth(client, "hospital-b@example.test", "customer-password-123")
    assert client.post("/v1/auth/change-password", headers=a, json={"current_password": "customer-password-123", "new_password": "customer-new-password-123"}).status_code == 200
    a = auth(client, "hospital-a@example.test", "customer-new-password-123")
    deployment = client.post("/v1/vendor/deployments", headers=root, json={"site_id": "hospital-a-icu", "environment": "hospital_local", "release_version": "prototype-1", "installation_ref": "INSTALL-001", "status": "planned"})
    assert deployment.status_code == 200, deployment.text
    assert client.get("/v1/deployments", headers=b).json()["deployments"] == []
    support = client.post("/v1/vendor/support-plans", headers=root, json={"site_id": "hospital-a-icu", "scope": "Approved edge node only", "support_hours": "Business hours by agreement", "response_target_minutes": None, "onsite_visits_included": 0, "escalation_contact_role": "Hospital IT contact", "exclusions": "Unrelated HIS issues"})
    assert support.status_code == 200, support.text
    visit = client.post("/v1/vendor/service-visits", headers=root, json={"site_id": "hospital-a-icu", "visit_on": "2027-01-20", "work_code": "backup_test", "engineer_role": "Deployment engineer", "work_summary": "Restore rehearsal", "acknowledgement_ref": "ACK-001"})
    assert visit.status_code == 200, visit.text
    training = client.post("/v1/vendor/training", headers=root, json={"site_id": "hospital-a-icu", "role_group": "nurse", "session_on": "2027-01-21", "completion_ref": "TRAIN-001", "trainer_role": "Clinical trainer"})
    assert training.status_code == 200, training.text
    assert len(client.get("/v1/service-visits", headers=a).json()["service_visits"]) == 1
    assert client.get("/v1/training", headers=b).json()["training"] == []
    request = client.post("/v1/offboarding", headers=a, json={"site_id": "hospital-a-icu", "reason": "Contract closure", "authorization_ref": "HOSPITAL-REQUEST-001"})
    assert request.status_code == 200, request.text
    request_id = request.json()["id"]
    assert client.post("/v1/offboarding", headers=b, json={"site_id": "hospital-a-icu", "reason": "Wrong tenant", "authorization_ref": "BAD-001"}).status_code == 403
    assert client.post("/v1/auth/change-password", headers=b, json={"current_password": "customer-password-123", "new_password": "customer-new-password-123"}).status_code == 200
    b = auth(client, "hospital-b@example.test", "customer-new-password-123")
    assert client.post("/v1/offboarding", headers=b, json={"site_id": "hospital-a-icu", "reason": "Wrong tenant", "authorization_ref": "BAD-001"}).status_code == 404
    assert client.post(f"/v1/vendor/offboarding/{request_id}/approve", headers=root, json={"reason": "Too early"}).status_code == 409
    for check in request.json()["required_checks"]:
        response = client.post(f"/v1/vendor/offboarding/{request_id}/checks", headers=root, json={"check": check, "evidence_ref": "EVIDENCE-" + check})
        assert response.status_code == 200, response.text
    assert client.get("/v1/offboarding", headers=b).json()["requests"] == []
    first = client.post(f"/v1/vendor/offboarding/{request_id}/approve", headers=root, json={"reason": "Checks reviewed"})
    assert first.status_code == 200 and first.json()["status"] == "awaiting_second_approval"
    assert client.post(f"/v1/vendor/offboarding/{request_id}/approve", headers=root, json={"reason": "Second attempt"}).status_code == 409
    assert client.post("/v1/vendor/staff", headers=root, json={"email": "security@example.test", "display_name": "Security", "role": "security_compliance", "password": "security-password-123"}).status_code == 200
    security = auth(client, "security@example.test", "security-password-123")
    second = client.post(f"/v1/vendor/offboarding/{request_id}/approve", headers=security, json={"reason": "Independent review"})
    assert second.status_code == 200 and second.json()["status"] == "ready_for_hospital_execution"
    assert second.json()["hospital_data_deleted"] is False
    assert client.get("/v1/sites", headers=a).json()["sites"][0]["id"] == "hospital-a-icu"
