import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from app.auth import Actor, ensure_scope, ensure_unit, require_roles
from app.core.config import settings
from app.integrations import copilot
from app.integrations.base import PayloadError
from app.integrations.hl7v2 import parse_adt
from app.integrations.service import get_integration_service
from app.integrations.synthetic import synthetic_bundle, synthetic_oru
from app.records import connector_spool
from app.schemas import MappingSignoffRequest, MappingSuggestRequest
from app.services.engine import get_engine

router = APIRouter(tags=["integrations"], prefix="/integrations")
INGEST = require_roles("admin", "integration")
ADMIN = require_roles("admin")
OPERATIONS = require_roles("admin", "operator")
MAX_PAYLOAD_BYTES = 10 * 1024 * 1024


async def _body(request: Request) -> str:
    raw = await request.body()
    if len(raw) > MAX_PAYLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Payload exceeds 10 MB; split Bulk Data files")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise HTTPException(status_code=422, detail="Payload must be UTF-8") from error


def _submit(connector: str, payload: str, actor: Actor, idempotency_key: str | None, backfill: bool) -> JSONResponse:
    engine = get_engine()
    if "synthetic-integration-test" in payload and engine.site.state.effective_mode != "demo":
        raise HTTPException(
            status_code=422,
            detail="Synthetic (Synthea-style) payloads are integration-test data and are refused outside demo mode.",
        )
    result = get_integration_service(engine).submit(
        connector, payload, actor, idempotency_key=idempotency_key, backfill=backfill
    )
    return JSONResponse(result.body, status_code=result.status_code)


def _adt_encounter(patient) -> dict:
    return {
        "encounter_key": patient.encounter_key,
        "patient_id": patient.patient_id,
        "encounter_id": patient.encounter_id,
        "display_name": patient.display_name,
        "unit_id": patient.unit_id,
        "bed_id": patient.bed_id,
        "kind": patient.kind,
        "status": patient.status,
    }


@router.post("/fhir/bundle")
async def ingest_fhir_bundle(
    request: Request,
    backfill: bool = Query(False, description="Retrospective import: scored, alerts recorded as shadow only"),
    idempotency_key: str | None = Header(default=None, max_length=200),
    actor: Actor = Depends(INGEST),
):
    ensure_scope(actor, "ingest:fhir")
    return _submit("fhir_r4", await _body(request), actor, idempotency_key, backfill)


@router.post("/fhir/ndjson")
async def ingest_fhir_ndjson(
    request: Request,
    backfill: bool = Query(True, description="Bulk Data exports are retrospective by default"),
    idempotency_key: str | None = Header(default=None, max_length=200),
    actor: Actor = Depends(INGEST),
):
    ensure_scope(actor, "ingest:fhir")
    return _submit("fhir_ndjson", await _body(request), actor, idempotency_key, backfill)


@router.post("/hl7v2/oru")
async def ingest_hl7v2(
    request: Request,
    idempotency_key: str | None = Header(default=None, max_length=200),
    actor: Actor = Depends(INGEST),
):
    ensure_scope(actor, "ingest:hl7v2")
    return _submit("hl7v2_oru", await _body(request), actor, idempotency_key, False)


@router.post("/hl7v2/adt")
async def ingest_hl7v2_adt(request: Request, actor: Actor = Depends(INGEST)):
    """Apply the bounded ADT A01/A02/A03 contract to the site census."""
    ensure_scope(actor, "ingest:hl7v2")
    try:
        event = parse_adt(await _body(request))
    except PayloadError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    engine = get_engine()
    key = f"{event['patient_id']}--{event['encounter_id']}"
    patient = engine.resolve_patient(key)
    event_code = str(event["event"])
    target_unit = str(event["unit_id"]) if event["unit_id"] else None
    if patient is not None:
        ensure_unit(actor, patient.unit_id)
    if target_unit:
        ensure_unit(actor, target_unit)
    try:
        if event_code == "A01":
            if patient is not None and patient.status == "admitted":
                duplicate = True
            else:
                patient = engine.admit_encounter(
                    patient_id=str(event["patient_id"]),
                    encounter_id=str(event["encounter_id"]),
                    display_name=str(event["display_name"]),
                    unit_id=target_unit or "",
                    bed_id=str(event["bed_id"]) if event["bed_id"] else None,
                    age=None,
                    sex=str(event["sex"]) if event["sex"] else None,
                    hypercapnic_scale2=False,
                    actor=actor,
                )
                duplicate = False
        elif event_code == "A02":
            if patient is None or patient.status != "admitted":
                raise ValueError("ADT transfer references an encounter that is not admitted")
            bed_id = str(event["bed_id"]) if event["bed_id"] else None
            duplicate = patient.unit_id == target_unit and patient.bed_id == bed_id
            if not duplicate:
                patient = engine.transfer_encounter(patient, target_unit or "", bed_id, actor)
        else:
            if patient is None:
                raise ValueError("ADT discharge references an unknown encounter")
            duplicate = patient.status == "discharged"
            if not duplicate:
                patient = engine.discharge_encounter(patient, actor)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {
        "connector": "hl7v2_adt",
        "event": event_code,
        "duplicate": duplicate,
        "encounter": _adt_encounter(patient),
        "contract": "synthetic-tested; partner PV1/PID conformance sign-off required",
    }


