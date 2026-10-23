"""Connector orchestration: idempotency, unit scoping, circuit breaker, retry spool, feed health."""

from __future__ import annotations

import hashlib
import json
import statistics
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException

from app.auth import Actor
from app.core.config import settings
from app.integrations.base import CONNECTORS, MappingReport, PayloadError
from app.integrations.csv_lab import parse_csv_lab
from app.integrations.fhir import map_bundle, map_resources, parse_ndjson
from app.integrations.hl7v2 import parse_oru
from app.integrations.mapping import MappingRegistry
from app.integrations.vendor_adapter import parse_vendor_adapter
from app.observability import METRICS
from app.records import connector_events, connector_spool, ingest_requests, utc_now
from app.schemas import ObservationBatch
from app.services.engine import Engine, ReadOnlyError


@dataclass
class Circuit:
    consecutive_failures: int = 0
    opened_at: float | None = None
    last_error: str | None = None

    def state(self) -> str:
        if self.opened_at is None:
            return "closed"
        if time.time() - self.opened_at < settings.circuit_cooldown_seconds:
            return "open"
        return "half_open"


@dataclass
class SubmitResult:
    status_code: int
    body: dict[str, Any]


def _parse(connector: str, payload: str, registry: MappingRegistry) -> MappingReport:
    if connector == "native_json":
        try:
            batch = ObservationBatch.model_validate_json(payload)
        except ValueError as error:
            raise PayloadError(str(error)) from error
        report = MappingReport(observations=list(batch.observations))
        report.resources["Observation"] = len(batch.observations)
        return report
    if connector == "fhir_r4":
        try:
            document = json.loads(payload)
        except json.JSONDecodeError as error:
            raise PayloadError("FHIR payload is not valid JSON") from error
        return map_bundle(document, registry)
    if connector == "fhir_ndjson":
        return map_resources(parse_ndjson(payload), registry, source="fhir-bulk-ndjson")
    if connector == "hl7v2_oru":
        return parse_oru(payload, registry)
    if connector == "csv_lab":
        return parse_csv_lab(payload, registry)
    if connector == "vendor_adapter":
        return parse_vendor_adapter(payload, registry)
    raise PayloadError(f"Unknown connector {connector}")


def _health_key(connector: str) -> str:
    return "fhir_r4" if connector == "fhir_ndjson" else connector


