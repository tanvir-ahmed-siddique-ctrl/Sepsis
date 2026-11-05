"""Standalone control-plane contract tests; no model bundle or hospital app needed."""

from __future__ import annotations

import copy
import hashlib
import hmac
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient


SPEC = importlib.util.spec_from_file_location("fleet_console", Path(__file__).with_name("fleet_console.py"))
assert SPEC and SPEC.loader
fleet_console = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fleet_console)
KEY = "test-fleet-key"
AUTH = {"Authorization": "Bearer console-token"}


def payload() -> dict:
    return {
        "schema": "predictrx-heartbeat/v1",
        "site_id": "site-1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "release_version": "0.3.0",
        "site": {"effective_mode": "silent", "interruptive_alerts_enabled": False, "demo_auth_enabled": False},
        "model": {"version": "v0.2.0-202609281906", "sha256": "a" * 64, "frozen": True},
        "runtime": {"read_only": False, "database_healthy": True},
        "audit": {"chain_valid": True, "events": 2},
        "readiness": {"passed": 0, "total": 10, "failed_gates": ["feeds_healthy"]},
        "connectors": [{"connector": "fhir_r4", "circuit": "closed", "minutes_since_success": None,
                        "quarantine_rate": None, "pending_spool": 0}],
        "activity": {"active_live_encounters": 0, "open_alerts": 0, "shadow_alerts": 0,
                     "predictions_24h": 0, "quarantined_24h": 0},
    }


def signed(data: dict) -> dict:
    message = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    return {"payload": data, "signature": hmac.new(KEY.encode(), message, hashlib.sha256).hexdigest()}


def client() -> TestClient:
    return TestClient(fleet_console.create_app({"site-1": {"name": "Site 1", "key": KEY,
                                                      "expected_model_sha256": "a" * 64}},
                                               console_token="console-token"))


def test_nested_metadata_contract_and_health_flags():
    app = client()
    assert app.get("/v1/sites").status_code == 401
    data = payload()
    assert app.post("/v1/heartbeats", json=signed(data)).status_code == 200
    row = app.get("/v1/sites", headers=AUTH).json()["sites"][0]
    assert row["status"] == "online"
    assert row["attention"] == []

    for field, value in (("patient_id", "abc"), ("notes", "patient details")):
        smuggled = copy.deepcopy(data)
        smuggled["activity"][field] = value
        assert client().post("/v1/heartbeats", json=signed(smuggled)).status_code == 422

    unhealthy = copy.deepcopy(data)
    unhealthy["runtime"] = {"read_only": True, "database_healthy": False}
    unhealthy["audit"]["chain_valid"] = False
    unhealthy["connectors"][0]["circuit"] = "open"
    app = client()
    assert app.post("/v1/heartbeats", json=signed(unhealthy)).status_code == 200
    codes = {item["code"] for item in app.get("/v1/sites", headers=AUTH).json()["sites"][0]["attention"]}
    assert {"read_only", "database_unhealthy", "audit_chain_invalid", "connector_circuit_open"} <= codes


def test_unreported_site_is_visible():
    row = client().get("/v1/sites", headers=AUTH).json()["sites"][0]
    assert row["attention"] == [{"code": "no_heartbeat", "severity": "warning", "message": "Site has never reported"}]
