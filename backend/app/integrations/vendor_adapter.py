"""L4 Vendor Adapter — minimal outbound contract for HIS/LIS without FHIR.

Hospital or vendor emits ``predictrx-vendor-adapter/1`` JSON; we map to
``ObservationIn`` and reuse the same quarantine path as other connectors.
"""

from __future__ import annotations

import json
from datetime import datetime

from app.integrations.base import MappingReport, PayloadError
from app.integrations.mapping import MappingRegistry
from app.schemas import ObservationIn
from app.services.clinical_contract import SPECS

CONTRACT = "predictrx-vendor-adapter/1"
LOINC_LIKE = {"http://loinc.org", "LN", "LNC", "LOINC", "loinc"}


def parse_vendor_adapter(payload: str, registry: MappingRegistry) -> MappingReport:
    try:
        document = json.loads(payload)
    except json.JSONDecodeError as error:
        raise PayloadError("Vendor adapter payload is not valid JSON") from error
    if not isinstance(document, dict):
        raise PayloadError("Vendor adapter root must be an object")
    version = document.get("contract_version")
    if version != CONTRACT:
        raise PayloadError(f"contract_version must be {CONTRACT!r}, got {version!r}")
    site_id = str(document.get("site_id") or "").strip()
    if not site_id:
        raise PayloadError("site_id is required")
    emitted_at = document.get("emitted_at")
    if not emitted_at:
        raise PayloadError("emitted_at is required")
    try:
        datetime.fromisoformat(str(emitted_at).replace("Z", "+00:00"))
    except ValueError as error:
        raise PayloadError("emitted_at must be an ISO-8601 datetime") from error
    rows = document.get("observations")
    if not isinstance(rows, list) or not rows:
        raise PayloadError("observations must be a non-empty array")

    report = MappingReport()
    provenance = document.get("provenance") if isinstance(document.get("provenance"), dict) else {}
    if provenance.get("synthetic"):
        report.resources["synthetic"] = 1
    report.resources["VendorAdapterBatch"] = 1

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            report.reject("row_not_object", code=str(index))
            continue
        patient_id = str(row.get("patient_id") or "").strip()
        encounter_id = str(row.get("encounter_id") or "").strip()
        code = str(row.get("code") or "").strip()
        unit = str(row.get("unit") or "").strip() or None
        unit_id = str(row.get("unit_id") or "").strip() or None
        system = str(row.get("code_system") or "local").strip() or "local"
        stamp_raw = row.get("timestamp")
        value_raw = row.get("value")
        if not patient_id or not encounter_id or not code or stamp_raw is None or value_raw is None or not unit:
            report.reject(
                "missing_required_field",
                patient_id=patient_id or None,
                encounter_id=encounter_id or None,
                code=code or None,
                source_time=str(stamp_raw) if stamp_raw else None,
            )
            continue
        try:
            when = datetime.fromisoformat(str(stamp_raw).replace("Z", "+00:00"))
            if when.tzinfo is None:
                raise ValueError
        except ValueError:
            report.reject(
                "timestamp_requires_timezone",
                patient_id=patient_id,
                encounter_id=encounter_id,
                code=code,
                source_time=str(stamp_raw),
            )
            continue
        try:
            value = float(value_raw)
        except (TypeError, ValueError):
            report.reject(
                "non_numeric_value",
                patient_id=patient_id,
                encounter_id=encounter_id,
                code=code,
                source_time=when,
            )
            continue

        target = code
        if code not in SPECS:
            mapping = registry.lookup(system if system in LOINC_LIKE else "http://loinc.org", code)
            if mapping is None:
                report.reject(
                    f"unmapped_code:{system}|{code}",
                    patient_id=patient_id,
                    encounter_id=encounter_id,
                    code=code,
                    source_time=when,
                )
                continue
            converted = registry.convert(mapping, value, unit)
            if converted.error:
                report.reject(
                    converted.error,
                    patient_id=patient_id,
                    encounter_id=encounter_id,
                    code=mapping.target,
                    source_time=when,
                )
                continue
            target, value, unit = mapping.target, float(converted.value), converted.unit

        report.observations.append(
            ObservationIn(
                patient_id=patient_id,
                encounter_id=encounter_id,
                timestamp=when,
                code=target,
                value=value,
                unit=unit,
                source="vendor-adapter",
                unit_id=unit_id,
            )
        )
    report.resources["VendorAdapterObservation"] = len(report.observations) + len(report.rejected)
    return report
