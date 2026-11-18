"""Offline signed licence verification and safe site-mode gating."""

from __future__ import annotations

import base64
import json
import threading
from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import HTTPException

from app.api.routes import site
from app.core.config import settings
from app.licensing import canonical, status, verify_package
from app.schemas import SiteModeRequest


def signed_package(monkeypatch, site_id="hospital-icu", expires_days=30, modules=None, entitlement_status="active"):
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    monkeypatch.setattr(settings, "licence_public_keys_json", json.dumps({"test-key": base64.b64encode(public).decode()}))
    claims = {
        "licence_id": "licence-test",
        "organization_id": "hospital",
        "site_id": site_id,
        "contract_id": "contract-test",
        "modules": modules or ["icu_risk"],
        "unit_limit": 1,
        "bed_limit": 24,
        "effective_on": (date.today() - timedelta(days=40)).isoformat(),
        "expires_on": (date.today() + timedelta(days=expires_days)).isoformat(),
        "issued_at": "2026-01-01T00:00:00+00:00",
        "entitlement_status": entitlement_status,
    }
    return {"claims": claims, "key_id": "test-key", "signature": base64.b64encode(key.sign(canonical(claims))).decode()}


def test_signed_package_is_site_bound_and_tamper_evident(monkeypatch):
    package = signed_package(monkeypatch)
    assert verify_package(package, "hospital-icu")["bed_limit"] == 24
    assert status(package, "hospital-icu")["activation_eligible"] is True
    assert status(package, "other-hospital")["activation_eligible"] is False
    package["claims"]["bed_limit"] = 100
    assert status(package, "hospital-icu")["status"] == "invalid"


def test_expired_or_wrong_module_package_cannot_authorize_new_live_request(monkeypatch):
    expired = signed_package(monkeypatch, expires_days=-1)
    assert status(expired, "hospital-icu")["status"] == "expired"
    other = signed_package(monkeypatch, modules=["support"])
    assert status(other, "hospital-icu")["activation_eligible"] is False


def test_revoked_or_suspended_entitlement_blocks_new_live_eligibility(monkeypatch):
    revoked = signed_package(monkeypatch, entitlement_status="revoked")
    assert status(revoked, "hospital-icu")["status"] == "revoked"
    assert status(revoked, "hospital-icu")["activation_eligible"] is False
    suspended = signed_package(monkeypatch, entitlement_status="suspended")
    assert status(suspended, "hospital-icu")["status"] == "suspended"
    assert status(suspended, "hospital-icu")["activation_eligible"] is False


def test_local_import_is_admin_only_and_demo_disabled(monkeypatch):
    package = signed_package(monkeypatch)
    monkeypatch.setattr(settings, "demo_mode", True)
    monkeypatch.setattr(settings, "evaluation_runtime", False)
    with pytest.raises(HTTPException) as error:
        site.import_licence(package, SimpleNamespace(user_id="admin", role="admin"))
    assert error.value.status_code == 403


def test_local_import_persists_verified_package_without_vendor_call(monkeypatch):
    package = signed_package(monkeypatch)
    saved = {}
    events = []
    class Records:
        def save_config(self, key, value, actor):
            saved[key] = value
            assert actor == "hospital-admin"
        def load_config(self, key):
            return saved.get(key)
    class Engine:
        lock = threading.RLock()
        records = Records()
        def _require_writable(self):
            pass
        def _log(self, name, payload):
            events.append((name, payload))
    monkeypatch.setattr(settings, "site_id", "hospital-icu")
    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "evaluation_runtime", False)
    monkeypatch.setattr(site, "get_engine", lambda: Engine())
    result = site.import_licence(package, SimpleNamespace(user_id="hospital-admin", role="admin"))
    assert result["status"] == "current"
    assert site.local_licence(SimpleNamespace(user_id="hospital-admin", role="admin"))["activation_eligible"] is True
    assert events[0][0] == "local_licence_imported"
    assert "signature" not in events[0][1]
    wrong_site = {**package, "claims": {**package["claims"], "site_id": "another-site"}}
    with pytest.raises(HTTPException) as error:
        site.import_licence(wrong_site, SimpleNamespace(user_id="hospital-admin", role="admin"))
    assert error.value.status_code == 422


def test_new_live_request_remains_disabled_without_licence(monkeypatch):
    class Records:
        def load_config(self, key):
            assert key == "local_licence"
            return None

    class Engine:
        records = Records()
        def set_site_mode(self, mode, actor, reason, gates):
            assert mode == "live"
            assert any(gate["gate"] == "commercial_licence" and not gate["passed"] for gate in gates)
            return {"effective_mode": "live-disabled"}

    monkeypatch.setattr(settings, "licence_required", True)
    monkeypatch.setattr(settings, "public_demo_lockdown", False)
    monkeypatch.setattr(site, "get_engine", lambda: Engine())
    monkeypatch.setattr(site, "evaluate_gates", lambda *args: [{"gate": "clinical_review", "passed": True}])
    monkeypatch.setattr(site, "get_integration_service", lambda _: SimpleNamespace(connector_health=lambda: []))
    response = site.set_site_mode(SiteModeRequest(mode="live", reason="site review"), SimpleNamespace(user_id="admin", role="admin"))
    assert response["site"]["effective_mode"] == "live-disabled"
