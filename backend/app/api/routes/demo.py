from fastapi import APIRouter, Depends, Query

from app.auth import CLINICAL_ROLES, Actor, require_roles
from app.services.engine import get_engine

router = APIRouter(tags=["demo"], prefix="/demo/replay")
CLINICAL = require_roles(*CLINICAL_ROLES)


@router.post("/step")
def replay_step(
    hours: int = Query(1, ge=1, le=24),
    _: Actor = Depends(CLINICAL),
):
    return get_engine().step(hours)


@router.post("/reset")
def replay_reset(_: Actor = Depends(CLINICAL)):
    engine = get_engine()
    engine.reset_replay()
    return {"patients": sum(patient.source_mode == "replay" for patient in engine.patients.values())}


@router.get("/status")
def replay_status(_: Actor = Depends(CLINICAL)):
    """Replay metadata, including labelled onset — for presentation mode only, never shown as a prediction."""
    engine = get_engine()
    with engine.lock:
        return {
            "model_version": engine.model_version,
            "site_mode": engine.site.state.effective_mode,
            "source_split": engine.manifest.get("source_split"),
            "selection_rule": engine.manifest.get("selection_rule"),
            "median_warning_hours_test": engine.manifest.get("median_warning_hours_test"),
            "patients": [
                {
                    "patient_id": p.patient_id,
                    "hour": p.predictions[-1]["hour"] if p.predictions else 0,
                    "remaining_hours": (len(p.source) - p.cursor) if p.source is not None else 0,
                    **p.replay_meta,
                }
                for p in engine.patients.values()
                if p.source_mode == "replay"
            ],
        }
