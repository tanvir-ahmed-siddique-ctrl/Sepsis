"""Patient-level paired bootstrap for discrimination and alert utility."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from predict_rx.eval.metrics import _patient_utility_rows


@dataclass
class PatientOperatingSummary:
    observed_utility: np.ndarray
    best_utility: np.ndarray
    inaction_utility: np.ndarray
    tp: np.ndarray
    fp: np.ndarray
    fn: np.ndarray
    tn: np.ndarray
    events: np.ndarray
    false_events: np.ndarray
    true_events: np.ndarray
    hours: np.ndarray
    detected: np.ndarray
    optimal_window: np.ndarray
    warning_hours: np.ndarray


def _patient_summaries(
    frame: pd.DataFrame,
    probability: np.ndarray,
    eligible: np.ndarray,
    threshold: float,
    groups: list[np.ndarray],
) -> PatientOperatingSummary:
    labels = frame["SepsisLabel"].to_numpy(dtype=int)
    pred = (probability >= threshold) & eligible
    rows: dict[str, list[float]] = {
        name: []
        for name in (
            "observed_utility",
            "best_utility",
            "inaction_utility",
            "tp",
            "fp",
            "fn",
            "tn",
            "events",
            "false_events",
            "true_events",
            "hours",
            "detected",
            "optimal_window",
            "warning_hours",
        )
    }
    for indices in groups:
        patient_labels = labels[indices]
        patient_pred = pred[indices]
        patient_eligible = eligible[indices]
        u_pos, u_neg, best_mask = _patient_utility_rows(patient_labels == 1)
        rows["observed_utility"].append(float(np.where(patient_pred, u_pos, u_neg).sum()))
        rows["best_utility"].append(float(np.where(best_mask, u_pos, u_neg).sum()))
        rows["inaction_utility"].append(float(u_neg.sum()))
        y = patient_labels[patient_eligible]
        p = patient_pred[patient_eligible]
        rows["tp"].append(float((p & (y == 1)).sum()))
        rows["fp"].append(float((p & (y == 0)).sum()))
        rows["fn"].append(float((~p & (y == 1)).sum()))
        rows["tn"].append(float((~p & (y == 0)).sum()))

        event = patient_pred & ~np.concatenate([[False], patient_pred[:-1]])
        if patient_labels.any():
            onset = int(np.argmax(patient_labels) + 6)
            positions = np.arange(len(indices))
            true_event = event & (positions >= onset - 12) & (positions <= onset + 3)
            alert_positions = positions[patient_pred]
            first_alert = int(alert_positions[0]) if len(alert_positions) else None
            lead = float(onset - first_alert) if first_alert is not None else np.nan
            detected = float(first_alert is not None and lead >= 0)
            optimal = float(first_alert is not None and 0 <= lead <= 12)
        else:
            true_event = np.zeros(len(indices), dtype=bool)
            lead = np.nan
            detected = 0.0
            optimal = 0.0
        rows["events"].append(float(event.sum()))
        rows["false_events"].append(float((event & ~true_event).sum()))
        rows["true_events"].append(float(true_event.sum()))
        rows["hours"].append(float(len(indices)))
        rows["detected"].append(detected if patient_labels.any() else np.nan)
        rows["optimal_window"].append(optimal if patient_labels.any() else np.nan)
        rows["warning_hours"].append(lead if detected else np.nan)
    return PatientOperatingSummary(**{key: np.asarray(value) for key, value in rows.items()})


def _aggregate_operating(summary: PatientOperatingSummary, sample: np.ndarray) -> dict[str, float | None]:
    observed = summary.observed_utility[sample].sum()
    best = summary.best_utility[sample].sum()
    inaction = summary.inaction_utility[sample].sum()
    denominator = best - inaction
    tp = summary.tp[sample].sum()
    fp = summary.fp[sample].sum()
    fn = summary.fn[sample].sum()
    tn = summary.tn[sample].sum()
    events = summary.events[sample].sum()
    true_events = summary.true_events[sample].sum()
    septic = ~np.isnan(summary.detected[sample])
    warning = summary.warning_hours[sample]
    return {
        "normalized_utility": float((observed - inaction) / denominator) if denominator else None,
        "sensitivity": float(tp / (tp + fn)) if tp + fn else None,
        "specificity": float(tn / (tn + fp)) if tn + fp else None,
        "ppv": float(tp / (tp + fp)) if tp + fp else None,
        "false_alerts_per_100_patient_hours": float(
            summary.false_events[sample].sum() / summary.hours[sample].sum() * 100
        ),
        "alert_precision": float(true_events / events) if events else None,
        "detected_before_onset": float(np.nanmean(summary.detected[sample])) if septic.any() else None,
        "detected_in_optimal_window": (
            float(np.nanmean(summary.optimal_window[sample])) if septic.any() else None
        ),
        "median_warning_hours": (
            float(np.nanmedian(warning)) if np.isfinite(warning).any() else None
        ),
    }


def _percentile_interval(values: list[float | None], confidence: float) -> dict[str, float | None]:
    valid = np.asarray([value for value in values if value is not None and np.isfinite(value)], dtype=float)
    if not len(valid):
        return {"lower": None, "upper": None}
    alpha = (1 - confidence) / 2
    return {
        "lower": float(np.quantile(valid, alpha)),
        "upper": float(np.quantile(valid, 1 - alpha)),
    }


def patient_paired_bootstrap(
    frame: pd.DataFrame,
    probabilities: dict[str, np.ndarray],
    eligible: np.ndarray,
    thresholds: dict[str, float],
    *,
    anchor: str,
    replicates: int,
    seed: int,
    confidence: float = 0.95,
) -> dict[str, object]:
    """Bootstrap patients with replacement using one paired draw for all models."""
    if set(probabilities) != set(thresholds):
        raise ValueError("Every probability vector must have one operating threshold.")
    group_indices = [
        indices
        for indices in frame.groupby("patient_id", sort=False).indices.values()
    ]
    eligible_groups = [indices[eligible[indices]] for indices in group_indices]
    summaries = {
        name: _patient_summaries(frame, probability, eligible, thresholds[name], group_indices)
        for name, probability in probabilities.items()
    }
    draws: dict[str, dict[str, list[float | None]]] = {
        name: {} for name in probabilities
    }
    paired: dict[str, dict[str, list[float | None]]] = {
        name: {} for name in probabilities if name != anchor
    }
    labels = frame["SepsisLabel"].to_numpy(dtype=int)
    rng = np.random.default_rng(seed)
    for _ in range(replicates):
        sample = rng.integers(0, len(group_indices), size=len(group_indices))
        row_indices = np.concatenate([eligible_groups[index] for index in sample])
        y = labels[row_indices]
        replicate_metrics: dict[str, dict[str, float | None]] = {}
        for name, probability in probabilities.items():
            p = probability[row_indices]
            ranking = {
                "auroc": float(roc_auc_score(y, p)) if len(np.unique(y)) > 1 else None,
                "auprc": float(average_precision_score(y, p)) if len(np.unique(y)) > 1 else None,
                "brier": float(brier_score_loss(y, p)),
            }
            metrics = {**ranking, **_aggregate_operating(summaries[name], sample)}
            replicate_metrics[name] = metrics
            for metric, value in metrics.items():
                draws[name].setdefault(metric, []).append(value)
        for name in paired:
            for metric in ("auroc", "auprc", "brier", "normalized_utility", "sensitivity", "specificity"):
                anchor_value = replicate_metrics[anchor][metric]
                comparator_value = replicate_metrics[name][metric]
                difference = (
                    None
                    if anchor_value is None or comparator_value is None
                    else float(anchor_value - comparator_value)
                )
                paired[name].setdefault(metric, []).append(difference)
    return {
        "method": "patient-level paired bootstrap with replacement",
        "replicates": replicates,
        "seed": seed,
        "confidence_level": confidence,
        "model_intervals": {
            name: {
                metric: _percentile_interval(values, confidence)
                for metric, values in metrics.items()
            }
            for name, metrics in draws.items()
        },
        "paired_differences_anchor_minus_comparator": {
            name: {
                metric: _percentile_interval(values, confidence)
                for metric, values in metrics.items()
            }
            for name, metrics in paired.items()
        },
    }
