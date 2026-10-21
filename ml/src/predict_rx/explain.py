"""Patient-level explanations: TreeSHAP contributions grouped by clinical variable.

Contributions are in log-odds space of the uncalibrated ensemble; they explain
*why the score moved*, not the calibrated probability itself, and are never
treatment advice.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from predict_rx.models import CalibratedEnsemble

# variable → (organ system / concept, clinician-readable name, unit)
KNOWLEDGE: dict[str, tuple[str, str, str]] = {
    "HR": ("Cardiovascular", "Heart rate", "bpm"),
    "SBP": ("Cardiovascular", "Systolic BP", "mmHg"),
    "DBP": ("Cardiovascular", "Diastolic BP", "mmHg"),
    "MAP": ("Cardiovascular", "Mean arterial pressure", "mmHg"),
    "shock_index": ("Cardiovascular", "Shock index (HR/SBP)", ""),
    "pulse_pressure": ("Cardiovascular", "Pulse pressure", "mmHg"),
    "TroponinI": ("Cardiovascular", "Troponin I", "ng/mL"),
    "Resp": ("Respiratory", "Respiratory rate", "/min"),
    "O2Sat": ("Respiratory", "SpO2", "%"),
    "SaO2": ("Respiratory", "SaO2", "%"),
    "FiO2": ("Respiratory", "FiO2", ""),
    "PaCO2": ("Respiratory", "PaCO2", "mmHg"),
    "EtCO2": ("Respiratory", "End-tidal CO2", "mmHg"),
    "Temp": ("Systemic inflammation", "Temperature", "°C"),
    "WBC": ("Systemic inflammation", "White cell count", "×10³/µL"),
    "Lactate": ("Perfusion", "Lactate", "mmol/L"),
    "BaseExcess": ("Acid–base", "Base excess", "mmol/L"),
    "HCO3": ("Acid–base", "Bicarbonate", "mmol/L"),
    "pH": ("Acid–base", "pH", ""),
    "Creatinine": ("Renal", "Creatinine", "mg/dL"),
    "BUN": ("Renal", "BUN", "mg/dL"),
    "bun_creatinine_ratio": ("Renal", "BUN/creatinine ratio", ""),
    "Potassium": ("Renal", "Potassium", "mmol/L"),
    "Chloride": ("Renal", "Chloride", "mmol/L"),
    "Magnesium": ("Renal", "Magnesium", "mmol/L"),
    "Phosphate": ("Renal", "Phosphate", "mg/dL"),
    "Calcium": ("Renal", "Calcium", "mg/dL"),
    "Bilirubin_total": ("Hepatic", "Total bilirubin", "mg/dL"),
    "Bilirubin_direct": ("Hepatic", "Direct bilirubin", "mg/dL"),
    "AST": ("Hepatic", "AST", "IU/L"),
    "Alkalinephos": ("Hepatic", "Alkaline phosphatase", "IU/L"),
    "Platelets": ("Coagulation", "Platelets", "×10³/µL"),
    "PTT": ("Coagulation", "PTT", "s"),
    "Fibrinogen": ("Coagulation", "Fibrinogen", "mg/dL"),
    "Hgb": ("Haematology", "Haemoglobin", "g/dL"),
    "Hct": ("Haematology", "Haematocrit", "%"),
    "Glucose": ("Metabolic", "Glucose", "mg/dL"),
    "Age": ("Context", "Age", "years"),
    "Gender": ("Context", "Sex", ""),
    "Unit1": ("Context", "ICU type", ""),
    "Unit2": ("Context", "ICU type", ""),
    "HospAdmTime": ("Context", "Time from hospital to ICU admission", "h"),
    "ICULOS": ("Context", "Hours in ICU", "h"),
    "hours_observed": ("Context", "Hours observed", "h"),
    "sf_ratio": ("Respiratory", "SpO2/FiO2 ratio", ""),
    "sofa_resp": ("Organ dysfunction (Sepsis-3)", "SOFA-lite respiratory", ""),
    "sofa_coag": ("Organ dysfunction (Sepsis-3)", "SOFA-lite coagulation", ""),
    "sofa_liver": ("Organ dysfunction (Sepsis-3)", "SOFA-lite liver", ""),
    "sofa_cardio": ("Organ dysfunction (Sepsis-3)", "SOFA-lite cardiovascular", ""),
    "sofa_renal": ("Organ dysfunction (Sepsis-3)", "SOFA-lite renal", ""),
    "sofa_lite": ("Organ dysfunction (Sepsis-3)", "SOFA-lite score", ""),
    "sofa_lite_rise_24h": ("Organ dysfunction (Sepsis-3)", "SOFA-lite rise over 24 h", ""),
    "qsofa_lite": ("Organ dysfunction (Sepsis-3)", "qSOFA-lite (RR, SBP)", ""),
    "sirs_count": ("Systemic inflammation", "SIRS criteria met", ""),
    "labs_measured_24h": ("Care process", "Lab values drawn in last 24 h", ""),
}

# Duration flags: base name → (organ system, description of the abnormal state)
FLAGS: dict[str, tuple[str, str]] = {
    "fever": ("Systemic inflammation", "Fever or hypothermia"),
    "tachycardia": ("Cardiovascular", "Heart rate > 90"),
    "tachypnoea": ("Respiratory", "Respiratory rate ≥ 22"),
    "hypotension": ("Cardiovascular", "Low blood pressure"),
    "hyperlactataemia": ("Perfusion", "Lactate > 2"),
    "abnormal_wbc": ("Systemic inflammation", "Abnormal white cell count"),
}
for _flag, (_organ, _name) in FLAGS.items():
    KNOWLEDGE[_flag] = (_organ, _name, "")

_SUFFIX = re.compile(
    r"_(missing|hours_since|delta_\dh|(mean|min|max|std)_\d+h|dev_baseline|max_since_admit|"
    r"min_since_admit|count_24h|hours_(12|24)h)$"
)


def base_variable(feature: str) -> str:
    return _SUFFIX.sub("", feature)


def _describe(var: str, row: pd.Series) -> str:
    if var in FLAGS:
        hours = row.get(f"{var}_hours_24h", np.nan)
        return f"{FLAGS[var][1]}: {0 if pd.isna(hours) else hours:.0f} of last 24 h"
    _, name, unit = KNOWLEDGE.get(var, ("Other", var, ""))
    value = row.get(var, np.nan)
    if pd.isna(value):
        since = row.get(f"{var}_hours_since", np.nan)
        return f"{name}: not measured" + ("" if pd.isna(since) else f" for {since:.0f} h")
    text = f"{name} {value:.1f}{(' ' + unit) if unit else ''}"
    delta = row.get(f"{var}_delta_6h", np.nan)
    if not pd.isna(delta) and abs(delta) > 1e-6:
        text += f" ({'+' if delta > 0 else ''}{delta:.1f} over 6 h)"
    return text


def explain_rows(model: CalibratedEnsemble, X: pd.DataFrame, top_k: int = 5) -> list[list[dict]]:
    contrib = model.contributions(X)[:, :-1]
    groups = pd.Series(model.feature_columns).map(base_variable).to_numpy()
    uniq, inverse = np.unique(groups, return_inverse=True)
    by_var = np.zeros((len(X), len(uniq)))
    np.add.at(by_var.T, inverse, contrib.T)
    out = []
    for i in range(len(X)):
        row = X.iloc[i]
        order = np.argsort(-np.abs(by_var[i]))[:top_k]
        items = []
        for j in order:
            var = uniq[j]
            organ = KNOWLEDGE.get(var, ("Other",))[0]
            items.append({
                "feature": var,
                "organ_system": organ,
                "direction": "raises" if by_var[i, j] > 0 else "lowers",
                "magnitude": float(abs(by_var[i, j])),
                "plain_language": _describe(var, row),
            })
        out.append(items)
    return out
