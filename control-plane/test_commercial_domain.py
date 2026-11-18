"""Commercial lifecycle and tenant boundary tests; no clinical DB or payment provider."""

from __future__ import annotations

import importlib.util
import base64
import json
import sqlite3
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(Path(__file__).parent))
spec = importlib.util.spec_from_file_location("account_service_commercial", Path(__file__).with_name("account_service.py"))
assert spec and spec.loader
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)


def auth(client, email, password):
    response = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def post(client, path, headers, payload, expected=200):
    response = client.post(path, headers=headers, json=payload)
    assert response.status_code == expected, response.text
    return response.json()


def patch(client, path, headers, payload, expected=200):
    response = client.patch(path, headers=headers, json=payload)
    assert response.status_code == expected, response.text
    return response.json()


def test_contract_invoice_payment_and_cross_tenant(tmp_path, monkeypatch):
    app = service.create_app(str(tmp_path / "accounts.db"))
    app.state.store.create_vendor("vendor@example.test", "Vendor", "vendor-password-123")
    client = TestClient(app)
    vendor = auth(client, "vendor@example.test", "vendor-password-123")
    for org in ("hospital-a", "hospital-b"):
        post(client, "/v1/vendor/organizations", vendor, {"organization_id": org, "name": org})
        post(client, "/v1/vendor/sites", vendor, {"organization_id": org, "site_id": org + "-icu", "name": "ICU"})
        post(client, "/v1/vendor/customers", vendor, {"organization_id": org, "email": org + "@example.test", "display_name": org, "password": "customer-password-123"})
    a = auth(client, "hospital-a@example.test", "customer-password-123")
    b = auth(client, "hospital-b@example.test", "customer-password-123")
    assert client.post("/v1/renewals", headers=a, json={"contract_id": "none", "request_type": "renew", "note": "Not yet"}).status_code == 403
    assert client.post("/v1/auth/change-password", headers=a, json={"current_password": "customer-password-123", "new_password": "customer-new-password-123"}).status_code == 200
    a = auth(client, "hospital-a@example.test", "customer-new-password-123")
    line = {"category": "assessment", "description": "Site readiness", "quantity": 2, "unit_minor": 10000, "discount_minor": 1000, "tax_basis_points": 500}
    lead = post(client, "/v1/vendor/leads", vendor, {"name": "Hospital A discovery", "contact_role": "IT lead", "contact_channel": "email", "next_action": "Assess source inventory"})
    lead_id = lead["id"]
    post(client, f"/v1/vendor/leads/{lead_id}/organization", vendor, {"organization_id": "hospital-a", "reason": "Institutional identity confirmed"})
    assert client.post("/v1/vendor/assessments", headers=vendor, json={"site_id": "hospital-b-icu", "lead_id": lead_id, "maturity": "M1", "findings": "Source inventory", "decision": "go"}).status_code == 409
    assessment = post(client, "/v1/vendor/assessments", vendor, {"site_id": "hospital-a-icu", "lead_id": lead_id, "maturity": "M1", "findings": "Source inventory reviewed", "decision": "go"})
    assert client.post("/v1/vendor/quotes", headers=vendor, json={"site_id": "hospital-b-icu", "assessment_id": assessment["id"], "currency": "BDT", "valid_until": "2027-02-01", "assumptions": "One site", "exclusions": "Clinical validation", "lines": [line]}).status_code == 409
    quote = post(client, "/v1/vendor/quotes", vendor, {"site_id": "hospital-a-icu", "assessment_id": assessment["id"], "currency": "BDT", "valid_until": "2027-02-01", "assumptions": "One approved site", "exclusions": "Clinical validation", "lines": [line]})
    quote_id = quote["id"]
    assert quote["total_minor"] == 19950
    assert client.get("/v1/quotes", headers=b).json()["quotes"] == []
    assert client.get(f"/v1/quotes/{quote_id}/versions", headers=b).status_code == 404
    patch(client, f"/v1/vendor/quotes/{quote_id}", vendor, {"status": "internal_review", "reason": "Finance review"})
    revision = post(client, f"/v1/vendor/quotes/{quote_id}/revisions", vendor, {"valid_until": "2027-03-01", "assumptions": "One approved site", "exclusions": "Clinical validation", "lines": [line], "reason": "Extended validity"})
    assert revision["version"] == 2
    assert client.get(f"/v1/quotes/{quote_id}/versions", headers=a).status_code == 404
    assert [v["version"] for v in client.get(f"/v1/quotes/{quote_id}/versions", headers=vendor).json()["versions"]] == [1, 2]
    patch(client, f"/v1/vendor/quotes/{quote_id}", vendor, {"status": "internal_review", "reason": "Reviewed revision"})
    patch(client, f"/v1/vendor/quotes/{quote_id}", vendor, {"status": "issued", "reason": "Authorized issue"})
    assert [v["version"] for v in client.get(f"/v1/quotes/{quote_id}/versions", headers=a).json()["versions"]] == [2]
    assert client.get(f"/v1/quotes/{quote_id}/versions/1/pdf", headers=a).status_code == 404
    quote_pdf = client.get(f"/v1/quotes/{quote_id}/versions/2/pdf", headers=a)
    assert quote_pdf.status_code == 200 and quote_pdf.content.startswith(b"%PDF-1.4")
    assert client.get(f"/v1/quotes/{quote_id}/versions/2/pdf", headers=b).status_code == 404
    patch(client, f"/v1/vendor/quotes/{quote_id}", vendor, {"status": "accepted", "reason": "Acceptance recorded"})
    contract = post(client, "/v1/vendor/contracts", vendor, {"site_id": "hospital-a-icu", "quote_id": quote_id, "starts_on": "2027-01-01", "ends_on": "2028-01-01", "notice_days": 90, "document_ref": "SIGNED-CONTRACT-001", "scope": "Readiness and software evaluation"})
    contract_id = contract["id"]
    patch(client, f"/v1/vendor/contracts/{contract_id}", vendor, {"status": "under_review", "reason": "Institutional review"})
    patch(client, f"/v1/vendor/contracts/{contract_id}", vendor, {"status": "signed", "reason": "Signed document verified"})
    licence = post(client, "/v1/vendor/licences", vendor, {"contract_id": contract_id, "modules": ["icu_risk"], "unit_limit": 1, "bed_limit": 32, "support_tier": "standard", "effective_on": "2027-01-01", "expires_on": "2028-01-01"})
    assert licence["status"] == "pending_governance"
    assert client.post(f"/v1/vendor/licences/{licence['id']}/issue", headers=vendor).status_code == 503
    signer = Ed25519PrivateKey.generate()
    private = signer.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    public = signer.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    monkeypatch.setenv("ACCOUNT_LICENCE_PRIVATE_KEY", base64.b64encode(private).decode())
    monkeypatch.setenv("ACCOUNT_LICENCE_KEY_ID", "test-2027")
    issued = post(client, f"/v1/vendor/licences/{licence['id']}/issue", vendor, {})
    assert issued["status"] == "issued_for_site_review"
    assert client.post(f"/v1/vendor/licences/{licence['id']}/issue", headers=vendor).status_code == 409
    assert client.get(f"/v1/licences/{licence['id']}/package", headers=b).status_code == 404
    package = client.get(f"/v1/licences/{licence['id']}/package", headers=a).json()["package"]
    sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))
    from app.core.config import settings
    from app.licensing import verify_package
    monkeypatch.setattr(settings, "licence_public_keys_json", json.dumps({"test-2027": base64.b64encode(public).decode()}))
    assert verify_package(package, "hospital-a-icu")["licence_id"] == licence["id"]
    assert client.get(f"/v1/licences/{licence['id']}/package", headers=b).status_code == 404
    assert client.get(f"/v1/licences/{licence['id']}/package", headers=a).status_code == 200
    assert client.get(f"/v1/licences/{licence['id']}/package", headers=vendor).status_code == 200
    package["claims"]["bed_limit"] = 9999
    import pytest
    with pytest.raises(ValueError):
        verify_package(package, "hospital-a-icu")
    assert client.get("/v1/licences", headers=b).json()["licences"] == []
    invoice = post(client, "/v1/vendor/invoices", vendor, {"contract_id": contract_id, "quote_id": quote_id, "invoice_number": "INV-2027-001", "due_on": "2027-02-01", "currency": "BDT", "lines": [line]})
    invoice_id = invoice["id"]
    assert client.get("/v1/invoices", headers=b).json()["invoices"] == []
    post(client, "/v1/payments", a, {"invoice_id": invoice_id, "amount_minor": 5000, "paid_on": "2027-01-15", "channel": "bank_transfer", "reference": "BANK-REF-1", "evidence_ref": "RECEIPT-1"}, expected=409)
    patch(client, f"/v1/vendor/invoices/{invoice_id}", vendor, {"status": "issued", "reason": "Contract milestone"})
    scoped_user = post(client, "/v1/vendor/customers", vendor, {"organization_id": "hospital-a", "email": "scoped@example.test", "display_name": "Scoped account", "password": "scoped-password-123", "role": "customer_viewer"})
    post(client, f"/v1/vendor/accounts/{scoped_user['user_id']}/memberships", vendor, {"organization_id": "hospital-b", "role": "procurement_finance", "reason": "Group procurement assignment"})
    scoped = auth(client, "scoped@example.test", "scoped-password-123")
    assert client.post("/v1/auth/change-password", headers=scoped, json={"current_password": "scoped-password-123", "new_password": "scoped-new-password-123"}).status_code == 200
    scoped = auth(client, "scoped@example.test", "scoped-new-password-123")
    assert client.get("/v1/quotes", headers=scoped).json()["quotes"] == []
    assert client.get(f"/v1/quotes/{quote_id}/versions", headers=scoped).status_code == 404
    assert client.get("/v1/contracts", headers=scoped).json()["contracts"] == []
    assert client.get("/v1/invoices", headers=scoped).json()["invoices"] == []
    assert client.get(f"/v1/invoices/{invoice_id}/pdf", headers=scoped).status_code == 404
    assert client.get("/v1/licences", headers=scoped).json()["licences"] == []
    assert client.get("/v1/assessments", headers=scoped).json()["assessments"] == []
    assert client.post("/v1/payments", headers=scoped, json={"invoice_id": invoice_id, "amount_minor": 100, "paid_on": "2027-01-15", "channel": "bank_transfer", "reference": "WRONG-ORG", "evidence_ref": "WRONG-ORG"}).status_code == 403
    vendor_claim = post(client, "/v1/payments", vendor, {"invoice_id": invoice_id, "amount_minor": 100, "paid_on": "2027-01-15", "channel": "bank_transfer", "reference": "VENDOR-CLAIM", "evidence_ref": "INTERNAL-RECORD"})
    patch(client, f"/v1/vendor/payments/{vendor_claim['id']}", vendor, {"status": "verified", "reason": "Self review"}, expected=403)
    patch(client, f"/v1/vendor/payments/{vendor_claim['id']}", vendor, {"status": "rejected", "reason": "No independent evidence"})
    pdf = client.get(f"/v1/invoices/{invoice_id}/pdf", headers=a)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-1.4")
    assert pdf.headers["content-type"] == "application/pdf"
    assert client.get(f"/v1/invoices/{invoice_id}/pdf", headers=b).status_code == 404
    patch(client, f"/v1/vendor/invoices/{invoice_id}", vendor, {"status": "void", "reason": "Attempted mutation"}, expected=409)
    first = post(client, "/v1/payments", a, {"invoice_id": invoice_id, "amount_minor": 5000, "paid_on": "2027-01-15", "channel": "bank_transfer", "reference": "BANK-REF-1", "evidence_ref": "RECEIPT-1"})
    assert first["status"] == "pending_verification"
    assert client.get(f"/v1/payments/{first['id']}/receipt.pdf", headers=a).status_code == 404
    assert client.get("/v1/invoices", headers=a).json()["invoices"][0]["balance_minor"] == 19950
    assert client.get("/v1/payments", headers=b).json()["payments"] == []
    patch(client, f"/v1/vendor/payments/{first['id']}", vendor, {"status": "verified", "reason": "Bank statement matched"})
    assert client.get(f"/v1/payments/{first['id']}/receipt.pdf", headers=a).content.startswith(b"%PDF-1.4")
    assert client.get("/v1/invoices", headers=a).json()["invoices"][0]["balance_minor"] == 14950
    credit = post(client, "/v1/vendor/credits", vendor, {"invoice_id": invoice_id, "amount_minor": 1000, "reason": "Approved adjustment", "document_ref": "CREDIT-DOC-1"})
    assert client.get("/v1/credits", headers=a).json()["credits"] == []
    patch(client, f"/v1/vendor/credits/{credit['id']}", vendor, {"status": "issued", "reason": "Finance approved"})
    assert client.get("/v1/invoices", headers=a).json()["invoices"][0]["balance_minor"] == 13950
    second = post(client, "/v1/payments", a, {"invoice_id": invoice_id, "amount_minor": 13950, "paid_on": "2027-01-16", "channel": "bank_transfer", "reference": "BANK-REF-2", "evidence_ref": "RECEIPT-2"})
    patch(client, f"/v1/vendor/payments/{second['id']}", vendor, {"status": "verified", "reason": "Bank statement matched"})
    final = client.get("/v1/invoices", headers=a).json()["invoices"][0]
    assert final["balance_minor"] == 0 and final["status"] == "paid"
    summary = client.get("/v1/vendor/finance/summary", headers=vendor).json()["currencies"]["BDT"]
    assert summary == {"invoiced_minor": 19950, "verified_receipts_minor": 18950, "issued_credits_minor": 1000, "pipeline_quotes_minor": 0, "outstanding_minor": 0}
    renewal = post(client, "/v1/renewals", a, {"contract_id": contract_id, "request_type": "renew", "note": "Request follow-up"})
    patch(client, f"/v1/vendor/renewals/{renewal['id']}", vendor, {"status": "under_review", "reason": "Account review"})
    assert client.get("/v1/renewals", headers=b).json()["renewals"] == []


