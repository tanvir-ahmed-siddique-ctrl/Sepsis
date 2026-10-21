"""Fleet heartbeat: patient-free payload, HMAC signature, control-plane verification."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings

pytestmark = pytest.mark.skipif(
    not (Path(settings.model_path).exists() and (Path(settings.demo_cases_dir) / "manifest.json").exists()),
    reason="model bundle or demo cases not generated",
)

CONSOLE_PATH = Path(__file__).resolve().parents[2] / "control-plane" / "fleet_console.py"
KEY = "test-fleet-signing-key"
OPERATOR = {"X-Demo-User": "fleet-ops", "X-Demo-Role": "operator"}
NURSE = {"X-Demo-User": "rn.fleet", "X-Demo-Role": "nurse"}


@pytest.fixture(scope="module")
def site():
    settings.database_url = "sqlite:///:memory:"
    settings.demo_mode = True
    settings.fleet_signing_key = KEY
    from app.main import app

    with TestClient(app, headers=OPERATOR) as client:
        client.post("/v1/demo/replay/step?hours=2", headers={"X-Demo-User": "a", "X-Demo-Role": "admin"})
        yield client
    settings.fleet_signing_key = None


@pytest.fixture()
def console():
    os.environ["FLEET_DB"] = ":memory:"
    spec = importlib.util.spec_from_file_location("fleet_console", CONSOLE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    app = module.create_app(
        {settings.site_id: {"name": "Test hospital", "key": KEY}},
        console_token="console-secret",
    )
    return TestClient(app)


def test_heartbeat_roles(site):
    assert site.get("/v1/ops/heartbeat").status_code == 200
    assert site.get("/v1/ops/heartbeat", headers=NURSE).status_code == 403


def test_heartbeat_contains_no_patient_or_user_values(site):
    body = site.get("/v1/ops/heartbeat").json()
    text = json.dumps(body)
    for forbidden in ("BED-", "replay-BED", "fleet-ops", "display_name", "patient_id", "encounter_id", "encounter_key", "bed_id"):
        assert forbidden not in text, forbidden
    assert body["signature_algorithm"] == "HMAC-SHA256"


def test_console_accepts_signed_heartbeat_and_lists_site(site, console):
    body = site.get("/v1/ops/heartbeat").json()
    assert console.post("/v1/heartbeats", json=body).status_code == 200
    assert console.post("/v1/heartbeats", json=body).status_code == 409
    assert console.get("/v1/sites").status_code == 401
    fleet = console.get("/v1/sites", headers={"Authorization": "Bearer console-secret"}).json()["sites"]
    assert fleet[0]["status"] == "online"
    assert fleet[0]["model_version"] == body["payload"]["model"]["version"]


def test_public_demo_console_is_read_only_but_still_verifies_signatures(site):
    spec = importlib.util.spec_from_file_location("fleet_console", CONSOLE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    public = TestClient(module.create_app({settings.site_id: {"name": "Demo", "key": KEY}}, public_read=True))
    body = site.get("/v1/ops/heartbeat").json()
    forged = {"payload": body["payload"], "signature": "0" * 64}
    assert public.post("/v1/heartbeats", json=forged).status_code == 401
    assert public.post("/v1/heartbeats", json=body).status_code == 200
    listed = public.get("/v1/sites").json()
    assert listed["public_read"] is True and listed["sites"][0]["status"] == "online"


def test_console_rejects_tampering_and_extra_fields(site, console):
    body = site.get("/v1/ops/heartbeat").json()
    tampered = copy.deepcopy(body)
    tampered["payload"]["activity"]["open_alerts"] += 1
    assert console.post("/v1/heartbeats", json=tampered).status_code == 401

    from app.fleet import sign

    smuggled = copy.deepcopy(body["payload"])
    smuggled["patients"] = [{"patient_id": "BED-01"}]
    resigned = {"payload": smuggled, "signature": sign(smuggled, KEY)}
    assert console.post("/v1/heartbeats", json=resigned).status_code == 422

    unknown = copy.deepcopy(body["payload"])
    unknown["site_id"] = "unknown-hospital"
    assert console.post("/v1/heartbeats", json={"payload": unknown, "signature": sign(unknown, KEY)}).status_code == 403
