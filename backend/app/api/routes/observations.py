from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse

from app.auth import Actor, ensure_scope, require_roles
from app.integrations.service import get_integration_service
from app.schemas import ObservationBatch
from app.services.engine import get_engine

router = APIRouter(tags=["observations"])


@router.post("/observations/batch")
def ingest_observations(
    batch: ObservationBatch,
    idempotency_key: str | None = Header(default=None, max_length=200),
    actor: Actor = Depends(require_roles("admin", "integration")),
):
    ensure_scope(actor, "ingest:json")
    result = get_integration_service(get_engine()).submit(
        "native_json", batch.model_dump_json(), actor, idempotency_key=idempotency_key
    )
    return JSONResponse(result.body, status_code=result.status_code)
