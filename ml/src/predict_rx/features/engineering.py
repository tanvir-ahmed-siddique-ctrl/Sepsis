"""Feature engineering for patient-hour sepsis risk windows.

Every feature at hour t uses only rows <= t, so the same function serves
offline training and hour-by-hour inference.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from predict_rx.features.schema import (
    FORWARD_FILL_HOURS,
    LAB_COLS,
    TIME_COL,
    VITAL_COLS,
)


MEASURE_COLS = VITAL_COLS + LAB_COLS


def forward_fill_limited(df: pd.DataFrame, limits: dict[str, int]) -> pd.DataFrame:
    """Forward-fill each column only within its allowed hour limit."""
    out = df.copy()
    for limit in sorted(set(limits.values())):
        cols = [c for c, lim in limits.items() if lim == limit and c in out.columns]
        out[cols] = out[cols].ffill(limit=limit)
    return out


def add_missingness_flags(df: pd.DataFrame, cols: Iterable[str]) -> pd.DataFrame:
    cols = [c for c in cols if c in df.columns]
    present = df[cols].notna().to_numpy()
    idx = np.arange(len(df), dtype=float)[:, None]
    last_seen = pd.DataFrame(np.where(present, idx, np.nan)).ffill().to_numpy()
    missing = pd.DataFrame((~present).astype(np.int8), columns=[f"{c}_missing" for c in cols], index=df.index)
    since = pd.DataFrame(idx - last_seen, columns=[f"{c}_hours_since" for c in cols], index=df.index)
    return pd.concat([df, missing, since], axis=1)


def derived_hemodynamics(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if {"HR", "SBP"}.issubset(out.columns):
        out["shock_index"] = out["HR"] / out["SBP"].replace(0, np.nan)
    if {"SBP", "DBP"}.issubset(out.columns):
        out["pulse_pressure"] = out["SBP"] - out["DBP"]
    if "MAP" not in out.columns and {"SBP", "DBP"}.issubset(out.columns):
        out["MAP"] = (out["SBP"] + 2 * out["DBP"]) / 3
    if {"BUN", "Creatinine"}.issubset(out.columns):
        out["bun_creatinine_ratio"] = out["BUN"] / out["Creatinine"].replace(0, np.nan)
    return out


def window_stats(df: pd.DataFrame, cols: list[str], windows: list[int] | None = None) -> pd.DataFrame:
    """Rolling mean/min/max/std over trailing windows (hours), plus 1h/6h deltas."""
    windows = windows or [6, 12, 24]
    cols = [c for c in cols if c in df.columns]
    values = df[cols]
    blocks = []
    for w in windows:
        roll = values.rolling(window=w, min_periods=1)
        for stat, frame in (("mean", roll.mean()), ("min", roll.min()), ("max", roll.max()), ("std", roll.std())):
            blocks.append(frame.set_axis([f"{c}_{stat}_{w}h" for c in cols], axis=1))
    blocks.append(values.diff(1).set_axis([f"{c}_delta_1h" for c in cols], axis=1))
    blocks.append(values.diff(6).set_axis([f"{c}_delta_6h" for c in cols], axis=1))
    return pd.concat([df, *blocks], axis=1)


BASELINE_COLS = ["HR", "SBP", "MAP", "Resp", "Temp", "O2Sat", "Lactate", "WBC",
                 "Creatinine", "BUN", "Platelets", "Bilirubin_total"]
BASELINE_HOURS = 24


def patient_baseline(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Change from the patient's own baseline (median of the first 24 h so far) and running extremes."""
    cols = [c for c in cols if c in df.columns]
    values = df[cols]
    baseline = values.expanding(min_periods=1).median()
    if len(df) > BASELINE_HOURS:
        baseline.iloc[BASELINE_HOURS:] = baseline.iloc[BASELINE_HOURS - 1].to_numpy()
    blocks = [
        (values - baseline).set_axis([f"{c}_dev_baseline" for c in cols], axis=1),
        values.cummax().set_axis([f"{c}_max_since_admit" for c in cols], axis=1),
        values.cummin().set_axis([f"{c}_min_since_admit" for c in cols], axis=1),
    ]
    return pd.concat([df, *blocks], axis=1)


