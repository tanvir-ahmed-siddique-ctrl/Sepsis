"""Account authority and metadata tenancy are independent of the hospital API."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from cryptography.fernet import Fernet

SPEC = importlib.util.spec_from_file_location("account_service", Path(__file__).with_name("account_service.py"))
sys.path.insert(0, str(Path(__file__).parent))
assert SPEC and SPEC.loader
account_service = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(account_service)


def login(client: TestClient, email: str, password: str) -> dict:
    response = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def test_customer_tenant_isolation_and_vendor_boundary(tmp_path):
    app = account_service.create_app(str(tmp_path / "accounts.db"))
    store = app.state.store
    store.create_vendor("vendor@example.test", "Vendor Operator", "vendor-password-123")
    client = TestClient(app)
    vendor = login(client, "vendor@example.test", "vendor-password-123")
    for org in ("hospital-a", "hospital-b"):
        assert client.post("/v1/vendor/organizations", headers=vendor, json={"organization_id": org, "name": org}).status_code == 200
        assert client.post("/v1/vendor/sites", headers=vendor, json={"organization_id": org, "site_id": org + "-icu", "name": "ICU"}).status_code == 200
        assert client.post("/v1/vendor/customers", headers=vendor, json={"organization_id": org, "email": org + "@example.test", "display_name": org, "password": "customer-password-123"}).status_code == 200
    a = login(client, "hospital-a@example.test", "customer-password-123")
    b = login(client, "hospital-b@example.test", "customer-password-123")
    assert client.post("/v1/tickets", headers=a, json={"site_id": "hospital-a-icu", "issue_code": "feed_unavailable", "severity": "urgent"}).status_code == 403
    changed = client.post("/v1/auth/change-password", headers=a, json={"current_password": "customer-password-123", "new_password": "new-customer-password-123"})
    assert changed.status_code == 200
    assert client.get("/v1/auth/me", headers=a).status_code == 401
    a = login(client, "hospital-a@example.test", "new-customer-password-123")
    assert [x["id"] for x in client.get("/v1/organizations", headers=a).json()["organizations"]] == ["hospital-a"]
    assert [x["id"] for x in client.get("/v1/sites", headers=b).json()["sites"]] == ["hospital-b-icu"]
    assert client.post("/v1/tickets", headers=a, json={"site_id": "hospital-b-icu", "issue_code": "feed_unavailable", "severity": "urgent"}).status_code == 404
    opened = client.post("/v1/tickets", headers=a, json={"site_id": "hospital-a-icu", "issue_code": "feed_unavailable", "severity": "urgent"})
    assert opened.status_code == 200
    ticket_id = opened.json()["id"]
    assert client.get("/v1/tickets", headers=b).json()["tickets"] == []
    assert client.patch(f"/v1/tickets/{ticket_id}", headers=a, json={"status": "resolved"}).status_code == 403
    assert client.patch(f"/v1/tickets/{ticket_id}", headers=vendor, json={"status": "acknowledged"}).status_code == 200
    assert client.get("/v1/tickets", headers=a).json()["tickets"][0]["status"] == "acknowledged"
    assert client.get("/v1/auth/me", headers=a).json()["workspaces"] == [{"id": "customer", "path": "/portal"}]
    asset = client.post("/v1/vendor/assets", headers=vendor, json={"site_id": "hospital-a-icu", "asset_tag": "EDGE-A-001", "kind": "edge_appliance", "model": "Approved server"})
    assert asset.status_code == 200
    assert len(client.get("/v1/assets", headers=a).json()["assets"]) == 1
    assert client.get("/v1/assets", headers=b).json()["assets"] == []
    assert client.post("/v1/vendor/assets", headers=a, json={"site_id": "hospital-a-icu", "asset_tag": "EDGE-A-002", "kind": "edge_appliance", "model": "Approved server"}).status_code == 403
    task = client.post("/v1/vendor/compliance-tasks", headers=vendor, json={"site_id": "hospital-a-icu", "task_type": "pilot_protocol", "owner": "External counsel"})
    assert task.status_code == 200
    task_id = task.json()["id"]
    assert client.patch(f"/v1/vendor/compliance-tasks/{task_id}", headers=vendor, json={"status": "approved"}).status_code == 422
    assert client.patch(f"/v1/vendor/compliance-tasks/{task_id}", headers=vendor, json={"status": "approved", "evidence_ref": "DOC-APPROVAL-001"}).status_code == 200
    assert len(client.get("/v1/compliance-tasks", headers=a).json()["tasks"]) == 1
    assert client.get("/v1/compliance-tasks", headers=b).json()["tasks"] == []
    assert client.patch(f"/v1/vendor/compliance-tasks/{task_id}", headers=a, json={"status": "rejected"}).status_code == 403


def test_session_revocation_and_no_clinical_routes(tmp_path):
    app = account_service.create_app(str(tmp_path / "accounts.db"))
    app.state.store.create_vendor("vendor@example.test", "Vendor Operator", "vendor-password-123")
    client = TestClient(app)
    token = login(client, "vendor@example.test", "vendor-password-123")
    assert client.get("/v1/patients", headers=token).status_code == 404
    assert client.post("/v1/auth/logout", headers=token).status_code == 200
    assert client.get("/v1/auth/me", headers=token).status_code == 401
    assert app.state.store.audit_integrity() is True
    app.state.store.db.execute("UPDATE audit_events SET action='tampered' WHERE id=1")
    app.state.store.db.commit()
    assert app.state.store.audit_integrity() is False


def test_evaluation_account_is_seeded_only_in_evaluation_runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("EVALUATION_RUNTIME", "true")
    monkeypatch.setenv("EVALUATION_ACCOUNT_PASSWORD", "evaluation-secret-123")
    client = TestClient(account_service.create_app(str(tmp_path / "evaluation.db")))
    token = login(client, "evaluator@auralis.invalid", "evaluation-secret-123")
    identity = client.get("/v1/auth/me", headers=token).json()
    assert identity["evaluation"] is True
    assert [item["id"] for item in identity["workspaces"]] == ["vendor", "customer"]
    assert [item["id"] for item in client.get("/v1/organizations", headers=token).json()["organizations"]] == ["evaluation-hospital"]
    assert client.post("/v1/vendor/organizations", headers=token, json={"organization_id": "real-hospital", "name": "Should fail"}).status_code == 403
    assert client.post("/v1/vendor/licences/not-real/issue", headers=token).status_code == 403
    assert client.post("/v1/vendor/customers", headers=token, json={"organization_id": "evaluation-hospital", "email": "reviewer@auralis.invalid", "display_name": "Reviewer", "password": "reviewer-password-123"}).status_code == 200
    reviewer = login(client, "reviewer@auralis.invalid", "reviewer-password-123")
    reviewer_identity = client.get("/v1/auth/me", headers=reviewer).json()
    assert reviewer_identity["evaluation"] is False
    assert reviewer_identity["workspaces"] == [{"id": "customer", "path": "/portal"}]


def test_vendor_mfa_requires_encrypted_totp_when_configured(tmp_path, monkeypatch):
    monkeypatch.setenv("ACCOUNT_REQUIRE_MFA", "true")
    monkeypatch.setenv("ACCOUNT_MFA_KEY", Fernet.generate_key().decode())
    app = account_service.create_app(str(tmp_path / "mfa.db"))
    uri = app.state.store.create_vendor("root@example.test", "Root", "root-password-123")
    assert uri and "secret=" in uri
    secret = uri.split("secret=", 1)[1].split("&", 1)[0]
    row = app.state.store.db.execute("SELECT mfa_secret FROM users WHERE email='root@example.test'").fetchone()
    assert secret not in row["mfa_secret"]
    client = TestClient(app)
    assert client.post("/v1/auth/login", json={"email": "root@example.test", "password": "root-password-123"}).status_code == 401
    assert client.post("/v1/auth/login", json={"email": "root@example.test", "password": "root-password-123", "totp_code": "000000"}).status_code == 401
    assert client.post("/v1/auth/login", json={"email": "root@example.test", "password": "root-password-123", "totp_code": account_service.totp_code(secret)}).status_code == 200


def test_evaluation_and_production_credentials_are_not_interchangeable(tmp_path, monkeypatch):
    monkeypatch.delenv("EVALUATION_RUNTIME", raising=False)
    production = account_service.create_app(str(tmp_path / "production.db"))
    production.state.store.create_vendor("root@example.test", "Root", "root-password-123")
    monkeypatch.setenv("EVALUATION_RUNTIME", "true")
    monkeypatch.setenv("EVALUATION_ACCOUNT_PASSWORD", "evaluation-secret-123")
    evaluation = account_service.create_app(str(tmp_path / "evaluation.db"))
    eval_client = TestClient(evaluation)
    assert eval_client.post("/v1/auth/login", json={"email": "root@example.test", "password": "root-password-123"}).status_code == 401
    assert login(eval_client, "evaluator@auralis.invalid", "evaluation-secret-123")
    monkeypatch.delenv("EVALUATION_RUNTIME", raising=False)
    prod_client = TestClient(production)
    assert prod_client.post("/v1/auth/login", json={"email": "evaluator@auralis.invalid", "password": "evaluation-secret-123"}).status_code == 401
    assert login(prod_client, "root@example.test", "root-password-123")


def test_multiple_memberships_revocation_and_disable(tmp_path, monkeypatch):
    monkeypatch.delenv("EVALUATION_RUNTIME", raising=False)
    app = account_service.create_app(str(tmp_path / "accounts.db"))
    app.state.store.create_vendor("root@example.test", "Root", "root-password-123")
    client = TestClient(app)
    root = login(client, "root@example.test", "root-password-123")
    for name in ("hospital-a", "hospital-b"):
        assert client.post("/v1/vendor/organizations", headers=root, json={"organization_id": name, "name": name}).status_code == 200
        assert client.post("/v1/vendor/sites", headers=root, json={"organization_id": name, "site_id": name + "-icu", "name": "ICU"}).status_code == 200
    assert client.post("/v1/vendor/assets", headers=root, json={"site_id": "hospital-a-icu", "asset_tag": "EDGE-A-RESTRICTED", "kind": "edge_appliance", "model": "Local gateway"}).status_code == 200
    assert client.post("/v1/vendor/compliance-tasks", headers=root, json={"site_id": "hospital-a-icu", "task_type": "pilot_protocol", "owner": "External counsel"}).status_code == 200
    created = client.post("/v1/vendor/customers", headers=root, json={"organization_id": "hospital-a", "email": "customer@example.test", "display_name": "Customer", "password": "customer-password-123", "role": "customer_viewer"}).json()
    customer_id = created["user_id"]
    customer = login(client, "customer@example.test", "customer-password-123")
    assert client.post(f"/v1/vendor/accounts/{customer_id}/memberships", headers=customer, json={"organization_id": "hospital-b", "role": "customer_owner", "reason": "Cross-site contract"}).status_code == 403
    assert client.post(f"/v1/vendor/accounts/{customer_id}/memberships", headers=root, json={"organization_id": "hospital-b", "role": "technical_contact", "reason": "Group account approved"}).status_code == 200
    assert client.get("/v1/auth/me", headers=customer).status_code == 401
    customer = login(client, "customer@example.test", "customer-password-123")
    assert sorted(client.get("/v1/auth/me", headers=customer).json()["organization_ids"]) == ["hospital-a", "hospital-b"]
    assert client.get("/v1/auth/me", headers=customer).json()["organization_roles"]["hospital-b"] == "technical_contact"
    assert client.post("/v1/auth/change-password", headers=customer, json={"current_password": "customer-password-123", "new_password": "customer-new-password-123"}).status_code == 200
    customer = login(client, "customer@example.test", "customer-new-password-123")
    assert client.post("/v1/tickets", headers=customer, json={"site_id": "hospital-a-icu", "issue_code": "feed_unavailable", "severity": "routine"}).status_code == 403
    assert client.post("/v1/tickets", headers=customer, json={"site_id": "hospital-b-icu", "issue_code": "feed_unavailable", "severity": "routine"}).status_code == 200
    assert len(client.get("/v1/tickets", headers=customer).json()["tickets"]) == 1
    assert client.patch(f"/v1/vendor/accounts/{customer_id}/memberships/hospital-b", headers=root, json={"organization_id": "hospital-b", "role": "customer_viewer", "reason": "Access review"}).status_code == 200
    assert client.get("/v1/auth/me", headers=customer).status_code == 401
    customer = login(client, "customer@example.test", "customer-new-password-123")
    assert client.post("/v1/tickets", headers=customer, json={"site_id": "hospital-b-icu", "issue_code": "feed_unavailable", "severity": "routine"}).status_code == 403
    assert client.get("/v1/tickets", headers=customer).json()["tickets"] == []
    assert client.get("/v1/assets", headers=customer).json()["assets"] == []
    assert client.get("/v1/compliance-tasks", headers=customer).json()["tasks"] == []
    assert client.delete(f"/v1/vendor/accounts/{customer_id}/memberships/hospital-a?reason=Scope+ended", headers=root).status_code == 200
    assert client.get("/v1/auth/me", headers=customer).status_code == 401
    customer = login(client, "customer@example.test", "customer-new-password-123")
    assert client.get("/v1/auth/me", headers=customer).json()["organization_ids"] == ["hospital-b"]
    assert client.patch(f"/v1/vendor/accounts/{customer_id}/state", headers=root, json={"disabled": True, "reason": "Institutional request"}).status_code == 200
    assert client.get("/v1/auth/me", headers=customer).status_code == 401
    assert client.post("/v1/auth/login", json={"email": "customer@example.test", "password": "customer-new-password-123"}).status_code == 401
    assert app.state.store.audit_integrity() is True


def test_customer_invitation_requires_acceptance_and_expires(tmp_path, monkeypatch):
    monkeypatch.delenv("EVALUATION_RUNTIME", raising=False)
    app = account_service.create_app(str(tmp_path / "accounts.db"))
    app.state.store.create_vendor("root@example.test", "Root", "root-password-123")
    client = TestClient(app)
    root = login(client, "root@example.test", "root-password-123")
    assert client.post("/v1/vendor/organizations", headers=root, json={"organization_id": "hospital-a", "name": "Hospital A"}).status_code == 200
    payload = {"organization_id": "hospital-a", "email": "invitee@example.test", "display_name": "Invited contact", "role": "technical_contact", "reason": "Institutional contact approved"}
    invitation = client.post("/v1/vendor/customer-invitations", headers=root, json=payload)
    assert invitation.status_code == 200
    secret = invitation.json()["token"]
    assert client.post("/v1/auth/login", json={"email": payload["email"], "password": "contact-password-123"}).status_code == 401
    assert client.post("/v1/auth/accept-invitation", json={"token": "wrong" * 10, "password": "contact-password-123"}).status_code == 400
    assert client.post("/v1/auth/accept-invitation", json={"token": secret, "password": "contact-password-123"}).json()["activated"] is True
    assert client.post("/v1/auth/accept-invitation", json={"token": secret, "password": "other-password-123"}).status_code == 400
    contact = login(client, "invitee@example.test", "contact-password-123")
    assert client.get("/v1/auth/me", headers=contact).json()["organization_roles"] == {"hospital-a": "technical_contact"}
    second = client.post("/v1/vendor/customer-invitations", headers=root, json={**payload, "email": "expired@example.test"}).json()
    app.state.store.db.execute("UPDATE customer_invitations SET expires_at='2000-01-01T00:00:00+00:00' WHERE id=?", (second["invitation_id"],))
    app.state.store.db.commit()
    assert client.post("/v1/auth/accept-invitation", json={"token": second["token"], "password": "contact-password-123"}).status_code == 400
    assert app.state.store.audit_integrity() is True


def test_permission_matrix_customer_invite_and_approval_workflow(tmp_path, monkeypatch):
    monkeypatch.delenv("EVALUATION_RUNTIME", raising=False)
    app = account_service.create_app(str(tmp_path / "accounts.db"))
    app.state.store.create_vendor("root@example.test", "Root", "root-password-123")
    client = TestClient(app)
    root = login(client, "root@example.test", "root-password-123")
    matrix = client.get("/v1/permissions/matrix", headers=root)
    assert matrix.status_code == 200
    body = matrix.json()
    assert "vendor.org.create" in body["permissions"]
    assert "customer_owner" in body["customer_roles"]
    assert "vendor.org.create" in body["caller"]["permissions"]

    staff = client.post(
        "/v1/vendor/staff",
        headers=root,
        json={"email": "security@example.test", "display_name": "Security", "password": "security-password-123", "role": "security_compliance"},
    )
    assert staff.status_code == 200
    security = login(client, "security@example.test", "security-password-123")
    assert client.get("/v1/permissions/matrix", headers=security).status_code == 200
    assert client.post("/v1/vendor/organizations", headers=security, json={"organization_id": "hospital-a", "name": "Hospital A"}).status_code == 403

    assert client.post("/v1/vendor/organizations", headers=root, json={"organization_id": "hospital-a", "name": "Hospital A"}).status_code == 200
    assert client.post("/v1/vendor/sites", headers=root, json={"organization_id": "hospital-a", "site_id": "hospital-a-icu", "name": "ICU"}).status_code == 200
    owner = client.post(
        "/v1/vendor/customers",
        headers=root,
        json={"organization_id": "hospital-a", "email": "owner@example.test", "display_name": "Owner", "password": "owner-password-123", "role": "customer_owner"},
    )
    assert owner.status_code == 200
    owner_headers = login(client, "owner@example.test", "owner-password-123")
    assert client.post("/v1/auth/change-password", headers=owner_headers, json={"current_password": "owner-password-123", "new_password": "owner-new-password-123"}).status_code == 200
    owner_headers = login(client, "owner@example.test", "owner-new-password-123")

    invite = client.post(
        "/v1/portal/organizations/hospital-a/invitations",
        headers=owner_headers,
        json={"organization_id": "hospital-a", "email": "nurse-admin@example.test", "display_name": "Tech Contact", "role": "technical_contact", "reason": "Hospital IT contact"},
    )
    assert invite.status_code == 200
    token = invite.json()["token"]
    assert client.post("/v1/auth/accept-invitation", json={"token": token, "password": "tech-password-123"}).status_code == 200
    tech = login(client, "nurse-admin@example.test", "tech-password-123")
    assert client.get("/v1/portal/organizations/hospital-a/members", headers=tech).json()["members"]
    assert client.post(
        "/v1/portal/organizations/hospital-a/invitations",
        headers=tech,
        json={"organization_id": "hospital-a", "email": "other@example.test", "display_name": "Other", "role": "customer_viewer", "reason": "Should fail"},
    ).status_code == 403

    approval = client.post(
        "/v1/vendor/approvals",
        headers=root,
        json={
            "kind": "customer_role_change",
            "payload": {"account_id": owner.json()["user_id"], "organization_id": "hospital-a", "role": "procurement_finance"},
            "reason": "Finance handover",
        },
    )
    assert approval.status_code == 200
    approval_id = approval.json()["id"]
    assert client.patch(f"/v1/vendor/approvals/{approval_id}", headers=root, json={"status": "approved", "reason": "Root self-decision allowed"}).status_code == 200
    assert client.get("/v1/auth/me", headers=owner_headers).status_code == 401
    owner_headers = login(client, "owner@example.test", "owner-new-password-123")
    assert client.get("/v1/auth/me", headers=owner_headers).json()["organization_roles"]["hospital-a"] == "procurement_finance"
    assert app.state.store.audit_integrity() is True
