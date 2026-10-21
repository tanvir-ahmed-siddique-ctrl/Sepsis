"""Normalized observation contract for the PhysioNet-compatible API."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class VariableSpec:
    minimum: float
    maximum: float
    canonical_unit: str | None
    accepted_units: frozenset[str] = frozenset()


@dataclass(frozen=True)
class ValidatedObservation:
    accepted: bool
    value: float | None
    canonical_unit: str | None
    warning: str | None = None
    error: str | None = None


def _normalize_unit(unit: str | None) -> str:
    return "" if unit is None else unit.strip().lower().replace(" ", "")


def _spec(minimum: float, maximum: float, unit: str | None, *aliases: str) -> VariableSpec:
    accepted = {_normalize_unit(unit)} if unit else set()
    accepted.update(_normalize_unit(alias) for alias in aliases)
    return VariableSpec(minimum, maximum, unit, frozenset(accepted))


SPECS: dict[str, VariableSpec] = {
    "HR": _spec(20, 300, "bpm", "beats/min", "1/min"),
    "O2Sat": _spec(0, 100, "%", "percent"),
    "Temp": _spec(25, 45, "degC", "C", "°C", "celsius"),
    "SBP": _spec(30, 300, "mmHg", "mm Hg"),
    "MAP": _spec(20, 250, "mmHg", "mm Hg"),
    "DBP": _spec(10, 200, "mmHg", "mm Hg"),
    "Resp": _spec(2, 80, "breaths/min", "/min", "1/min"),
    "EtCO2": _spec(0, 100, "mmHg", "mm Hg"),
    "BaseExcess": _spec(-50, 50, "mmol/L"),
    "HCO3": _spec(0, 80, "mmol/L"),
    "FiO2": _spec(0, 1, "fraction"),
    "pH": _spec(6.5, 8.0, None),
    "PaCO2": _spec(5, 200, "mmHg", "mm Hg"),
    "SaO2": _spec(0, 100, "%", "percent"),
    "AST": _spec(0, 20_000, "IU/L", "U/L"),
    "BUN": _spec(0, 300, "mg/dL"),
    "Alkalinephos": _spec(0, 5000, "IU/L", "U/L"),
    "Calcium": _spec(0, 25, "mg/dL"),
    "Chloride": _spec(40, 180, "mmol/L"),
    "Creatinine": _spec(0, 30, "mg/dL"),
    "Bilirubin_direct": _spec(0, 50, "mg/dL"),
    "Glucose": _spec(0, 1500, "mg/dL"),
    "Lactate": _spec(0, 40, "mmol/L"),
    "Magnesium": _spec(0, 20, "mg/dL"),
    "Phosphate": _spec(0, 30, "mg/dL"),
    "Potassium": _spec(1, 12, "mmol/L"),
    "Bilirubin_total": _spec(0, 80, "mg/dL"),
    "TroponinI": _spec(0, 500, "ng/mL"),
    "Hct": _spec(0, 80, "%", "percent"),
    "Hgb": _spec(0, 30, "g/dL"),
    "PTT": _spec(5, 300, "seconds", "s"),
    "WBC": _spec(0, 300, "10^3/uL", "10^3/µL", "K/uL"),
    "Fibrinogen": _spec(0, 1500, "mg/dL"),
    "Platelets": _spec(0, 2000, "10^3/uL", "10^3/µL", "K/uL"),
    "Age": _spec(18, 120, "years", "year", "y"),
    "Gender": _spec(0, 1, None),
    "Unit1": _spec(0, 1, None),
    "Unit2": _spec(0, 1, None),
    "HospAdmTime": _spec(-100_000, 10_000, "hours", "h"),
    "ICULOS": _spec(1, 100_000, "hours", "h"),
    # Ward-charting metadata used only by the deterministic NEWS2 module.
    # These fields never enter the frozen ICU feature pipeline.
    "OxygenTherapy": _spec(0, 1, None),
    "AVPU": _spec(0, 3, None),
}


def validate_observation(code: str, value: float | None, unit: str | None) -> ValidatedObservation:
    spec = SPECS.get(code)
    if spec is None:
        return ValidatedObservation(False, value, None, error="unknown_code")
    if value is not None and not isfinite(value):
        return ValidatedObservation(False, value, spec.canonical_unit, error="non_finite_value")
    if unit and spec.canonical_unit and _normalize_unit(unit) not in spec.accepted_units:
        return ValidatedObservation(
            False,
            value,
            spec.canonical_unit,
            error=f"unit_mismatch:expected_{spec.canonical_unit}",
        )
    if value is not None and not spec.minimum <= value <= spec.maximum:
        return ValidatedObservation(
            False,
            value,
            spec.canonical_unit,
            error=f"implausible_range:{spec.minimum}_to_{spec.maximum}",
        )
    warning = "unit_assumed" if unit is None and spec.canonical_unit else None
    return ValidatedObservation(True, value, spec.canonical_unit, warning=warning)
