"""Connector mapping contracts — pure functions, no model required."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import settings
from app.integrations.base import PayloadError
from app.integrations.csv_lab import parse_csv_lab
from app.integrations.fhir import map_bundle, map_resources, parse_ndjson
from app.integrations.hl7v2 import parse_hl7_timestamp, parse_oru
from app.integrations.mapping import MappingRegistry
from app.integrations.synthetic import synthetic_bundle, synthetic_oru
from app.services.clinical_contract import SPECS, validate_observation


@pytest.fixture(scope="module")
def registry() -> MappingRegistry:
    return MappingRegistry(settings.fhir_mapping_path)


def _observation(code: str, value: float, unit: str, **overrides) -> dict:
    resource = {
        "resourceType": "Observation",
        "id": f"obs-{code}",
        "status": "final",
        "subject": {"reference": "Patient/p1"},
        "encounter": {"reference": "Encounter/e1"},
        "effectiveDateTime": "2026-01-10T08:05:00+06:00",
        "code": {"coding": [{"system": "http://loinc.org", "code": code}]},
        "valueQuantity": {"value": value, "unit": unit, "code": unit},
    }
    resource.update(overrides)
    return resource


def test_registry_targets_and_canonical_units_match_clinical_contract(registry):
    assert registry.version == "1.0.0"
    for mapping in registry.entries.values():
        assert mapping.target in SPECS
        assert mapping.canonical_unit == SPECS[mapping.target].canonical_unit
        converted = registry.convert(mapping, 1.0, next(iter(registry.document_units(mapping.code))))
        assert converted.error is None


def test_csv_lab_accepts_header_aliases_direct_codes_and_loinc(registry):
    payload = "\n".join([
        "MRN,visit,result_time,test_code,result,units,ward",
        "p1,e1,2026-10-18T08:00:00+06:00,HR,88,bpm,icu-a",
        "p1,e1,2026-10-18T08:01:00+06:00,2524-7,18,mg/dL,icu-a",
        "p1,e1,bad-time,unknown,hello,,icu-a",
    ])
    report = parse_csv_lab(payload, registry)
    assert [(item.code, item.value, item.unit) for item in report.observations] == [
        ("HR", 88.0, "bpm"),
        ("Lactate", pytest.approx(1.998), "mmol/L"),
    ]
    assert all(item.unit_id == "icu-a" for item in report.observations)
    assert len(report.rejected) == 1 and "timestamp_requires_timezone" in report.rejected[0]["reason"]


def test_fhir_bundle_maps_components_conversions_and_demographics(registry):
    bundle = synthetic_bundle(hours=4, unit_id="icu-fhir", age_years=67, gender="female")
    report = map_bundle(bundle, registry)
    assert report.rejected == []
    codes = {ob.code for ob in report.observations}
    assert {"HR", "SBP", "DBP", "MAP", "Resp", "O2Sat", "Temp", "Lactate", "Creatinine", "WBC", "Platelets"} <= codes
    assert {"Age", "Gender"} <= codes
    assert all(ob.unit_id == "icu-fhir" for ob in report.observations)
    assert all(ob.patient_id == "synthetic-001" and ob.encounter_id == "synthetic-enc-001" for ob in report.observations)
    temp = next(ob for ob in report.observations if ob.code == "Temp")
    assert temp.unit == "degC" and 36.5 < temp.value < 37.3
    creatinine = next(ob for ob in report.observations if ob.code == "Creatinine")
    assert creatinine.unit == "mg/dL" and creatinine.value == pytest.approx(80 * 0.0113122, rel=1e-4)
    age = next(ob for ob in report.observations if ob.code == "Age")
    gender = next(ob for ob in report.observations if ob.code == "Gender")
    assert age.value == 67 and gender.value == 0
    for ob in report.observations:
        assert validate_observation(ob.code, ob.value, ob.unit).accepted, ob


def test_fhir_rejects_unmapped_status_context_time_and_units(registry):
    resources = [
        {"resourceType": "Patient", "id": "p1", "gender": "male", "birthDate": "1960-01-01"},
        _observation("8867-4", 92, "/min"),
        _observation("99999-9", 1, "1"),
        _observation("8867-4", 92, "/min", status="entered-in-error"),
        _observation("8867-4", 92, "/min", encounter=None),
        _observation("8867-4", 92, "/min", effectiveDateTime="2026-01-10"),
        _observation("8867-4", 2, "Hz"),
        _observation("8310-5", 101.3, "[degF]", effectiveDateTime="2026-01-10T09:00:00"),
    ]
    report = map_resources(resources, registry)
    reasons = sorted(issue["reason"] for issue in report.rejected)
    assert reasons == sorted([
        "mapping:unmapped_code:http://loinc.org|99999-9",
        "mapping:status_entered-in-error",
        "mapping:missing_encounter_reference",
        "mapping:effective_time_not_datetime",
        "mapping:unit_unmapped:Hz",
    ])
    hr = next(ob for ob in report.observations if ob.code == "HR")
    assert hr.timestamp.utcoffset() == timedelta(hours=6)
    naive_temp = next(ob for ob in report.observations if ob.code == "Temp")
    assert naive_temp.timestamp.tzinfo is None
    assert naive_temp.value == pytest.approx(38.5, abs=0.01)


def test_bundle_and_ndjson_payload_errors(registry):
    with pytest.raises(PayloadError):
        map_bundle({"resourceType": "Patient"}, registry)
    with pytest.raises(PayloadError):
        parse_ndjson('{"resourceType": "Observation"}\nnot-json')
    lines = "\n".join(
        __import__("json").dumps(resource)
        for resource in (_observation("8867-4", 88, "/min"), _observation("8480-6", 118, "mm[Hg]"))
    )
    report = map_resources(parse_ndjson(lines), registry, source="fhir-bulk-ndjson")
    assert {ob.code for ob in report.observations} == {"HR", "SBP"}
    assert {ob.source for ob in report.observations} == {"fhir-bulk-ndjson"}


def test_hl7_oru_contract_maps_segments_and_timezones(registry):
    report = parse_oru(synthetic_oru(unit_id="icu-hl7"), registry)
    assert report.rejected == []
    assert {ob.code for ob in report.observations} == {"HR", "SBP", "MAP", "O2Sat", "Resp", "Lactate"}
    first = report.observations[0]
    assert first.patient_id == "synthetic-hl7-001"
    assert first.encounter_id == "synthetic-visit-001"
    assert first.unit_id == "icu-hl7"
    assert first.timestamp == datetime(2026, 1, 10, 9, 5, tzinfo=timezone.utc)

    no_offset = synthetic_oru().replace("+0000", "")
    naive = parse_oru(no_offset, registry)
    assert all(ob.timestamp.tzinfo is None for ob in naive.observations)

    cancelled = synthetic_oru().replace("|||||F|||", "|||||X|||", 1)
    assert any(issue["reason"] == "mapping:result_status_X" for issue in parse_oru(cancelled, registry).rejected)

    with pytest.raises(PayloadError):
        parse_oru(synthetic_oru().replace("ORU^R01", "ADT^A01"), registry)
    with pytest.raises(PayloadError):
        parse_oru("PID|1||x", registry)


def test_hl7_timestamp_offsets():
    assert parse_hl7_timestamp("202601100905+0600") == datetime(
        2026, 1, 10, 9, 5, tzinfo=timezone(timedelta(hours=6))
    )
    assert parse_hl7_timestamp("20260110090501.123-0330").utcoffset() == -timedelta(hours=3, minutes=30)
    assert parse_hl7_timestamp("2026-01-10") is None
