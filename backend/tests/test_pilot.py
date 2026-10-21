"""Silent-pilot evidence: metric math, readiness gates, outcomes/feedback, exports, retention, workflow."""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.core.config import settings
from app.pilot import compute_metrics, evaluate_gates, latest_predictions
from app.records import RecordStore, outcome_records, prediction_records, utc_now
from app.site import SiteState

T0 = datetime(2026, 6, 1, tzinfo=timezone.utc)
ADMIN = {"X-Demo-User": "pilot-admin", "X-Demo-Role": "admin"}
CLINICIAN = {"X-Demo-User": "bedside-rn", "X-Demo-Role": "clinician"}
needs_model = pytest.mark.skipif(
    not (Path(settings.model_path).exists() and (Path(settings.demo_cases_dir) / "manifest.json").exists()),
    reason="model bundle or demo cases not generated",
)


def _row(encounter: str, hour: int, probability: float, *, revision: int = 0, alert: str | None = None,
         quality: str = "ok", site_mode: str = "silent", sex: str | None = "F", age: int | None = 70,
         freshness: dict | None = None) -> dict:
    return {
        "record_id": hashlib.sha256(f"{encounter}|{hour}|{revision}".encode()).hexdigest()[:32],
        "site_id": "test-site", "unit_id": "icu-test", "encounter_key": encounter,
        "patient_id": encounter, "encounter_id": "e", "source_time": (T0 + timedelta(hours=hour)).isoformat(),
        "scored_at": (T0 + timedelta(hours=hour, minutes=5)).isoformat(), "hour": hour,
        "probability": probability, "risk_band": "watch" if probability >= 0.05 else "low_observed",
        "trust_state": "watch" if probability >= 0.05 else "abstain", "data_quality": quality,
        "freshness_minutes": 30, "input_shift": 0.5, "input_revision": revision, "model_version": "run4",
        "site_mode": site_mode, "ingest_mode": "realtime", "alert_id": alert,
        "alert_disposition": "shadow" if alert else "none", "age": age, "sex": sex, "processing_ms": 12.0,
        "payload": json.dumps({"signal_freshness": freshness or {"HR": 30, "SBP": 30, "MAP": 30, "O2Sat": 30}}),
    }


@pytest.fixture()
def fake_engine():
    records = RecordStore(create_engine("sqlite://"))
    no_map = {"HR": 30, "SBP": 30, "MAP": None, "O2Sat": 30}
    rows = []
    for hour in range(12):
        rows.append(_row("enc-a", hour, round(0.01 * hour, 3), alert="alert-a" if hour >= 7 else None, freshness=no_map))
        rows.append(_row("enc-b", hour, 0.02, sex="M", age=50))
        rows.append(_row("enc-c", hour, 0.2, alert="alert-c", quality="stale" if hour == 5 else "ok",
                         site_mode="demo", sex=None, age=None))
    rows.append(_row("enc-a", 3, 0.9, revision=-1))
    records.insert_many_ignore(prediction_records, rows)
    for key, adjudication, onset in (("enc-a", "sepsis", T0 + timedelta(hours=10)), ("enc-b", "no_sepsis", None)):
        records.insert(outcome_records, {
            "outcome_id": key, "encounter_key": key, "adjudication": adjudication,
            "onset_time": onset.isoformat() if onset else None, "criteria": "sepsis-3",
            "adjudicator": "reviewer", "notes": None, "recorded_at": utc_now(),
        })
    return SimpleNamespace(
        records=records, lock=threading.RLock(), patients={}, alerts={},
        site=SimpleNamespace(state=SiteState(site_id="test-site", requested_mode="silent")),
        thresholds={"watch": 0.05, "high_risk": 0.1}, model_version="run4", model_hash="abc",
    )


def test_latest_revision_wins(fake_engine):
    rows = [row for row in latest_predictions(fake_engine) if row["encounter_key"] == "enc-a" and row["hour"] == 3]
    assert len(rows) == 1 and rows[0]["probability"] == 0.03


