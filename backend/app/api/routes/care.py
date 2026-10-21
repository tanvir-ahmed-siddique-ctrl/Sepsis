"""Bedside workflow: care units, ADT, charting, completeness and NEWS2 ward board."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import CLINICAL_ROLES, Actor, ensure_unit, require_roles
from app.schemas import (
    AdmitRequest,
    CareUnitRequest,
    ChartVitalsRequest,
    News2ScaleRequest,
    ObservationIn,
    TransferRequest,
)
from app.services.engine import REQUIRED_SIGNALS, Engine, Patient, get_engine

router = APIRouter(tags=["care workflow"], prefix="/care")
CLINICAL = require_roles(*CLINICAL_ROLES)
ADMIN = require_roles("admin")

CHART_FIELDS = {
    "heart_rate": ("HR", "bpm"),
    "spo2": ("O2Sat", "%"),
    "systolic_bp": ("SBP", "mmHg"),
    "diastolic_bp": ("DBP", "mmHg"),
    "mean_arterial_pressure": ("MAP", "mmHg"),
    "respiration_rate": ("Resp", "breaths/min"),
    "lactate": ("Lactate", "mmol/L"),
    "wbc": ("WBC", "10^3/uL"),
    "creatinine": ("Creatinine", "mg/dL"),
    "platelets": ("Platelets", "10^3/uL"),
}
WARD_REQUIRED = ("Resp", "O2Sat", "OxygenTherapy", "SBP", "HR", "AVPU", "Temp")


def _patient(engine: Engine, actor: Actor, identifier: str) -> Patient:
    patient = engine.resolve_patient(identifier)
    if patient is None or patient.source_mode != "api":
        raise HTTPException(status_code=404, detail="Encounter not found")
    ensure_unit(actor, patient.unit_id)
    return patient


def _freshness(patient: Patient, code: str) -> int | None:
    if code not in patient.raw or patient.raw[code].dropna().empty:
        return None
    latest_hour = int(patient.raw.loc[patient.raw[code].notna(), "_hour"].max())
    return max(0, int(datetime.now(timezone.utc).timestamp() // 3600 - latest_hour) * 60)


def _census_row(patient: Patient) -> dict:
    required = WARD_REQUIRED if patient.kind == "ward" else REQUIRED_SIGNALS
    freshness = {code: _freshness(patient, code) for code in required}
    missing = [code for code, age in freshness.items() if age is None]
    stale = [code for code, age in freshness.items() if age is not None and age > 180]
    latest_news2 = patient.news2[-1] if patient.news2 else None
    now = datetime.now(timezone.utc)
    due = bool(
        latest_news2
        and latest_news2.get("due_at")
        and datetime.fromisoformat(latest_news2["due_at"]) < now
    )
    return {
        "encounter_key": patient.encounter_key,
        "patient_id": patient.patient_id,
        "display_name": patient.display_name,
        "encounter_id": patient.encounter_id,
        "unit_id": patient.unit_id,
        "bed_id": patient.bed_id,
        "kind": patient.kind,
        "status": patient.status,
        "hypercapnic_scale2": patient.hypercapnic_scale2,
        "age": patient.age,
        "sex": patient.sex,
        "admitted_at": patient.admitted_at,
        "missing_required": missing,
        "stale_required": stale,
        "complete_required": not missing and not stale,
        "latest_news2": latest_news2,
        "observations_due": due or bool(missing),
    }


@router.get("/units")
def list_care_units(actor: Actor = Depends(CLINICAL)):
    engine = get_engine()
    with engine.lock:
        units = [row for row in engine.units.values() if actor.can_access_unit(row["unit_id"])]
    return {"units": sorted(units, key=lambda row: row["unit_id"])}


@router.post("/units")
def save_care_unit(body: CareUnitRequest, actor: Actor = Depends(ADMIN)):
    try:
        return get_engine().save_unit(
            body.unit_id, body.label, body.kind, actor, body.news2_scale_default
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/census")
def census(
    unit_id: str | None = Query(default=None, max_length=64),
    actor: Actor = Depends(CLINICAL),
):
    if unit_id:
        ensure_unit(actor, unit_id)
    engine = get_engine()
    with engine.lock:
        rows = [
            _census_row(patient)
            for patient in engine.patients.values()
            if patient.source_mode == "api"
            and patient.status == "admitted"
            and (unit_id is None or patient.unit_id == unit_id)
            and actor.can_access_unit(patient.unit_id)
        ]
    rows.sort(key=lambda row: (not row["observations_due"], row["bed_id"] or "", row["display_name"]))
    return {
        "unit_id": unit_id,
        "encounters": rows,
        "due_count": sum(row["observations_due"] for row in rows),
        "complete_count": sum(row["complete_required"] for row in rows),
    }


@router.get("/completeness")
def shift_completeness(
    unit_id: str,
    hours: int = Query(default=8, ge=1, le=24),
    actor: Actor = Depends(CLINICAL),
):
    """Observed required cells during the shift window; missing cells are never imputed."""
    ensure_unit(actor, unit_id)
    engine = get_engine()
    rows = []
    with engine.lock:
        for patient in engine.patients.values():
            if patient.unit_id != unit_id or patient.status != "admitted" or patient.source_mode != "api":
                continue
            required = WARD_REQUIRED if patient.kind == "ward" else REQUIRED_SIGNALS
            frame = engine.patient_frame(patient).tail(hours)
            expected = len(frame) * len(required)
            observed = sum(int(frame[code].notna().sum()) for code in required if code in frame)
            rows.append({
                "encounter_key": patient.encounter_key,
                "bed_id": patient.bed_id,
                "observed_required_cells": observed,
                "expected_required_cells": expected,
                "completeness": None if expected == 0 else round(observed / expected, 4),
                "window_hours": len(frame),
            })
    expected = sum(row["expected_required_cells"] for row in rows)
    observed = sum(row["observed_required_cells"] for row in rows)
    return {
        "unit_id": unit_id,
        "requested_shift_hours": hours,
        "observed_required_cells": observed,
        "expected_required_cells": expected,
        "completeness": None if expected == 0 else round(observed / expected, 4),
        "encounters": rows,
        "definition": "Observed required signal-hour cells / expected required signal-hour cells. No values are imputed.",
    }


@router.post("/encounters")
def admit(body: AdmitRequest, actor: Actor = Depends(CLINICAL)):
    ensure_unit(actor, body.unit_id)
    try:
        patient = get_engine().admit_encounter(actor=actor, **body.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return _census_row(patient)


@router.post("/encounters/{encounter_key}/transfer")
def transfer(encounter_key: str, body: TransferRequest, actor: Actor = Depends(CLINICAL)):
    ensure_unit(actor, body.unit_id)
    engine = get_engine()
    patient = _patient(engine, actor, encounter_key)
    try:
        return _census_row(engine.transfer_encounter(patient, body.unit_id, body.bed_id, actor))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/encounters/{encounter_key}/discharge")
def discharge(encounter_key: str, actor: Actor = Depends(CLINICAL)):
    engine = get_engine()
    patient = _patient(engine, actor, encounter_key)
    return _census_row(engine.discharge_encounter(patient, actor))


@router.post("/encounters/{encounter_key}/news2-scale")
def set_news2_scale(encounter_key: str, body: News2ScaleRequest, actor: Actor = Depends(CLINICAL)):
    engine = get_engine()
    patient = _patient(engine, actor, encounter_key)
    try:
        return _census_row(
            engine.set_news2_scale(patient, body.hypercapnic_scale2, body.reason, actor)
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/encounters/{encounter_key}/chart")
def chart(encounter_key: str, body: ChartVitalsRequest, actor: Actor = Depends(CLINICAL)):
    engine = get_engine()
    patient = _patient(engine, actor, encounter_key)
    payload = body.model_dump()
    observations: list[ObservationIn] = []

    if payload["temperature"] is not None:
        temp = float(payload["temperature"])
        if payload["temperature_unit"] == "F":
            temp = (temp - 32) * 5 / 9
        observations.append(ObservationIn(
            patient_id=patient.patient_id, encounter_id=patient.encounter_id,
            unit_id=patient.unit_id, timestamp=body.measured_at, code="Temp",
            value=round(temp, 3), unit="degC", source=f"manual-chart:{actor.user_id}",
        ))

    map_value = payload["mean_arterial_pressure"]
    if map_value is None and payload["systolic_bp"] is not None and payload["diastolic_bp"] is not None:
        map_value = (float(payload["systolic_bp"]) + 2 * float(payload["diastolic_bp"])) / 3
        payload["mean_arterial_pressure"] = round(map_value, 2)

    for field, (code, unit) in CHART_FIELDS.items():
        value = payload[field]
        if value is not None:
            observations.append(ObservationIn(
                patient_id=patient.patient_id, encounter_id=patient.encounter_id,
                unit_id=patient.unit_id, timestamp=body.measured_at, code=code,
                value=float(value), unit=unit, source=f"manual-chart:{actor.user_id}",
            ))
    if body.on_oxygen is not None:
        observations.append(ObservationIn(
            patient_id=patient.patient_id, encounter_id=patient.encounter_id,
            unit_id=patient.unit_id, timestamp=body.measured_at, code="OxygenTherapy",
            value=float(body.on_oxygen), source=f"manual-chart:{actor.user_id}",
        ))
    if body.avpu is not None:
        observations.append(ObservationIn(
            patient_id=patient.patient_id, encounter_id=patient.encounter_id,
            unit_id=patient.unit_id, timestamp=body.measured_at, code="AVPU",
            value=float({"A": 0, "V": 1, "P": 2, "U": 3}[body.avpu]), source=f"manual-chart:{actor.user_id}",
        ))
    result = engine.ingest(observations, actor, connector="manual_chart")
    return {**result, "encounter": _census_row(patient), "derived_map": map_value}


@router.get("/wards/{unit_id}/news2")
def ward_news2(unit_id: str, actor: Actor = Depends(CLINICAL)):
    ensure_unit(actor, unit_id)
    engine = get_engine()
    if engine.unit_kind(unit_id) != "ward":
        raise HTTPException(status_code=422, detail="NEWS2 board is only available for ward units")
    with engine.lock:
        rows = [
            _census_row(patient)
            for patient in engine.patients.values()
            if patient.unit_id == unit_id and patient.kind == "ward" and patient.status == "admitted"
        ]
    urgency = {"emergency": 4, "urgent": 3, "low": 2, "routine": 1, None: 0}
    rows.sort(key=lambda row: (-urgency.get((row["latest_news2"] or {}).get("urgency"), 0), not row["observations_due"]))
    return {
        "unit_id": unit_id,
        "patients": rows,
        "note": "NEWS2 is a published deterministic rule. Ward observations never enter the frozen ICU sepsis model.",
    }
