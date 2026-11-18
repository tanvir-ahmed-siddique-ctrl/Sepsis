"""Partnership, consultation, FDE and hospital profile tests; no clinical DB."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent))
spec = importlib.util.spec_from_file_location("account_service_partnership", Path(__file__).with_name("account_service.py"))
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


def test_consultation_opportunity_profile_fde_isolation(tmp_path, monkeypatch):
    monkeypatch.delenv("EVALUATION_RUNTIME", raising=False)
    app = service.create_app(str(tmp_path / "accounts.db"))
    app.state.store.create_vendor("vendor@example.test", "Vendor", "vendor-password-123")
    client = TestClient(app)
    vendor = auth(client, "vendor@example.test", "vendor-password-123")

    for org in ("hospital-a", "hospital-b"):
        post(client, "/v1/vendor/organizations", vendor, {"organization_id": org, "name": org})
        post(client, "/v1/vendor/sites", vendor, {"organization_id": org, "site_id": org + "-icu", "name": "ICU"})
        post(
            client,
            "/v1/vendor/customers",
            vendor,
            {"organization_id": org, "email": org + "@example.test", "display_name": org, "password": "customer-password-123"},
        )

    a = auth(client, "hospital-a@example.test", "customer-password-123")
    b = auth(client, "hospital-b@example.test", "customer-password-123")

    bad = client.post(
        "/v1/public/consultations",
        json={
            "organization": "Hope Clinic",
            "contact_name": "Dr Lee",
            "work_email": "lee@hope.example",
            "job_title": "CIO",
            "country": "Bangladesh",
            "location": "Dhaka",
            "hospital_type": "district",
            "purpose": "site_readiness",
            "preferred_dates": "Next Tuesday morning",
            "modality": "online",
            "consent": False,
        },
    )
    assert bad.status_code == 422

    created = post(
        client,
        "/v1/public/consultations",
        {},
        {
            "organization": "Hope Clinic",
            "contact_name": "Dr Lee",
            "work_email": "lee@hope.example",
            "job_title": "CIO",
            "department": "IT",
            "country": "Bangladesh",
            "location": "Dhaka",
            "hospital_type": "district",
            "organization_size": "small",
            "readiness_self_report": "foundation",
            "purpose": "site_readiness",
            "preferred_dates": "Week of 12 May, mornings",
            "modality": "online",
            "message": "Infrastructure first",
            "consent": True,
            "website": "",
        },
    )
    assert created["status"] == "pending"
    assert "pending confirmation" in created["note"].lower() or "pending" in created["note"].lower()

    consultations = client.get("/v1/vendor/consultations", headers=vendor).json()["consultations"]
    assert len(consultations) == 1
    consultation_id = consultations[0]["id"]
    assert client.patch(
        f"/v1/vendor/consultations/{consultation_id}",
        headers=a,
        json={"status": "confirmed", "reason": "Customer must not confirm"},
    ).status_code in {401, 403}

    patch = client.patch(
        f"/v1/vendor/consultations/{consultation_id}",
        headers=vendor,
        json={"status": "confirmed", "assigned_to": "vendor-owner", "organization_id": "hospital-a", "confirmed_at": "2026-11-18T10:00:00+00:00", "reason": "Slot agreed"},
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["status"] == "confirmed"

    opp = post(
        client,
        "/v1/vendor/opportunities",
        vendor,
        {
            "name": "Hope Clinic readiness",
            "organization_id": "hospital-a",
            "site_id": "hospital-a-icu",
            "primary_contact": "Dr Lee",
            "owner": "vendor-owner",
            "organization_size": "small",
            "readiness_tier": "foundation",
            "next_action": "Schedule discovery",
            "consultation_id": consultation_id,
        },
    )
    assert opp["stage"] == "new_inquiry"
    assert client.patch(
        f"/v1/vendor/opportunities/{opp['id']}",
        headers=vendor,
        json={"stage": "site_readiness", "next_action": "Run checklist", "reason": "Qualified"},
    ).status_code == 200

    profile = client.put(
        "/v1/vendor/organizations/hospital-a/profile",
        headers=vendor,
        json={
            "display_name": "Hospital A",
            "organization_size": "small",
            "readiness_tier": "foundation",
            "relationship_status": "assessment",
            "country": "Bangladesh",
            "reason": "Initial profile",
        },
    )
    assert profile.status_code == 200, profile.text
    assert profile.json()["readiness_tier"] == "foundation"

    customer_profile = client.get("/v1/organizations/hospital-a/profile", headers=a).json()
    assert customer_profile["profile"]["relationship_status"] == "assessment"
    assert "notes" not in (customer_profile["profile"] or {})
    assert client.get("/v1/organizations/hospital-a/profile", headers=b).status_code in {403, 404}

    site_profile = client.put(
        "/v1/vendor/sites/hospital-a-icu/profile",
        headers=vendor,
        json={"bed_scope": 12, "timezone": "Asia/Dhaka", "environment_status": "not_provisioned", "reason": "Site scope"},
    )
    assert site_profile.status_code == 200
    assert client.get("/v1/sites/hospital-a-icu/profile", headers=b).status_code in {403, 404}

    fde = post(
        client,
        "/v1/vendor/fde-projects",
        vendor,
        {
            "organization_id": "hospital-a",
            "site_id": "hospital-a-icu",
            "title": "Site readiness A",
            "category": "site_readiness",
            "deployment_lead": "deploy-1",
            "scope": "Foundation assessment",
            "opportunity_id": opp["id"],
        },
    )
    assert fde["readiness_items"] >= 10
    readiness = client.get(f"/v1/fde-projects/{fde['id']}/readiness", headers=vendor).json()["items"]
    item_id = readiness[0]["id"]
    assert client.patch(
        f"/v1/vendor/fde-projects/{fde['id']}/readiness/{item_id}",
        headers=vendor,
        json={"state": "in_progress", "reason": "Started"},
    ).status_code == 200
    assert client.get(f"/v1/fde-projects/{fde['id']}/readiness", headers=b).status_code in {403, 404}

    equipment = post(
        client,
        "/v1/vendor/equipment",
        vendor,
        {
            "organization_id": "hospital-a",
            "site_id": "hospital-a-icu",
            "category": "monitor",
            "model": "Example-Monitor",
            "quantity": 2,
            "ownership_model": "hospital_owned",
            "supplier_ref": "SUP-PRIVATE",
        },
    )
    assert equipment["id"]
    a_equip = client.get("/v1/equipment", headers=a).json()["equipment"]
    assert len(a_equip) == 1
    assert "supplier_ref" not in a_equip[0]
    assert client.get("/v1/equipment", headers=b).json()["equipment"] == []

    proposal = post(
        client,
        "/v1/vendor/proposals",
        vendor,
        {
            "organization_id": "hospital-a",
            "site_id": "hospital-a-icu",
            "opportunity_id": opp["id"],
            "title": "Readiness proposal",
            "executive_summary": "Foundation enablement first",
            "scope_json": '{"services":["site_readiness"]}',
            "assumptions": "Hospital provides IT owner",
            "exclusions": "Clinical AI not included until gates pass",
            "timeline_notes": "Planning assumptions only",
            "valid_until": "2027-06-01",
        },
    )
    assert proposal["status"] == "draft"
    assert client.get("/v1/proposals", headers=a).json()["proposals"] == []
    assert client.patch(
        f"/v1/vendor/proposals/{proposal['id']}",
        headers=vendor,
        json={"status": "issued", "reason": "Authorized issue"},
    ).status_code == 200
    assert len(client.get("/v1/proposals", headers=a).json()["proposals"]) == 1
    assert client.get("/v1/proposals", headers=b).json()["proposals"] == []

    event = post(
        client,
        "/v1/vendor/education-events",
        vendor,
        {
            "title": "ICU data-quality workshop",
            "event_type": "technical_workshop",
            "objectives": "Timestamp and unit literacy",
            "event_on": "2027-01-15",
            "format": "online",
            "audience": "clinical IT",
            "organization_id": "hospital-a",
            "included_complimentary": True,
        },
    )
    assert event["status"] == "planned"

    plan = post(
        client,
        "/v1/vendor/partnership-plans",
        vendor,
        {
            "organization_id": "hospital-a",
            "horizon_years": 8,
            "year_1_focus": "Foundation assessment",
            "years_2_3_focus": "Connectivity",
            "years_4_5_focus": "Governed intelligence if eligible",
            "years_6_8_focus": "Multi-site expansion if approved",
        },
    )
    assert plan["status"] == "internal_planning"
    assert client.get("/v1/vendor/partnership-plans", headers=a).status_code in {401, 403}

    assumptions = client.get("/v1/vendor/pricing-assumptions", headers=vendor).json()
    assert assumptions["assumptions"]
    assert assumptions["assumptions"][0]["public"] is False
    assert client.get("/v1/vendor/pricing-assumptions", headers=a).status_code in {401, 403}

    tax = client.get("/v1/partnership/taxonomy", headers=a).json()
    assert "foundation" in tax["readiness_tiers"]
    assert "new_inquiry" in tax["opportunity_stages"]
