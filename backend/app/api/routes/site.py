from fastapi import APIRouter, Depends, HTTPException

from app.auth import CLINICAL_ROLES, Actor, require_roles
from app.core.config import settings
from app.integrations.service import get_integration_service
from app.pilot import evaluate_gates
from app.records import utc_now
from app.schemas import GovernanceSignoffRequest, SiteModeRequest
from app.services.engine import get_engine

router = APIRouter(tags=["site"], prefix="/site")
ADMIN = require_roles("admin")
OPERATIONS = require_roles("admin", "operator")


@router.get("/status")
def site_status(_: Actor = Depends(require_roles(*CLINICAL_ROLES, "operator"))):
    state = get_engine().site.state
    return {
        "site_id": state.site_id,
        "effective_mode": state.effective_mode,
        "requested_mode": state.requested_mode,
        "interruptive_alerts_enabled": state.interruptive_alerts_enabled,
        "bedside_blinded": state.blinded,
        "demo_auth_enabled": settings.demo_mode,
        "review_sla_minutes": settings.alert_review_sla_minutes,
    }


@router.get("/readiness")
def site_readiness(_: Actor = Depends(OPERATIONS)):
    engine = get_engine()
    gates = evaluate_gates(engine, get_integration_service(engine).connector_health())
    return {
        "site": engine.site.state.as_dict(),
        "gates": gates,
        "live_eligible": all(gate["passed"] for gate in gates),
        "policy": "Interruptive alerts for real encounters stay disabled until every gate passes.",
    }


@router.put("/mode")
def set_site_mode(body: SiteModeRequest, actor: Actor = Depends(ADMIN)):
    if settings.public_demo_lockdown:
        raise HTTPException(
            status_code=403,
            detail="This public judge demo is locked to replay mode. Hospital installations retain audited mode changes.",
        )
    engine = get_engine()
    gates = evaluate_gates(engine, get_integration_service(engine).connector_health()) if body.mode == "live" else []
    try:
        state = engine.set_site_mode(body.mode, actor, body.reason, gates)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"site": state, "gates": gates}


@router.post("/governance-signoff")
def governance_signoff(body: GovernanceSignoffRequest, actor: Actor = Depends(ADMIN)):
    engine = get_engine()
    signoff = {**body.model_dump(), "recorded_by": actor.user_id, "recorded_at": utc_now()}
    engine.site.state.governance_signoff = signoff
    engine.record_site_config_change("governance_signoff_recorded", actor, signoff)
    return signoff