def test_metrics_detection_burden_calibration_and_simulation(fake_engine):
    metrics = compute_metrics(fake_engine, thresholds=[0.05, 0.5])
    assert metrics["volume"]["encounters"] == 3 and metrics["volume"]["patient_hours"] == 36
    detection = metrics["detection"]
    assert detection["adjudicated_sepsis"] == 1 and detection["detected"] == 1
    assert detection["sensitivity"] == 1.0 and detection["median_lead_hours"] == 3.0
    assert detection["adjudicated_no_sepsis"] == 1 and detection["no_sepsis_encounters_with_alert"] == 0
    burden = metrics["alert_burden"]
    assert burden["alerts"] == 2 and burden["shadow_alerts"] == 2 and burden["interruptive_alerts"] == 0
    assert burden["alerts_per_100_patient_hours"] == round(200 / 36, 3)
    assert metrics["missingness"]["MAP"]["missing_rate"] == round(12 / 36, 4)
    assert metrics["missingness"]["HR"]["missing_rate"] == 0
    calibration = metrics["calibration"]
    assert calibration["status"] == "computed"
    assert calibration["labelled_hours"] == 24 and calibration["positive_hours"] == 8
    simulation = {row["threshold"]: row for row in metrics["threshold_simulation"]["rows"]}
    assert simulation[0.05]["is_current_watch"] and simulation[0.1]["is_current_high_risk"]
    assert simulation[0.05]["episodes"] == 3
    assert simulation[0.05]["sensitivity"] == 1.0 and simulation[0.05]["false_alert_encounter_rate"] == 0
    assert simulation[0.5]["episodes"] == 0 and simulation[0.5]["sensitivity"] == 0
    assert set(metrics["subgroups"]["sex"]) == {"F", "M", "unknown"}
    assert set(metrics["subgroups"]["age_band"]) == {"65-79", "45-64", "unknown"}
    assert metrics["trends"][0]["date"] == "2026-06-01"


def test_pilot_only_excludes_demo_rows_and_calibration_needs_labels(fake_engine):
    metrics = compute_metrics(fake_engine, pilot_only=True)
    assert metrics["volume"]["encounters"] == 2 and metrics["alert_burden"]["alerts"] == 1
    fake_engine.records.delete(outcome_records, outcome_records.c.encounter_key.in_(["enc-a", "enc-b"]))
    metrics = compute_metrics(fake_engine)
    assert metrics["calibration"]["status"] == "insufficient_labels"
    assert metrics["detection"]["sensitivity"] is None


def test_gates_fail_closed_until_evidence_exists(fake_engine):
    gates = {gate["gate"]: gate for gate in evaluate_gates(fake_engine, [])}
    assert set(gates) == {
        "local_retrospective_validation", "silent_pilot_duration", "silent_pilot_encounters",
        "adjudicated_outcomes", "sensitivity_floor", "alert_burden_budget", "feeds_healthy",
        "governance_signoff", "production_security",
    }
    assert not any(gate["passed"] for name, gate in gates.items() if name != "alert_burden_budget")
    assert gates["sensitivity_floor"]["value"] == 1.0
    fake_engine.site.state.governance_signoff = {"committee": "IRB"}
    gates = {gate["gate"]: gate for gate in evaluate_gates(fake_engine, [{"connector": "fhir_r4", "state": "healthy"}])}
    assert gates["governance_signoff"]["passed"] and gates["feeds_healthy"]["passed"]
    stale = evaluate_gates(fake_engine, [{"connector": "fhir_r4", "state": "stale"}])
    assert not next(gate for gate in stale if gate["gate"] == "feeds_healthy")["passed"]


# ---------------------------------------------------------------- API workflow


@pytest.fixture(scope="module")
def client():
    settings.database_url = "sqlite:///:memory:"
    settings.demo_mode = True
    from app.main import app

    with TestClient(app, headers=ADMIN) as c:
        c.put("/v1/site/mode", json={"mode": "silent", "reason": "pilot tests"})
        for name, lactate in (("pilot-a", 4.5), ("pilot-b", 1.0)):
            observations = []
            for hour in range(10):
                stamp = (T0 + timedelta(hours=hour)).isoformat()
                for code, value in (("HR", 90 + 3 * hour), ("SBP", 120 - 2 * hour), ("MAP", 82 - hour),
                                    ("O2Sat", 96), ("Resp", 18 + hour), ("Temp", 37.2 + 0.1 * hour)):
                    observations.append({"patient_id": name, "encounter_id": "e1", "unit_id": "icu-pilot",
                                         "timestamp": stamp, "code": code, "value": value})
                if hour % 4 == 0:
                    observations.append({"patient_id": name, "encounter_id": "e1", "unit_id": "icu-pilot",
                                         "timestamp": stamp, "code": "Lactate", "value": lactate})
            response = c.post("/v1/observations/batch", json={"observations": observations})
            assert response.status_code == 200, response.text
        yield c
        c.put("/v1/site/mode", json={"mode": "demo", "reason": "cleanup"})


