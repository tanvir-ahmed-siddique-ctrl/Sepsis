"""FHIR R4 Bundle / Bulk Data NDJSON → encounter-scoped observations.

Only pseudonymous resource ids are carried forward. Names, addresses, telecom and
other identifiers are never read. Encounter context is required: an Observation
without an encounter reference is rejected rather than guessed.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Iterable

from app.integrations.base import MappingReport, PayloadError
from app.integrations.mapping import MappingRegistry
from app.schemas import ObservationIn

ACCEPTED_STATUSES = {"final", "amended", "corrected", "preliminary"}
GENDER_CODES = {"male": 1.0, "female": 0.0}


def _reference_id(reference: str | None, index: dict[str, dict[str, Any]]) -> str | None:
    if not reference:
        return None
    resolved = index.get(reference)
    if resolved is not None and resolved.get("id"):
        return str(resolved["id"])
    if reference.startswith("urn:uuid:"):
        return reference.removeprefix("urn:uuid:")
    return reference.rsplit("/", 1)[-1]


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or "T" not in value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _effective_time(observation: dict[str, Any]) -> datetime | None:
    for candidate in (
        observation.get("effectiveDateTime"),
        observation.get("effectiveInstant"),
        (observation.get("effectivePeriod") or {}).get("start"),
        observation.get("issued"),
    ):
        parsed = _parse_time(candidate)
        if parsed is not None:
            return parsed
    return None


def _codings(concept: dict[str, Any] | None) -> list[dict[str, Any]]:
    return list((concept or {}).get("coding") or [])


def _age_years(birth_date: str | None, at: datetime) -> float | None:
    try:
        born = date.fromisoformat((birth_date or "")[:10])
    except ValueError:
        return None
    years = at.year - born.year - ((at.month, at.day) < (born.month, born.day))
    return float(years)


def map_resources(
    resources: Iterable[dict[str, Any]],
    registry: MappingRegistry,
    *,
    full_urls: dict[str, dict[str, Any]] | None = None,
    source: str = "fhir-r4",
) -> MappingReport:
    report = MappingReport()
    resources = list(resources)
    index: dict[str, dict[str, Any]] = dict(full_urls or {})
    patients: dict[str, dict[str, Any]] = {}
    encounters: dict[str, dict[str, Any]] = {}
    for resource in resources:
        if not isinstance(resource, dict) or "resourceType" not in resource:
            raise PayloadError("Every entry must be a FHIR resource with resourceType")
        kind = resource["resourceType"]
        report.resources[kind] += 1
        if resource.get("id"):
            index[f"{kind}/{resource['id']}"] = resource
        if kind == "Patient" and resource.get("id"):
            patients[str(resource["id"])] = resource
        elif kind == "Encounter" and resource.get("id"):
            encounters[str(resource["id"])] = resource

    first_seen: dict[tuple[str, str], datetime] = {}
    for resource in resources:
        if resource["resourceType"] != "Observation":
            continue
        patient_id = _reference_id((resource.get("subject") or {}).get("reference"), index)
        encounter_id = _reference_id((resource.get("encounter") or {}).get("reference"), index)
        timestamp = _effective_time(resource)
        codes = [coding.get("code") for coding in _codings(resource.get("code"))]
        label = codes[0] if codes else None
        if not patient_id:
            report.reject("missing_subject_reference", code=label)
            continue
        if not encounter_id:
            report.reject("missing_encounter_reference", patient_id=patient_id, code=label)
            continue
        status = resource.get("status")
        if status not in ACCEPTED_STATUSES:
            report.reject(f"status_{status or 'missing'}", patient_id=patient_id, encounter_id=encounter_id, code=label)
            continue
        if timestamp is None:
            report.reject("effective_time_not_datetime", patient_id=patient_id, encounter_id=encounter_id, code=label)
            continue
        encounter = encounters.get(encounter_id) or {}
        unit_id = _location_unit(encounter, index)
        parts = [(resource.get("code"), resource.get("valueQuantity"))]
        parts += [(component.get("code"), component.get("valueQuantity")) for component in resource.get("component") or []]
        mapped_any = False
        for concept, quantity in parts:
            if quantity is None:
                continue
            mapping = next(
                (
                    found
                    for coding in _codings(concept)
                    if (found := registry.lookup(coding.get("system"), coding.get("code"))) is not None
                ),
                None,
            )
            code_label = next((coding.get("code") for coding in _codings(concept)), None)
            if mapping is None:
                system = next((coding.get("system") for coding in _codings(concept)), None)
                report.reject(
                    f"unmapped_code:{system}|{code_label}",
                    patient_id=patient_id,
                    encounter_id=encounter_id,
                    code=code_label,
                    source_time=timestamp,
                )
                mapped_any = True
                continue
            converted = registry.convert(mapping, quantity.get("value"), quantity.get("code") or quantity.get("unit"))
            if converted.error:
                report.reject(
                    converted.error,
                    patient_id=patient_id,
                    encounter_id=encounter_id,
                    code=mapping.target,
                    source_time=timestamp,
                )
                mapped_any = True
                continue
            report.observations.append(
                ObservationIn(
                    patient_id=patient_id,
                    encounter_id=encounter_id,
                    timestamp=timestamp,
                    code=mapping.target,
                    value=converted.value,
                    unit=converted.unit,
                    source=source,
                    unit_id=unit_id,
                )
            )
            mapped_any = True
            key = (patient_id, encounter_id)
            if timestamp.tzinfo is not None and (key not in first_seen or timestamp < first_seen[key]):
                first_seen[key] = timestamp
        if not mapped_any:
            report.reject("no_value_quantity", patient_id=patient_id, encounter_id=encounter_id, code=label, source_time=timestamp)

    for (patient_id, encounter_id), first in first_seen.items():
        patient = patients.get(patient_id)
        if patient is None:
            continue
        unit_id = _location_unit(encounters.get(encounter_id) or {}, index)
        age = _age_years(patient.get("birthDate"), first)
        if age is not None:
            report.observations.append(
                ObservationIn(
                    patient_id=patient_id, encounter_id=encounter_id, timestamp=first,
                    code="Age", value=age, unit="years", source=source, unit_id=unit_id,
                )
            )
        gender = GENDER_CODES.get(str(patient.get("gender", "")).lower())
        if gender is not None:
            report.observations.append(
                ObservationIn(
                    patient_id=patient_id, encounter_id=encounter_id, timestamp=first,
                    code="Gender", value=gender, source=source, unit_id=unit_id,
                )
            )
    return report


def _location_unit(encounter: dict[str, Any], index: dict[str, dict[str, Any]]) -> str | None:
    for location in encounter.get("location") or []:
        reference = (location.get("location") or {}).get("reference")
        unit = _reference_id(reference, index)
        if unit:
            return unit[:64]
    return None


def map_bundle(bundle: Any, registry: MappingRegistry, source: str = "fhir-r4") -> MappingReport:
    if not isinstance(bundle, dict) or bundle.get("resourceType") != "Bundle":
        raise PayloadError("Expected a FHIR Bundle resource")
    entries = bundle.get("entry") or []
    if not isinstance(entries, list):
        raise PayloadError("Bundle.entry must be an array")
    full_urls: dict[str, dict[str, Any]] = {}
    resources = []
    for entry in entries:
        resource = (entry or {}).get("resource")
        if resource is None:
            raise PayloadError("Every Bundle.entry needs a resource")
        resources.append(resource)
        if entry.get("fullUrl"):
            full_urls[entry["fullUrl"]] = resource
    return map_resources(resources, registry, full_urls=full_urls, source=source)


def parse_ndjson(text: str) -> list[dict[str, Any]]:
    resources = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            resources.append(json.loads(line))
        except json.JSONDecodeError as error:
            raise PayloadError(f"NDJSON line {number} is not valid JSON") from error
    return resources
