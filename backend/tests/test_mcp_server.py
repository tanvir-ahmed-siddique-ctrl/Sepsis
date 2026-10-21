"""MCP server: read-only tools route through the metadata-only operator role."""

from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path

import pytest

from app.core.config import settings

mcp_available = importlib.util.find_spec("mcp") is not None
pytestmark = [
    pytest.mark.skipif(not mcp_available, reason="mcp SDK not installed"),
    pytest.mark.skipif(
        not (Path(settings.model_path).exists() and (Path(settings.demo_cases_dir) / "manifest.json").exists()),
        reason="model bundle or demo cases not generated",
    ),
]

SERVER_PATH = Path(__file__).resolve().parents[2] / "mcp-server" / "predictrx_mcp.py"


@pytest.fixture(scope="module")
def mcp_module():
    from fastapi.testclient import TestClient

    settings.database_url = "sqlite:///:memory:"
    settings.demo_mode = True
    from app.main import app

    spec = importlib.util.spec_from_file_location("predictrx_mcp", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    operator = {"X-Demo-User": "mcp-operator", "X-Demo-Role": "operator"}
    with TestClient(app, headers=operator) as client:
        module.client_factory = lambda: _Reusable(client)
        yield module


class _Reusable:
    def __init__(self, client):
        self.client = client

    def __enter__(self):
        return self.client

    def __exit__(self, *args):
        return False


def _call(module, name: str) -> dict:
    result = asyncio.run(module.server.call_tool(name, {}))
    if getattr(result, "structuredContent", None):
        payload = result.structuredContent
        return payload.get("result", payload)
    return json.loads(result.content[0].text)


def test_tools_are_read_only(mcp_module):
    tools = asyncio.run(mcp_module.server.list_tools())
    names = {tool.name for tool in tools}
    assert {
        "site_health", "integration_status", "readiness_gates", "model_card", "unmapped_source_codes", "fleet_heartbeat",
    } <= names
    assert all(tool.annotations and tool.annotations.read_only_hint for tool in tools)


def test_site_health_reports_frozen_model(mcp_module):
    health = _call(mcp_module, "site_health")
    assert health["model"]["frozen"] is True
    assert len(health["model"]["sha256"]) == 64


def test_integration_status_strips_encounter_counts(mcp_module):
    status = _call(mcp_module, "integration_status")
    assert "connectors" in status and "encounters" not in status
