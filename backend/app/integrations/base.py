"""Connector boundary: every source format maps to encounter-scoped ``ObservationIn`` rows."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.schemas import ObservationIn


class PayloadError(ValueError):
    """The payload is malformed for its declared format (client error, never retried)."""


@dataclass
class MappingReport:
    observations: list[ObservationIn] = field(default_factory=list)
    rejected: list[dict[str, Any]] = field(default_factory=list)
    resources: Counter = field(default_factory=Counter)

    def reject(
        self,
        reason: str,
        *,
        patient_id: str | None = None,
        encounter_id: str | None = None,
        code: str | None = None,
        source_time: datetime | str | None = None,
    ) -> None:
        self.rejected.append(
            {
                "patient_id": patient_id,
                "encounter_id": encounter_id,
                "code": code,
                "source_time": source_time.isoformat() if isinstance(source_time, datetime) else source_time,
                "reason": f"mapping:{reason}",
            }
        )

    def summary(self) -> dict[str, Any]:
        return {
            "resources": dict(self.resources),
            "mapped_observations": len(self.observations),
            "mapping_rejected": len(self.rejected),
        }


CONNECTORS: dict[str, dict[str, str]] = {
    "native_json": {
        "label": "Native JSON observations",
        "standard": "PredictRx ObservationBatch v1",
        "status": "supported",
        "scope": "ingest:json",
        "endpoint": "POST /v1/observations/batch",
    },
    "fhir_r4": {
        "label": "FHIR R4 Bundle and Bulk Data NDJSON",
        "standard": "HL7 FHIR R4 (4.0.1) Patient / Encounter / Observation",
        "status": "supported — draft LOINC registry, verify per site",
        "scope": "ingest:fhir",
        "endpoint": "POST /v1/integrations/fhir/bundle · POST /v1/integrations/fhir/ndjson",
    },
    "hl7v2_oru": {
        "label": "HL7 v2 ORU^R01 results",
        "standard": "HL7 v2.5.1 ORU^R01 (PredictRx adapter contract v0)",
        "status": "contract — synthetic-message tested only; validate with the site interface engine",
        "scope": "ingest:hl7v2",
        "endpoint": "POST /v1/integrations/hl7v2/oru",
    },
    "csv_lab": {
        "label": "Hospital lab CSV",
        "standard": "PredictRx CSV Lab Contract v1 (header aliases + LOINC mapping)",
        "status": "supported — verify site export columns and units",
        "scope": "ingest:json",
        "endpoint": "POST /v1/integrations/csv/lab",
    },
}
