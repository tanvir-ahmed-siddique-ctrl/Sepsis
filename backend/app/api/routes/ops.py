import hmac
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import PlainTextResponse

from app.auth import Actor, authenticate, require_roles
from app.core.config import settings
from app.fleet import build_heartbeat
from app.integrations.service import get_integration_service
from app.observability import render_prometheus
from app.records import prediction_records
from app.services.engine import LEASE_KEY, get_engine

router = APIRouter(tags=["ops"])
ADMIN = require_roles("admin")
OPERATIONS = require_roles("admin", "operator")


def _metrics_access(
    authorization: str | None = Header(default=None),
    x_integration_key: str | None = Header(default=None),
    x_demo_user: str | None = Header(default=None),
    x_demo_role: str | None = Header(default=None),
) -> None:
    if settings.metrics_token and authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and hmac.compare_digest(token, settings.metrics_token):
            return
    actor = authenticate(authorization, x_integration_key, x_demo_user, x_demo_role)
    if not actor.roles & {"admin", "operator"}:
        raise HTTPException(status_code=403, detail="Insufficient role")


def _drift_window(engine) -> dict[str, float]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    rows = engine.records.select(prediction_records, prediction_records.c.scored_at >= cutoff)
    scored = [row["probability"] for row in rows if row["probability"] is not None]
    shifts = [row["input_shift"] for row in rows if row["input_shift"] is not None]
    missing = [row for row in rows if row["data_quality"] == "missing_required_vitals"]
    return {
        "predictions": float(len(rows)),
        "mean_probability": round(sum(scored) / len(scored), 6) if scored else 0.0,
        "mean_input_shift": round(sum(shifts) / len(shifts), 6) if shifts else 0.0,
        "missing_required_rate": round(len(missing) / len(rows), 6) if rows else 0.0,
    }


@router.get("/metrics", response_class=PlainTextResponse)
def prometheus_metrics(_: None = Depends(_metrics_access)):
    engine = get_engine()
    service = get_integration_service(engine)
    health = service.connector_health()
    with engine.lock:
        audit = engine.audit_verifier.verify(engine.audit)
        open_alerts = sum(a["status"] == "open" for a in engine.alerts.values())
        silent_alerts = sum(a["status"] == "silent" for a in engine.alerts.values())
        patients = {mode: sum(p.source_mode == mode for p in engine.patients.values()) for mode in ("api", "replay")}
    drift = _drift_window(engine)
    gauges = {
        "predictrx_feed_minutes_since_success": [
            ({"connector": item["connector"]}, item["minutes_since_success"] if item["minutes_since_success"] is not None else -1)
            for item in health
        ],
        "predictrx_feed_median_source_lag_minutes": [
            ({"connector": item["connector"]}, item["median_source_lag_minutes"] or 0) for item in health
        ],
        "predictrx_feed_quarantine_rate": [
            ({"connector": item["connector"]}, item["quarantine_rate"] or 0) for item in health
        ],
        "predictrx_feed_circuit_open": [
            ({"connector": item["connector"]}, int(item["circuit"] == "open")) for item in health
        ],
        "predictrx_spool_pending": [({"connector": item["connector"]}, item["pending_spool"]) for item in health],
        "predictrx_quarantined_last_24h": [({}, service.quarantine_last_24h())],
        "predictrx_alerts_open": [({}, open_alerts)],
        "predictrx_alerts_shadow_active": [({}, silent_alerts)],
        "predictrx_encounters": [({"source": mode}, count) for mode, count in patients.items()],
        "predictrx_predictions_24h": [({}, drift["predictions"])],
        "predictrx_drift_mean_probability_24h": [({}, drift["mean_probability"])],
        "predictrx_drift_mean_input_shift_24h": [({}, drift["mean_input_shift"])],
        "predictrx_drift_missing_required_rate_24h": [({}, drift["missing_required_rate"])],
        "predictrx_audit_chain_valid": [({}, int(audit["linkage_valid"] and audit["content_hash_mismatches"] == 0))],
        "predictrx_audit_events": [({}, audit["events_verified"])],
        "predictrx_read_only": [({}, int(engine.read_only))],
        "predictrx_site_interruptive_alerts_enabled": [({}, int(engine.site.state.interruptive_alerts_enabled))],
    }
    return PlainTextResponse(render_prometheus(gauges), media_type="text/plain; version=0.0.4")


@router.get("/v1/ops/status")
def ops_status(_: Actor = Depends(OPERATIONS)):
    engine = get_engine()
    with engine.lock:
        audit = engine.audit_verifier.verify(engine.audit)
    return {
        "writer": {
            "this_instance": engine.writer_id,
            "read_only": engine.read_only,
            "read_only_reason": engine.read_only_reason,
            "lease": engine.records.lease_info(LEASE_KEY),
            "lease_seconds": settings.writer_lease_seconds,
            "horizontal_scaling": "disabled — single active writer until state is fully row-level",
        },
        "database": {"healthy": engine.store.healthy(), "dialect": engine.store.engine.dialect.name},
        "audit": audit,
        "model": {"version": engine.model_version, "sha256": engine.model_hash, "frozen": engine.frozen},
        "site": engine.site.state.as_dict(),
        "retention_days": settings.retention_days,
    }


@router.get("/v1/ops/heartbeat")
def fleet_heartbeat(_: Actor = Depends(OPERATIONS)):
    engine = get_engine()
    service = get_integration_service(engine)
    return build_heartbeat(engine, service.connector_health(), service.quarantine_last_24h())


@router.get("/v1/ops/audit/verify")
def audit_verify(_: Actor = Depends(OPERATIONS)):
    engine = get_engine()
    with engine.lock:
        return engine.audit_verifier.verify(engine.audit)
