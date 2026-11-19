"""API tests against the real model bundle and replay cases (skipped if not generated)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings

pytestmark = pytest.mark.skipif(
    not (Path(settings.model_path).exists() and (Path(settings.demo_cases_dir) / "manifest.json").exists()),
    reason="model bundle or demo cases not generated",
)


@pytest.fixture(scope="module")
def client():
    settings.database_url = "sqlite:///:memory:"
    settings.demo_mode = True
    from app.main import app

    with TestClient(app, headers={"X-Demo-User": "tester", "X-Demo-Role": "admin"}) as c:
        assert c.get("/health").json()["replay_patients"] > 0
        yield c


def test_health_reports_model(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["replay_patients"] > 0


def test_readiness_checks_model_database_and_replay(client):
    response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert all(body["checks"].values())
    assert len(body["model_hash"]) == 64


def test_hospital_passport_recommends_retrospective_validation(client):
    body = client.get("/v1/model/passport").json()
    assert body["recommended_mode"] == "Retrospective validation"
    assert "no_local_retrospective_validation" in body["blockers"]
    assert body["passport_version"] == "1.0.0"


def test_model_card_uses_site_held_out_wording(client):
    body = client.get("/v1/model").json()
    assert "geographically distinct public hospital cohort" in body["validation_wording"]
    assert "not an exact incident" in body["label_definition"].lower()


def test_evidence_graph_endpoint_keeps_context_noncausal(client):
    body = client.get("/v1/evidence/features/Lactate_hours_since").json()
    assert body["mapped"]
    assert body["graph_version"] == "1.0.0"
    assert "not a causal" in body["model_influence"]["meaning"]


def test_jwt_roles_enforce_clinical_and_integration_boundaries(client):
    def bearer(role: str) -> dict[str, str]:
        token_response = client.post(
            "/v1/auth/demo-token",
            params={"user_id": f"test-{role}", "role": role},
        )
        assert token_response.status_code == 200
        return {"Authorization": f"Bearer {token_response.json()['access_token']}"}

    observation = {
        "patient_id": "auth-patient",
        "encounter_id": "e1",
        "timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat(),
        "code": "HR",
        "value": 88,
    }
    assert client.post(
        "/v1/observations/batch",
        json={"observations": [observation]},
        headers=bearer("integration"),
    ).status_code == 200
    assert client.post(
        "/v1/observations/batch",
        json={"observations": [observation]},
        headers=bearer("clinician"),
    ).status_code == 403
    assert client.get(
        "/v1/audit",
        headers=bearer("integration"),
    ).status_code == 403
    assert client.get(
        "/v1/audit",
        headers={"Authorization": "Bearer invalid"},
    ).status_code == 401


def test_overview_sorted_by_trustgate_then_risk(client):
    trust = {"alert": 4, "verify_data": 3, "watch": 2, "abstain": 1}
    body = client.get(f"/v1/units/{settings.demo_unit_id}/overview").json()
    cards = body["patients"]
    ranks = [trust.get(c["trust_state"], 0) for c in cards]
    assert ranks == sorted(ranks, reverse=True)
    assert body["high_risk_count"] == sum(c["trust_state"] == "alert" for c in cards)
    assert body["watch_count"] == sum(c["trust_state"] == "watch" for c in cards)
    assert body["verify_count"] == sum(c["trust_state"] == "verify_data" for c in cards)
    assert body["abstain_count"] == sum(c["trust_state"] == "abstain" for c in cards)


def test_prediction_fields_and_bounds(client):
    pid = client.get(f"/v1/units/{settings.demo_unit_id}/overview").json()["patients"][0]["patient_id"]
    risk = client.get(f"/v1/patients/{pid}/risk/current").json()
    assert risk["model_version"] and risk["timestamp"] and risk["data_quality"]
    assert risk["trustgate"]["state"] in {"alert", "watch", "verify_data", "abstain"}
    assert 0 <= risk["trustgate"]["input_shift_score"] <= 1
    if risk["probability"] is not None:
        assert 0.0 <= risk["probability"] <= 1.0
        assert risk["contributing_factors"]


def test_replay_step_advances_every_bed(client):
    before = client.get("/v1/demo/replay/status").json()["patients"]
    client.post("/v1/demo/replay/step?hours=1")
    after = client.get("/v1/demo/replay/status").json()["patients"]
    for b, a in zip(before, after):
        if b["remaining_hours"] > 0:
            assert a["remaining_hours"] == b["remaining_hours"] - 1


def test_alert_workflow_is_audited(client):
    for _ in range(24):
        if client.get("/v1/alerts?status=open").json()["alerts"]:
            break
        client.post("/v1/demo/replay/step?hours=1")
    alerts = client.get("/v1/alerts?status=open").json()["alerts"]
    if not alerts:
        pytest.skip("no alert fired in 24 replay hours")
    alert_id = alerts[0]["alert_id"]
    res = client.post(f"/v1/alerts/{alert_id}/acknowledge", json={"user_id": "tester", "action": "acknowledged"})
    assert res.status_code == 200
    assert client.post(
        f"/v1/alerts/{alert_id}/acknowledge",
        json={"user_id": "tester", "action": "dismissed", "reason": "Already reviewed"},
    ).status_code == 409
    events = client.get("/v1/audit?event=alert_acknowledged").json()["events"]
    assert any(e["alert_id"] == alert_id and e["user_id"] == "tester" for e in events)


def test_unknown_alert_and_patient_404(client):
    assert client.get("/v1/patients/nope/risk/current").status_code == 404
    assert client.post(
        "/v1/alerts/nope/acknowledge",
        json={"user_id": "x", "action": "dismissed", "reason": "Not clinically actionable"},
    ).status_code == 404


def test_observation_ingest_scores_new_patient(client):
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    obs = []
    for h in range(6):
        ts = (t0 + timedelta(hours=h)).isoformat()
        obs += [
            {"patient_id": "api-1", "encounter_id": "e1", "timestamp": ts, "code": "HR", "value": 90 + 5 * h},
            {"patient_id": "api-1", "encounter_id": "e1", "timestamp": ts, "code": "SBP", "value": 120 - 4 * h},
            {"patient_id": "api-1", "encounter_id": "e1", "timestamp": ts, "code": "Resp", "value": 18 + h},
        ]
    obs.append({"patient_id": "api-1", "encounter_id": "e1", "timestamp": t0.isoformat(), "code": "NOT_A_CODE", "value": 1})
    assert client.post("/v1/observations/batch", json={"observations": obs}).json()["patients_rescored"] == 1
    risk = client.get("/v1/patients/api-1/risk/current").json()
    assert 0.0 <= risk["probability"] <= 1.0
    timeline = client.get("/v1/patients/api-1/risk/timeline").json()["points"]
    assert timeline[0]["risk_band"] == "insufficient_data"


def test_watch_is_passive_and_does_not_create_alert(client):
    from app.services.engine import get_engine

    engine = get_engine()
    patient = next(p for p in engine.patients.values() if p.source_mode == "replay")
    before = len(engine.alerts)
    engine._maybe_alert(patient, {"risk_band": "watch"}, "stable")
    assert len(engine.alerts) == before


def test_sparse_ingest_preserves_real_hour_gaps_and_timestamps(client):
    t0 = datetime(2026, 2, 1, tzinfo=timezone.utc)
    observations = []
    for hour in (0, 5):
        for code, value in (("HR", 90), ("SBP", 115), ("MAP", 75), ("O2Sat", 97)):
            observations.append(
                {
                    "patient_id": "gap-patient",
                    "encounter_id": "gap-encounter",
                    "timestamp": (t0 + timedelta(hours=hour)).isoformat(),
                    "code": code,
                    "value": value,
                }
            )
    result = client.post("/v1/observations/batch", json={"observations": observations})
    assert result.status_code == 200
    points = client.get("/v1/patients/gap-patient/risk/timeline").json()["points"]
    assert len(points) == 6
    assert points[-1]["hour"] == 6
    assert points[-1]["timestamp"] == (t0 + timedelta(hours=5)).isoformat().replace("+00:00", "Z")


def test_fractional_observation_after_integer_seed_does_not_degrade_native_json(client):
    """Replay/seed frames may create int64 vital columns; live feeds send floats like 92.5."""
    t0 = datetime(2026, 5, 1, tzinfo=timezone.utc)
    first = {
        "patient_id": "dtype-float",
        "encounter_id": "enc-1",
        "timestamp": t0.isoformat(),
        "code": "O2Sat",
        "value": 93,
        "unit": "%",
    }
    second = {**first, "value": 92.5}
    assert client.post("/v1/observations/batch", json={"observations": [first]}).status_code == 200
    body = client.post("/v1/observations/batch", json={"observations": [second]}).json()
    assert body["accepted"] == 1
    assert body.get("error") is None
    assert not any("int64" in str(item).lower() for item in body.get("quarantined", []))


def test_invalid_units_ranges_and_unknown_codes_are_quarantined_and_audited(client):
    timestamp = datetime(2026, 3, 1, tzinfo=timezone.utc).isoformat()
    observations = [
        {"patient_id": "bad", "encounter_id": "e1", "timestamp": timestamp, "code": "HR", "value": 999, "unit": "bpm"},
        {"patient_id": "bad", "encounter_id": "e1", "timestamp": timestamp, "code": "Temp", "value": 98.6, "unit": "degF"},
        {"patient_id": "bad", "encounter_id": "e1", "timestamp": timestamp, "code": "UNKNOWN", "value": 1},
    ]
    body = client.post("/v1/observations/batch", json={"observations": observations}).json()
    assert body["accepted"] == 0
    assert len(body["quarantined"]) == 3
    events = client.get("/v1/audit?event=observation_quarantined").json()["events"]
    assert any(event["patient_id"] == "bad" and event["code"] == "UNKNOWN" for event in events)


def test_encounters_are_isolated_and_duplicates_are_idempotent(client):
    timestamp = datetime(2026, 4, 1, tzinfo=timezone.utc).isoformat()
    first = {
        "patient_id": "same-patient",
        "encounter_id": "encounter-a",
        "timestamp": timestamp,
        "code": "HR",
        "value": 88,
    }
    second = {**first, "encounter_id": "encounter-b", "value": 92}
    assert client.post("/v1/observations/batch", json={"observations": [first, second]}).status_code == 200
    duplicate = client.post("/v1/observations/batch", json={"observations": [first]}).json()
    assert duplicate["patients_rescored"] == 0
    assert duplicate["duplicates_ignored"] == 1
    assert client.get("/v1/patients/same-patient--encounter-a/risk/current").status_code == 200
    assert client.get("/v1/patients/same-patient--encounter-b/risk/current").status_code == 200
    assert client.get("/v1/patients/same-patient/risk/current").status_code == 404


def test_static_values_propagate_and_replay_reset_preserves_api_encounters(client):
    from app.services.engine import get_engine

    t0 = datetime(2026, 5, 1, tzinfo=timezone.utc)
    observations = [
        {"patient_id": "static-patient", "encounter_id": "e1", "timestamp": t0.isoformat(), "code": "Age", "value": 64},
        {"patient_id": "static-patient", "encounter_id": "e1", "timestamp": t0.isoformat(), "code": "Gender", "value": 1},
        {
            "patient_id": "static-patient",
            "encounter_id": "e1",
            "timestamp": (t0 + timedelta(hours=3)).isoformat(),
            "code": "HR",
            "value": 95,
        },
    ]
    client.post("/v1/observations/batch", json={"observations": observations})
    engine = get_engine()
    patient = engine.resolve_patient("static-patient")
    materialized = engine._materialize_api_timeline(patient)
    assert materialized["Age"].eq(64).all()
    assert materialized["Gender"].eq(1).all()
    client.post("/v1/demo/replay/reset")
    assert engine.resolve_patient("static-patient") is not None


def test_late_data_recompute_is_idempotent_and_audit_chain_is_linked(client):
    t0 = datetime(2026, 6, 1, tzinfo=timezone.utc)
    observations = []
    for hour in range(6):
        observations.append(
            {
                "patient_id": "late-patient",
                "encounter_id": "e1",
                "timestamp": (t0 + timedelta(hours=hour)).isoformat(),
                "code": "HR",
                "value": 80 + hour,
            }
        )
    client.post("/v1/observations/batch", json={"observations": observations})
    before = client.get("/v1/patients/late-patient/risk/timeline").json()["points"]
    late = {
        "patient_id": "late-patient",
        "encounter_id": "e1",
        "timestamp": (t0 + timedelta(hours=2)).isoformat(),
        "code": "HR",
        "value": 110,
    }
    client.post("/v1/observations/batch", json={"observations": [late]})
    after = client.get("/v1/patients/late-patient/risk/timeline").json()["points"]
    assert len(after) == len(before)
    alert_ids = [point["alert_id"] for point in after if point["alert_id"]]
    assert len(alert_ids) == len(set(alert_ids))

    from app.services.engine import get_engine

    audit = get_engine().audit
    assert all(current["previous_hash"] == previous["event_hash"] for previous, current in zip(audit, audit[1:]))


def test_dismissal_requires_reason(client):
    response = client.post(
        "/v1/alerts/not-important/acknowledge",
        json={"user_id": "tester", "action": "dismissed"},
    )
    assert response.status_code == 422


def test_api_state_and_audit_survive_engine_restart(tmp_path, monkeypatch):
    from app.schemas import ObservationIn
    from app.services.engine import Engine

    database_url = f"sqlite:///{(tmp_path / 'restart.db').as_posix()}"
    monkeypatch.setattr(settings, "database_url", database_url)
    first = Engine()
    first.ingest(
        [
            ObservationIn(
                patient_id="restart-patient",
                encounter_id="restart-encounter",
                timestamp=datetime(2026, 7, 1, tzinfo=timezone.utc),
                code="HR",
                value=93,
            )
        ]
    )
    audit_count = len(first.audit)
    first.close()

    restarted = Engine()
    restored = restarted.resolve_patient("restart-patient")
    assert restored is not None
    assert restored.encounter_id == "restart-encounter"
    assert float(restored.raw["HR"].iloc[0]) == 93
    assert len(restarted.audit) > audit_count
    assert all(
        current["previous_hash"] == previous["event_hash"]
        for previous, current in zip(restarted.audit, restarted.audit[1:])
    )
    restarted.close()


def test_concurrent_duplicate_ingestion_is_idempotent(client):
    observation = {
        "patient_id": "concurrent-patient",
        "encounter_id": "concurrent-encounter",
        "timestamp": datetime(2026, 8, 1, tzinfo=timezone.utc).isoformat(),
        "code": "HR",
        "value": 91,
    }
    first = client.post("/v1/observations/batch", json={"observations": [observation]})
    assert first.status_code == 200

    def submit_duplicate(_: int):
        return client.post("/v1/observations/batch", json={"observations": [observation]})

    with ThreadPoolExecutor(max_workers=6) as pool:
        responses = list(pool.map(submit_duplicate, range(12)))
    assert all(response.status_code == 200 for response in responses)
    assert sum(response.json()["duplicates_ignored"] for response in responses) == 12
    assert sum(response.json()["patients_rescored"] for response in responses) == 0


def test_basic_readiness_load_smoke(client):
    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(lambda _: client.get("/ready"), range(40)))
    assert all(response.status_code == 200 for response in responses)
