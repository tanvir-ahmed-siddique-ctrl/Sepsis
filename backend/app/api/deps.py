"""Shared route helpers: patient resolution with unit scoping and silent-pilot blinding."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException

from app.auth import Actor
from app.core.config import settings
from app.services.engine import Engine, Patient

BLINDED_DETAIL = "Silent pilot: scores for live encounters are blinded to bedside staff."


def review_state(alert: dict) -> dict:
    """Wall-clock age of an alert and whether its first review is past the SLA."""
    raised = alert.get("raised_at")
    if not raised:
        return {"age_minutes": None, "sla_minutes": settings.alert_review_sla_minutes, "overdue": False}
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(raised)).total_seconds() / 60
    return {
        "age_minutes": int(age),
        "sla_minutes": settings.alert_review_sla_minutes,
        "overdue": alert["status"] == "open" and age > settings.alert_review_sla_minutes,
    }


def is_blinded(engine: Engine, actor: Actor, patient: Patient) -> bool:
    return patient.source_mode == "api" and engine.site.state.blinded and "admin" not in actor.roles


def patient_for(engine: Engine, actor: Actor, identifier: str, *, require_predictions: bool = True) -> Patient:
    patient = engine.resolve_patient(identifier)
    if patient is None or (require_predictions and not patient.predictions):
        raise HTTPException(status_code=404, detail="Patient not found")
    if not actor.can_access_unit(patient.unit_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    if is_blinded(engine, actor, patient):
        raise HTTPException(status_code=403, detail=BLINDED_DETAIL)
    return patient