@needs_model
def test_pilot_metrics_are_admin_only_and_scoped(client):
    assert client.get("/v1/pilot/metrics", headers=CLINICIAN).status_code == 403
    metrics = client.get("/v1/pilot/metrics?unit_id=icu-pilot&pilot_only=true").json()
    assert metrics["site_mode"] == "silent" and metrics["volume"]["encounters"] == 2
    assert metrics["volume"]["patient_hours"] == 20
    assert metrics["alert_burden"]["interruptive_alerts"] == 0
    assert metrics["latency"]["median_processing_ms"] is not None
    assert client.get("/v1/pilot/metrics?thresholds=0.1,abc").status_code == 422
    assert client.get("/v1/pilot/metrics?thresholds=1.5").status_code == 422


@needs_model
def test_outcomes_and_feedback_are_validated_and_audited(client):
    naive = client.post("/v1/pilot/outcomes", json={
        "patient_id": "pilot-a--e1", "adjudication": "sepsis", "onset_time": "2026-06-01T08:00:00",
    })
    assert naive.status_code == 422
    assert client.post("/v1/pilot/outcomes", json={"patient_id": "pilot-a--e1", "adjudication": "sepsis"}).status_code == 422
    first = client.post("/v1/pilot/outcomes", json={
        "patient_id": "pilot-a--e1", "adjudication": "indeterminate", "notes": "awaiting cultures",
    }).json()
    assert first["supersedes_previous"] == 0
    revised = client.post("/v1/pilot/outcomes", json={
        "patient_id": "pilot-a--e1", "adjudication": "sepsis", "onset_time": (T0 + timedelta(hours=8)).isoformat(),
        "criteria": "sepsis-3", "notes": "Blood culture + SOFA rise",
    }).json()
    assert revised["supersedes_previous"] == 1
    client.post("/v1/pilot/outcomes", json={"patient_id": "pilot-b--e1", "adjudication": "no_sepsis"})
    metrics = client.get("/v1/pilot/metrics?unit_id=icu-pilot").json()
    assert metrics["detection"]["adjudicated_sepsis"] == 1 and metrics["detection"]["adjudicated_no_sepsis"] == 1

    bad_tag = client.post("/v1/pilot/feedback", json={
        "patient_id": "pilot-a--e1", "usefulness": "helpful", "workflow": ["start_antibiotics"],
    })
    assert bad_tag.status_code == 422
    wrong_alert = client.post("/v1/pilot/feedback", json={
        "patient_id": "pilot-a--e1", "usefulness": "helpful", "alert_id": "not-this-encounter",
    })
    assert wrong_alert.status_code == 422
    assert client.post("/v1/pilot/feedback", headers=CLINICIAN, json={
        "patient_id": "pilot-a--e1", "usefulness": "helpful",
    }).status_code == 403
    saved = client.post("/v1/pilot/feedback", json={
        "patient_id": "pilot-a--e1", "usefulness": "not_helpful", "workflow": ["already_aware", "alarm_fatigue"],
        "comment": "Patient Rahim in bed 4 was already on the sepsis pathway",
    })
    assert saved.status_code == 200
    metrics = client.get("/v1/pilot/metrics?unit_id=icu-pilot").json()
    assert metrics["feedback"]["usefulness"] == {"not_helpful": 1}
    assert metrics["feedback"]["workflow"] == {"already_aware": 1, "alarm_fatigue": 1}
    events = {event["event"] for event in client.get("/v1/audit?limit=200").json()["events"]}
    assert {"outcome_adjudicated", "clinician_feedback_recorded"} <= events


@needs_model
def test_export_is_pseudonymised_hashed_and_logged(client):
    assert client.post("/v1/pilot/export?reason=no").status_code == 422
    assert client.post("/v1/pilot/export?reason=quarterly review", headers=CLINICIAN).status_code == 403
    response = client.post("/v1/pilot/export?reason=governance quarterly review&unit_id=icu-pilot")
    assert response.status_code == 200
    body = response.json()
    text = json.dumps(body["export"])
    for identifier in ("pilot-a--e1", "pilot-b--e1", '"e1"', "Rahim", "Blood culture", "awaiting cultures"):
        assert identifier not in text
    canonical = json.dumps(body["export"], sort_keys=True, separators=(",", ":"), default=str)
    assert hashlib.sha256(canonical.encode()).hexdigest() == body["sha256"]
    recorded = len(client.get("/v1/pilot/outcomes").json()["outcomes"])
    assert body["counts"]["predictions"] == 20 and body["counts"]["outcomes"] == recorded
    encounters = {row["encounter"] for row in body["export"]["predictions"]}
    assert len(encounters) == 2 and all(len(value) == 20 for value in encounters)
    assert {row["age_band"] for row in body["export"]["predictions"]} == {"unknown"}
    logged = client.get("/v1/pilot/exports").json()["exports"]
    assert logged[0]["export_id"] == body["export_id"] and logged[0]["sha256"] == body["sha256"]
    audit = client.get("/v1/audit?event=pilot_export_created").json()["events"]
    assert audit and audit[-1]["sha256"] == body["sha256"]