def test_internal_contact_and_lead_scope(tmp_path):
    app = service.create_app(str(tmp_path / "accounts.db"))
    app.state.store.create_vendor("vendor@example.test", "Vendor", "vendor-password-123")
    client = TestClient(app)
    vendor = auth(client, "vendor@example.test", "vendor-password-123")
    post(client, "/v1/vendor/organizations", vendor, {"organization_id": "hospital-a", "name": "Hospital A"})
    post(client, "/v1/vendor/customers", vendor, {"organization_id": "hospital-a", "email": "customer@example.test", "display_name": "Customer", "password": "customer-password-123"})
    customer = auth(client, "customer@example.test", "customer-password-123")
    lead = post(client, "/v1/vendor/leads", vendor, {"name": "Prospective institution", "contact_role": "IT lead", "contact_channel": "email", "next_action": "Schedule discovery"})
    assert client.get("/v1/vendor/leads", headers=customer).status_code == 403
    patch(client, f"/v1/vendor/leads/{lead['id']}", vendor, {"stage": "discovery", "next_action": "Assess source", "reason": "Meeting completed"})
    for visible in (False, True):
        post(client, "/v1/vendor/contacts", vendor, {"organization_id": "hospital-a", "channel": "meeting", "contact_role": "IT lead", "summary": "Workflow discussion", "customer_visible": visible})
    assert len(client.get("/v1/contacts", headers=customer).json()["contacts"]) == 1
    assert len(client.get("/v1/contacts", headers=vendor).json()["contacts"]) == 2


