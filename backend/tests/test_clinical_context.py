"""Patient-specific context: annotations and alert policy around the frozen model."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import clinical_context as cc
from app.core.config import settings

NOW = datetime(2026, 10, 20, 8, 0, tzinfo=timezone.utc)
FACTORS = [
    {"feature": "Creatinine", "direction": "raises"},
    {"feature": "BUN", "direction": "raises"},
    {"feature": "HR", "direction": "raises"},
    {"feature": "Temp", "direction": "lowers"},
]


def _context(goals="full_treatment", conditions=(), note=None, hours=72, now=NOW):
    return cc.build(
        goals_of_care=goals,
        conditions=list(conditions),
        other_note=note,
        reason="Documented on ward round",
        review_hours=hours,
        actor_id="dr.karim",
        actor_role="clinician",
        now=now,
    )


def test_no_context_is_standard_policy():
    result = cc.evaluate(None, factors=FACTORS, risk_band="high_risk", now=NOW)
    assert result["documented"] is False
    assert result["alert_policy"] == "standard"


def test_ckd_annotates_baseline_drivers_without_suppressing():
    result = cc.evaluate(_context(conditions=["ckd_dialysis"]), factors=FACTORS, risk_band="high_risk", now=NOW)
    assert result["alert_policy"] == "standard"
    assert {item["feature"] for item in result["driver_annotations"]} == {"Creatinine", "BUN"}
    assert any("not suppressed" in caution for caution in result["cautions"])


def test_immunosuppression_warns_low_score_may_reassure_falsely():
    result = cc.evaluate(_context(conditions=["immunosuppressed"]), factors=FACTORS, risk_band="stable", now=NOW)
    assert result["alert_policy"] == "standard"
    assert any("falsely reassuring" in caution for caution in result["cautions"])


@pytest.mark.parametrize(
    ("goals", "conditions", "reason"),
    [
        ("comfort_care", [], "comfort_care_documented"),
        ("full_treatment", ["pregnancy_postpartum"], "outside_validated_population:pregnancy_postpartum"),
    ],
)
def test_comfort_care_and_out_of_scope_are_shadow_only(goals, conditions, reason):
    assert cc.alert_policy(_context(goals=goals, conditions=conditions), NOW) == ("shadow_only", reason)


def test_overdue_review_restores_standard_alerting():
    context = _context(goals="comfort_care", hours=1)
    assert cc.alert_policy(context, NOW + timedelta(hours=2)) == ("standard", None)
    result = cc.evaluate(context, now=NOW + timedelta(hours=2))
    assert result["review_overdue"] is True
    assert any("overdue" in caution for caution in result["cautions"])


def test_unmodelled_condition_requires_note_and_flags_subgroup():
    with pytest.raises(cc.ContextError):
        _context(conditions=["other_unmodelled"])
    context = _context(conditions=["other_unmodelled"], note="Suspected Guillain-Barre syndrome")
    result = cc.evaluate(context, now=NOW)
    assert "condition:other_unmodelled" in result["subgroups"]
    assert any("Guillain-Barre" in caution for caution in result["cautions"])


def test_unknown_condition_code_is_rejected():
    with pytest.raises(cc.ContextError):
        _context(conditions=["made_up"])


ADMIN = {"X-Demo-User": "ctx-admin", "X-Demo-Role": "admin"}
DOCTOR = {"X-Demo-User": "dr.karim", "X-Demo-Role": "clinician"}
NURSE = {"X-Demo-User": "rn.akter", "X-Demo-Role": "nurse"}
OPERATOR = {"X-Demo-User": "ops", "X-Demo-Role": "operator"}

needs_model = pytest.mark.skipif(
    not (Path(settings.model_path).exists() and (Path(settings.demo_cases_dir) / "manifest.json").exists()),
    reason="model bundle or demo cases not generated",
)


@pytest.fixture(scope="module")
def client():
    settings.database_url = "sqlite:///:memory:"
    settings.demo_mode = True
    from app.main import app

    with TestClient(app, headers=ADMIN) as c:
        c.post("/v1/demo/replay/reset")
        yield c


@needs_model
def test_context_roles(client):
    body = {"goals_of_care": "limited_escalation", "conditions": ["ckd_dialysis"], "reason": "Family meeting"}
    assert client.get("/v1/patients/BED-06/context", headers=NURSE).status_code == 200
    assert client.put("/v1/patients/BED-06/context", json=body, headers=NURSE).status_code == 403
    assert client.get("/v1/patients/BED-06/context", headers=OPERATOR).status_code == 403
    saved = client.put("/v1/patients/BED-06/context", json=body, headers=DOCTOR)
    assert saved.status_code == 200, saved.text
    context = saved.json()["context"]
    assert context["recorded_by"] == "dr.karim"
    assert context["goals_of_care"] == "limited_escalation"
    events = client.get("/v1/audit?event=clinical_context_updated&patient_id=BED-06").json()["events"]
    assert events and events[0]["conditions"] == ["ckd_dialysis"]


@needs_model
def test_comfort_care_keeps_alert_silent_and_score_unchanged(client):
    # BED-03 is the replay case that raises a trusted interruptive alert within 8 hours.
    client.post("/v1/demo/replay/reset")
    before = client.get("/v1/patients/BED-03/risk/current").json()["probability"]
    saved = client.put(
        "/v1/patients/BED-03/context",
        json={"goals_of_care": "comfort_care", "reason": "Comfort care agreed with family"},
        headers=DOCTOR,
    )
    assert saved.json()["context"]["alert_policy"] == "shadow_only"
    assert client.get("/v1/patients/BED-03/risk/current").json()["probability"] == before

    client.post("/v1/demo/replay/step?hours=8")
    open_ids = {a["patient_id"] for a in client.get("/v1/alerts?status=open").json()["alerts"]}
    silent = [a for a in client.get("/v1/alerts?status=silent").json()["alerts"] if a["patient_id"] == "BED-03"]
    assert "BED-03" not in open_ids
    assert silent and silent[0]["context_policy"] == "comfort_care_documented"

    client.post("/v1/demo/replay/reset")
    client.post("/v1/demo/replay/step?hours=8")
    open_ids = {a["patient_id"] for a in client.get("/v1/alerts?status=open").json()["alerts"]}
    assert "BED-03" in open_ids
