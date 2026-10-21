"""Feature schema and clinical variable definitions for V1."""

from __future__ import annotations

from dataclasses import dataclass


# PhysioNet Challenge 2019 vital / lab columns (subset frozen for V1)
VITAL_COLS = [
    "HR",
    "O2Sat",
    "Temp",
    "SBP",
    "MAP",
    "DBP",
    "Resp",
    "EtCO2",
]

LAB_COLS = [
    "BaseExcess",
    "HCO3",
    "FiO2",
    "pH",
    "PaCO2",
    "SaO2",
    "AST",
    "BUN",
    "Alkalinephos",
    "Calcium",
    "Chloride",
    "Creatinine",
    "Bilirubin_direct",
    "Glucose",
    "Lactate",
    "Magnesium",
    "Phosphate",
    "Potassium",
    "Bilirubin_total",
    "TroponinI",
    "Hct",
    "Hgb",
    "PTT",
    "WBC",
    "Fibrinogen",
    "Platelets",
]

DEMO_COLS = ["Age", "Gender", "Unit1", "Unit2", "HospAdmTime", "ICULOS"]

LABEL_COL = "SepsisLabel"
# Historical Challenge-compatible target. SepsisLabel becomes positive six
# hours before defined onset and remains positive afterward; it is not a pure
# incident six-hour hazard target.
TARGET_COL = "target"
ID_COL = "patient_id"
TIME_COL = "ICULOS"

# Forward-fill limits in hours (clinically conservative defaults)
FORWARD_FILL_HOURS: dict[str, int] = {
    **{c: 2 for c in VITAL_COLS},
    **{c: 24 for c in LAB_COLS},
}

WINDOW_HOURS = 24
HORIZON_HOURS = 6
MIN_HOURS_BEFORE_PRED = 4


@dataclass(frozen=True)
class RiskBandThresholds:
    """Probability thresholds — set on validation only, never on Dataset B."""

    watch: float = 0.15
    high_risk: float = 0.35


RISK_BANDS = ("insufficient_data", "stable", "watch", "high_risk")
