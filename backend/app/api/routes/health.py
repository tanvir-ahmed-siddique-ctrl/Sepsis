from fastapi import APIRouter, Response, status

from app.core.config import settings
from app.guidelines import get_guideline_registry
from app.integrations.mapping import MappingRegistry
from app.services.engine import get_engine

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    engine = get_engine()
    return {
        "status": "ok",
        "service": settings.app_name,
        "model_version": engine.model_version,
        "model_frozen": engine.frozen,
        "site_mode": engine.site.state.effective_mode,
        "read_only": engine.read_only,
        "replay_patients": sum(patient.source_mode == "replay" for patient in engine.patients.values()),
        "disclaimer": settings.disclaimer,
    }


def _loads(factory) -> bool:
    try:
        factory()
        return True
    except Exception:
        return False


@router.get("/ready")
def readiness(response: Response):
    """Production readiness. Replay cases are required only while the site runs in demo mode."""
    engine = get_engine()
    demo = engine.site.state.effective_mode == "demo"
    checks = {
        "model_loaded": bool(engine.model_version),
        "model_frozen": engine.frozen,
        "database": engine.store.healthy(),
        "writer_lease": not engine.read_only,
        "mapping_registry": _loads(lambda: MappingRegistry(settings.fhir_mapping_path)),
        "guideline_registry": _loads(get_guideline_registry),
    }
    if demo:
        checks["replay_cases"] = any(patient.source_mode == "replay" for patient in engine.patients.values())
    ready = all(checks.values())
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ready" if ready else "not_ready",
        "checks": checks,
        "site_mode": engine.site.state.effective_mode,
        "read_only_reason": engine.read_only_reason,
        "model_version": engine.model_version,
        "model_hash": engine.model_hash,
    }
