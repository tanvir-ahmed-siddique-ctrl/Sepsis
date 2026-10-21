from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import CLINICAL_ROLES, Actor, require_roles
from app.evidence import get_evidence_graph
from app.guidelines import (
    decide_local_protocol,
    get_guideline_registry,
    guidance_for_features,
    list_local_protocols,
    search_guidance,
    submit_local_protocol,
)
from app.records import utc_now
from app.schemas import LocalProtocolRequest
from app.services.engine import get_engine

router = APIRouter(tags=["evidence"], prefix="/evidence")
CLINICAL = require_roles(*CLINICAL_ROLES)
ADMIN = require_roles("admin")


def _split(names: str) -> list[str]:
    return [name.strip() for name in names.split(",") if name.strip()][:12]


@router.get("/features")
def features_evidence(names: str = Query(..., min_length=1), _: Actor = Depends(CLINICAL)):
    graph = get_evidence_graph()
    return {"results": [graph.query_feature(name) for name in _split(names)]}


@router.get("/features/{feature}")
def feature_evidence(feature: str, _: Actor = Depends(CLINICAL)):
    return get_evidence_graph().query_feature(feature)


@router.get("/guidance")
def guidance(features: str = Query(..., min_length=1), _: Actor = Depends(CLINICAL)):
    return guidance_for_features(get_engine(), _split(features))


@router.get("/guidance/search")
def guidance_search(q: str = Query(..., min_length=2, max_length=200), _: Actor = Depends(CLINICAL)):
    return search_guidance(get_engine(), q)


@router.get("/guidelines")
def guideline_registry(_: Actor = Depends(CLINICAL)):
    registry = get_guideline_registry()
    engine = get_engine()
    return {
        "registry_id": registry.document["registry_id"],
        "version": registry.version,
        "sha256": registry.sha256,
        "status": registry.document["status"],
        "policy": registry.document["policy"],
        "sources": list(registry.sources.values()),
        "passage_count": len(registry.passages),
        "site_approval": engine.site.state.guideline_approval,
    }


@router.post("/guidelines/approve")
def approve_guideline_version(reason: str = Query(..., min_length=3, max_length=500), actor: Actor = Depends(ADMIN)):
    registry = get_guideline_registry()
    engine = get_engine()
    approval = {
        "registry_version": registry.version,
        "registry_sha256": registry.sha256,
        "approved_by": actor.user_id,
        "approved_at": utc_now(),
        "reason": reason,
    }
    engine.site.state.guideline_approval = approval
    engine.record_site_config_change("guideline_registry_approved", actor, approval)
    return approval


@router.get("/local-protocols")
def local_protocol_list(_: Actor = Depends(ADMIN)):
    return {"protocols": list_local_protocols(get_engine())}


@router.post("/local-protocols")
def local_protocol_submit(body: LocalProtocolRequest, actor: Actor = Depends(ADMIN)):
    try:
        return submit_local_protocol(get_engine(), actor, body.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/local-protocols/{entry_id}/{decision}")
def local_protocol_decide(entry_id: str, decision: str, actor: Actor = Depends(ADMIN)):
    try:
        return decide_local_protocol(get_engine(), actor, entry_id, decision)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Protocol not found") from error
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
