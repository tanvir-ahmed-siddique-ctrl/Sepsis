"""A source declaration must stay separate from evidence of a working feed."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.integrations.source_inventory import assess

pytestmark = pytest.mark.skipif(
    not (Path(settings.model_path).exists() and (Path(settings.demo_cases_dir) / "manifest.json").exists()),
    reason="model bundle or demo cases not generated",
)

ADMIN = {"X-Demo-User": "inventory-admin", "X-Demo-Role": "admin"}
CLINICIAN = {"X-Demo-User": "inventory-clinician", "X-Demo-Role": "clinician"}


@pytest.fixture(scope="module")
def client():
    settings.database_url = "sqlite:///:memory:"
    settings.demo_mode = True
    from app.main import app

    with TestClient(app, headers=ADMIN) as instance:
        yield instance


def _source(**changes):
    body = {
        "source_id": "monitor-1", "kind": "monitor", "label": "ICU gateway",
        "method": "fhir_r4", "signals": ["HR", "SBP", "MAP", "O2Sat"],
        "expected_interval_minutes": 60, "timestamp_basis": "measurement",
        "export_confirmed": True, "test_message_verified": True,
        "manual_chart_dry_run_verified": False, "correction_path_verified": False,
        "owner_role": "biomed",
    }
    return {**body, **changes}


def test_inventory_requires_admin_and_does_not_imply_connected_feed(client):
    assert client.get("/v1/integrations/source-inventory", headers=CLINICIAN).status_code == 403
    initial = client.get("/v1/integrations/source-inventory").json()
    assert initial["sources"] == []
    response = client.put("/v1/integrations/source-inventory", json={"sources": [_source()]})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["assessment"]["missing_required_vitals"] == []
    assert result["assessment"]["required_vitals_without_hourly_source"] == []
    assert result["assessment"]["sources"][0]["declared_test_ready"] is True
    assert result["assessment"]["sources"][0]["feed_observed"] is False
    assert result["assessment"]["observed_connected_sources"] == 0
    assert result["assessment"]["next_stage"] == "connect_feed"
    assert client.get("/v1/integrations/source-inventory").json()["sources"][0]["label"] == "ICU gateway"
    assert client.put("/v1/integrations/source-inventory", headers=CLINICIAN,
                      json={"sources": []}).status_code == 403
    events = client.get("/v1/audit?event=source_inventory_updated").json()["events"]
    assert events


def test_inventory_rejects_inconsistent_or_duplicate_declarations(client):
    unverified = _source(export_confirmed=False, test_message_verified=True)
    assert client.put("/v1/integrations/source-inventory", json={"sources": [unverified]}).status_code == 422
    assert client.put("/v1/integrations/source-inventory", json={"sources": [_source(), _source()]}).status_code == 422
    assert client.put("/v1/integrations/source-inventory", json={"sources": [_source(signals=["patient_id"])]}).status_code == 422
    assert client.put("/v1/integrations/source-inventory", json={"sources": [_source(patient_id="forbidden")]}).status_code == 422


def test_manual_chart_path_can_be_declared_without_a_hospital_interface(client):
    manual = _source(source_id="chart-1", kind="manual", method="manual", export_confirmed=False,
                     test_message_verified=False, manual_chart_dry_run_verified=True, owner_role="nursing")
    response = client.put("/v1/integrations/source-inventory", json={"sources": [manual]})
    assert response.status_code == 200, response.text
    row = response.json()["assessment"]["sources"][0]
    assert row["tier"] == "L0" and row["declared_test_ready"] is True and row["feed_observed"] is False


def test_slow_vitals_are_not_mistaken_for_hourly_coverage(client):
    response = client.put("/v1/integrations/source-inventory",
                          json={"sources": [_source(expected_interval_minutes=240)]})
    assert response.status_code == 200, response.text
    assessment = response.json()["assessment"]
    assert assessment["missing_required_vitals"] == []
    assert assessment["required_vitals_without_hourly_source"] == ["HR", "MAP", "O2Sat", "SBP"]
    assert assessment["next_stage"] == "check_vital_cadence"


def test_simulator_activity_is_not_counted_as_hospital_feed_evidence():
    document = {"sources": [_source()]}
    health = [{"connector": "fhir_r4", "state": "healthy"}]
    assert assess(document, health, simulation_mode=False)["observed_connected_sources"] == 1
    assert assess(document, health, simulation_mode=True)["observed_connected_sources"] == 0
