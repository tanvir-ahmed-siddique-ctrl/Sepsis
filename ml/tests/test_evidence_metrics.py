from __future__ import annotations

import numpy as np
import pandas as pd

from predict_rx.eval.bootstrap import patient_paired_bootstrap
from predict_rx.eval.metrics import calibration_diagnostics, full_report, ranking_metrics


def test_ranking_metrics_include_prevalence_normalized_and_brier_skill():
    y = np.array([0, 0, 1, 1])
    probability = np.array([0.1, 0.2, 0.8, 0.9])
    metrics = ranking_metrics(y, probability)
    assert metrics["auprc_over_prevalence"] == 2.0
    assert metrics["brier_reference"] == 0.25
    assert metrics["brier_skill"] > 0


def test_calibration_diagnostics_have_intercept_slope_and_bins():
    y = np.array([0, 0, 0, 1, 1, 1])
    probability = np.array([0.05, 0.1, 0.2, 0.7, 0.8, 0.9])
    diagnostics = calibration_diagnostics(y, probability, n_bins=3)
    assert diagnostics["intercept"] is not None
    assert diagnostics["slope"] is not None
    assert len(diagnostics["reliability"]) == 3


def test_full_report_includes_calibration_slope():
    frame = pd.DataFrame(
        {
            "patient_id": ["p1"] * 4 + ["p2"] * 4,
            "SepsisLabel": [0, 0, 1, 1, 0, 0, 0, 0],
            "hours_observed": [1, 2, 3, 4, 1, 2, 3, 4],
        }
    )
    probability = np.array([0.1, 0.2, 0.8, 0.9, 0.05, 0.1, 0.15, 0.2])
    eligible = np.array([False, False, True, True, False, False, True, True])
    report = full_report(frame, probability, eligible, {"watch": 0.3, "high_risk": 0.7})
    assert report["calibration"]["slope"] is not None
    assert report["ranking"]["brier_skill"] is not None


def test_patient_bootstrap_is_paired_across_models():
    frame = pd.DataFrame(
        {
            "patient_id": np.repeat(["s1", "s2", "n1", "n2"], 12),
            "SepsisLabel": (
                [0] * 4 + [1] * 8
                + [0] * 5 + [1] * 7
                + [0] * 12
                + [0] * 12
            ),
        }
    )
    labels = frame["SepsisLabel"].to_numpy()
    anchor = np.where(labels == 1, 0.9, 0.1).astype(float)
    baseline = np.full(len(frame), 0.4)
    result = patient_paired_bootstrap(
        frame,
        {"lightgbm": anchor, "logistic": baseline},
        np.ones(len(frame), dtype=bool),
        {"lightgbm": 0.5, "logistic": 0.5},
        anchor="lightgbm",
        replicates=30,
        seed=7,
    )
    assert result["replicates"] == 30
    difference = result["paired_differences_anchor_minus_comparator"]["logistic"]["auprc"]
    assert difference["lower"] is not None
    assert difference["upper"] is not None
