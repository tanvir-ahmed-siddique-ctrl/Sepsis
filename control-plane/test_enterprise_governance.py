"""Enterprise governance: SLA, licence entitlement, retention, assets, CAPA/QMS."""

from __future__ import annotations

import base64
import importlib.util
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent))
spec = importlib.util.spec_from_file_location("account_service_gov", Path(__file__).with_name("account_service.py"))
assert spec and spec.loader
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)
from commercial_domain import simple_pdf


def auth(client, email, password):
    response = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def bootstrap(tmp_path, monkeypatch):
    monkeypatch.delenv("EVALUATION_RUNTIME", raising=False)
    monkeypatch.setenv("ACCOUNT_DOCUMENT_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr("document_domain.scanner_clean", lambda _: True)
    app = service.create_app(str(tmp_path / "gov.db"))
    app.state.store.create_vendor("root@example.test", "Root", "root-password-123")
    client = TestClient(app)
    root = auth(client, "root@example.test", "root-password-123")
    assert client.post("/v1/vendor/organizations", headers=root, json={"organization_id": "hospital-a", "name": "Hospital A"}).status_code == 200
    assert client.post("/v1/vendor/sites", headers=root, json={"organization_id": "hospital-a", "site_id": "hospital-a-icu", "name": "ICU"}).status_code == 200
    assert client.post("/v1/vendor/customers", headers=root, json={"organization_id": "hospital-a", "email": "hospital-a@example.test", "display_name": "Hospital A", "password": "customer-password-123"}).status_code == 200
    customer = auth(client, "hospital-a@example.test", "customer-password-123")
    assert client.post("/v1/auth/change-password", headers=customer, json={"current_password": "customer-password-123", "new_password": "customer-new-password-123"}).status_code == 200
    customer = auth(client, "hospital-a@example.test", "customer-new-password-123")
    return app, client, root, customer


def test_ticket_sla_clock_and_escalation(tmp_path, monkeypatch):
    app, client, root, customer = bootstrap(tmp_path, monkeypatch)
    plan = client.post(
        "/v1/vendor/support-plans",
        headers=root,
        json={
            "site_id": "hospital-a-icu",
            "scope": "Approved edge node only",
            "support_hours": "Business hours",
            "response_target_minutes": 30,
            "onsite_visits_included": 0,
            "escalation_contact_role": "Hospital IT",
            "exclusions": "HIS issues",
        },
    )
    assert plan.status_code == 200, plan.text
    opened = client.post("/v1/tickets", headers=customer, json={"site_id": "hospital-a-icu", "issue_code": "feed_unavailable", "severity": "urgent"})
    assert opened.status_code == 200, opened.text
    body = opened.json()
    assert body["sla_target_minutes"] == 30
    assert body["support_plan_id"] == plan.json()["id"]
    assert body["sla_due_at"]
    ticket_id = body["id"]
    # Force breach by backdating SLA due.
    with app.state.store.lock:
        past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        app.state.store.db.execute("UPDATE tickets SET sla_due_at=? WHERE id=?", (past, ticket_id))
        app.state.store.db.commit()
    listed = client.get("/v1/tickets", headers=customer).json()["tickets"][0]
    assert listed["sla_breached"] is True
    breaches = client.get("/v1/tickets/sla-breaches", headers=root).json()["tickets"]
    assert any(item["id"] == ticket_id for item in breaches)
    late = client.patch(f"/v1/tickets/{ticket_id}", headers=root, json={"status": "acknowledged", "assigned_to": "duty-engineer", "escalate": True, "reason": "Customer waiting"})
    assert late.status_code == 200, late.text
    assert late.json()["first_response_at"]
    assert late.json()["escalation_level"] == 1
    assert late.json()["sla_breached"] is True
    assert late.json()["assigned_to"] == "duty-engineer"


def test_licence_revoke_invalidates_entitlement(tmp_path, monkeypatch):
    monkeypatch.delenv("EVALUATION_RUNTIME", raising=False)
    monkeypatch.setenv("ACCOUNT_DOCUMENT_KEY", Fernet.generate_key().decode())
    signer = Ed25519PrivateKey.generate()
    private = signer.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    public = signer.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    monkeypatch.setenv("ACCOUNT_LICENCE_PRIVATE_KEY", base64.b64encode(private).decode())
    monkeypatch.setenv("ACCOUNT_LICENCE_KEY_ID", "gov-key")
    app = service.create_app(str(tmp_path / "licence.db"))
    app.state.store.create_vendor("root@example.test", "Root", "root-password-123")
    client = TestClient(app)
    root = auth(client, "root@example.test", "root-password-123")
    for path, payload in (
        ("/v1/vendor/organizations", {"organization_id": "hospital-a", "name": "Hospital A"}),
        ("/v1/vendor/sites", {"organization_id": "hospital-a", "site_id": "hospital-a-icu", "name": "ICU"}),
        ("/v1/vendor/customers", {"organization_id": "hospital-a", "email": "hospital-a@example.test", "display_name": "Hospital A", "password": "customer-password-123"}),
        ("/v1/vendor/staff", {"email": "finance@example.test", "display_name": "Finance", "role": "finance_legal", "password": "finance-password-123"}),
    ):
        assert client.post(path, headers=root, json=payload).status_code == 200, path
    finance = auth(client, "finance@example.test", "finance-password-123")
    customer = auth(client, "hospital-a@example.test", "customer-password-123")
    assert client.post("/v1/auth/change-password", headers=customer, json={"current_password": "customer-password-123", "new_password": "customer-new-password-123"}).status_code == 200
    customer = auth(client, "hospital-a@example.test", "customer-new-password-123")
    quote = client.post(
        "/v1/vendor/quotes",
        headers=finance,
        json={
            "site_id": "hospital-a-icu",
            "currency": "BDT",
            "valid_until": "2027-12-01",
            "assumptions": "Local edge only",
            "exclusions": "No HIS rewrite",
            "lines": [{"category": "licence", "description": "ICU module", "quantity": 1, "unit_minor": 10000, "discount_minor": 0, "tax_basis_points": 0}],
        },
    )
    assert quote.status_code == 200, quote.text
    quote_id = quote.json()["id"]
    for status, reason in (("internal_review", "Review"), ("issued", "Issue"), ("accepted", "Accepted")):
        assert client.patch(f"/v1/vendor/quotes/{quote_id}", headers=finance, json={"status": status, "reason": reason}).status_code == 200
    contract = client.post(
        "/v1/vendor/contracts",
        headers=finance,
        json={"site_id": "hospital-a-icu", "quote_id": quote_id, "starts_on": "2027-01-01", "ends_on": "2028-01-01", "notice_days": 30, "document_ref": "DOC-1", "scope": "ICU readiness"},
    )
    assert contract.status_code == 200, contract.text
    contract_id = contract.json()["id"]
    for status, reason in (("under_review", "Legal"), ("signed", "Signed")):
        assert client.patch(f"/v1/vendor/contracts/{contract_id}", headers=finance, json={"status": status, "reason": reason}).status_code == 200
    licence = client.post(
        "/v1/vendor/licences",
        headers=root,
        json={"contract_id": contract_id, "modules": ["icu_risk"], "unit_limit": 1, "bed_limit": 24, "support_tier": "standard", "effective_on": "2027-01-01", "expires_on": "2028-01-01"},
    )
    assert licence.status_code == 200
    licence_id = licence.json()["id"]
    issued = client.post(f"/v1/vendor/licences/{licence_id}/issue", headers=root)
    assert issued.status_code == 200, issued.text
    package = client.get(f"/v1/licences/{licence_id}/package", headers=customer).json()["package"]
    assert package["claims"]["entitlement_status"] == "active"
    revoked = client.patch(f"/v1/vendor/licences/{licence_id}/entitlement", headers=root, json={"entitlement_status": "revoked", "reason": "Contract terminated"})
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["entitlement_status"] == "revoked"
    assert client.get(f"/v1/licences/{licence_id}/package", headers=customer).status_code == 409
    invalidation_package = revoked.json()["package"]
    sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))
    from app.core.config import settings
    from app.licensing import status, verify_package

    monkeypatch.setattr(settings, "licence_public_keys_json", json.dumps({"gov-key": base64.b64encode(public).decode()}))
    assert verify_package(invalidation_package, "hospital-a-icu")["entitlement_status"] == "revoked"
    assert status(invalidation_package, "hospital-a-icu")["activation_eligible"] is False
    assert status(invalidation_package, "hospital-a-icu")["status"] == "revoked"
    assert len(client.get(f"/v1/licences/{licence_id}/invalidations", headers=root).json()["invalidations"]) == 1
    assert client.patch(f"/v1/vendor/licences/{licence_id}/entitlement", headers=root, json={"entitlement_status": "active", "reason": "Try revive"}).status_code == 409


