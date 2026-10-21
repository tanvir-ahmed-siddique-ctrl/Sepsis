"""HL7 v2 ORU^R01 adapter — PredictRx contract v0.

This adapter has only been exercised with synthetic messages. A site interface
engine (for example Mirth/NextGen Connect) must confirm segment usage before any
pilot. Contract:

* MSH-9 = ORU^R01; MSH-7 is the fallback observation time.
* PID-3 (first repetition, component 1) = pseudonymous patient id.
* PV1-19 (component 1) = encounter/visit id; PV1-3 (component 1) = ICU unit id.
* OBX-2 = NM; OBX-3 = code^text^LN; OBX-5 = value; OBX-6 = UCUM unit (component 1);
  OBX-11 in F/C/P; OBX-14 = observation time with an explicit UTC offset.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from app.integrations.base import MappingReport, PayloadError
from app.integrations.mapping import MappingRegistry
from app.schemas import ObservationIn

ACCEPTED_RESULT_STATUS = {"F", "C", "P"}
ACCEPTED_ADT_EVENTS = {"A01", "A02", "A03"}
_TS = re.compile(r"^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})?(?:\.\d+)?([+-]\d{4})?$")


def parse_hl7_timestamp(value: str) -> datetime | None:
    match = _TS.match(value.strip())
    if not match:
        return None
    year, month, day, hour, minute, second, offset = match.groups()
    tz = None
    if offset:
        sign = 1 if offset[0] == "+" else -1
        tz = timezone(sign * timedelta(hours=int(offset[1:3]), minutes=int(offset[3:5])))
    return datetime(int(year), int(month), int(day), int(hour), int(minute), int(second or 0), tzinfo=tz)


def _component(field: str, index: int = 0, separator: str = "^") -> str:
    parts = field.split(separator)
    return parts[index].strip() if index < len(parts) else ""


def parse_adt(message: str) -> dict[str, str | datetime | None]:
    """Parse the bounded ADT contract used for A01, A02 and A03.

    PID-3 supplies the patient identifier, PID-5 the display name, PV1-3 the
    point-of-care/unit and bed, and PV1-19 the encounter identifier. A partner
    conformance profile must confirm these fields before hospital use.
    """
    segments = [segment for segment in re.split(r"\r\n|\r|\n", message.strip()) if segment.strip()]
    if not segments or not segments[0].startswith("MSH"):
        raise PayloadError("HL7 v2 message must start with an MSH segment")
    field_sep = segments[0][3]
    msh = segments[0].split(field_sep)
    if len(msh) < 9:
        raise PayloadError("MSH segment is incomplete")
    component_sep = msh[1][0] if msh[1] else "^"
    message_type = msh[8]
    if _component(message_type, 0, component_sep) != "ADT":
        raise PayloadError(f"Unsupported message type {message_type!r}; expected ADT")
    event = _component(message_type, 1, component_sep)
    if event not in ACCEPTED_ADT_EVENTS:
        raise PayloadError(f"Unsupported ADT event {event!r}; expected A01, A02 or A03")
    patient_id = encounter_id = unit_id = bed_id = ""
    display_name = ""
    sex: str | None = None
    for segment in segments[1:]:
        fields = segment.split(field_sep)
        if fields[0] == "PID":
            patient_id = _component((fields[3] if len(fields) > 3 else "").split("~")[0], 0, component_sep)
            name = fields[5] if len(fields) > 5 else ""
            family = _component(name, 0, component_sep)
            given = _component(name, 1, component_sep)
            display_name = " ".join(part for part in (given, family) if part)
            raw_sex = (fields[8] if len(fields) > 8 else "").upper()
            sex = raw_sex if raw_sex in {"F", "M", "X"} else "unknown"
        elif fields[0] == "PV1":
            location = fields[3] if len(fields) > 3 else ""
            unit_id = _component(location, 0, component_sep)
            room = _component(location, 1, component_sep)
            bed = _component(location, 2, component_sep)
            bed_id = bed or room
            encounter_id = _component(fields[19], 0, component_sep) if len(fields) > 19 else ""
    if not patient_id:
        raise PayloadError("ADT message is missing PID-3 patient identifier")
    if not encounter_id:
        raise PayloadError("ADT message is missing PV1-19 encounter identifier")
    if event in {"A01", "A02"} and not unit_id:
        raise PayloadError("ADT admission/transfer is missing PV1-3 unit")
    return {
        "event": event,
        "patient_id": patient_id,
        "encounter_id": encounter_id,
        "display_name": display_name or bed_id or encounter_id,
        "unit_id": unit_id or None,
        "bed_id": bed_id or None,
        "sex": sex,
        "message_time": parse_hl7_timestamp(msh[6]) if len(msh) > 6 else None,
    }


def parse_oru(message: str, registry: MappingRegistry, source: str = "hl7v2") -> MappingReport:
    segments = [segment for segment in re.split(r"\r\n|\r|\n", message.strip()) if segment.strip()]
    if not segments or not segments[0].startswith("MSH"):
        raise PayloadError("HL7 v2 message must start with an MSH segment")
    field_sep = segments[0][3]
    msh = segments[0].split(field_sep)
    if len(msh) < 9:
        raise PayloadError("MSH segment is incomplete")
    component_sep = msh[1][0] if msh[1] else "^"
    message_type = msh[8]
    if _component(message_type, 0, component_sep) != "ORU" or _component(message_type, 1, component_sep) != "R01":
        raise PayloadError(f"Unsupported message type {message_type!r}; expected ORU^R01")
    message_time = parse_hl7_timestamp(msh[6]) if len(msh) > 6 else None

    report = MappingReport()
    patient_id = encounter_id = unit_id = None
    for segment in segments[1:]:
        fields = segment.split(field_sep)
        kind = fields[0]
        report.resources[kind] += 1
        if kind == "PID":
            identifiers = fields[3] if len(fields) > 3 else ""
            patient_id = _component(identifiers.split("~")[0], 0, component_sep) or None
            encounter_id = unit_id = None
        elif kind == "PV1":
            unit_id = _component(fields[3], 0, component_sep) if len(fields) > 3 else None
            encounter_id = _component(fields[19], 0, component_sep) if len(fields) > 19 else None
        elif kind == "OBX":
            fields += [""] * (15 - len(fields))
            identifier = fields[3]
            code = _component(identifier, 0, component_sep)
            system = _component(identifier, 2, component_sep) or None
            observed = parse_hl7_timestamp(fields[14]) if fields[14] else message_time
            if not patient_id:
                report.reject("obx_before_pid", code=code)
                continue
            if not encounter_id:
                report.reject("missing_pv1_19_visit_number", patient_id=patient_id, code=code)
                continue
            if fields[2] != "NM":
                report.reject(f"value_type_{fields[2] or 'missing'}", patient_id=patient_id, encounter_id=encounter_id, code=code)
                continue
            if fields[11] not in ACCEPTED_RESULT_STATUS:
                report.reject(f"result_status_{fields[11] or 'missing'}", patient_id=patient_id, encounter_id=encounter_id, code=code)
                continue
            if observed is None:
                report.reject("observation_time_unparseable", patient_id=patient_id, encounter_id=encounter_id, code=code)
                continue
            mapping = registry.lookup(system, code)
            if mapping is None:
                report.reject(f"unmapped_code:{system}|{code}", patient_id=patient_id, encounter_id=encounter_id, code=code, source_time=observed)
                continue
            try:
                value = float(fields[5])
            except ValueError:
                report.reject("non_numeric_value", patient_id=patient_id, encounter_id=encounter_id, code=mapping.target, source_time=observed)
                continue
            converted = registry.convert(mapping, value, _component(fields[6], 0, component_sep))
            if converted.error:
                report.reject(converted.error, patient_id=patient_id, encounter_id=encounter_id, code=mapping.target, source_time=observed)
                continue
            report.observations.append(
                ObservationIn(
                    patient_id=patient_id,
                    encounter_id=encounter_id,
                    timestamp=observed,
                    code=mapping.target,
                    value=converted.value,
                    unit=converted.unit,
                    source=source,
                    unit_id=unit_id or None,
                )
            )
    return report
