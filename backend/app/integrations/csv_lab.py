"""Tolerant hospital-lab CSV adapter with explicit header aliases and row quarantine."""

from __future__ import annotations

import csv
import io
from datetime import datetime

from app.integrations.base import MappingReport, PayloadError
from app.integrations.mapping import MappingRegistry
from app.schemas import ObservationIn
from app.services.clinical_contract import SPECS

ALIASES = {
    "patient_id": {"patient_id", "patient", "patientid", "mrn", "uhid"},
    "encounter_id": {"encounter_id", "encounter", "visit_id", "visit", "admission_id"},
    "timestamp": {"timestamp", "datetime", "result_time", "observation_time", "collected_at"},
    "code": {"code", "test_code", "loinc", "loinc_code", "analyte"},
    "value": {"value", "result", "result_value", "numeric_result"},
    "unit": {"unit", "units", "result_unit"},
    "unit_id": {"unit_id", "ward", "location", "department"},
    "system": {"system", "code_system"},
}
REQUIRED = {"patient_id", "encounter_id", "timestamp", "code", "value"}


def _canonical_headers(fieldnames: list[str]) -> dict[str, str]:
    mapped: dict[str, str] = {}
    for original in fieldnames:
        normalized = original.lstrip("\ufeff").strip().lower().replace(" ", "_")
        canonical = next((name for name, aliases in ALIASES.items() if normalized in aliases), normalized)
        if canonical in mapped:
            raise PayloadError(f"CSV has two columns mapped to {canonical!r}")
        mapped[canonical] = original
    missing = REQUIRED - set(mapped)
    if missing:
        raise PayloadError(f"CSV is missing columns: {', '.join(sorted(missing))}")
    return mapped


def parse_csv_lab(payload: str, registry: MappingRegistry) -> MappingReport:
    reader = csv.DictReader(io.StringIO(payload))
    if reader.fieldnames is None:
        raise PayloadError("CSV header is required")
    headers = _canonical_headers(reader.fieldnames)
    report = MappingReport()
    for line, raw in enumerate(reader, start=2):
        if None in raw:
            report.reject(f"csv_line_{line}:too_many_fields")
            continue
        row = {name: (raw.get(original) or "").strip() for name, original in headers.items()}
        if not any(row.values()):
            continue
        patient_id, encounter_id, code = row["patient_id"], row["encounter_id"], row["code"]
        try:
            stamp = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise ValueError
        except ValueError:
            report.reject(f"csv_line_{line}:timestamp_requires_timezone", patient_id=patient_id, encounter_id=encounter_id, code=code)
            continue
        try:
            value = float(row["value"])
        except ValueError:
            report.reject(f"csv_line_{line}:non_numeric_value", patient_id=patient_id, encounter_id=encounter_id, code=code, source_time=stamp)
            continue
        unit = row.get("unit") or None
        target = code
        if code not in SPECS:
            mapping = registry.lookup(row.get("system") or "http://loinc.org", code)
            if mapping is None:
                report.reject(f"csv_line_{line}:unmapped_code:{code}", patient_id=patient_id, encounter_id=encounter_id, code=code, source_time=stamp)
                continue
            converted = registry.convert(mapping, value, unit)
            if converted.error:
                report.reject(f"csv_line_{line}:{converted.error}", patient_id=patient_id, encounter_id=encounter_id, code=mapping.target, source_time=stamp)
                continue
            target, value, unit = mapping.target, float(converted.value), converted.unit
        report.observations.append(ObservationIn(
            patient_id=patient_id,
            encounter_id=encounter_id,
            timestamp=stamp,
            code=target,
            value=value,
            unit=unit,
            source="csv-lab",
            unit_id=row.get("unit_id") or None,
        ))
    report.resources["CSVRow"] = len(report.observations) + len(report.rejected)
    return report
