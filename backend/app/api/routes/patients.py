from fastapi import APIRouter, Depends, HTTPException, Query

from app import clinical_context
from app.api.deps import patient_for
from app.auth import CLINICAL_READ_ROLES, CLINICAL_ROLES, PHYSICIAN_ROLES, Actor, require_roles
from app.core.config import settings
from app.schemas import (
    ClinicalContextRequest,
    HandoffNoteRequest,
    OwnershipRequest,
    RiskCurrentResponse,
    RiskTimelineResponse,
)
from app.services.engine import ReadOnlyError, get_engine

router = APIRouter(tags=["patients"])
CLINICAL = require_roles(*CLINICAL_ROLES)
CLINICAL_READ = require_roles(*CLINICAL_READ_ROLES)
PHYSICIAN = require_roles(*PHYSICIAN_ROLES)


def _context_view(engine, patient) -> dict:
    latest = patient.predictions[-1] if patient.predictions else {}
    return {
        "patient_id": patient.encounter_key,
        "context": clinical_context.evaluate(
            patient.context,
            factors=latest.get("factors"),
            risk_band=latest.get("risk_band"),
        ),
        "catalogue": clinical_context.catalogue(),
    }


@router.get("/patients/{patient_id}/context")
def get_clinical_context(patient_id: str, actor: Actor = Depends(CLINICAL_READ)):
    engine = get_engine()
    with engine.lock:
        p = patient_for(engine, actor, patient_id, require_predictions=False)
        return _context_view(engine, p)


@router.put("/patients/{patient_id}/context")
def set_clinical_context(patient_id: str, body: ClinicalContextRequest, actor: Actor = Depends(PHYSICIAN)):
    engine = get_engine()
    p = patient_for(engine, actor, patient_id, require_predictions=False)
    try:
        context = clinical_context.build(
            goals_of_care=body.goals_of_care,
            conditions=body.conditions,
            other_note=body.other_note,
            reason=body.reason,
            review_hours=body.review_hours,
            actor_id=actor.user_id,
            actor_role=actor.role,
        )
        engine.set_clinical_context(p, context, actor)
    except clinical_context.ContextError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ReadOnlyError as exc:
        raise HTTPException(status_code=503, detail="This instance is read-only") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    with engine.lock:
        return _context_view(engine, p)


@router.get("/patients/{patient_id}/risk/current", response_model=RiskCurrentResponse)
def current_risk(patient_id: str, actor: Actor = Depends(CLINICAL_READ)):
    engine = get_engine()
    p = patient_for(engine, actor, patient_id)
    if p.kind != "icu" or not p.predictions:
        raise HTTPException(status_code=404, detail="ICU model risk is not available for this encounter")
    latest = p.predictions[-1]
    owner = engine.ownership.get(p.encounter_key)
    return RiskCurrentResponse(
        patient_id=p.patient_id,
        encounter_id=p.encounter_id,
        encounter_key=p.encounter_key,
        unit_id=p.unit_id,
        source_mode=p.source_mode,
        owner=owner["owner"] if owner else None,
        thresholds=engine.thresholds,
        contributing_factors=latest["factors"],
        disclaimer=settings.disclaimer,
        **{k: v for k, v in latest.items() if k != "factors"},
    )


@router.get("/patients/{patient_id}/risk/timeline", response_model=RiskTimelineResponse)
def risk_timeline(patient_id: str, actor: Actor = Depends(CLINICAL_READ)):
    engine = get_engine()
    p = patient_for(engine, actor, patient_id)
    if p.kind != "icu":
        raise HTTPException(status_code=404, detail="ICU model timeline is not available for this encounter")
    return RiskTimelineResponse(
        patient_id=p.encounter_key,
        points=p.predictions,
        thresholds=engine.thresholds,
        disclaimer=settings.disclaimer,
    )


@router.get("/patients/{patient_id}/provenance")
def observation_provenance(patient_id: str, actor: Actor = Depends(CLINICAL_READ)):
    engine = get_engine()
    with engine.lock:
        p = patient_for(engine, actor, patient_id)
        return {
            "patient_id": p.encounter_key,
            "source_mode": p.source_mode,
            "unit_id": p.unit_id,
            "observations": engine.provenance(p),
            "note": (
                "Latest observed value per variable with its source system and source time. "
                "Replay values come from the held-out PhysioNet cohort, not a live feed."
            ),
        }


@router.get("/patients/{patient_id}/signals")
def missing_signal_matrix(
    patient_id: str,
    hours: int = Query(24, ge=4, le=72),
    actor: Actor = Depends(CLINICAL_READ),
):
    engine = get_engine()
    with engine.lock:
        p = patient_for(engine, actor, patient_id)
        return {"patient_id": p.encounter_key, **engine.signal_matrix(p, hours)}


@router.post("/patients/{patient_id}/ownership")
def claim_bed(patient_id: str, body: OwnershipRequest, actor: Actor = Depends(CLINICAL)):
    engine = get_engine()
    p = patient_for(engine, actor, patient_id, require_predictions=False)
    return engine.claim_ownership(p, actor, body.shift_label)


@router.delete("/patients/{patient_id}/ownership")
def release_bed(patient_id: str, actor: Actor = Depends(CLINICAL)):
    engine = get_engine()
    p = patient_for(engine, actor, patient_id, require_predictions=False)
    engine.release_ownership(p, actor)
    return {"released": True, "patient_id": p.encounter_key}


@router.get("/patients/{patient_id}/handoff-notes")
def list_handoff_notes(patient_id: str, limit: int = Query(10, ge=1, le=50), actor: Actor = Depends(CLINICAL_READ)):
    engine = get_engine()
    p = patient_for(engine, actor, patient_id, require_predictions=False)
    return {"patient_id": p.encounter_key, "notes": engine.handoff_notes_for(p.encounter_key, limit)}


@router.post("/patients/{patient_id}/handoff-notes")
def add_handoff_note(patient_id: str, body: HandoffNoteRequest, actor: Actor = Depends(CLINICAL)):
    engine = get_engine()
    p = patient_for(engine, actor, patient_id, require_predictions=False)
    return engine.add_handoff_note(p, actor, body.note.strip())