@router.post("/csv/lab")
async def ingest_lab_csv(
    request: Request,
    backfill: bool = Query(False, description="Retrospective import: scored, alerts recorded as shadow only"),
    idempotency_key: str | None = Header(default=None, max_length=200),
    actor: Actor = Depends(INGEST),
):
    ensure_scope(actor, "ingest:json")
    return _submit("csv_lab", await _body(request), actor, idempotency_key, backfill)


@router.get("/status")
def integration_status(_: Actor = Depends(OPERATIONS)):
    engine = get_engine()
    service = get_integration_service(engine)
    health = service.connector_health()
    with engine.lock:
        replay = sum(p.source_mode == "replay" for p in engine.patients.values())
        api = sum(p.source_mode == "api" for p in engine.patients.values())
        units = sorted({p.unit_id for p in engine.patients.values() if p.source_mode == "api"})
    connected = [item for item in health if item["state"] != "never_connected"]
    mapping_signoff = engine.site.state.mapping_signoff
    mapping_ready = bool(mapping_signoff and mapping_signoff.get("registry_sha256") == service.registry.sha256)
    return {
        "site": engine.site.state.as_dict(),
        "simulation_mode": settings.public_demo_lockdown,
        "connectors": health,
        "feed_alarm": any(item["state"] in {"stale", "circuit_open"} for item in connected),
        "mapping_registry": {
            "version": service.registry.version,
            "sha256": service.registry.sha256,
            "entries": len(service.registry.entries),
            "status": "ready" if mapping_ready else service.registry.document["status"],
            "signoff": mapping_signoff if mapping_ready else None,
        },
        "encounters": {"api": api, "replay": replay, "api_units": units},
        "replay": {"enabled": engine.site.state.effective_mode == "demo", "beds": replay},
        "backfill": service.backfill_state(),
        "quarantined_last_24h": service.quarantine_last_24h(),
        "operation": {
            "read_only": engine.read_only,
            "read_only_reason": engine.read_only_reason,
            "external_network_required": False,
            "offline_note": "Scoring, audit and the evidence copilot run on site; no internet connection is used."
            + (" The mapping copilot's model is an approved external API that receives field names and units only."
               if copilot.llm_endpoint()["external"] else ""),
            "copilot_llm": {**copilot.llm_endpoint(), "configured": bool(settings.copilot_llm_url),
                            "model": settings.copilot_llm_model if settings.copilot_llm_url else None},
        },
        "roadmap": {
            "smart_on_fhir": "SMART App Launch 2.2 (EHR launch) — planned EHR-embedded patient view.",
            "cds_hooks": "CDS Hooks 2.0 patient-view card — planned; returns links to this cockpit, never orders.",
            "bulk_data": "FHIR Bulk Data 3.0 $export NDJSON → POST /v1/integrations/fhir/ndjson for retrospective validation.",
        },
    }


@router.get("/mappings")
def mapping_registry(_: Actor = Depends(require_roles("admin", "integration", "operator"))):
    return get_integration_service(get_engine()).registry.describe()


