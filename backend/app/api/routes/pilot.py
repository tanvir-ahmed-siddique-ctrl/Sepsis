import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import patient_for
from app.auth import CLINICAL_ROLES, PHYSICIAN_ROLES, Actor, require_roles
from app.pilot import apply_retention, build_export, compute_metrics, monitoring_findings
from app.records import export_log, feedback_records, outcome_records, utc_now
from app.schemas import FeedbackRequest, OutcomeRequest
from app.services.engine import get_engine

router = APIRouter(tags=["pilot"], prefix="/pilot")
ADMIN = require_roles("admin")
CLINICAL = require_roles(*CLINICAL_ROLES)
PHYSICIAN = require_roles(*PHYSICIAN_ROLES)


@router.get("/metrics")
def pilot_metrics(
    unit_id: str | None = None,
    thresholds: str | None = Query(None, description="Comma-separated thresholds to simulate"),
    pilot_only: bool = False,
    _: Actor = Depends(ADMIN),
):
    grid = None
    if thresholds:
        try:
            grid = [float(value) for value in thresholds.split(",") if value.strip()]
        except ValueError as error:
            raise HTTPException(status_code=422, detail="Thresholds must be numbers") from error
        if any(not 0 < value < 1 for value in grid) or len(grid) > 20:
            raise HTTPException(status_code=422, detail="Up to 20 thresholds strictly between 0 and 1")
    return compute_metrics(get_engine(), unit_id=unit_id, thresholds=grid, pilot_only=pilot_only)


@router.get("/monitoring")
def pilot_monitoring(_: Actor = Depends(ADMIN)):
    """Local operational findings; demo and backfill rows cannot become clinical evidence."""
    return monitoring_findings(compute_metrics(get_engine(), pilot_only=True))


@router.post("/feedback")
def record_feedback(body: FeedbackRequest, actor: Actor = Depends(CLINICAL)):
    engine = get_engine()
    patient = patient_for(engine, actor, body.patient_id, require_predictions=False)
    if body.alert_id and engine.alerts.get(body.alert_id, {}).get("encounter_key") != patient.encounter_key:
        raise HTTPException(status_code=422, detail="Alert does not belong to this encounter")
    recorded_at = utc_now()
    row = {
        "feedback_id": hashlib.sha256(f"{patient.encounter_key}|{actor.user_id}|{recorded_at}".encode()).hexdigest()[:32],
        "alert_id": body.alert_id,
        "encounter_key": patient.encounter_key,
        "user_id": actor.user_id,
        "role": actor.role,
        "usefulness": body.usefulness.value,
        "workflow": json.dumps(body.workflow),
        "comment": body.comment,
        "recorded_at": recorded_at,
    }
    with engine.lock:
        engine._require_writable()
        engine.records.insert(feedback_records, row)
        engine._log("clinician_feedback_recorded", {
            "feedback_id": row["feedback_id"], "patient_id": patient.patient_id,
            "encounter_key": patient.encounter_key, "alert_id": body.alert_id,
            "actor": actor.user_id, "actor_role": actor.role, "usefulness": row["usefulness"],
        })
    return {**row, "workflow": body.workflow}


@router.get("/feedback")
def list_feedback(patient_id: str | None = None, _: Actor = Depends(ADMIN)):
    engine = get_engine()
    conditions = []
    if patient_id:
        patient = engine.resolve_patient(patient_id)
        conditions.append(feedback_records.c.encounter_key == (patient.encounter_key if patient else patient_id))
    rows = engine.records.select(feedback_records, *conditions, order_by=feedback_records.c.recorded_at.desc())
    return {"feedback": [{**row, "workflow": json.loads(row["workflow"])} for row in rows]}


@router.post("/outcomes")
def record_outcome(body: OutcomeRequest, actor: Actor = Depends(PHYSICIAN)):
    engine = get_engine()
    patient = engine.resolve_patient(body.patient_id)
    if patient is None or not actor.can_access_unit(patient.unit_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    recorded_at = utc_now()
    row = {
        "outcome_id": hashlib.sha256(f"{patient.encounter_key}|{actor.user_id}|{recorded_at}".encode()).hexdigest()[:32],
        "encounter_key": patient.encounter_key,
        "adjudication": body.adjudication.value,
        "onset_time": body.onset_time.isoformat() if body.onset_time else None,
        "criteria": body.criteria,
        "adjudicator": actor.user_id,
        "notes": body.notes,
        "recorded_at": recorded_at,
    }
    with engine.lock:
        engine._require_writable()
        previous = engine.records.select(outcome_records, outcome_records.c.encounter_key == patient.encounter_key)
        engine.records.insert(outcome_records, row)
        engine._log("outcome_adjudicated", {
            "outcome_id": row["outcome_id"], "patient_id": patient.patient_id,
            "encounter_key": patient.encounter_key, "adjudication": row["adjudication"],
            "onset_time": row["onset_time"], "criteria": row["criteria"],
            "actor": actor.user_id, "actor_role": actor.role, "supersedes": len(previous),
        })
    return {**row, "supersedes_previous": len(previous)}


@router.get("/outcomes")
def list_outcomes(patient_id: str | None = None, _: Actor = Depends(ADMIN)):
    engine = get_engine()
    conditions = []
    if patient_id:
        patient = engine.resolve_patient(patient_id)
        conditions.append(outcome_records.c.encounter_key == (patient.encounter_key if patient else patient_id))
    return {"outcomes": engine.records.select(outcome_records, *conditions, order_by=outcome_records.c.recorded_at.desc())}


@router.post("/export")
def export_pilot(
    reason: str = Query(..., min_length=5, max_length=500),
    unit_id: str | None = None,
    actor: Actor = Depends(ADMIN),
):
    return build_export(get_engine(), actor, reason, unit_id)


@router.get("/exports")
def list_exports(_: Actor = Depends(ADMIN)):
    rows = get_engine().records.select(export_log, order_by=export_log.c.created_at.desc())
    return {"exports": [{**row, "counts": json.loads(row["counts"])} for row in rows]}


@router.post("/retention/apply")
def retention(actor: Actor = Depends(ADMIN)):
    return {"deleted": apply_retention(get_engine(), actor)}
