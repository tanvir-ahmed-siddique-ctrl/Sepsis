"""Deterministic Synthea-style FHIR R4 and HL7 v2 samples.

For connector and integration testing only. Synthetic encounters are never model
evidence, never validation data, and are tagged as synthetic in ``meta.tag``.
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

SYNTHETIC_TAG = {
    "system": "https://predictrx.example/fhir/tags",
    "code": "synthetic-integration-test",
    "display": "Synthetic — integration testing only",
}


def _uuid(*parts: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "predictrx-synthetic/" + "/".join(parts)))


def _quantity(value: float, unit: str) -> dict[str, Any]:
    return {"value": round(value, 2), "unit": unit, "system": "http://unitsofmeasure.org", "code": unit}


def _coding(code: str, display: str) -> dict[str, Any]:
    return {"coding": [{"system": "http://loinc.org", "code": code, "display": display}], "text": display}


def synthetic_bundle(
    *,
    patient_id: str = "synthetic-001",
    encounter_id: str = "synthetic-enc-001",
    unit_id: str = "icu-api",
    start: datetime | None = None,
    hours: int = 12,
    deteriorating: bool = True,
    age_years: int = 67,
    gender: str = "male",
) -> dict[str, Any]:
    start = start or datetime(2026, 1, 10, 8, 0, tzinfo=timezone.utc)
    patient_url = f"urn:uuid:{_uuid(patient_id)}"
    encounter_url = f"urn:uuid:{_uuid(patient_id, encounter_id)}"
    birth = start.date().replace(year=start.year - age_years) - timedelta(days=30)
    entries: list[dict[str, Any]] = [
        {
            "fullUrl": patient_url,
            "resource": {
                "resourceType": "Patient",
                "id": patient_id,
                "meta": {"tag": [SYNTHETIC_TAG]},
                "gender": gender,
                "birthDate": birth.isoformat(),
            },
        },
        {
            "fullUrl": encounter_url,
            "resource": {
                "resourceType": "Encounter",
                "id": encounter_id,
                "meta": {"tag": [SYNTHETIC_TAG]},
                "status": "in-progress",
                "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "IMP"},
                "subject": {"reference": patient_url},
                "period": {"start": start.isoformat()},
                "location": [{"location": {"reference": f"Location/{unit_id}", "display": unit_id}}],
            },
        },
    ]

    def observation(hour: int, name: str, body: dict[str, Any]) -> None:
        when = start + timedelta(hours=hour, minutes=5)
        entries.append(
            {
                "fullUrl": f"urn:uuid:{_uuid(patient_id, encounter_id, name, str(hour))}",
                "resource": {
                    "resourceType": "Observation",
                    "id": _uuid(patient_id, encounter_id, name, str(hour)),
                    "meta": {"tag": [SYNTHETIC_TAG]},
                    "status": "final",
                    "subject": {"reference": patient_url},
                    "encounter": {"reference": encounter_url},
                    "effectiveDateTime": when.isoformat(),
                    **body,
                },
            }
        )

    for hour in range(hours):
        drift = hour / max(hours - 1, 1) if deteriorating else 0.0
        wobble = math.sin(hour * 1.3)
        observation(hour, "hr", {"code": _coding("8867-4", "Heart rate"),
                                 "valueQuantity": _quantity(84 + 38 * drift + 2 * wobble, "/min")})
        observation(hour, "bp", {
            "code": _coding("85354-9", "Blood pressure panel with all children optional"),
            "component": [
                {"code": _coding("8480-6", "Systolic blood pressure"),
                 "valueQuantity": _quantity(124 - 34 * drift + wobble, "mm[Hg]")},
                {"code": _coding("8462-4", "Diastolic blood pressure"),
                 "valueQuantity": _quantity(72 - 18 * drift, "mm[Hg]")},
            ],
        })
        observation(hour, "map", {"code": _coding("8478-0", "Mean blood pressure"),
                                  "valueQuantity": _quantity(89 - 25 * drift, "mm[Hg]")})
        observation(hour, "resp", {"code": _coding("9279-1", "Respiratory rate"),
                                   "valueQuantity": _quantity(16 + 12 * drift, "/min")})
        observation(hour, "spo2", {"code": _coding("59408-5", "Oxygen saturation by pulse oximetry"),
                                   "valueQuantity": _quantity(97 - 6 * drift, "%")})
        temperature_f = (36.9 + 2.1 * drift) * 9 / 5 + 32
        observation(hour, "temp", {"code": _coding("8310-5", "Body temperature"),
                                   "valueQuantity": _quantity(temperature_f, "[degF]")})
        if hour % 6 == 0:
            observation(hour, "lactate", {"code": _coding("2524-7", "Lactate"),
                                          "valueQuantity": _quantity(1.1 + 3.4 * drift, "mmol/L")})
            observation(hour, "creatinine", {"code": _coding("2160-0", "Creatinine"),
                                             "valueQuantity": _quantity(80 + 110 * drift, "umol/L")})
            observation(hour, "wbc", {"code": _coding("6690-2", "Leukocytes"),
                                      "valueQuantity": _quantity(8.5 + 9 * drift, "10*3/uL")})
            observation(hour, "platelets", {"code": _coding("777-3", "Platelets"),
                                            "valueQuantity": _quantity(240 - 120 * drift, "10*3/uL")})
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "meta": {"tag": [SYNTHETIC_TAG]},
        "entry": entries,
    }


def synthetic_oru(
    *,
    patient_id: str = "synthetic-hl7-001",
    visit_id: str = "synthetic-visit-001",
    unit_id: str = "icu-api",
    observed: datetime | None = None,
) -> str:
    observed = observed or datetime(2026, 1, 10, 9, 5, tzinfo=timezone.utc)
    stamp = observed.strftime("%Y%m%d%H%M%S") + "+0000"
    return "\r".join(
        [
            f"MSH|^~\\&|SYNTH-MONITOR|SITE|PREDICTRX|SITE|{stamp}||ORU^R01|MSG-{patient_id}|P|2.5.1",
            f"PID|1||{patient_id}^^^SYNTH^MR||Synthetic^Patient",
            "|".join(["PV1", "1", "I", f"{unit_id}^BED-01^^SITE", *([""] * 15), visit_id]),
            "OBR|1|||85353-1^Vital signs panel^LN",
            f"OBX|1|NM|8867-4^Heart rate^LN||118|/min|||||F|||{stamp}",
            f"OBX|2|NM|8480-6^Systolic blood pressure^LN||92|mm[Hg]|||||F|||{stamp}",
            f"OBX|3|NM|8478-0^Mean blood pressure^LN||64|mm[Hg]|||||F|||{stamp}",
            f"OBX|4|NM|59408-5^SpO2^LN||93|%|||||F|||{stamp}",
            f"OBX|5|NM|9279-1^Respiratory rate^LN||26|/min|||||F|||{stamp}",
            f"OBX|6|NM|2524-7^Lactate^LN||3.6|mmol/L|||||F|||{stamp}",
        ]
    )
