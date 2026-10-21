"""PredictRx Sentinel API — clinical decision support for ICU sepsis risk."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from app import ratelimit
from app.api.routes import (
    alerts,
    auth,
    care,
    demo,
    evidence,
    health,
    integrations,
    model,
    observations,
    ops,
    patients,
    pilot,
    site,
    units,
)
from app.auth import validate_security_configuration
from app.core.config import settings
from app.observability import METRICS
from app.services.engine import ModeError, ReadOnlyError, get_engine, shutdown_engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_security_configuration()
    get_engine()  # load model, take the writer lease and restore state at startup
    yield
    shutdown_engine()


app = FastAPI(
    title="PredictRx Sentinel API",
    version="0.3.0",
    description=(
        "Research prototype — not approved for clinical use. "
        "Risk scores support, but do not replace, clinical judgment."
    ),
    lifespan=lifespan,
    docs_url=None,
)


@app.get("/docs", include_in_schema=False)
async def swagger_ui() -> HTMLResponse:
    """Serve Swagger with the schema URL appropriate for this deployment."""
    return get_swagger_ui_html(
        openapi_url=settings.docs_openapi_url,
        title=f"{app.title} — API documentation",
    )

@app.middleware("http")
async def abuse_limits(request: Request, call_next):
    if not settings.rate_limit_enabled:
        return await call_next(request)
    classified = ratelimit.classify(request)
    if classified is None:
        return await call_next(request)
    bucket, client, limit = classified
    if ratelimit.oversized(request):
        METRICS.request_rejected(bucket, "too_large")
        return JSONResponse(status_code=413, content={"detail": "Request body too large."})
    retry_after = ratelimit.LIMITER.hit(bucket, client, limit)
    if retry_after is not None:
        METRICS.request_rejected(bucket, "rate_limited")
        return JSONResponse(
            status_code=429,
            content={"detail": f"Too many requests for this client ({limit}/minute). Retry later."},
            headers={"Retry-After": str(int(retry_after))},
        )
    return await call_next(request)


@app.middleware("http")
async def request_metrics(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    route = request.scope.get("route")
    METRICS.observe_request(
        request.method,
        getattr(route, "path", "unmatched"),
        response.status_code,
        time.perf_counter() - started,
    )
    return response


# Added last so it is outermost: 413/429 responses still carry CORS headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ReadOnlyError)
async def read_only_handler(_: Request, error: ReadOnlyError):
    return JSONResponse(
        status_code=503,
        content={"detail": f"Read-only degraded mode: {error}. Writes are disabled on this instance."},
    )


@app.exception_handler(ModeError)
async def mode_handler(_: Request, error: ModeError):
    return JSONResponse(status_code=409, content={"detail": str(error)})


app.include_router(health.router)
app.include_router(ops.router)
for module in (auth, care, observations, integrations, patients, alerts, units, model, demo, evidence, site, pilot):
    app.include_router(module.router, prefix="/v1")