def test_vendor_finance_role_cannot_provision_sites_or_see_patients(tmp_path):
    app = service.create_app(str(tmp_path / "accounts.db"))
    app.state.store.create_vendor("root@example.test", "Root", "root-password-123")
    client = TestClient(app)
    root = auth(client, "root@example.test", "root-password-123")
    created = post(client, "/v1/vendor/staff", root, {"email": "finance@example.test", "display_name": "Finance", "role": "finance_legal", "password": "finance-password-123"})
    assert created["role"] == "finance_legal"
    finance = auth(client, "finance@example.test", "finance-password-123")
    assert client.get("/v1/auth/me", headers=finance).json()["role"] == "finance_legal"
    assert client.post("/v1/vendor/sites", headers=finance, json={"organization_id": "hospital-a", "site_id": "hospital-a-icu", "name": "ICU"}).status_code == 403
    assert client.get("/v1/patients", headers=finance).status_code == 404
    assert client.get("/v1/invoices", headers=finance).status_code == 200


def test_public_inquiry_requires_consent_and_deduplicates(tmp_path):
    app = service.create_app(str(tmp_path / "accounts.db"))
    app.state.store.create_vendor("root@example.test", "Root", "root-password-123")
    client = TestClient(app)
    payload = {"organization": "Example institution", "work_email": "contact@example.test", "contact_role": "IT lead", "interest": "site_assessment", "consent": True, "website": ""}
    assert client.post("/v1/public/inquiries", json={**payload, "consent": False}).status_code == 422
    assert client.post("/v1/public/inquiries", json={**payload, "website": "spam"}).status_code == 422
    assert client.post("/v1/public/inquiries", json=payload).json() == {"recorded": True}
    assert client.post("/v1/public/inquiries", json=payload).json() == {"recorded": True}
    root = auth(client, "root@example.test", "root-password-123")
    assert len(client.get("/v1/vendor/inquiries", headers=root).json()["inquiries"]) == 1


