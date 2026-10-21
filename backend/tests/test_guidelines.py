"""Evidence copilot: cited, versioned, deterministic retrieval with no treatment generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.guidelines import TREATMENT_TERMS, GuidelineRegistry

ADMIN = {"X-Demo-User": "protocol-author", "X-Demo-Role": "admin"}
SECOND_ADMIN = {"X-Demo-User": "protocol-approver", "X-Demo-Role": "admin"}
CLINICIAN = {"X-Demo-User": "bedside-rn", "X-Demo-Role": "clinician"}
PROTOCOL = {
    "title": "ICU sepsis screening escalation",
    "section": "3.2 Escalation",
    "text": "If the sepsis screen is positive, the bedside nurse escalates to the ICU registrar within 15 minutes.",
    "topic": "escalation",
    "concepts": ["concept:systemic_response"],
    "version": "2026.1",
    "document_ref": "ICU-PRO-014",
    "review_due": "2027-06-30",
}


def test_registry_is_versioned_cited_and_treatment_free():
    registry = GuidelineRegistry(settings.guidelines_path)
    assert registry.version == "1.0.0" and len(registry.sha256) == 64
    assert {"ssc-2021", "who-wha70-2017", "sepsis-3-2016"} <= set(registry.sources)
    for passage in registry.passages:
        citation = registry.cite(passage)["citation"]
        assert citation["title"] and citation["url"].startswith("https://") and citation["section"]
        words = set(passage["text"].lower().replace(",", " ").replace(".", " ").split())
        assert not words & {"dose", "dosing", "ml/kg", "mg/kg", "vasopressor", "norepinephrine"}, passage["passage_id"]


def test_registry_rejects_unknown_sources_and_topics(tmp_path):
    document = json.loads(Path(settings.guidelines_path).read_text(encoding="utf-8"))
    document["passages"][0]["topic"] = "treatment"
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="disallowed topic"):
        GuidelineRegistry(path)


@pytest.fixture(scope="module")
def client():
    settings.database_url = "sqlite:///:memory:"
    settings.demo_mode = True
    from app.main import app

    with TestClient(app, headers=ADMIN) as c:
        yield c


def test_feature_guidance_links_lactate_to_ssc_recommendation(client):
    body = client.get("/v1/evidence/guidance?features=Lactate,MAP", headers=CLINICIAN).json()
    ids = [passage["passage_id"] for passage in body["passages"]]
    assert "ssc-2021-rec-3" in ids and "sepsis-3-definition" in ids
    lactate = next(passage for passage in body["passages"] if passage["passage_id"] == "ssc-2021-rec-3")
    assert "concept:hypoperfusion" in lactate["matched_concepts"]
    assert lactate["citation"]["publisher"] and lactate["citation"]["doi"]
    assert body["patient_specific"] is False and "not patient-specific" in body["disclaimer"]
    matched = [len(p["matched_concepts"]) for p in body["passages"]]
    assert matched == sorted(matched, reverse=True)


def test_treatment_questions_are_refused(client):
    for query in ("antibiotic dose for septic shock", "how much fluid bolus", "start norepinephrine"):
        body = client.get("/v1/evidence/guidance/search", params={"q": query}).json()
        assert body["refused"] is True and body["results"] == [] and body["matched_terms"]
    allowed = client.get("/v1/evidence/guidance/search", params={"q": "lactate measurement"}).json()
    assert allowed["refused"] is False
    assert allowed["results"][0]["passage_id"] in {"ssc-2021-rec-3", "ssc-2021-lactate-rationale"}
    assert {"antibiotic", "dose", "fluid", "vasopressor"} <= TREATMENT_TERMS


def test_local_protocols_need_two_people_and_no_doses(client):
    dosed = client.post("/v1/evidence/local-protocols",
                        json={**PROTOCOL, "text": "Give 30 ml/kg crystalloid as the first dose within 3 hours."})
    assert dosed.status_code == 422
    assert client.post("/v1/evidence/local-protocols", json={**PROTOCOL, "topic": "treatment"}).status_code == 422
    assert client.post("/v1/evidence/local-protocols", json=PROTOCOL, headers=CLINICIAN).status_code == 403

    entry = client.post("/v1/evidence/local-protocols", json=PROTOCOL).json()
    assert entry["status"] == "pending_approval"
    before = client.get("/v1/evidence/guidance?features=Lactate").json()
    assert all(p["passage_id"] != entry["entry_id"] for p in before["passages"])

    self_approval = client.post(f"/v1/evidence/local-protocols/{entry['entry_id']}/approve")
    assert self_approval.status_code == 403
    approved = client.post(f"/v1/evidence/local-protocols/{entry['entry_id']}/approve", headers=SECOND_ADMIN)
    assert approved.status_code == 200 and approved.json()["approved_by"] == "protocol-approver"
    assert client.post(f"/v1/evidence/local-protocols/{entry['entry_id']}/approve", headers=SECOND_ADMIN).status_code == 409
    assert client.post("/v1/evidence/local-protocols/missing/approve", headers=SECOND_ADMIN).status_code == 404

    after = client.get("/v1/evidence/guidance?features=Lactate").json()
    assert after["passages"][0]["passage_id"] == entry["entry_id"]
    assert after["passages"][0]["source_type"] == "local_protocol"
    assert after["passages"][0]["citation"]["document_ref"] == "ICU-PRO-014"
    search = client.get("/v1/evidence/guidance/search", params={"q": "escalation registrar"}).json()
    assert search["results"][0]["passage_id"] == entry["entry_id"]

    client.post(f"/v1/evidence/local-protocols/{entry['entry_id']}/retire")
    retired = client.get("/v1/evidence/guidance?features=Lactate").json()
    assert all(p["passage_id"] != entry["entry_id"] for p in retired["passages"])
    events = {event["event"] for event in client.get("/v1/audit?limit=200").json()["events"]}
    assert {"local_protocol_submitted", "local_protocol_approved", "local_protocol_retired"} <= events


def test_guidelines_withheld_outside_demo_until_site_approves_version(client):
    client.put("/v1/site/mode", json={"mode": "silent", "reason": "pilot"})
    try:
        withheld = client.get("/v1/evidence/guidance?features=Lactate").json()
        assert withheld["withheld_reason"] == "guideline_registry_version_not_approved_by_site"
        assert not any(p["source_type"] == "guideline" for p in withheld["passages"])
        assert client.post("/v1/evidence/guidelines/approve?reason=committee", headers=CLINICIAN).status_code == 403
        approval = client.post("/v1/evidence/guidelines/approve?reason=Approved by sepsis committee").json()
        assert approval["registry_version"] == "1.0.0"
        visible = client.get("/v1/evidence/guidance?features=Lactate").json()
        assert visible["site_approved"] is True and visible["withheld_reason"] is None
        assert any(p["passage_id"] == "ssc-2021-rec-3" for p in visible["passages"])
        registry = client.get("/v1/evidence/guidelines").json()
        assert registry["site_approval"]["approved_by"] == "protocol-author"
    finally:
        client.put("/v1/site/mode", json={"mode": "demo", "reason": "cleanup"})