class IntegrationService:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.registry = MappingRegistry(settings.fhir_mapping_path)
        self.circuits: dict[str, Circuit] = {name: Circuit() for name in CONNECTORS}
        self.lock = threading.Lock()

    # ---------- submission ----------
    def submit(
        self,
        connector: str,
        payload: str,
        actor: Actor,
        *,
        idempotency_key: str | None = None,
        backfill: bool = False,
        from_spool: str | None = None,
    ) -> SubmitResult:
        health_key = _health_key(connector)
        request_hash = hashlib.sha256(f"{connector}|{int(backfill)}|{payload}".encode()).hexdigest()
        if idempotency_key and from_spool is None:
            stored = self.engine.records.select(
                ingest_requests, ingest_requests.c.idempotency_key == idempotency_key
            )
            if stored:
                if stored[0]["request_sha256"] != request_hash:
                    raise HTTPException(status_code=409, detail="Idempotency-Key was reused with a different payload")
                body = json.loads(stored[0]["response"])
                body["idempotent_replay"] = True
                METRICS.observe_ingest(health_key, "idempotent_replay")
                return SubmitResult(200, body)

        received_at = datetime.now(timezone.utc)
        try:
            report = _parse(connector, payload, self.registry)
        except PayloadError as error:
            self._event(health_key, received_at, "rejected", actor, backfill, idempotency_key, error=str(error))
            METRICS.observe_ingest(health_key, "rejected")
            raise HTTPException(status_code=422, detail=str(error)) from error

        for observation in report.observations:
            unit = observation.unit_id or settings.api_unit_id
            if not actor.can_access_unit(unit):
                self._event(health_key, received_at, "forbidden", actor, backfill, idempotency_key,
                            error=f"unit_out_of_scope:{unit}")
                METRICS.observe_ingest(health_key, "forbidden")
                raise HTTPException(status_code=403, detail=f"Credential is not scoped to unit {unit}")

        circuit = self.circuits[health_key]
        if from_spool is None and (self.engine.read_only or circuit.state() == "open"):
            reason = self.engine.read_only_reason if self.engine.read_only else "circuit_open"
            return self._spool(connector, health_key, payload, actor, backfill, idempotency_key, received_at, reason)

        try:
            result = self.engine.ingest(
                report.observations,
                actor,
                connector=health_key,
                backfill=backfill,
                mapping_rejections=report.rejected,
            )
        except Exception as error:  # noqa: BLE001 — any engine failure is spooled for retry
            with self.lock:
                circuit.consecutive_failures += 1
                circuit.last_error = f"{type(error).__name__}: {error}"
                if circuit.consecutive_failures >= settings.circuit_failure_threshold:
                    circuit.opened_at = time.time()
            if from_spool is not None:
                raise
            reason = "read_only" if isinstance(error, ReadOnlyError) else "processing_error"
            return self._spool(connector, health_key, payload, actor, backfill, idempotency_key, received_at,
                               reason, error=circuit.last_error)
        with self.lock:
            circuit.consecutive_failures = 0
            circuit.opened_at = None

        lag_seconds = None
        if result["max_source_time"]:
            lag_seconds = max(0.0, (received_at - datetime.fromisoformat(result["max_source_time"])).total_seconds())
        status = "processed" if not result["quarantined"] else "partial"
        if from_spool is not None:
            status = "replayed"
        quarantined = len(result["quarantined"])
        self._event(
            health_key, received_at, status, actor, backfill, idempotency_key,
            received=len(report.observations) + len(report.rejected),
            accepted=result["accepted"],
            quarantined=quarantined,
            duplicates=result["duplicates_ignored"],
            max_source_time=result["max_source_time"],
            lag_seconds=lag_seconds,
            processing_ms=result["processing_ms"],
        )
        METRICS.observe_ingest(health_key, status)
        body = {
            **result,
            "connector": connector,
            "backfill": backfill,
            "mapping": {**report.summary(), "registry_version": self.registry.version},
            "site_mode": self.engine.site.state.effective_mode,
            "idempotent_replay": False,
        }
        if idempotency_key:
            self.engine.records.insert(
                ingest_requests,
                {
                    "idempotency_key": idempotency_key,
                    "connector": connector,
                    "request_sha256": request_hash,
                    "response": json.dumps(body, default=str),
                    "created_at": utc_now(),
                },
            )
        return SubmitResult(200, body)

    def _spool(
        self,
        connector: str,
        health_key: str,
        payload: str,
        actor: Actor,
        backfill: bool,
        idempotency_key: str | None,
        received_at: datetime,
        reason: str,
        error: str | None = None,
    ) -> SubmitResult:
        spool_id = f"spool-{uuid.uuid4().hex[:16]}"
        now = utc_now()
        self.engine.records.insert(
            connector_spool,
            {
                "spool_id": spool_id,
                "connector": connector,
                "received_at": now,
                "updated_at": now,
                "payload": payload,
                "status": "pending",
                "attempts": 0,
                "last_error": error or reason,
                "actor": actor.user_id,
                "backfill": int(backfill),
                "idempotency_key": idempotency_key,
            },
        )
        self._event(health_key, received_at, "spooled", actor, backfill, idempotency_key, error=error or reason)
        METRICS.observe_ingest(health_key, "spooled")
        return SubmitResult(
            202,
            {"spooled": True, "spool_id": spool_id, "reason": reason, "connector": connector,
             "detail": "Payload stored in the retry spool; an administrator can replay it once the engine recovers."},
        )

    def replay_spool(self, actor: Actor, limit: int = 100) -> dict[str, Any]:
        pending = self.engine.records.select(
            connector_spool,
            connector_spool.c.status == "pending",
            order_by=connector_spool.c.received_at,
            limit=limit,
        )
        replayed = failed = 0
        for row in pending:
            try:
                self.submit(
                    row["connector"],
                    row["payload"],
                    actor,
                    idempotency_key=row["idempotency_key"],
                    backfill=bool(row["backfill"]),
                    from_spool=row["spool_id"],
                )
                status, error = "replayed", None
                replayed += 1
            except Exception as exc:  # noqa: BLE001
                status, error = "pending", f"{type(exc).__name__}: {exc}"
                failed += 1
            self.engine.records.upsert(
                connector_spool,
                "spool_id",
                {**row, "status": status, "attempts": row["attempts"] + 1, "last_error": error, "updated_at": utc_now()},
            )
        return {"attempted": len(pending), "replayed": replayed, "still_pending": failed}

    def _event(
        self,
        connector: str,
        received_at: datetime,
        status: str,
        actor: Actor,
        backfill: bool,
        idempotency_key: str | None,
        *,
        received: int = 0,
        accepted: int = 0,
        quarantined: int = 0,
        duplicates: int = 0,
        max_source_time: str | None = None,
        lag_seconds: float | None = None,
        processing_ms: float | None = None,
        error: str | None = None,
    ) -> None:
        self.engine.records.insert(
            connector_events,
            {
                "event_id": f"evt-{uuid.uuid4().hex[:20]}",
                "connector": connector,
                "received_at": received_at.isoformat(),
                "status": status,
                "received": received,
                "accepted": accepted,
                "quarantined": quarantined,
                "duplicates": duplicates,
                "max_source_time": max_source_time,
                "lag_seconds": lag_seconds,
                "processing_ms": processing_ms,
                "error": (error or "")[:2000] or None,
                "idempotency_key": idempotency_key,
                "actor": actor.user_id,
                "backfill": int(backfill),
            },
        )

    # ---------- health ----------
    def connector_health(self) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        health = []
        for name, meta in CONNECTORS.items():
            events = self.engine.records.select(
                connector_events,
                connector_events.c.connector == name,
                order_by=connector_events.c.received_at.desc(),
                limit=50,
            )
            successes = [event for event in events if event["status"] in {"processed", "partial", "replayed"}]
            received = sum(event["received"] for event in successes)
            quarantined = sum(event["quarantined"] for event in successes)
            quarantine_rate = quarantined / received if received else None
            lags = [event["lag_seconds"] for event in successes if event["lag_seconds"] is not None and not event["backfill"]]
            processing = [event["processing_ms"] for event in successes if event["processing_ms"] is not None]
            last_success = successes[0]["received_at"] if successes else None
            minutes_since_success = (
                (now - datetime.fromisoformat(last_success)).total_seconds() / 60 if last_success else None
            )
            circuit = self.circuits[name]
            pending_spool = len(self.engine.records.select(
                connector_spool,
                connector_spool.c.status == "pending",
                connector_spool.c.connector.in_([name, "fhir_ndjson"] if name == "fhir_r4" else [name]),
            ))
            if circuit.state() == "open":
                state = "circuit_open"
            elif not events:
                state = "never_connected"
            elif minutes_since_success is None or minutes_since_success > settings.feed_stale_minutes:
                state = "stale"
            elif (quarantine_rate or 0) > 0.2 or events[0]["status"] in {"rejected", "spooled", "forbidden"}:
                state = "degraded"
            else:
                state = "healthy"
            health.append({
                "connector": name,
                **meta,
                "state": state,
                "circuit": circuit.state(),
                "consecutive_failures": circuit.consecutive_failures,
                "last_error": circuit.last_error or next((e["error"] for e in events if e["error"]), None),
                "last_received_at": events[0]["received_at"] if events else None,
                "last_success_at": last_success,
                "minutes_since_success": None if minutes_since_success is None else round(minutes_since_success, 1),
                "recent_events": len(events),
                "recent_received": received,
                "recent_quarantined": quarantined,
                "quarantine_rate": None if quarantine_rate is None else round(quarantine_rate, 4),
                "median_source_lag_minutes": round(statistics.median(lags) / 60, 1) if lags else None,
                "median_processing_ms": round(statistics.median(processing), 1) if processing else None,
                "pending_spool": pending_spool,
                "stale_after_minutes": settings.feed_stale_minutes,
            })
        return health

    def backfill_state(self) -> dict[str, Any]:
        events = self.engine.records.select(
            connector_events,
            connector_events.c.backfill == 1,
            order_by=connector_events.c.received_at.desc(),
            limit=500,
        )
        return {
            "jobs": len(events),
            "observations_accepted": sum(event["accepted"] for event in events),
            "last_backfill_at": events[0]["received_at"] if events else None,
            "alerts_policy": "Backfilled encounters are scored retrospectively; alerts are recorded as shadow only.",
        }

    def recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.engine.records.select(
            connector_events, order_by=connector_events.c.received_at.desc(), limit=limit
        )

    def quarantine(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.engine.lock:
            rows = [event for event in reversed(self.engine.audit) if event["event"] == "observation_quarantined"]
        return rows[:limit]

    def quarantine_last_24h(self) -> int:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        with self.engine.lock:
            return sum(
                1 for event in self.engine.audit
                if event["event"] == "observation_quarantined" and event["recorded_at"] >= cutoff
            )


_service: IntegrationService | None = None
_service_engine: Engine | None = None


def get_integration_service(engine: Engine) -> IntegrationService:
    global _service, _service_engine
    if _service is None or _service_engine is not engine:
        _service = IntegrationService(engine)
        _service_engine = engine
    return _service
