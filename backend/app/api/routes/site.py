import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.auth import CLINICAL_ROLES, Actor, require_roles
from app.core.config import settings
from app.integrations.service import get_integration_service
from app.licensing import status as licence_status, verify_package
from app.pilot import evaluate_gates
from app.records import utc_now
from app.schemas import GovernanceSignoffRequest, SiteModeRequest, SoftLandingRequest
from app import shift_roster
from app.services.engine import get_engine

router = APIRouter(tags=["site"], prefix="/site")
ADMIN = require_roles("admin")
OPERATIONS = require_roles("admin", "operator")
CLINICAL = require_roles(*CLINICAL_ROLES, "operator")


class ShiftAssignmentBody(BaseModel):
    id: str | None = None
    user_id: str = Field(min_length=1, max_length=128)
    display_name: str = Field(min_length=1, max_length=200)
    role: str = Field(default="clinician", max_length=64)
    shift_id: str = Field(min_length=1, max_length=64)
    unit_id: str | None = Field(default=None, max_length=64)
    active: bool = True


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
    licence = licence_status(engine.records.load_config("local_licence"), settings.site_id)
    if settings.licence_required:
        gates.append({"gate": "commercial_licence", "passed": licence["activation_eligible"], "value": licence["status"], "target": "current", "detail": "An offline signed, site-bound licence is required for a new live-mode request."})
    return {
        "site": engine.site.state.as_dict(),
        "gates": gates,
        "licence": licence,
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
    if body.mode == "live" and settings.licence_required:
        licence = licence_status(engine.records.load_config("local_licence"), settings.site_id)
        gates.append({"gate": "commercial_licence", "passed": licence["activation_eligible"], "value": licence["status"], "target": "current", "detail": "An offline signed, site-bound licence is required for a new live-mode request."})
    try:
        state = engine.set_site_mode(body.mode, actor, body.reason, gates)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"site": state, "gates": gates}


@router.get("/licence")
def local_licence(_: Actor = Depends(OPERATIONS)):
    engine = get_engine()
    return {**licence_status(engine.records.load_config("local_licence"), settings.site_id), "required_for_new_live_request": settings.licence_required, "clinical_approval_separate": True}


@router.put("/licence")
def import_licence(package: dict, actor: Actor = Depends(ADMIN)):
    if settings.demo_mode or settings.evaluation_runtime:
        raise HTTPException(status_code=403, detail="Clinical licence import is disabled in demo and evaluation")
    if len(json.dumps(package)) > 16384:
        raise HTTPException(status_code=413, detail="Licence package too large")
    try:
        claims = verify_package(package, settings.site_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    engine = get_engine()
    with engine.lock:
        engine._require_writable()
        engine.records.save_config("local_licence", package, actor.user_id)
        engine._log("local_licence_imported", {"actor": actor.user_id, "licence_id": claims["licence_id"], "site_id": settings.site_id, "key_id": package["key_id"]})
    return {**licence_status(package, settings.site_id), "clinical_approval_separate": True}


@router.post("/governance-signoff")
def governance_signoff(body: GovernanceSignoffRequest, actor: Actor = Depends(ADMIN)):
    engine = get_engine()
    signoff = {**body.model_dump(), "recorded_by": actor.user_id, "recorded_at": utc_now()}
    engine.site.state.governance_signoff = signoff
    engine.record_site_config_change("governance_signoff_recorded", actor, signoff)
    return signoff


@router.put("/soft-landing")
def set_soft_landing(body: SoftLandingRequest, actor: Actor = Depends(ADMIN)):
    """L5 — treat PredictRx as ICU intelligence UI; HIS keeps registration/billing."""
    if settings.public_demo_lockdown:
        raise HTTPException(
            status_code=403,
            detail="Public judge demo cannot change soft-landing; hospital installs retain this flag.",
        )
    engine = get_engine()
    engine.site.state.soft_landing = bool(body.enabled)
    engine.site.save(actor.user_id)
    payload = {"enabled": body.enabled, "reason": body.reason}
    engine.record_site_config_change("soft_landing_updated", actor, payload)
    return {"soft_landing": engine.site.state.soft_landing, **payload}


@router.get("/shift-roster")
def get_shift_roster(unit_id: str | None = Query(None), _: Actor = Depends(CLINICAL)):
    """Full roster + who is on the current shift (transparency, not payroll attendance)."""
    document = shift_roster.load(get_engine())
    return {
        **document,
        "current": shift_roster.current_staff(document, unit_id=unit_id),
        "csv_template": shift_roster.csv_template(),
    }


@router.get("/shift-roster/current")
def current_shift_staff(unit_id: str | None = Query(None), _: Actor = Depends(CLINICAL)):
    document = shift_roster.load(get_engine())
    return shift_roster.current_staff(document, unit_id=unit_id)


@router.put("/shift-roster/assignments")
def upsert_shift_assignment(body: ShiftAssignmentBody, actor: Actor = Depends(ADMIN)):
    engine = get_engine()
    document = shift_roster.load(engine)
    try:
        row = shift_roster.upsert_assignment(document, body.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    shift_roster.save(engine, document, actor.user_id)
    engine.record_site_config_change("shift_roster_upsert", actor, {"assignment_id": row["id"], "user_id": row["user_id"]})
    return {"assignment": row, "current": shift_roster.current_staff(document)}


@router.delete("/shift-roster/assignments/{assignment_id}")
def delete_shift_assignment(assignment_id: str, actor: Actor = Depends(ADMIN)):
    engine = get_engine()
    document = shift_roster.load(engine)
    if not shift_roster.delete_assignment(document, assignment_id):
        raise HTTPException(status_code=404, detail="Assignment not found")
    shift_roster.save(engine, document, actor.user_id)
    engine.record_site_config_change("shift_roster_delete", actor, {"assignment_id": assignment_id})
    return {"deleted": assignment_id, "current": shift_roster.current_staff(document)}


@router.post("/shift-roster/csv")
async def import_shift_roster_csv(request: Request, replace: bool = Query(False), actor: Actor = Depends(ADMIN)):
    """Import CSV columns: user_id,display_name,role,shift_id,unit_id,active."""
    raw = (await request.body()).decode("utf-8")
    engine = get_engine()
    document = shift_roster.load(engine)
    try:
        rows = shift_roster.parse_csv(raw)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if replace:
        document["assignments"] = []
    saved = []
    for row in rows:
        saved.append(shift_roster.upsert_assignment(document, row))
    shift_roster.save(engine, document, actor.user_id)
    engine.record_site_config_change(
        "shift_roster_csv_import",
        actor,
        {"imported": len(saved), "replace": replace},
    )
    return {"imported": len(saved), "assignments": document["assignments"], "current": shift_roster.current_staff(document)}