def test_document_retention_and_destroy(tmp_path, monkeypatch):
    app, client, root, customer = bootstrap(tmp_path, monkeypatch)
    pdf = simple_pdf(["Retention policy document"])
    uploaded = client.post(
        "/v1/vendor/documents",
        headers=root,
        json={
            "organization_id": "hospital-a",
            "site_id": "hospital-a-icu",
            "document_key": "ret-001",
            "version": 1,
            "title": "Retention agreement",
            "document_type": "agreement",
            "access": "customer_visible",
            "owner_role": "Finance",
            "retention_policy": "operational",
            "retention_years": 1,
            "content_b64": base64.b64encode(pdf).decode(),
        },
    )
    assert uploaded.status_code == 200, uploaded.text
    document_id = uploaded.json()["id"]
    assert uploaded.json()["retention_until"]
    assert client.patch(f"/v1/vendor/documents/{document_id}", headers=root, json={"reason": "Approved"}).status_code == 200
    assert client.get(f"/v1/documents/{document_id}/download", headers=customer).status_code == 200
    # Force retention elapsed and destroy content.
    with app.state.store.lock:
        past = (date.today() - timedelta(days=1)).isoformat()
        app.state.store.db.execute("UPDATE documents SET retention_until=?, review_on=? WHERE id=?", (past, past, document_id))
        app.state.store.db.commit()
    due = client.get("/v1/documents/lifecycle-due", headers=root).json()["documents"]
    assert any(item["id"] == document_id for item in due)
    destroyed = client.patch(
        f"/v1/vendor/documents/{document_id}/lifecycle",
        headers=root,
        json={"lifecycle_status": "destroyed", "reason": "Retention elapsed"},
    )
    assert destroyed.status_code == 200, destroyed.text
    assert destroyed.json()["content_destroyed"] is True
    assert client.get(f"/v1/documents/{document_id}/download", headers=customer).status_code in {404, 409, 410}
    assert client.get(f"/v1/documents/{document_id}/download", headers=root).status_code == 410