@needs_model
def test_retention_deletes_only_expired_rows(client):
    from app.services.engine import get_engine

    engine = get_engine()
    old = _row("ancient", 0, 0.01)
    old["scored_at"] = (datetime.now(timezone.utc) - timedelta(days=settings.retention_days + 5)).isoformat()
    engine.records.insert(prediction_records, old)
    before = len(engine.records.select(prediction_records))
    deleted = client.post("/v1/pilot/retention/apply").json()["deleted"]
    assert deleted["prediction_records"] == 1
    assert len(engine.records.select(prediction_records)) == before - 1
    assert client.get("/v1/audit?event=retention_applied").json()["events"]


@needs_model
def test_governance_signoff_flows_into_readiness(client):
    readiness = client.get("/v1/site/readiness").json()
    gates = {gate["gate"]: gate for gate in readiness["gates"]}
    assert not gates["governance_signoff"]["passed"] and readiness["live_eligible"] is False
    assert client.get("/v1/site/readiness", headers=CLINICIAN).status_code == 403
    signoff = client.post("/v1/site/governance-signoff", json={
        "committee": "Hospital Ethics Committee", "reference": "HEC-2026-041", "approver": "Prof. Karim",
    })
    assert signoff.status_code == 200
    gates = {gate["gate"]: gate for gate in client.get("/v1/site/readiness").json()["gates"]}
    assert gates["governance_signoff"]["passed"]
    assert gates["silent_pilot_encounters"]["value"] == 2
    live = client.put("/v1/site/mode", json={"mode": "live", "reason": "premature"}).json()
    assert live["site"]["effective_mode"] == "live-disabled"
    client.put("/v1/site/mode", json={"mode": "silent", "reason": "back to silent"})


@needs_model
def test_ownership_handoff_notes_and_provenance(client):
    claim = client.post("/v1/patients/pilot-a--e1/ownership", json={"shift_label": "night"})
    assert claim.status_code == 200 and claim.json()["owner"] == "pilot-admin"
    note = client.post("/v1/patients/pilot-a--e1/handoff-notes", json={"note": "Repeat lactate due 06:00"})
    assert note.status_code == 200
    assert client.post("/v1/patients/pilot-a--e1/handoff-notes", json={"note": ""}).status_code == 422
    card = next(c for c in client.get("/v1/units/icu-pilot/overview").json()["patients"]
                if c["patient_id"] == "pilot-a--e1")
    assert card["owner"] == "pilot-admin"
    handoff = client.get("/v1/units/icu-pilot/handoff").json()
    bed = next(b for b in handoff["beds"] if b["patient_id"] == "pilot-a--e1")
    assert bed["owner"]["shift_label"] == "night" and bed["notes"][0]["note"] == "Repeat lactate due 06:00"
    assert bed["trend"] in {"rising", "falling", "steady"}
    assert client.get("/v1/units/icu-pilot/handoff", headers=CLINICIAN).json()["beds"] == []
    released = client.delete("/v1/patients/pilot-a--e1/ownership")
    assert released.status_code == 200
    card = next(c for c in client.get("/v1/units/icu-pilot/overview").json()["patients"]
                if c["patient_id"] == "pilot-a--e1")
    assert card["owner"] is None
    events = {event["event"] for event in client.get("/v1/audit?limit=200").json()["events"]}
    assert {"bed_ownership_claimed", "bed_ownership_released", "handoff_note_added"} <= events

    provenance = client.get("/v1/patients/pilot-a--e1/provenance").json()
    lactate = next(row for row in provenance["observations"] if row["code"] == "Lactate")
    assert lactate["value"] == 4.5 and lactate["connector"] == "native_json"
    matrix = client.get("/v1/patients/pilot-a--e1/signals?hours=10").json()
    rows = {row["code"]: row for row in matrix["signals"]}
    assert rows["HR"]["observed_hours"] == 10 and rows["Lactate"]["observed_hours"] == 3
    assert client.get("/v1/patients/pilot-a--e1/signals?hours=2").status_code == 422