def measurement_frequency(df: pd.DataFrame) -> pd.DataFrame:
    """How often each lab was actually drawn in the last 24 h (uses pre-fill missingness flags)."""
    labs = [c for c in LAB_COLS if f"{c}_missing" in df.columns]
    drawn = 1 - df[[f"{c}_missing" for c in labs]].to_numpy()
    counts = pd.DataFrame(drawn, index=df.index).rolling(24, min_periods=1).sum()
    counts.columns = [f"{c}_count_24h" for c in labs]
    counts["labs_measured_24h"] = counts.sum(axis=1)
    return pd.concat([df, counts], axis=1)


# Abnormal-state flags on forward-filled values; durations count hours in the flag state.
ABNORMAL_FLAGS = {
    "fever": lambda d: (d["Temp"] > 38.0) | (d["Temp"] < 36.0),
    "tachycardia": lambda d: d["HR"] > 90,
    "tachypnoea": lambda d: d["Resp"] >= 22,
    "hypotension": lambda d: (d["SBP"] <= 100) | (d["MAP"] < 65),
    "hyperlactataemia": lambda d: d["Lactate"] > 2.0,
    "abnormal_wbc": lambda d: (d["WBC"] > 12) | (d["WBC"] < 4),
}


def _band_score(values: pd.Series, cuts: list[float], higher_is_worse: bool) -> pd.Series:
    """0–4 organ score from ordered cut-points; missing values score 0 (as in bedside SOFA)."""
    v = values.to_numpy()
    score = np.zeros(len(v))
    for i, cut in enumerate(cuts, start=1):
        hit = v >= cut if higher_is_worse else v < cut
        score = np.where(hit, i, score)
    return pd.Series(score, index=values.index)


def clinical_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Sepsis-3-oriented scores computable from PhysioNet variables.

    SOFA-lite omits GCS and vasopressors (not recorded) and uses SpO2/FiO2 for the
    respiratory component (Pandharipande et al. 2009 cut-points). qSOFA-lite omits mentation.
    """
    out: dict[str, pd.Series] = {}
    fio2 = df["FiO2"].where(df["FiO2"] <= 1.0, df["FiO2"] / 100.0)
    sf_ratio = df["O2Sat"] / fio2.where(fio2 > 0)
    out["sf_ratio"] = sf_ratio
    out["sofa_resp"] = _band_score(sf_ratio, [512, 357, 214, 89], higher_is_worse=False)
    out["sofa_coag"] = _band_score(df["Platelets"], [150, 100, 50, 20], higher_is_worse=False)
    out["sofa_liver"] = _band_score(df["Bilirubin_total"], [1.2, 2.0, 6.0, 12.0], higher_is_worse=True)
    out["sofa_cardio"] = (df["MAP"] < 70).astype(float)
    out["sofa_renal"] = _band_score(df["Creatinine"], [1.2, 2.0, 3.5, 5.0], higher_is_worse=True)
    sofa = sum(out[k] for k in ("sofa_resp", "sofa_coag", "sofa_liver", "sofa_cardio", "sofa_renal"))
    out["sofa_lite"] = sofa
    out["sofa_lite_rise_24h"] = sofa - sofa.rolling(24, min_periods=1).min()
    out["qsofa_lite"] = ((df["Resp"] >= 22).astype(float) + (df["SBP"] <= 100).astype(float))
    out["sirs_count"] = sum(
        f(df).astype(float) for k, f in ABNORMAL_FLAGS.items() if k in ("fever", "tachycardia", "abnormal_wbc")
    ) + ((df["Resp"] > 20) | (df["PaCO2"] < 32)).astype(float)
    for name, rule in ABNORMAL_FLAGS.items():
        flag = rule(df).astype(float)
        out[f"{name}_hours_12h"] = flag.rolling(12, min_periods=1).sum()
        out[f"{name}_hours_24h"] = flag.rolling(24, min_periods=1).sum()
    return pd.concat([df, pd.DataFrame(out, index=df.index)], axis=1)


def build_patient_features(patient_df: pd.DataFrame) -> pd.DataFrame:
    """Transform one patient's hourly PSV dataframe into model-ready rows."""
    df = patient_df.sort_values(TIME_COL).reset_index(drop=True)
    cols = [c for c in MEASURE_COLS if c in df.columns]
    df[cols] = df[cols].apply(pd.to_numeric, errors="coerce").astype(float)
    df = add_missingness_flags(df, cols)
    df = forward_fill_limited(df, FORWARD_FILL_HOURS)
    df = derived_hemodynamics(df)
    df = window_stats(df, cols)
    df = patient_baseline(df, BASELINE_COLS)
    df = measurement_frequency(df)
    return clinical_scores(df)
