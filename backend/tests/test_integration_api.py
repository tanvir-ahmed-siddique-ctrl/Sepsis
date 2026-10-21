"""Integration, site-mode, security and reliability contracts against the real model bundle."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import IntegrationKey, settings
from app.integrations.synthetic import synthetic_bundle, synthetic_oru

pytestmark = pytest.mark.skipif(
    not (Path(settings.model_path).exists() and (Path(settings.demo_cases_dir) / "manifest.json").exists()),
    reason="model bundle or demo cases not generated",
)

ADMIN = {"X-Demo-User": "pilot-admin", "X-Demo-Role": "admin"}
CLINICIAN = {"X-Demo-User": "bedside-rn", "X-Demo-Role": "clinician"}


@pytest.fixture(scope="module")
def client():
    settings.database_url = "sqlite:///:memory:"
    settings.demo_mode = True
    from app.main import app

    with TestClient(app, headers=ADMIN) as c:
        yield c


@pytest.fixture()
def demo_mode_after(client):
    yield
    client.put("/v1/site/mode", json={"mode": "demo", "reason": "test cleanup"})


def _bundle(patient: str, unit: str = "icu-fhir", hours: int = 8, deteriorating: bool = True, start=None) -> str:
    return json.dumps(synthetic_bundle(
        patient_id=patient, encounter_id=f"{patient}-enc", unit_id=unit, hours=hours,
        deteriorating=deteriorating, start=start,
    ))


def test_fhir_bundle_ingest_scores_encounter_with_provenance(client):
    response = client.post("/v1/integrations/fhir/bundle", content=_bundle("fhir-a"))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["accepted"] > 0 and body["patients_rescored"] == 1
    assert body["mapping"]["registry_version"] == "1.0.0"
    overview = client.get("/v1/units/icu-fhir/overview").json()
    card = next(c for c in overview["patients"] if c["patient_id"] == "fhir-a--fhir-a-enc")
    assert card["source_mode"] == "api" and card["age"] == 67
    provenance = client.get("/v1/patients/fhir-a--fhir-a-enc/provenance").json()
    hr = next(row for row in provenance["observations"] if row["code"] == "HR")
    assert hr["connector"] == "fhir_r4" and hr["source"] == "fhir-r4" and hr["unit"] == "bpm"
    temp = next(row for row in provenance["observations"] if row["code"] == "Temp")
    assert temp["unit"] == "degC" and 36 < temp["value"] < 40
    matrix = client.get("/v1/patients/fhir-a--fhir-a-enc/signals?hours=8").json()
    hr_row = next(row for row in matrix["signals"] if row["code"] == "HR")
    lactate_row = next(row for row in matrix["signals"] if row["code"] == "Lactate")
    assert hr_row["observed_hours"] == 8 and lactate_row["observed_hours"] < 8


def test_idempotency_key_replays_and_rejects_reuse(client):
    payload = _bundle("idem-a", hours=5)
    first = client.post("/v1/integrations/fhir/bundle", content=payload, headers={"Idempotency-Key": "msg-001"})
    again = client.post("/v1/integrations/fhir/bundle", content=payload, headers={"Idempotency-Key": "msg-001"})
    assert first.status_code == again.status_code == 200
    assert again.json()["idempotent_replay"] is True
    assert again.json()["accepted"] == first.json()["accepted"]
    conflict = client.post(
        "/v1/integrations/fhir/bundle", content=_bundle("idem-b", hours=5), headers={"Idempotency-Key": "msg-001"}
    )
    assert conflict.status_code == 409


def test_duplicate_and_late_fhir_data_are_idempotent_and_recomputed(client):
    start = datetime(2026, 2, 1, 6, 0, tzinfo=timezone.utc)
    full = _bundle("late-a", hours=8, start=start)
    client.post("/v1/integrations/fhir/bundle", content=full)
    duplicate = client.post("/v1/integrations/fhir/bundle", content=full).json()
    assert duplicate["accepted"] == 0 and duplicate["patients_rescored"] == 0
    assert duplicate["duplicates_ignored"] > 0
    late = {
        "observations": [{
            "patient_id": "late-a", "encounter_id": "late-a-enc", "unit_id": "icu-fhir",
            "timestamp": (start + timedelta(hours=2, minutes=30)).isoformat(), "code": "Lactate", "value": 4.4,
        }]
    }
    result = client.post("/v1/observations/batch", json=late).json()
    assert result["accepted"] == 1 and result["patients_rescored"] == 1
    events = client.get("/v1/audit?event=observation_late_accepted&patient_id=late-a--late-a-enc").json()["events"]
    assert events


def test_mapping_rejections_are_quarantined_and_visible(client):
    bundle = synthetic_bundle(patient_id="reject-a", encounter_id="reject-a-enc", hours=4)
    bundle["entry"][2]["resource"]["code"]["coding"][0]["code"] = "00000-0"
    body = client.post("/v1/integrations/fhir/bundle", content=json.dumps(bundle)).json()
    assert any(issue["reason"].startswith("mapping:unmapped_code") for issue in body["quarantined"])
    quarantine = client.get("/v1/integrations/quarantine").json()["events"]
    assert any(event["reason"].startswith("mapping:unmapped_code") and event["connector"] == "fhir_r4" for event in quarantine)
    assert client.post("/v1/integrations/fhir/bundle", content="{not json").status_code == 422


def test_hl7_and_ndjson_endpoints(client):
    response = client.post("/v1/integrations/hl7v2/oru", content=synthetic_oru(unit_id="icu-hl7"))
    assert response.status_code == 200, response.text
    assert response.json()["accepted"] == 6
    bundle = synthetic_bundle(patient_id="bulk-a", encounter_id="bulk-a-enc", hours=5)
    ndjson = "\n".join(json.dumps(entry["resource"]) for entry in bundle["entry"])
    bulk = client.post("/v1/integrations/fhir/ndjson", content=ndjson)
    assert bulk.status_code == 200 and bulk.json()["backfill"] is True
    status = client.get("/v1/integrations/status").json()
    assert status["backfill"]["jobs"] >= 1
    states = {item["connector"]: item["state"] for item in status["connectors"]}
    assert states["fhir_r4"] in {"healthy", "degraded"} and states["hl7v2_oru"] in {"healthy", "degraded"}
    assert status["operation"]["external_network_required"] is False
    mappings = client.get("/v1/integrations/mappings").json()
    assert any(entry["code"] == "8867-4" and entry["target"] == "HR" for entry in mappings["entries"])


def test_scoped_integration_keys_enforce_units_and_scopes(client, monkeypatch):
    secret = "s3cret-value-for-tests"
    monkeypatch.setattr(settings, "integration_api_keys", [
        IntegrationKey(key_id="feed-a", sha256=hashlib.sha256(secret.encode()).hexdigest(),
                       scopes=["ingest:fhir"], units=["icu-a"]),
    ])
    key = {"X-Integration-Key": f"feed-a.{secret}", "X-Demo-Role": "", "X-Demo-User": ""}
    allowed = client.post("/v1/integrations/fhir/bundle", content=_bundle("scoped-a", unit="icu-a", hours=4), headers=key)
    assert allowed.status_code == 200, allowed.text
    other_unit = client.post("/v1/integrations/fhir/bundle", content=_bundle("scoped-b", unit="icu-b", hours=4), headers=key)
    assert other_unit.status_code == 403
    wrong_scope = client.post("/v1/integrations/hl7v2/oru", content=synthetic_oru(unit_id="icu-a"), headers=key)
    assert wrong_scope.status_code == 403
    revoked = client.post("/v1/integrations/fhir/bundle", content=_bundle("scoped-c", unit="icu-a", hours=4),
                          headers={"X-Integration-Key": "feed-a.wrong"})
    assert revoked.status_code == 401
    assert client.get("/v1/units/icu-a/overview", headers=key).status_code == 403


def test_engine_failures_spool_open_circuit_and_replay(client, monkeypatch):
    from app.integrations.service import get_integration_service
    from app.services.engine import get_engine

    engine = get_engine()
    service = get_integration_service(engine)
    original = engine.ingest

    def broken(*args, **kwargs):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(engine, "ingest", broken)
    responses = [
        client.post("/v1/integrations/fhir/bundle", content=_bundle(f"spool-{index}", hours=4))
        for index in range(settings.circuit_failure_threshold + 1)
    ]
    assert all(response.status_code == 202 for response in responses)
    assert responses[0].json()["reason"] == "processing_error"
    assert responses[-1].json()["reason"] == "circuit_open"
    health = {item["connector"]: item for item in service.connector_health()}
    assert health["fhir_r4"]["state"] == "circuit_open"
    assert health["fhir_r4"]["pending_spool"] == len(responses)

    monkeypatch.setattr(engine, "ingest", original)
    service.circuits["fhir_r4"].opened_at = None
    replay = client.post("/v1/integrations/spool/replay").json()
    assert replay["replayed"] == len(responses) and replay["still_pending"] == 0
    assert client.get("/v1/patients/spool-0--spool-0-enc/risk/current").status_code == 200
    health = {item["connector"]: item for item in service.connector_health()}
    assert health["fhir_r4"]["circuit"] == "closed" and health["fhir_r4"]["pending_spool"] == 0


def test_silent_mode_records_shadow_alerts_and_blinds_bedside(client, demo_mode_after):
    from app.services.engine import get_engine

    response = client.put("/v1/site/mode", json={"mode": "silent", "reason": "start silent pilot"})
    assert response.status_code == 200
    assert response.json()["site"]["effective_mode"] == "silent"
    assert client.get("/health").json()["replay_patients"] == 0
    assert client.post("/v1/demo/replay/step").status_code == 409
    ready = client.get("/ready")
    assert ready.status_code == 200 and "replay_cases" not in ready.json()["checks"]

    client.post("/v1/observations/batch", json={"observations": [
        {"patient_id": "silent-a", "encounter_id": "e1", "unit_id": "icu-silent",
         "timestamp": (datetime(2026, 3, 1, tzinfo=timezone.utc) + timedelta(hours=h)).isoformat(),
         "code": code, "value": value}
        for h in range(5) for code, value in (("HR", 90), ("SBP", 118), ("MAP", 80), ("O2Sat", 97))
    ]})
    engine = get_engine()
    patient = engine.resolve_patient("silent-a--e1")
    prediction = {**patient.predictions[-1], "risk_band": "high_risk", "probability": 0.6,
                  "trustgate": {**patient.predictions[-1]["trustgate"], "state": "alert"}}
    with engine.lock:
        engine._maybe_alert(patient, prediction, "watch")
    alert = engine.alerts[prediction["alert_id"]]
    assert alert["status"] == "silent" and alert["disposition"] == "shadow"

    assert all(a["alert_id"] != alert["alert_id"] for a in client.get("/v1/alerts").json()["alerts"])
    shadow = client.get("/v1/alerts?status=silent").json()["alerts"]
    assert any(a["alert_id"] == alert["alert_id"] for a in shadow)
    assert client.get("/v1/alerts?status=silent", headers=CLINICIAN).status_code == 403
    assert client.get("/v1/patients/silent-a--e1/risk/current", headers=CLINICIAN).status_code == 403
    assert client.get("/v1/patients/silent-a--e1/risk/current").status_code == 200
    bedside = client.get("/v1/units/icu-silent/overview", headers=CLINICIAN).json()
    assert bedside["bedside_blinded"] and bedside["blinded_encounters"] == 1 and bedside["patients"] == []
    assert client.post(f"/v1/alerts/{alert['alert_id']}/acknowledge", json={"action": "acknowledged"}).status_code == 409

    live = client.put("/v1/site/mode", json={"mode": "live", "reason": "attempt live"}).json()
    assert live["site"]["effective_mode"] == "live-disabled"
    assert live["site"]["interruptive_alerts_enabled"] is False
    assert any(not gate["passed"] for gate in live["gates"])
    assert client.get("/v1/site/status", headers=CLINICIAN).json()["bedside_blinded"] is True

    client.put("/v1/site/mode", json={"mode": "demo", "reason": "back to demo"})
    assert client.get("/health").json()["replay_patients"] > 0
    changes = client.get("/v1/audit?event=site_mode_changed").json()["events"]
    assert {event["effective_mode"] for event in changes} >= {"silent", "live-disabled", "demo"}


def test_synthetic_payloads_refused_outside_demo(client, demo_mode_after):
    client.put("/v1/site/mode", json={"mode": "silent", "reason": "pilot"})
    refused = client.post("/v1/integrations/fhir/bundle", content=_bundle("synthetic-refused", hours=4))
    assert refused.status_code == 422
    assert client.post("/v1/integrations/samples/load").status_code == 409


def test_backfill_never_creates_interruptive_alerts(client):
    from app.services.engine import get_engine

    engine = get_engine()
    client.post("/v1/integrations/fhir/bundle?backfill=true", content=_bundle("backfill-a", hours=12))
    patient = engine.resolve_patient("backfill-a--backfill-a-enc")
    assert patient is not None
    assert all(
        alert["status"] != "open"
        for alert in engine.alerts.values() if alert.get("encounter_key") == patient.encounter_key
    )


def test_read_only_instance_spools_ingest_and_rejects_writes(client):
    from app.services.engine import get_engine

    engine = get_engine()
    engine.read_only_reason = "test_forced"
    try:
        spooled = client.post("/v1/observations/batch", json={"observations": [{
            "patient_id": "ro-a", "encounter_id": "e1",
            "timestamp": datetime(2026, 4, 1, tzinfo=timezone.utc).isoformat(), "code": "HR", "value": 80,
        }]})
        assert spooled.status_code == 202 and spooled.json()["reason"] == "test_forced"
        assert client.post("/v1/demo/replay/step").status_code == 503
        assert client.get("/ready").status_code == 503
    finally:
        engine.read_only_reason = None


def test_second_writer_starts_read_only(tmp_path, monkeypatch):
    from app.schemas import ObservationIn
    from app.services.engine import Engine, ReadOnlyError

    monkeypatch.setattr(settings, "database_url", f"sqlite:///{(tmp_path / 'lease.db').as_posix()}")
    writer = Engine()
    standby = Engine()
    try:
        assert not writer.read_only
        assert standby.read_only and standby.read_only_reason == "another_writer_holds_lease"
        with pytest.raises(ReadOnlyError):
            standby.ingest([ObservationIn(patient_id="x", encounter_id="y",
                                          timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc), code="HR", value=80)])
    finally:
        standby.close()
        writer.close()
    successor = Engine()
    assert not successor.read_only
    successor.close()


def test_reads_require_authentication_outside_demo(client, monkeypatch):
    token = client.post("/v1/auth/demo-token", params={"user_id": "rn-1", "role": "clinician"}).json()["access_token"]
    monkeypatch.setattr(settings, "demo_mode", False)
    bare = {"X-Demo-User": "", "X-Demo-Role": ""}
    for path in (
        f"/v1/units/{settings.demo_unit_id}/overview",
        "/v1/alerts",
        "/v1/model",
        "/v1/model/passport",
        "/v1/evidence/features/HR",
        "/v1/demo/replay/status",
        "/v1/audit",
    ):
        assert client.get(path, headers={**bare, "X-Demo-Role": "admin"}).status_code == 401, path
    assert client.get("/health").status_code == 200
    authed = client.get(f"/v1/units/{settings.demo_unit_id}/overview", headers={"Authorization": f"Bearer {token}"})
    assert authed.status_code == 200
    assert client.post("/v1/auth/demo-token").status_code == 404


def test_unit_scoped_clinician_tokens_isolate_units(client):
    token = client.post(
        "/v1/auth/demo-token", params={"user_id": "rn-unit", "role": "clinician", "units": settings.demo_unit_id}
    ).json()["access_token"]
    scoped = {"Authorization": f"Bearer {token}"}
    assert client.get(f"/v1/units/{settings.demo_unit_id}/overview", headers=scoped).status_code == 200
    assert client.get("/v1/units/icu-fhir/overview", headers=scoped).status_code == 403
    assert client.get("/v1/patients/fhir-a--fhir-a-enc/risk/current", headers=scoped).status_code == 404
    me = client.get("/v1/auth/me", headers=scoped).json()
    assert me["units"] == [settings.demo_unit_id] and me["role"] == "clinician"
    units = client.get("/v1/units", headers=scoped).json()["units"]
    assert units == [settings.demo_unit_id]


def test_oidc_tokens_are_validated_against_jwks(client, monkeypatch):
    from cryptography.hazmat.primitives.asymmetric import rsa

    from app import auth

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class FakeJwks:
        def get_signing_key_from_jwt(self, token):
            return type("Key", (), {"key": key.public_key()})()

    monkeypatch.setattr(auth, "_jwks_client", FakeJwks())
    monkeypatch.setattr(settings, "auth_mode", "oidc")
    monkeypatch.setattr(settings, "oidc_issuer", "https://idp.hospital.local/realms/icu")
    monkeypatch.setattr(settings, "oidc_audience", "predictrx")
    monkeypatch.setattr(settings, "oidc_role_claim", "realm_access.roles")

    def token(**overrides):
        now = datetime.now(timezone.utc)
        claims = {
            "sub": "u-123", "preferred_username": "dr.rahman", "iss": settings.oidc_issuer,
            "aud": "predictrx", "iat": now, "exp": now + timedelta(minutes=5),
            "realm_access": {"roles": ["predictrx-clinician", "predictrx-admin"]}, "icu_units": ["icu-fhir"],
            **overrides,
        }
        return {"Authorization": "Bearer " + jwt.encode(claims, key, algorithm="RS256")}

    me = client.get("/v1/auth/me", headers=token())
    assert me.status_code == 200
    assert me.json()["user_id"] == "dr.rahman" and me.json()["role"] == "admin"
    assert me.json()["auth_mode"] == "oidc" and me.json()["units"] == ["icu-fhir"]
    assert client.get("/v1/auth/me", headers=token(aud="other")).status_code == 401
    assert client.get("/v1/auth/me", headers=token(realm_access={"roles": ["nurse"]})).status_code == 403
    expired = token(iat=datetime.now(timezone.utc) - timedelta(hours=2), exp=datetime.now(timezone.utc) - timedelta(hours=1))
    assert client.get("/v1/auth/me", headers=expired).status_code == 401


def test_jwt_secret_rotation_accepts_previous_until_removed(client, monkeypatch):
    old_token = client.post("/v1/auth/demo-token", params={"user_id": "rotating", "role": "admin"}).json()["access_token"]
    old_secret = settings.jwt_secret
    monkeypatch.setattr(settings, "jwt_secret", "a-brand-new-secret-that-is-long-enough-123")
    monkeypatch.setattr(settings, "jwt_previous_secrets", [old_secret])
    headers = {"Authorization": f"Bearer {old_token}"}
    assert client.get("/v1/auth/me", headers=headers).status_code == 200
    monkeypatch.setattr(settings, "jwt_previous_secrets", [])
    assert client.get("/v1/auth/me", headers=headers).status_code == 401


def test_security_configuration_rejects_unsafe_production(monkeypatch):
    from app.auth import validate_security_configuration

    monkeypatch.setattr(settings, "demo_mode", False)
    with pytest.raises(RuntimeError) as error:
        validate_security_configuration()
    message = str(error.value)
    assert "JWT_SECRET" in message and "SITE_MODE=demo" in message and "EXPORT_SALT" in message
    monkeypatch.setattr(settings, "jwt_secret", "x" * 40)
    monkeypatch.setattr(settings, "site_mode", "silent")
    monkeypatch.setattr(settings, "export_salt", "site-specific-salt")
    validate_security_configuration()