@router.post("/mappings/signoff")
def signoff_mapping_registry(body: MappingSignoffRequest, actor: Actor = Depends(ADMIN)):
    engine = get_engine()
    registry = get_integration_service(engine).registry
    if body.registry_sha256 != registry.sha256:
        raise HTTPException(status_code=409, detail="Mapping registry changed; review and sign the current SHA-256")
    signoff = {
        **body.model_dump(),
        "recorded_by": actor.user_id,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    engine.site.state.mapping_signoff = signoff
    engine.record_site_config_change("mapping_registry_signed_off", actor, signoff)
    return signoff


@router.post("/mappings/suggest")
def suggest_mapping(body: MappingSuggestRequest, actor: Actor = Depends(ADMIN)):
    engine = get_engine()
    registry = get_integration_service(engine).registry
    try:
        result = copilot.suggest(registry, **body.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    engine._log("mapping_suggestion_generated", {
        "actor": actor.user_id,
        "actor_role": actor.role,
        "local_code": body.local_code,
        "recommended_code": result["recommended_code"],
        "llm_status": result["llm"]["status"],
        "llm_host": result["llm"].get("host"),
        "prompt_sha256": result["prompt"]["sha256"],
        "registry_sha256": registry.sha256,
    })
    return result


@router.get("/mappings/unmapped")
def unmapped_codes(_: Actor = Depends(OPERATIONS)):
    counts: dict[str, int] = {}
    for event in get_integration_service(get_engine()).quarantine(500):
        reason = str(event.get("reason", ""))
        if "unmapped_code:" in reason:
            code = reason.split("unmapped_code:", 1)[1]
            counts[code] = counts.get(code, 0) + 1
    return {
        "unmapped": [{"source_code": code, "rejections": n} for code, n in sorted(counts.items(), key=lambda kv: -kv[1])],
        "note": "Aggregated source codes only; no patient identifiers.",
    }


@router.get("/quarantine")
def quarantine(limit: int = Query(100, ge=1, le=500), _: Actor = Depends(ADMIN)):
    return {"events": get_integration_service(get_engine()).quarantine(limit)}


@router.get("/events")
def connector_events(limit: int = Query(50, ge=1, le=500), _: Actor = Depends(ADMIN)):
    return {"events": get_integration_service(get_engine()).recent_events(limit)}


@router.get("/spool")
def spool(_: Actor = Depends(ADMIN)):
    rows = get_engine().records.select(connector_spool, order_by=connector_spool.c.received_at.desc(), limit=200)
    return {"items": [{key: value for key, value in row.items() if key != "payload"} for row in rows]}


@router.post("/spool/replay")
def replay_spool(actor: Actor = Depends(ADMIN)):
    engine = get_engine()
    return get_integration_service(engine).replay_spool(actor)


@router.get("/samples/fhir-bundle")
def sample_fhir_bundle(
    patient_id: str = Query("synthetic-001", min_length=1, max_length=64),
    hours: int = Query(12, ge=4, le=48),
    deteriorating: bool = True,
    unit_id: str = Query(settings.api_unit_id, min_length=1, max_length=64),
    _: Actor = Depends(ADMIN),
):
    return synthetic_bundle(
        patient_id=patient_id,
        encounter_id=f"{patient_id}-enc",
        unit_id=unit_id,
        hours=hours,
        deteriorating=deteriorating,
    )


@router.get("/samples/hl7v2")
def sample_hl7(_: Actor = Depends(ADMIN)):
    return {"message": synthetic_oru(), "content_type": "text/plain (segments separated by carriage returns)"}


@router.post("/samples/load")
def load_synthetic_samples(actor: Actor = Depends(ADMIN)):
    """Demo only: push three Synthea-style encounters through the FHIR connector."""
    engine = get_engine()
    if engine.site.state.effective_mode != "demo":
        raise HTTPException(status_code=409, detail="Synthetic samples can only be loaded in demo mode")
    start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) - timedelta(hours=12)
    service = get_integration_service(engine)
    results = []
    for index, deteriorating in enumerate((True, True, False), start=1):
        bundle = synthetic_bundle(
            patient_id=f"synthetic-{index:03d}",
            encounter_id=f"synthetic-enc-{index:03d}",
            unit_id=settings.api_unit_id,
            start=start,
            hours=12,
            deteriorating=deteriorating,
            age_years=55 + 9 * index,
            gender="female" if index == 2 else "male",
        )
        result = service.submit("fhir_r4", json.dumps(bundle), actor)
        results.append({"patient_id": f"synthetic-{index:03d}", "status_code": result.status_code,
                        "accepted": result.body.get("accepted"), "quarantined": len(result.body.get("quarantined", []))})
    return {"unit_id": settings.api_unit_id, "loaded": results,
            "note": "Synthetic integration-test encounters — not model evidence."}
