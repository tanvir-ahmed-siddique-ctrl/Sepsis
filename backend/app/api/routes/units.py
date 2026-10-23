from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.api.deps import is_blinded
from app.auth import CLINICAL_ROLES, Actor, ensure_unit, require_roles
from app.core.config import settings
from app.schemas import PatientOverviewCard, UnitOverviewResponse
from app.services.engine import BAND_ORDER, REQUIRED_SIGNALS, Engine, Patient, get_engine

router = APIRouter(tags=["units"])
TRUST_ORDER = {"alert": 4, "verify_data": 3, "watch": 2, "abstain": 1}
CLINICAL = require_roles(*CLINICAL_ROLES)


def _minutes_since(stamp: str | None) -> int | None:
    if not stamp:
        return None
    return int((datetime.now(timezone.utc) - datetime.fromisoformat(stamp)).total_seconds() // 60)


def _open_alerts(engine: Engine, patient: Patient) -> list[dict]:
    now = datetime.now(timezone.utc)
    open_rows: list[dict] = []
    for alert in engine.alerts.values():
        if alert.get("encounter_key") != patient.encounter_key:
            continue
        if alert["status"] == "open":
            open_rows.append(alert)
            continue
        if alert["status"] == "snoozed":
            until = alert.get("snoozed_until")
            if until and datetime.fromisoformat(until) <= now:
                alert["status"] = "open"
                alert.pop("snoozed_until", None)
                open_rows.append(alert)
    return sorted(open_rows, key=lambda alert: alert.get("raised_at") or "")


def _data_gaps(prediction: dict) -> list[str]:
    freshness = prediction.get("signal_freshness_minutes", {})
    gaps = []
    for signal in REQUIRED_SIGNALS:
        value = freshness.get(signal)
        if value is None:
            gaps.append(f"{signal} missing")
        elif value > 120:
            gaps.append(f"{signal} {value} min old")
    return gaps


def _urgency(trust_state: str, band: str, open_alerts: int, probability: float | None) -> tuple:
    return (-TRUST_ORDER.get(trust_state, 0), -BAND_ORDER[band], -min(open_alerts, 1), -(probability or 0))


@router.get("/units")
def list_units(actor: Actor = Depends(CLINICAL)):
    engine = get_engine()
    with engine.lock:
        units = sorted({
            p.unit_id
            for p in engine.patients.values()
            if p.status == "admitted" and actor.can_access_unit(p.unit_id)
        })
    return {"units": units, "default_unit": settings.demo_unit_id if settings.demo_unit_id in units else (units[0] if units else None)}


@router.get("/units/{unit_id}/overview", response_model=UnitOverviewResponse)
def unit_overview(unit_id: str, actor: Actor = Depends(CLINICAL)):
    ensure_unit(actor, unit_id)
    engine = get_engine()
    sla = settings.alert_review_sla_minutes
    cards = []
    blinded = 0
    with engine.lock:
        for p in engine.patients.values():
            if p.unit_id != unit_id or p.kind != "icu" or p.status != "admitted" or not p.predictions:
                continue
            if is_blinded(engine, actor, p):
                blinded += 1
                continue
            latest = p.predictions[-1]
            open_alerts = _open_alerts(engine, p)
            oldest = _minutes_since(open_alerts[0].get("raised_at")) if open_alerts else None
            owner = engine.ownership.get(p.encounter_key)
            cards.append(PatientOverviewCard(
                patient_id=p.encounter_key,
                encounter_id=p.encounter_id,
                encounter_key=p.encounter_key,
                display_name=p.display_name,
                risk_band=latest["risk_band"],
                probability=latest["probability"],
                uncertainty=latest["uncertainty"],
                hour=latest["hour"],
                scored_at=latest.get("scored_at"),
                data_freshness_minutes=latest["data_freshness_minutes"],
                trust_state=latest["trustgate"]["state"],
                unresolved_alerts=len(open_alerts),
                open_alert_id=open_alerts[0]["alert_id"] if open_alerts else None,
                trend=[pt["probability"] for pt in p.predictions[-12:]],
                age=p.age,
                sex=p.sex,
                source_mode=p.source_mode,
                owner=owner["owner"] if owner else None,
                oldest_open_alert_minutes=oldest,
                review_overdue=oldest is not None and oldest > sla,
                missing_required_signals=[gap.split(" ")[0] for gap in _data_gaps(latest)],
            ))
        state = engine.site.state
    cards.sort(key=lambda c: _urgency(c.trust_state, c.risk_band.value, c.unresolved_alerts, c.probability))
    return UnitOverviewResponse(
        unit_id=unit_id,
        patients=cards,
        watch_count=sum(c.trust_state == "watch" for c in cards),
        high_risk_count=sum(c.trust_state == "alert" for c in cards),
        verify_count=sum(c.trust_state == "verify_data" for c in cards),
        abstain_count=sum(c.trust_state == "abstain" for c in cards),
        open_alerts=sum(c.unresolved_alerts for c in cards),
        overdue_reviews=sum(c.review_overdue for c in cards),
        model_version=engine.model_version,
        thresholds=engine.thresholds,
        site_mode=state.effective_mode,
        interruptive_alerts_enabled=state.interruptive_alerts_enabled,
        bedside_blinded=state.blinded,
        blinded_encounters=blinded,
        review_sla_minutes=sla,
        disclaimer=settings.disclaimer,
    )


@router.get("/units/{unit_id}/handoff")
def unit_handoff(unit_id: str, actor: Actor = Depends(CLINICAL)):
    """Deterministic shift-handoff summary assembled from recorded data — nothing is generated."""
    ensure_unit(actor, unit_id)
    engine = get_engine()
    sla = settings.alert_review_sla_minutes
    beds = []
    with engine.lock:
        for p in engine.patients.values():
            if (
                p.unit_id != unit_id
                or p.kind != "icu"
                or p.status != "admitted"
                or not p.predictions
                or is_blinded(engine, actor, p)
            ):
                continue
            latest = p.predictions[-1]
            earlier = p.predictions[-7] if len(p.predictions) >= 7 else None
            delta = None
            if earlier and earlier["probability"] is not None and latest["probability"] is not None:
                delta = latest["probability"] - earlier["probability"]
            trend = "unknown" if delta is None else ("rising" if delta >= 0.02 else "falling" if delta <= -0.02 else "steady")
            open_alerts = _open_alerts(engine, p)
            open_alert = None
            if open_alerts:
                minutes = _minutes_since(open_alerts[0].get("raised_at"))
                open_alert = {
                    "alert_id": open_alerts[0]["alert_id"],
                    "minutes_open": minutes,
                    "overdue": minutes is not None and minutes > sla,
                    "reason": open_alerts[0]["reason"],
                }
            actions = [
                {**action, "alert_id": alert["alert_id"]}
                for alert in engine.alerts.values() if alert.get("encounter_key") == p.encounter_key
                for action in alert.get("actions", [])
            ]
            last_action = max(actions, key=lambda action: action["at"]) if actions else None
            owner = engine.ownership.get(p.encounter_key)
            beds.append({
                "patient_id": p.encounter_key,
                "display_name": p.display_name,
                "source_mode": p.source_mode,
                "owner": owner,
                "hour": latest["hour"],
                "risk_band": latest["risk_band"],
                "probability": latest["probability"],
                "probability_6h_ago": earlier["probability"] if earlier else None,
                "trend": trend,
                "trust_state": latest["trustgate"]["state"],
                "trust_reasons": latest["trustgate"]["reasons"],
                "open_alert": open_alert,
                "last_alert_action": last_action,
                "data_gaps": _data_gaps(latest),
                "top_factors": [f["plain_language"] for f in latest.get("factors", [])[:3]],
                "notes": engine.handoff_notes_for(p.encounter_key, 3),
            })
    beds.sort(key=lambda b: _urgency(b["trust_state"], b["risk_band"], 1 if b["open_alert"] else 0, b["probability"]))
    return {
        "unit_id": unit_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "review_sla_minutes": sla,
        "beds": beds,
        "note": "Assembled from recorded scores, alerts, actions and clinician notes. No text is generated.",
        "disclaimer": settings.disclaimer,
    }
