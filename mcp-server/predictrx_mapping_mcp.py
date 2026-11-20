"""PredictRx mapping MCP — read-only LOINC registry + unmapped source codes.

Side-branch for Bangla/local lab mapping agents. Never exposes patient charts.
Run (stdio):  python mcp-server/predictrx_mapping_mcp.py
Environment:  PREDICTRX_API_URL, PREDICTRX_API_TOKEN, PREDICTRX_DEMO=1
"""

from __future__ import annotations

import os
from typing import Any, Callable

import httpx
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

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
    name="predictrx-mapping",
    title="PredictRx Sentinel (mapping registry)",
    instructions=(
        "Read-only LOINC/local mapping registry and unmapped source codes for integration agents. "
        "No patient identifiers. Mapping proposals still require human sign-off in the product UI."
    ),
    version="1.0.0",
)


@server.tool(description="Versioned code/unit mapping registry with its SHA-256.", annotations=READ_ONLY)
def mapping_registry() -> dict[str, Any]:
    return _get("/v1/integrations/mappings")


@server.tool(description="Source codes rejected as unmapped, aggregated without patient identifiers.", annotations=READ_ONLY)
def unmapped_source_codes() -> dict[str, Any]:
    return _get("/v1/integrations/mappings/unmapped")


@server.tool(description="Connector feed states, lag, quarantine count and mapping-registry status.", annotations=READ_ONLY)
def integration_status() -> dict[str, Any]:
    status = _get("/v1/integrations/status")
    status.pop("encounters", None)
    return status


if __name__ == "__main__":
    server.run("stdio")
