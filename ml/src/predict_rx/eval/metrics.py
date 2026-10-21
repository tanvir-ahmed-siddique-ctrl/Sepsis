"""Evaluation metrics, including the official PhysioNet 2019 utility score.

Utility follows the challenge scoring code (evaluate_sepsis_score.py):
onset t_sepsis = first positive label index + 6; rewards for predicting in
[t_sepsis-12, t_sepsis+3], penalties for late/missed detection and false alarms.
It is precomputed per row as u_pos (utility if predicted positive) and u_neg,
so any threshold can be scored with one vectorised sum.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.linear_model import LogisticRegression

DT_EARLY, DT_OPTIMAL, DT_LATE = -12, -6, 3
MAX_U_TP, MIN_U_FN, U_FP, U_TN = 1.0, -2.0, -0.05, 0.0


def _patient_utility_rows(labels: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = len(labels)
    t = np.arange(n, dtype=float)
    if labels.any():
        t_sepsis = float(np.argmax(labels) - DT_OPTIMAL)
        m1 = MAX_U_TP / (DT_OPTIMAL - DT_EARLY)
        b1 = -m1 * DT_EARLY
        m2 = -MAX_U_TP / (DT_LATE - DT_OPTIMAL)
        b2 = -m2 * DT_LATE
        m3 = MIN_U_FN / (DT_LATE - DT_OPTIMAL)
        b3 = -m3 * DT_OPTIMAL
        rel = t - t_sepsis
        early = t <= t_sepsis + DT_OPTIMAL
        late = (~early) & (t <= t_sepsis + DT_LATE)
        u_pos = np.where(early, np.maximum(m1 * rel + b1, U_FP), np.where(late, m2 * rel + b2, 0.0))
        u_neg = np.where(late, m3 * rel + b3, 0.0)
        best = np.zeros(n, dtype=bool)
        lo, hi = int(max(0, t_sepsis + DT_EARLY)), int(min(t_sepsis + DT_LATE + 1, n))
        best[lo:hi] = True
    else:
        u_pos = np.full(n, U_FP)
        u_neg = np.full(n, U_TN)
        best = np.zeros(n, dtype=bool)
    return u_pos, u_neg, best


@dataclass
class UtilityTable:
    u_pos: np.ndarray
    u_neg: np.ndarray
    best: float
    inaction: float

    @classmethod
    def from_frame(cls, df: pd.DataFrame, label_col: str = "SepsisLabel") -> "UtilityTable":
        """df must be ordered by patient then time, containing every hour of each stay."""
        u_pos = np.empty(len(df))
        u_neg = np.empty(len(df))
        best_mask = np.empty(len(df), dtype=bool)
        labels = df[label_col].to_numpy()
        starts = _group_starts(df["patient_id"].to_numpy())
        for s, e in zip(starts[:-1], starts[1:]):
            u_pos[s:e], u_neg[s:e], best_mask[s:e] = _patient_utility_rows(labels[s:e] == 1)
        best = float(np.where(best_mask, u_pos, u_neg).sum())
        return cls(u_pos=u_pos, u_neg=u_neg, best=best, inaction=float(u_neg.sum()))

    def normalized(self, pred: np.ndarray) -> float:
        observed = float(np.where(pred, self.u_pos, self.u_neg).sum())
        return (observed - self.inaction) / (self.best - self.inaction)


def _group_starts(ids: np.ndarray) -> np.ndarray:
    change = np.flatnonzero(ids[1:] != ids[:-1]) + 1
    return np.concatenate([[0], change, [len(ids)]])


def expected_calibration_error(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    """Equal-mass bins: with ~2% prevalence equal-width bins leave upper bins empty."""
    order = np.argsort(y_prob)
    ece = 0.0
    for chunk in np.array_split(order, n_bins):
        if len(chunk):
            ece += len(chunk) / len(y_prob) * abs(y_true[chunk].mean() - y_prob[chunk].mean())
    return float(ece)


def candidate_thresholds(prob: np.ndarray, n: int = 300) -> np.ndarray:
    qs = np.quantile(prob, np.linspace(0.5, 0.9995, n))
    return np.unique(qs)


def best_utility_threshold(table: UtilityTable, prob: np.ndarray, eligible: np.ndarray,
                           labels: np.ndarray | None = None, min_specificity: float | None = None) -> tuple[float, float]:
    """Utility-maximising threshold, optionally restricted to hour-level specificity >= min_specificity."""
    best_t, best_u = 1.0, -np.inf
    negatives = None if labels is None else eligible & (labels == 0)
    for t in candidate_thresholds(prob[eligible]):
        pred = (prob >= t) & eligible
        if min_specificity is not None and 1 - pred[negatives].mean() < min_specificity:
            continue
        u = table.normalized(pred)
        if u > best_u:
            best_t, best_u = float(t), u
    return best_t, float(best_u)


def patient_onsets(df: pd.DataFrame, label_col: str = "SepsisLabel") -> pd.Series:
    """Row-position onset (first label + 6) per septic patient."""
    pos = df.groupby("patient_id", sort=False).cumcount()
    first = pos[df[label_col] == 1].groupby(df["patient_id"]).min()
    return first - DT_OPTIMAL


def patient_detection(df: pd.DataFrame, pred: np.ndarray, label_col: str = "SepsisLabel") -> dict:
    """Per septic patient: first alert position vs onset."""
    pos = df.groupby("patient_id", sort=False).cumcount().to_numpy()
    onset = patient_onsets(df, label_col)
    alerted = pd.Series(np.where(pred, pos, np.nan), index=df.index)
    first_alert = alerted.groupby(df["patient_id"]).min().reindex(onset.index)
    lead = onset - first_alert
    detected = lead >= 0
    return {
        "septic_patients": int(len(onset)),
        "detected_before_onset": float(detected.mean()) if len(onset) else None,
        "detected_in_optimal_window": float(((lead >= 0) & (lead <= -DT_EARLY)).mean()) if len(onset) else None,
        "median_warning_hours": float(lead[detected].median()) if detected.any() else None,
    }


def patient_sensitivity_threshold(df: pd.DataFrame, prob: np.ndarray, eligible: np.ndarray,
                                  target: float) -> float:
    """Highest threshold that still flags `target` fraction of septic patients before onset."""
    pos = df.groupby("patient_id", sort=False).cumcount().to_numpy()
    onset = patient_onsets(df)
    onset_row = df["patient_id"].map(onset).to_numpy()
    window = eligible & ~np.isnan(onset_row) & (pos <= onset_row)
    best_before = pd.Series(np.where(window, prob, -1.0)).groupby(df["patient_id"].to_numpy()).max()
    best_before = best_before.reindex(onset.index).to_numpy()
    return float(np.quantile(best_before, 1 - target))


def alert_events(df: pd.DataFrame, pred: np.ndarray) -> dict:
    """Alert = transition into positive. True if it lands in [onset-12, onset+3]."""
    ids = df["patient_id"].to_numpy()
    prev = np.concatenate([[False], pred[:-1]])
    new_patient = np.concatenate([[True], ids[1:] != ids[:-1]])
    event = pred & (~prev | new_patient)
    pos = df.groupby("patient_id", sort=False).cumcount().to_numpy()
    onset = df["patient_id"].map(patient_onsets(df)).to_numpy()
    true_event = event & ~np.isnan(onset) & (pos >= onset + DT_EARLY) & (pos <= onset + DT_LATE)
    hours = len(df)
    return {
        "alerts_per_patient_day": float(event.sum() / hours * 24),
        "false_alerts_per_100_patient_hours": float((event & ~true_event).sum() / hours * 100),
        "alert_precision": float(true_event.sum() / event.sum()) if event.any() else None,
    }


def ranking_metrics(y: np.ndarray, prob: np.ndarray) -> dict:
    two_classes = len(np.unique(y)) > 1
    prevalence = float(y.mean())
    brier = float(brier_score_loss(y, prob))
    brier_reference = prevalence * (1 - prevalence)
    return {
        "auroc": float(roc_auc_score(y, prob)) if two_classes else None,
        "auprc": float(average_precision_score(y, prob)) if two_classes else None,
        "auprc_over_prevalence": (
            float(average_precision_score(y, prob) / prevalence)
            if two_classes and prevalence > 0
            else None
        ),
        "brier": brier,
        "brier_reference": brier_reference,
        "brier_skill": 1 - brier / brier_reference if brier_reference > 0 else None,
        "ece": expected_calibration_error(y, prob),
        "prevalence": prevalence,
        "rows": int(len(y)),
    }


def calibration_diagnostics(y: np.ndarray, prob: np.ndarray, n_bins: int = 10) -> dict:
    """Calibration intercept/slope and an equal-mass reliability table."""
    y = np.asarray(y, dtype=int)
    prob = np.asarray(prob, dtype=float)
    clipped = np.clip(prob, 1e-6, 1 - 1e-6)
    if len(np.unique(y)) < 2:
        intercept = slope = None
    else:
        logit = np.log(clipped / (1 - clipped)).reshape(-1, 1)
        recalibrator = LogisticRegression(
            C=np.inf,
            solver="lbfgs",
            max_iter=1000,
        ).fit(logit, y)
        intercept = float(recalibrator.intercept_[0])
        slope = float(recalibrator.coef_[0, 0])
    order = np.argsort(prob)
    reliability = []
    for index, chunk in enumerate(np.array_split(order, n_bins), start=1):
        if not len(chunk):
            continue
        reliability.append(
            {
                "bin": index,
                "rows": int(len(chunk)),
                "mean_predicted": float(prob[chunk].mean()),
                "observed_rate": float(y[chunk].mean()),
                "minimum_predicted": float(prob[chunk].min()),
                "maximum_predicted": float(prob[chunk].max()),
            }
        )
    return {
        "intercept": intercept,
        "slope": slope,
        "binning": f"{n_bins} equal-mass bins",
        "reliability": reliability,
    }


def confusion_metrics(y: np.ndarray, pred: np.ndarray) -> dict:
    tp = int((pred & (y == 1)).sum())
    fp = int((pred & (y == 0)).sum())
    fn = int((~pred & (y == 1)).sum())
    tn = int((~pred & (y == 0)).sum())
    div = lambda a, b: float(a / b) if b else None  # noqa: E731
    return {
        "sensitivity": div(tp, tp + fn),
        "specificity": div(tn, tn + fp),
        "ppv": div(tp, tp + fp),
        "npv": div(tn, tn + fn),
    }


def full_report(df: pd.DataFrame, prob: np.ndarray, eligible: np.ndarray,
                thresholds: dict[str, float], table: UtilityTable | None = None) -> dict:
    """df: every hour of each stay, ordered. prob scored on all rows; ineligible rows never alert."""
    table = table or UtilityTable.from_frame(df)
    y = df["SepsisLabel"].to_numpy()
    report = {
        "ranking": ranking_metrics(y[eligible], prob[eligible]),
        "calibration": calibration_diagnostics(y[eligible], prob[eligible]),
        "patients": int(df["patient_id"].nunique()),
    }
    for name, t in thresholds.items():
        pred = (prob >= t) & eligible
        report[name] = {
            "threshold": t,
            "normalized_utility": table.normalized(pred),
            **confusion_metrics(y, pred),
            **alert_events(df, pred),
            **patient_detection(df, pred),
        }
    return report


def subgroup_report(df: pd.DataFrame, prob: np.ndarray, eligible: np.ndarray, threshold: float) -> dict:
    first = df.groupby("patient_id", sort=False).first()
    age_band = pd.cut(first["Age"], [0, 45, 65, 80, 200], right=False,
                      labels=["18-44", "45-64", "65-79", "80+"]).astype(str)
    unit = np.select([first["Unit1"] == 1, first["Unit2"] == 1], ["MICU", "SICU"], "unknown")
    groups = {
        "sex": first["Gender"].map({0: "female", 1: "male"}).fillna("unknown"),
        "age": age_band,
        "icu_type": pd.Series(unit, index=first.index),
    }
    out: dict = {}
    for gname, labels in groups.items():
        row_group = df["patient_id"].map(labels).to_numpy()
        out[gname] = _group_metrics(df, prob, eligible, threshold, row_group)
    miss_cols = [c for c in df.columns if c.endswith("_missing")]
    if miss_cols:
        row_missing = df[miss_cols].mean(axis=1)
        try:
            miss_band = (
                pd.qcut(row_missing, 3, labels=["low", "medium", "high"], duplicates="drop")
                .astype(str)
                .to_numpy()
            )
            out["missingness"] = _group_metrics(df, prob, eligible, threshold, miss_band, patient_level=False)
        except ValueError:
            out["missingness"] = {
                "insufficient_variation": {
                    "rows": int(len(df)),
                    "note": "missingness tertiles undefined on this frame",
                }
            }
    return out


def _group_metrics(df, prob, eligible, threshold, row_group, patient_level: bool = True) -> dict:
    res = {}
    y = df["SepsisLabel"].to_numpy()
    for g in sorted(pd.unique(row_group)):
        m = (row_group == g) & eligible
        entry = {"rows": int(m.sum()), **ranking_metrics(y[m], prob[m])}
        entry.update(confusion_metrics(y[m], prob[m] >= threshold))
        if patient_level:
            sub = df[row_group == g]
            entry.update(patient_detection(sub, ((prob >= threshold) & eligible)[row_group == g]))
        res[str(g)] = entry
    return res
