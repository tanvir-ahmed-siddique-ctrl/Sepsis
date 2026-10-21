"""Patient-free site heartbeat for the vendor control plane.

The heartbeat is built from an explicit allowlist of operational fields. It
contains no patient, encounter, bed, user or free-text values, so the vendor
can monitor many hospitals without receiving protected health information.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.pilot import evaluate_gates
from app.records import prediction_records

SCHEMA = "predictrx-heartbeat/v1"
TOP_LEVEL_KEYS = frozenset({
    "schema", "site_id", "generated_at", "release_version", "site", "model", "runtime",
    "audit", "readiness", "connectors", "activity",
})
CONNECTOR_KEYS = ("connector", "circuit", "minutes_since_success", "quarantine_rate", "pending_spool")


def canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()


def sign(payload: dict, key: str) -> str:
    return hmac.new(key.encode(), canonical(payload), hashlib.sha256).hexdigest()


def build_heartbeat(engine, connector_health: list[dict], quarantined_24h: int) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    gates = evaluate_gates(engine, connector_health)
    with engine.lock:
        audit = engine.audit_verifier.verify(engine.audit)
        state = engine.site.state
        active = sum(p.status == "admitted" and p.source_mode == "api" for p in engine.patients.values())
        open_alerts = sum(a["status"] == "open" for a in engine.alerts.values())
        shadow_alerts = sum(a["status"] == "silent" for a in engine.alerts.values())
    predictions_24h = len(engine.records.select(prediction_records, prediction_records.c.scored_at >= cutoff))
    payload = {
        "schema": SCHEMA,
        "site_id": state.site_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "release_version": settings.release_version,
        "site": {
            "effective_mode": state.effective_mode,
            "interruptive_alerts_enabled": state.interruptive_alerts_enabled,
            "demo_auth_enabled": settings.demo_mode,
        },
        "model": {"version": engine.model_version, "sha256": engine.model_hash, "frozen": engine.frozen},
        "runtime": {"read_only": engine.read_only, "database_healthy": engine.store.healthy()},
        "audit": {
            "chain_valid": bool(audit["linkage_valid"] and audit["content_hash_mismatches"] == 0),
            "events": audit["events_verified"],
        },
        "readiness": {
            "passed": sum(gate["passed"] for gate in gates),
            "total": len(gates),
            "failed_gates": [gate["gate"] for gate in gates if not gate["passed"]],
        },
        "connectors": [{key: item.get(key) for key in CONNECTOR_KEYS} for item in connector_health],
        "activity": {
            "active_live_encounters": active,
            "open_alerts": open_alerts,
            "shadow_alerts": shadow_alerts,
            "predictions_24h": predictions_24h,
            "quarantined_24h": quarantined_24h,
        },
    }
    assert set(payload) == TOP_LEVEL_KEYS
    return {
        "payload": payload,
        "signature": sign(payload, settings.fleet_signing_key) if settings.fleet_signing_key else None,
        "signature_algorithm": "HMAC-SHA256" if settings.fleet_signing_key else "unsigned",
    }
