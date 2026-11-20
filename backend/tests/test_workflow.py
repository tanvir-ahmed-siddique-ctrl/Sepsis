"""Local accounts, bedside charting, ADT and deterministic NEWS2."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.accounts import totp_now
from app.auth import create_access_token
from app.core.config import settings
from app.news2 import score

pytestmark = pytest.mark.skipif(
    not (Path(settings.model_path).exists() and (Path(settings.demo_cases_dir) / "manifest.json").exists()),
    reason="model bundle or demo cases not generated",
)

ADMIN = {"X-Demo-User": "workflow-admin", "X-Demo-Role": "admin"}


@pytest.fixture(scope="module")
def client():
    settings.database_url = "sqlite:///:memory:"
    settings.demo_mode = True
    settings.auth_mode = "local"
    from app.main import app

    with TestClient(app, headers=ADMIN) as value:
        yield value


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Demo-User": "", "X-Demo-Role": ""}


def test_news2_boundaries_and_missing_data():
    normal = score(
        respiration_rate=16, spo2=97, on_oxygen=False, systolic_bp=120,
        heart_rate=70, consciousness="A", temperature=37.0,
    )
    assert normal["score"] == 0 and normal["urgency"] == "routine"
    high = score(
        respiration_rate=25, spo2=91, on_oxygen=True, systolic_bp=90,
        heart_rate=131, consciousness="V", temperature=35.0,
    )
    assert high["score"] == 20 and high["urgency"] == "emergency"
    single_three = score(
        respiration_rate=8, spo2=97, on_oxygen=False, systolic_bp=120,
        heart_rate=70, consciousness="A", temperature=37.0,
    )
    assert single_three["score"] == 3 and single_three["urgency"] == "urgent"
    missing = score(
        respiration_rate=None, spo2=97, on_oxygen=False, systolic_bp=120,
        heart_rate=70, consciousness="A", temperature=37.0,
    )
    assert missing["score"] is None and missing["missing"] == ["respiration_rate"]


def test_local_account_password_pin_totp_and_revocation(client):
    assert client.post("/v1/care/units", json={
        "unit_id": "ward-a", "label": "Medicine Ward A", "kind": "ward", "news2_scale_default": 1,
    }).status_code == 200
    created = client.post("/v1/auth/users", json={
        "user_id": "nurse.one",
        "display_name": "Nurse One",
        "role": "clinician",
        "password": "Temporary-Pass-123!",
        "units": ["ward-a"],
    })
    assert created.status_code == 200, created.text
    login = client.post("/v1/auth/login", json={
        "user_id": "nurse.one", "password": "Temporary-Pass-123!",
    }).json()
    headers = bearer(login["access_token"])
    me = client.get("/v1/auth/me", headers=headers).json()
    assert me["user_id"] == "nurse.one" and me["must_change_password"]
    assert client.get("/v1/care/census", headers=headers).status_code == 403

    changed = client.post("/v1/auth/password", headers=headers, json={
        "current_password": "Temporary-Pass-123!",
        "new_password": "Permanent-Pass-456!",
    })
    assert changed.status_code == 200
    assert client.get("/v1/auth/me", headers=headers).status_code == 401

    fresh = client.post("/v1/auth/login", json={
        "user_id": "nurse.one", "password": "Permanent-Pass-456!",
    }).json()
    headers = bearer(fresh["access_token"])
    assert client.post("/v1/auth/pin", headers=headers, json={"pin": "4826"}).status_code == 200
    pin_login = client.post("/v1/auth/pin-login", json={"user_id": "nurse.one", "pin": "4826"})
    assert pin_login.status_code == 200

    # PIN setup revoked the previous password session; use a new one for TOTP enrolment.
    fresh = client.post("/v1/auth/login", json={
        "user_id": "nurse.one", "password": "Permanent-Pass-456!",
    }).json()
    headers = bearer(fresh["access_token"])
    secret = client.post("/v1/auth/totp/begin", headers=headers).json()["secret"]
    code = totp_now(secret, datetime.now(timezone.utc).timestamp(), window=0)[0]
    assert client.post("/v1/auth/totp/confirm", headers=headers, json={"code": code}).status_code == 200
    assert client.post("/v1/auth/login", json={
        "user_id": "nurse.one", "password": "Permanent-Pass-456!",
    }).status_code == 401
    assert client.post("/v1/auth/login", json={
        "user_id": "nurse.one", "password": "Permanent-Pass-456!", "totp_code": code,
    }).status_code == 200
    assert client.post("/v1/auth/pin-login", json={
        "user_id": "nurse.one", "pin": "4826",
    }).status_code == 401
    assert client.post("/v1/auth/pin-login", json={
        "user_id": "nurse.one", "pin": "4826", "totp_code": code,
    }).status_code == 200


def test_admin_account_lifecycle_and_last_admin_guard(client):
    # Ensure a known unit exists even when this test runs in isolation.
    client.post("/v1/care/units", json={
        "unit_id": "ward-a", "label": "Medicine Ward A", "kind": "ward", "news2_scale_default": 1,
    })
    unknown_scope = client.post("/v1/auth/users", json={
        "user_id": "bad.scope",
        "display_name": "Bad Scope",
        "role": "clinician",
        "password": "Temporary-Scope-123!",
        "units": ["not-a-real-unit"],
    })
    assert unknown_scope.status_code == 422

    for user_id in ("site.admin.one", "site.admin.two"):
        response = client.post("/v1/auth/users", json={
            "user_id": user_id,
            "display_name": user_id,
            "role": "admin",
            "password": "Temporary-Admin-123!",
            "units": None,
        })
        assert response.status_code == 200, response.text

    first_login = client.post("/v1/auth/login", json={
        "user_id": "site.admin.one", "password": "Temporary-Admin-123!",
    }).json()
    assert client.post("/v1/auth/password", headers=bearer(first_login["access_token"]), json={
        "current_password": "Temporary-Admin-123!",
        "new_password": "Permanent-Admin-456!",
    }).status_code == 200
    current_token = client.post("/v1/auth/login", json={
        "user_id": "site.admin.one", "password": "Permanent-Admin-456!",
    }).json()["access_token"]
    assert client.patch("/v1/auth/users/site.admin.one", json={"role": "clinician"}).status_code == 200
    assert client.get("/v1/auth/users", headers=bearer(current_token)).status_code == 401
    stale_role_token = create_access_token("site.admin.one", "admin", auth_mode="password")
    # Depending on timestamp ordering this is rejected by the revocation marker
    # or by reconciliation with the account's current clinician role.
    assert client.get("/v1/auth/users", headers=bearer(stale_role_token)).status_code in {401, 403}

    assert client.delete("/v1/auth/users/site.admin.one").status_code == 200
    # Demo mode seeds demo-admin / sim-admin; disable them so site.admin.two
    # is the only remaining active administrator for the last-admin guard.
    for seeded in ("demo-admin", "sim-admin"):
        disabled = client.patch(f"/v1/auth/users/{seeded}", json={"disabled": True})
        assert disabled.status_code == 200, disabled.text
    last = client.patch("/v1/auth/users/site.admin.two", json={"role": "clinician"})
    assert last.status_code == 409

    created = client.post("/v1/auth/users", json={
        "user_id": "temporary.user",
        "display_name": "Temporary User",
        "role": "clinician",
        "password": "Temporary-User-123!",
        "units": ["ward-a"],
    })
    assert created.status_code == 200
    login = client.post("/v1/auth/login", json={
        "user_id": "temporary.user", "password": "Temporary-User-123!",
    }).json()
    headers = bearer(login["access_token"])
    assert client.patch("/v1/auth/users/temporary.user", json={"units": None}).status_code == 200
    assert client.get("/v1/auth/me", headers=headers).status_code == 401
    login = client.post("/v1/auth/login", json={
        "user_id": "temporary.user", "password": "Temporary-User-123!",
    }).json()
    headers = bearer(login["access_token"])
    assert client.post("/v1/auth/pin", headers=headers, json={"pin": "1947"}).status_code == 403
    assert client.post("/v1/auth/password", headers=headers, json={
        "current_password": "Temporary-User-123!",
        "new_password": "Permanent-User-456!",
    }).status_code == 200
    login = client.post("/v1/auth/login", json={
        "user_id": "temporary.user", "password": "Permanent-User-456!",
    }).json()
    headers = bearer(login["access_token"])
    assert client.post("/v1/auth/pin", headers=headers, json={"pin": "1947"}).status_code == 200
    reset = client.post("/v1/auth/users/temporary.user/reset-password", json={
        "new_password": "Reset-Temporary-789!",
    })
    assert reset.status_code == 200
    assert reset.json()["must_change_password"] is True
    assert client.post("/v1/auth/pin-login", json={"user_id": "temporary.user", "pin": "1947"}).status_code == 401

    assert client.delete("/v1/auth/users/temporary.user").status_code == 200
    assert client.post("/v1/auth/login", json={
        "user_id": "temporary.user", "password": "Reset-Temporary-789!",
    }).status_code == 401


def test_ward_adt_charting_news2_and_unit_scope(client):
    assert client.post("/v1/care/units", json={
        "unit_id": "ward-a", "label": "Medicine Ward A", "kind": "ward", "news2_scale_default": 1,
    }).status_code == 200
    admitted = client.post("/v1/care/encounters", json={
        "patient_id": "p-ward-1",
        "encounter_id": "visit-1",
        "display_name": "Bed A-01",
        "unit_id": "ward-a",
        "bed_id": "A-01",
        "age": 52,
        "sex": "F",
    })
    assert admitted.status_code == 200, admitted.text
    key = admitted.json()["encounter_key"]
    duplicate_bed = client.post("/v1/care/encounters", json={
        "patient_id": "p-ward-2",
        "encounter_id": "visit-2",
        "display_name": "Duplicate Bed",
        "unit_id": "ward-a",
        "bed_id": "A-01",
        "age": 60,
        "sex": "M",
    })
    assert duplicate_bed.status_code == 409
    charted = client.post(f"/v1/care/encounters/{key}/chart", json={
        "measured_at": "2026-10-18T12:00:00+00:00",
        "heart_rate": 70,
        "spo2": 97,
        "temperature": 98.6,
        "temperature_unit": "F",
        "systolic_bp": 120,
        "diastolic_bp": 75,
        "respiration_rate": 16,
        "on_oxygen": False,
        "avpu": "A",
    })
    assert charted.status_code == 200, charted.text
    row = charted.json()["encounter"]
    assert row["latest_news2"]["score"] == 0
    assert row["latest_news2"]["inputs"]["temperature"] == pytest.approx(37.0, abs=0.01)
    assert charted.json()["derived_map"] == pytest.approx(90.0)

    from app.services.engine import get_engine

    patient = get_engine().resolve_patient(key)
    assert patient is not None and patient.kind == "ward"
    assert patient.predictions == []  # Ward observations never enter frozen Run 4.
    board = client.get("/v1/care/wards/ward-a/news2").json()
    assert board["patients"][0]["latest_news2"]["source"].startswith("RCP NEWS2")
    scale = client.post(f"/v1/care/encounters/{key}/news2-scale", json={
        "hypercapnic_scale2": True,
        "reason": "Documented hypercapnic respiratory failure",
    })
    assert scale.status_code == 200
    assert scale.json()["hypercapnic_scale2"] is True
    assert scale.json()["latest_news2"]["scale"] == 2

    assert client.post("/v1/care/units", json={
        "unit_id": "icu-a", "label": "ICU A", "kind": "icu", "news2_scale_default": 1,
    }).status_code == 200
    assert client.post(f"/v1/care/encounters/{key}/transfer", json={
        "unit_id": "icu-a", "bed_id": "I-01",
    }).status_code == 200
    assert client.post(f"/v1/care/encounters/{key}/chart", json={
        "measured_at": "2026-10-18T14:00:00+00:00", "heart_rate": 75,
    }).status_code == 200
    patient = get_engine().resolve_patient(key)
    assert patient is not None and patient.kind == "icu"
    assert patient.news2 == []
    assert len(patient.predictions) == 1
    assert patient.predictions[0]["risk_band"] == "insufficient_data"
    assert list(get_engine().patient_frame(patient)["_hour"]) == [
        int(datetime(2026, 10, 18, 14, tzinfo=timezone.utc).timestamp() // 3600)
    ]

    assert client.post(f"/v1/care/encounters/{key}/discharge").status_code == 200
    assert client.post(f"/v1/care/encounters/{key}/chart", json={
        "measured_at": "2026-10-18T13:00:00+00:00", "heart_rate": 75,
    }).status_code == 200  # Route resolves the record; engine rejects writes after discharge.


def test_lab_csv_endpoint_maps_aliases_and_quarantines_bad_rows(client):
    response = client.post(
        "/v1/integrations/csv/lab",
        headers={**ADMIN, "Content-Type": "text/csv", "Idempotency-Key": "lab-csv-1"},
        content="\n".join([
            "MRN,visit,result_time,LOINC,result,units,ward",
            "csv-p1,csv-e1,2026-10-18T12:00:00+00:00,2524-7,18,mg/dL,icu-api",
            "csv-p1,csv-e1,bad,9999,not-a-number,,icu-api",
        ]),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["accepted"] == 1 and len(body["quarantined"]) == 1
    assert body["connector"] == "csv_lab"


def test_hl7_adt_a01_a02_a03_updates_census(client):
    for unit_id in ("icu-adt-a", "icu-adt-b"):
        assert client.post("/v1/care/units", json={
            "unit_id": unit_id, "label": unit_id.upper(), "kind": "icu", "news2_scale_default": 1,
        }).status_code == 200

    def message(event: str, unit: str, bed: str, control: str) -> str:
        pv1 = ["PV1", "", "I", f"{unit}^ROOM^{bed}", *([""] * 15), "adt-visit-1"]
        return "\r".join([
            f"MSH|^~\\&|HIS|HOSP|PREDICTRX|ICU|20261018120000+0000||ADT^{event}|{control}|P|2.5.1",
            "PID|||adt-patient-1^^^HOSP^MR||Rahman^Amina|||F",
            "|".join(pv1),
        ])

    admitted = client.post(
        "/v1/integrations/hl7v2/adt",
        headers={**ADMIN, "Content-Type": "text/plain"},
        content=message("A01", "icu-adt-a", "A-01", "ADT1"),
    )
    assert admitted.status_code == 200, admitted.text
    assert admitted.json()["encounter"]["display_name"] == "Amina Rahman"
    assert admitted.json()["encounter"]["bed_id"] == "A-01"
    duplicate = client.post(
        "/v1/integrations/hl7v2/adt",
        headers={**ADMIN, "Content-Type": "text/plain"},
        content=message("A01", "icu-adt-a", "A-01", "ADT1-REPLAY"),
    )
    assert duplicate.status_code == 200 and duplicate.json()["duplicate"] is True

    transferred = client.post(
        "/v1/integrations/hl7v2/adt",
        headers={**ADMIN, "Content-Type": "text/plain"},
        content=message("A02", "icu-adt-b", "B-03", "ADT2"),
    )
    assert transferred.status_code == 200, transferred.text
    assert transferred.json()["encounter"]["unit_id"] == "icu-adt-b"
    assert transferred.json()["encounter"]["bed_id"] == "B-03"

    discharged = client.post(
        "/v1/integrations/hl7v2/adt",
        headers={**ADMIN, "Content-Type": "text/plain"},
        content=message("A03", "icu-adt-b", "B-03", "ADT3"),
    )
    assert discharged.status_code == 200, discharged.text
    assert discharged.json()["encounter"]["status"] == "discharged"

    unsupported = client.post(
        "/v1/integrations/hl7v2/adt",
        headers={**ADMIN, "Content-Type": "text/plain"},
        content=message("A08", "icu-adt-b", "B-03", "ADT4"),
    )
    assert unsupported.status_code == 422


def test_mapping_signoff_is_bound_to_current_registry(client):
    current = client.get("/v1/integrations/status").json()["mapping_registry"]
    wrong = client.post("/v1/integrations/mappings/signoff", json={
        "registry_sha256": "0" * 64,
        "source_system": "Test LIS",
        "approver_name": "Interface Analyst",
        "approver_role": "Hospital IT",
        "examples_verified": 10,
        "notes": "Verified synthetic commissioning examples.",
    })
    assert wrong.status_code == 409
    signed = client.post("/v1/integrations/mappings/signoff", json={
        "registry_sha256": current["sha256"],
        "source_system": "Test LIS",
        "approver_name": "Interface Analyst",
        "approver_role": "Hospital IT",
        "examples_verified": 10,
        "notes": "Verified codes, units, timestamps and representative examples.",
    })
    assert signed.status_code == 200, signed.text
    updated = client.get("/v1/integrations/status").json()["mapping_registry"]
    assert updated["status"] == "ready"
    assert updated["signoff"]["registry_sha256"] == current["sha256"]
