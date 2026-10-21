"""PredictRx Sentinel MCP server — read-only deployment metadata for AI assistants.

Exposes site health, integration feeds, readiness gates, model provenance and
unmapped source codes from a running PredictRx API so an operator can ask an
assistant (Cursor, Claude Desktop, any MCP client) "is the site ready, and what
is blocking it?". It authenticates as the metadata-only ``operator`` role, so
the API itself refuses patient lists, charts, alerts and audit events.

Run (stdio):  python mcp-server/predictrx_mcp.py
Environment:  PREDICTRX_API_URL   default http://127.0.0.1:8000
              PREDICTRX_API_TOKEN bearer token of an operator account
              PREDICTRX_DEMO=1    use demo operator headers (demo sites only)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

import httpx
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

ROOT = Path(__file__).resolve().parents[1]
DOCS = {
    "model-card": ROOT / "docs" / "model-card.md",
    "safety-ethics": ROOT / "docs" / "safety-ethics.md",
    "hospital-onboarding": ROOT / "docs" / "hospital-onboarding.md",
}
READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)


def _default_client() -> httpx.Client:
    headers = {}
    if token := os.environ.get("PREDICTRX_API_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    elif os.environ.get("PREDICTRX_DEMO") == "1":
        headers.update({"X-Demo-User": "mcp-operator", "X-Demo-Role": "operator"})
    return httpx.Client(base_url=os.environ.get("PREDICTRX_API_URL", "http://127.0.0.1:8000"), headers=headers, timeout=15)


client_factory: Callable[[], httpx.Client] = _default_client


def _get(path: str) -> dict[str, Any]:
    with client_factory() as client:
        response = client.get(path)
    if response.status_code in (401, 403):
        return {"error": "not_authorised", "detail": "Configure an operator token; patient-level data is never exposed."}
    response.raise_for_status()
    return response.json()


server = MCPServer(
    name="predictrx-sentinel",
    title="PredictRx Sentinel (read-only operations)",
    instructions=(
        "Read-only deployment metadata for a PredictRx Sentinel ICU site. No patient data is available. "
        "Never present model output as a diagnosis; the site may be in demo or silent mode."
    ),
    version="1.0.0",
)


@server.tool(description="Database, writer, audit-chain integrity, frozen model hash and site mode.", annotations=READ_ONLY)
def site_health() -> dict[str, Any]:
    return _get("/v1/ops/status")


@server.tool(description="Connector feed states, lag, quarantine count and mapping-registry status.", annotations=READ_ONLY)
def integration_status() -> dict[str, Any]:
    status = _get("/v1/integrations/status")
    status.pop("encounters", None)
    return status


@server.tool(description="SafeLaunch gates that must all pass before interruptive alerts may be enabled.", annotations=READ_ONLY)
def readiness_gates() -> dict[str, Any]:
    return _get("/v1/site/readiness")


@server.tool(description="Hospital readiness passport: blockers, next actions and evidence limitations.", annotations=READ_ONLY)
def readiness_passport() -> dict[str, Any]:
    return _get("/v1/model/passport")


@server.tool(description="Model card: version, frozen SHA-256, validation metrics and stated limitations.", annotations=READ_ONLY)
def model_card() -> dict[str, Any]:
    return _get("/v1/model")


@server.tool(description="Source codes rejected as unmapped, aggregated without patient identifiers.", annotations=READ_ONLY)
def unmapped_source_codes() -> dict[str, Any]:
    return _get("/v1/integrations/mappings/unmapped")


@server.tool(description="Allowlisted, patient-free fleet heartbeat exactly as sent to the vendor control plane.", annotations=READ_ONLY)
def fleet_heartbeat() -> dict[str, Any]:
    return _get("/v1/ops/heartbeat")


@server.tool(description="Versioned code/unit mapping registry with its SHA-256.", annotations=READ_ONLY)
def mapping_registry() -> dict[str, Any]:
    return _get("/v1/integrations/mappings")


def _doc(key: str) -> str:
    return DOCS[key].read_text(encoding="utf-8")


@server.resource("predictrx://docs/model-card", name="Model card", mime_type="text/markdown")
def model_card_doc() -> str:
    return _doc("model-card")


@server.resource("predictrx://docs/safety-ethics", name="Safety and ethics", mime_type="text/markdown")
def safety_doc() -> str:
    return _doc("safety-ethics")


@server.resource("predictrx://docs/hospital-onboarding", name="Hospital onboarding", mime_type="text/markdown")
def onboarding_doc() -> str:
    return _doc("hospital-onboarding")


if __name__ == "__main__":
    server.run("stdio")