def test_existing_commercial_tables_upgrade_without_erasing_leads(tmp_path):
    path = tmp_path / "older-accounts.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE leads (id TEXT PRIMARY KEY,name TEXT NOT NULL,stage TEXT NOT NULL,contact_role TEXT NOT NULL,contact_channel TEXT NOT NULL,next_action TEXT NOT NULL,follow_up_date TEXT,reason TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)")
        db.execute("INSERT INTO leads VALUES(?,?,?,?,?,?,?,?,?,?)", ("prior-lead", "Existing prospect", "received", "IT lead", "email", "Schedule meeting", None, None, "2026-01-01", "2026-01-01"))
        db.execute("CREATE TABLE assessments (id TEXT PRIMARY KEY,organization_id TEXT,site_id TEXT,maturity TEXT,source_inventory_ref TEXT,findings TEXT,decision TEXT,created_at TEXT)")
        db.execute("CREATE TABLE quotes (id TEXT PRIMARY KEY,organization_id TEXT,site_id TEXT,currency TEXT,status TEXT,current_version INTEGER,created_at TEXT)")
        db.execute("CREATE TABLE payments (id TEXT PRIMARY KEY,organization_id TEXT,invoice_id TEXT,amount_minor INTEGER,paid_on TEXT,channel TEXT,reference TEXT,evidence_ref TEXT,status TEXT,reviewed_by TEXT,review_reason TEXT,created_at TEXT,reviewed_at TEXT)")
    app = service.create_app(str(path))
    for table, column in (("leads", "organization_id"), ("assessments", "lead_id"), ("quotes", "assessment_id"), ("payments", "submitted_by")):
        assert column in {row[1] for row in app.state.store.db.execute(f"PRAGMA table_info({table})")}
    assert app.state.store.db.execute("SELECT name FROM leads WHERE id='prior-lead'").fetchone()[0] == "Existing prospect"
