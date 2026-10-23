"""U1/U2 — SMART on FHIR sandbox launch surface + CDS Hooks 2.0 cards.

Legal boundary:
* These endpoints implement our own CDS Hooks discovery/service and a
  sandbox SMART launch that reads from *this* PredictRx instance only.
* Production Epic / Oracle Health embedding requires the hospital's Vendor
  Services / app gallery registration and OAuth against *their* FHIR server.
  We never claim Showroom listing or Epic partnership from these stubs.
* Cards return informational links into our cockpit — never medication orders.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.auth import CLINICAL_ROLES, Actor, require_roles
from app.core.config import settings
from app.services.engine import get_engine

router = APIRouter(tags=["ehr-bridge"], prefix="/ehr")
OPS = require_roles(*CLINICAL_ROLES, "operator")
ADMIN = require_roles("admin")

# In-process sandbox launch tokens (demo / local only).
_SANDBOX_TOKENS: dict[str, dict[str, Any]] = {}


class CdsHookRequest(BaseModel):
    hook: str = "patient-view"
    hookInstance: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    prefetch: dict[str, Any] | None = None


def _public_base(request: Request) -> str:
    configured = (settings.cors_origins or [""])[0].rstrip("/") if settings.cors_origins else ""
    if configured and "localhost" not in configured:
        return configured
    return str(request.base_url).rstrip("/").removesuffix("/v1").rstrip("/")


@router.get("/smart/metadata")
def smart_metadata(request: Request):
    """Public SMART App Launch 2.x capability document for sandbox registration."""
    base = _public_base(request)
    return {
        "software": {"name": "PredictRx Sentinel", "version": "0.3.0"},
        "smart_version": "2.2",
        "status": "sandbox",
        "note": (
            "Sandbox SMART surface for commissioning and judge demos. "
            "Hospital Epic/Cerner production launch requires Vendor Services "
            "registration against the hospital FHIR authorization server — "
            "PredictRx remains the app owner; the EHR is the shell."
        ),
        "launch_uri": f"{base}/v1/ehr/smart/launch",
        "redirect_uri": f"{base}/v1/ehr/smart/callback",
        "sandbox_token_uri": f"{base}/v1/ehr/smart/sandbox/token",
        "scopes_requested": ["launch", "patient/*.read", "openid", "fhirUser"],
        "capabilities": [
            "launch-ehr",
            "client-public",
            "context-ehr-patient",
            "sso-openid-connect",
        ],
        "production_checklist": [
            "Register client_id with hospital EHR vendor services",
            "Point redirect_uri at hospital-approved HTTPS origin",
            "Exchange authorization code against hospital FHIR auth server",
            "Fetch Patient/Observation from hospital FHIR; score only on-prem",
        ],
    }


@router.get("/smart/launch")
def smart_launch(
    request: Request,
    iss: str | None = Query(None, description="EHR FHIR base URL"),
    launch: str | None = Query(None, description="Opaque EHR launch token"),
    patient: str | None = Query(None, description="Sandbox patient/encounter key"),
    _: Actor = Depends(OPS),
):
    """EHR launch entry. Sandbox resolves a local encounter; production needs iss OAuth."""
    engine = get_engine()
    base = _public_base(request)
    if iss and "sandbox" not in iss.lower() and not settings.demo_mode:
        return {
            "status": "needs_hospital_oauth",
            "iss": iss,
            "launch": launch,
            "next": (
                "Complete authorization code flow against the hospital FHIR "
                "authorization server, then POST the resulting access token "
                "context to /v1/ehr/smart/session (hospital install)."
            ),
            "metadata": f"{base}/v1/ehr/smart/metadata",
        }

    target = None
    if patient:
        target = engine.resolve_patient(patient)
    if target is None:
        with engine.lock:
            admitted = [p for p in engine.patients.values() if p.status == "admitted"]
            target = admitted[0] if admitted else None
    if target is None:
        raise HTTPException(status_code=404, detail="No admitted encounter available for sandbox launch")

    token = secrets.token_urlsafe(24)
    expires = datetime.now(timezone.utc) + timedelta(minutes=30)
    _SANDBOX_TOKENS[token] = {
        "encounter_key": target.encounter_key,
        "patient_id": target.patient_id,
        "expires_at": expires.isoformat(),
        "iss": iss or "predictrx-sandbox",
    }
    cockpit = f"{base}/patients/{target.encounter_key}" if base else f"/patients/{target.encounter_key}"
    return {
        "status": "sandbox_launched",
        "token_type": "Bearer",
        "access_token": token,
        "expires_in": 1800,
        "patient": target.patient_id,
        "encounter": target.encounter_id,
        "encounter_key": target.encounter_key,
        "fhirUser": "Practitioner/predictrx-sandbox",
        "cockpit_url": cockpit,
        "note": "Sandbox token reads PredictRx-local FHIR-shaped resources only.",
    }


@router.get("/smart/callback")
def smart_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    """OAuth redirect landing — documents the production hand-off; sandbox uses /launch."""
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {
        "status": "awaiting_token_exchange",
        "code_present": bool(code),
        "state": state,
        "note": (
            "In production the backend exchanges this code with the hospital "
            "authorization server. Sandbox demos use GET /v1/ehr/smart/launch instead."
        ),
    }


@router.post("/smart/sandbox/token")
def smart_sandbox_token(patient: str | None = None, actor: Actor = Depends(ADMIN)):
    """Issue a short-lived sandbox SMART token bound to a local encounter."""
    if not settings.demo_mode:
        raise HTTPException(status_code=403, detail="Sandbox tokens require DEMO_MODE=true")
    engine = get_engine()
    target = engine.resolve_patient(patient) if patient else None
    if target is None:
        with engine.lock:
            admitted = [p for p in engine.patients.values() if p.status == "admitted"]
            target = admitted[0] if admitted else None
    if target is None:
        raise HTTPException(status_code=404, detail="No admitted encounter for sandbox token")
    token = secrets.token_urlsafe(24)
    expires = datetime.now(timezone.utc) + timedelta(minutes=30)
    _SANDBOX_TOKENS[token] = {
        "encounter_key": target.encounter_key,
        "patient_id": target.patient_id,
        "expires_at": expires.isoformat(),
        "iss": "predictrx-sandbox",
        "issued_by": actor.user_id,
    }
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": 1800,
        "patient": target.patient_id,
        "encounter_key": target.encounter_key,
        "scope": "launch patient/*.read",
    }


@router.get("/smart/sandbox/Patient/{patient_id}")
def sandbox_patient(patient_id: str, request: Request):
    """FHIR-shaped Patient for sandbox SMART clients (local engine only)."""
    token = (request.headers.get("Authorization") or "").removeprefix("Bearer ").strip()
    session = _SANDBOX_TOKENS.get(token)
    if not session:
        raise HTTPException(status_code=401, detail="Valid sandbox Bearer token required")
    if datetime.fromisoformat(session["expires_at"]) < datetime.now(timezone.utc):
        _SANDBOX_TOKENS.pop(token, None)
        raise HTTPException(status_code=401, detail="Sandbox token expired")
    engine = get_engine()
    patient = engine.resolve_patient(session["encounter_key"]) or engine.resolve_patient(patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {
        "resourceType": "Patient",
        "id": patient.patient_id,
        "meta": {"source": "predictrx-sandbox"},
        "identifier": [{"system": "urn:predictrx:encounter", "value": patient.encounter_key}],
        "gender": {"M": "male", "F": "female"}.get((patient.sex or "").upper(), "unknown"),
        "extension": [
            {"url": "https://predictrx.example/fhir/StructureDefinition/unit-id", "valueString": patient.unit_id},
        ],
    }


@router.get("/cds-services")
def cds_services_discovery(request: Request):
    """CDS Hooks 2.0 discovery document (informational cards only)."""
    base = str(request.base_url).rstrip("/")
    return {
        "services": [
            {
                "hook": "patient-view",
                "title": "PredictRx Sentinel — ICU risk cockpit",
                "description": (
                    "Opens the hospital-local PredictRx patient view. "
                    "Informational only — never proposes orders or medications."
                ),
                "id": "predictrx-patient-view",
                "prefetch": {
                    "patient": "Patient/{{context.patientId}}",
                },
                "usageRequirements": "Research prototype — not approved for clinical use.",
            }
        ],
        "extension": {
            "predictrx_service_url": f"{base}/cds-services/predictrx-patient-view",
            "legal": "Hospital must register this CDS service under its own EHR CDS Hooks configuration.",
        },
    }


@router.post("/cds-services/predictrx-patient-view")
def cds_patient_view(body: CdsHookRequest, request: Request, _: Actor = Depends(OPS)):
    """patient-view hook — returns a link card into our cockpit, never orders."""
    engine = get_engine()
    base = _public_base(request)
    patient_ref = str((body.context or {}).get("patientId") or (body.context or {}).get("patient") or "")
    encounter_ref = str((body.context or {}).get("encounterId") or (body.context or {}).get("encounter") or "")
    key = None
    if patient_ref and encounter_ref:
        key = f"{patient_ref.split('/')[-1]}--{encounter_ref.split('/')[-1]}"
    elif patient_ref:
        key = patient_ref.split("/")[-1]
    patient = engine.resolve_patient(key) if key else None
    if patient is None and key:
        # Try bare patient_id match
        with engine.lock:
            for candidate in engine.patients.values():
                if candidate.patient_id == patient_ref.split("/")[-1] or candidate.encounter_key == key:
                    patient = candidate
                    break

    if patient is None:
        return {
            "cards": [
                {
                    "uuid": hashlib.sha256(f"missing|{body.hookInstance}".encode()).hexdigest()[:36],
                    "summary": "PredictRx — patient not on this ICU instance",
                    "indicator": "info",
                    "source": {"label": "PredictRx Sentinel"},
                    "detail": (
                        "No matching encounter on this hospital-local PredictRx node. "
                        "Confirm the interface feed or chart-entry path before relying on scores."
                    ),
                }
            ]
        }

    latest = patient.predictions[-1] if patient.predictions else None
    probability = latest.get("probability") if latest else None
    trust = latest.get("trust_state") if latest else "unknown"
    band = latest.get("risk_band") if latest else "n/a"
    indicator = "info"
    if trust == "alert":
        indicator = "critical"
    elif trust == "watch":
        indicator = "warning"

    cockpit = f"{base}/patients/{patient.encounter_key}"
    summary = f"PredictRx · {band}"
    if probability is not None:
        summary = f"PredictRx · {band} ({probability:.0%} calibrated)"

    return {
        "cards": [
            {
                "uuid": hashlib.sha256(f"{patient.encounter_key}|{body.hookInstance}".encode()).hexdigest()[:36],
                "summary": summary,
                "indicator": indicator,
                "source": {
                    "label": "PredictRx Sentinel",
                    "url": base or "https://predictrx.example",
                },
                "detail": (
                    f"TrustGate={trust}. Research prototype — supports clinical judgment; "
                    "does not replace it. No order actions are offered."
                ),
                "links": [
                    {
                        "label": "Open PredictRx cockpit",
                        "url": cockpit,
                        "type": "absolute",
                    }
                ],
            }
        ]
    }


@router.get("/connection-status")
def ehr_connection_status(_: Actor = Depends(OPS)):
    """Live Connection Ladder / SMART / CDS readiness for Integration Hub + /connection."""
    engine = get_engine()
    soft = bool(getattr(engine.site.state, "soft_landing", False))
    return {
        "smart": {
            "tier": "U1",
            "status": "shipped_sandbox",
            "production": "requires_hospital_vendor_services_registration",
            "metadata_path": "/v1/ehr/smart/metadata",
        },
        "cds_hooks": {
            "tier": "U2",
            "status": "shipped",
            "discovery_path": "/v1/ehr/cds-services",
            "service_id": "predictrx-patient-view",
            "orders": False,
        },
        "soft_landing": {
            "tier": "L5",
            "enabled": soft,
            "detail": "HIS keeps registration/billing; PredictRx is the ICU intelligence UI.",
        },
        "legal": {
            "epic_showroom": False,
            "note": "No Epic partnership or Showroom listing is claimed. SMART/CDS are standards we implement; gallery listing is a commercial step.",
        },
    }