def test_asset_lifecycle_transitions(tmp_path, monkeypatch):
    _, client, root, customer = bootstrap(tmp_path, monkeypatch)
    created = client.post(
        "/v1/vendor/assets",
        headers=root,
        json={
            "site_id": "hospital-a-icu",
            "asset_tag": "EDGE-LIFE-001",
            "kind": "edge_appliance",
            "model": "Approved server",
            "serial_number": "SN-1",
            "warranty_until": "2020-01-01",
            "lifecycle_state": "commissioned",
        },
    )
    assert created.status_code == 200, created.text
    asset_id = created.json()["id"]
    assets = client.get("/v1/assets", headers=customer).json()["assets"]
    assert assets[0]["warranty_expired"] is True
    assert client.patch(f"/v1/vendor/assets/{asset_id}", headers=root, json={"lifecycle_state": "in_service", "reason": "Go-live"}).status_code == 200
    assert client.patch(f"/v1/vendor/assets/{asset_id}", headers=root, json={"lifecycle_state": "disposed", "reason": "Skip"}).status_code == 409
    retired = client.patch(
        f"/v1/vendor/assets/{asset_id}",
        headers=root,
        json={"lifecycle_state": "retired", "disposition_ref": "RMA-9", "reason": "End of life"},
    )
    assert retired.status_code == 200, retired.text
    assert retired.json()["retired_at"]
    disposed = client.patch(
        f"/v1/vendor/assets/{asset_id}",
        headers=root,
        json={"lifecycle_state": "disposed", "disposition_ref": "DISP-9", "reason": "Scrapped"},
    )
    assert disposed.status_code == 200


def test_capa_and_qms_workflow(tmp_path, monkeypatch):
    _, client, root, customer = bootstrap(tmp_path, monkeypatch)
    capa = client.post(
        "/v1/vendor/capa",
        headers=root,
        json={
            "site_id": "hospital-a-icu",
            "title": "Missed backup acknowledgement",
            "severity": "high",
            "owner": "Quality lead",
            "due_on": "2027-02-01",
            "description": "Backup acknowledgement missing for two cycles",
        },
    )
    assert capa.status_code == 200, capa.text
    capa_id = capa.json()["id"]
    finding = client.post(
        "/v1/vendor/qms-findings",
        headers=root,
        json={
            "site_id": "hospital-a-icu",
            "finding_type": "process_gap",
            "description": "Backup acknowledgement not recorded",
            "severity": "moderate",
            "owner": "Quality lead",
            "due_on": "2027-01-15",
        },
    )
    assert finding.status_code == 200, finding.text
    finding_id = finding.json()["id"]
    linked = client.patch(
        f"/v1/vendor/qms-findings/{finding_id}",
        headers=root,
        json={"status": "linked_capa", "capa_id": capa_id, "reason": "Linked to CAPA"},
    )
    assert linked.status_code == 200
    assert client.patch(
        f"/v1/vendor/capa/{capa_id}",
        headers=root,
        json={"status": "closed", "reason": "Incomplete"},
    ).status_code == 422
    closed = client.patch(
        f"/v1/vendor/capa/{capa_id}",
        headers=root,
        json={
            "status": "closed",
            "root_cause": "Checklist gap",
            "corrective_action": "Add acknowledgement step",
            "preventive_action": "Quarterly drill",
            "evidence_ref": "SOP-BACKUP-2",
            "reason": "Verified",
        },
    )
    assert closed.status_code == 200
    assert client.get("/v1/capa", headers=customer).json()["records"][0]["id"] == capa_id
    assert client.get("/v1/qms-findings", headers=customer).json()["findings"][0]["capa_id"] == capa_id
