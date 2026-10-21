from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.auth import CLINICAL_ROLES, PHYSICIAN_ROLES, Actor, require_roles
from app.core.config import settings
from app.schemas import AlertAckRequest, AlertAckResponse
from app.services.engine import get_engine

router = APIRouter(tags=["alerts"])
CLINICAL = require_roles(*CLINICAL_ROLES)
PHYSICIAN = require_roles(*PHYSICIAN_ROLES)


def _with_review_clock(alert: dict) -> dict:
    sla = settings.alert_review_sla_minutes
    raised = alert.get("raised_at")
    end = alert["actions"][0]["at"] if alert.get("actions") else None
    minutes = None
    if raised:
        finish = datetime.fromisoformat(end) if end else datetime.now(timezone.utc)
        minutes = max(0, int((finish - datetime.fromisoformat(raised)).total_seconds() // 60))
    return {
        **alert,
        "review_minutes": minutes,
        "review_sla_minutes": sla,
        "overdue": alert["status"] == "open" and minutes is not None and minutes > sla,
    }


@router.get("/alerts")
def list_alerts(
    status: str | None = None,
    patient_id: str | None = None,
    unit_id: str | None = None,
    actor: Actor = Depends(CLINICAL),
):
    if status == "silent" and "admin" not in actor.roles:
        raise HTTPException(status_code=403, detail="Shadow alerts are visible to the pilot team only")
    engine = get_engine()
    with engine.lock:
        units = {key: p.unit_id for key, p in engine.patients.items()}
        alerts = []
        for alert in engine.alerts.values():
            unit = alert.get("unit_id") or units.get(alert.get("encounter_key"), settings.demo_unit_id)
            if not actor.can_access_unit(unit) or (unit_id and unit != unit_id):
                continue
            if alert["status"] == "silent" and status != "silent":
                continue
            if status is not None and alert["status"] != status:
                continue
            if patient_id is not None and patient_id not in {alert["patient_id"], alert.get("encounter_key")}:
                continue
            alerts.append(_with_review_clock(alert))
    return {"alerts": sorted(alerts, key=lambda a: a["created_at"], reverse=True)}


@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertAckResponse)
def acknowledge_alert(
    alert_id: str,
    body: AlertAckRequest,
    actor: Actor = Depends(PHYSICIAN),
):
    engine = get_engine()
    alert = engine.alerts.get(alert_id)
    if alert is None or not actor.can_access_unit(alert.get("unit_id") or settings.demo_unit_id):
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert["status"] != "open":
        raise HTTPException(status_code=409, detail="Alert already resolved or not interruptive")
    recorded = body.timestamp or datetime.now(timezone.utc)
    audit_id = engine.act_on_alert(alert_id, actor.user_id, body.action.value, body.reason, recorded, actor.role)
    return AlertAckResponse(alert_id=alert_id, action=body.action, recorded_at=recorded, audit_id=audit_id)


@router.get("/audit")
def audit_log(
    limit: int = 100,
    event: str | None = None,
    patient_id: str | None = None,
    actor: Actor = Depends(CLINICAL),
):
    engine = get_engine()
    with engine.lock:
        allowed_keys = None
        if actor.units is not None:
            allowed_keys = {key for key, p in engine.patients.items() if actor.can_access_unit(p.unit_id)}
        rows = []
        for e in reversed(engine.audit):
            if event is not None and e["event"] != event:
                continue
            if patient_id is not None and patient_id not in {e.get("patient_id"), e.get("encounter_key")}:
                continue
            if allowed_keys is not None and e.get("encounter_key") not in allowed_keys:
                continue
            rows.append(e)
            if len(rows) >= limit:
                break
        total = len(engine.audit)
    return {"events": rows, "total": total}
