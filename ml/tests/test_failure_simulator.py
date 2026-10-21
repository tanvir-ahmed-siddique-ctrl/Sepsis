import numpy as np
import pandas as pd

from predict_rx.robustness.failures import (
    FailureScenario,
    evaluate_scenarios,
    perturb_patient,
)


def _patient() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ICULOS": np.arange(1, 9),
            "HR": [70, 72, 75, 78, 90, 105, 115, 120],
            "SBP": [120, 120, 118, 115, 110, 105, 100, 95],
            "MAP": [85, 84, 82, 80, 77, 73, 70, 66],
            "O2Sat": [98, 98, 97, 97, 96, 95, 94, 93],
            "Lactate": [np.nan, np.nan, 1.2, np.nan, 1.8, np.nan, 2.5, 3.0],
            "WBC": [8, np.nan, np.nan, 9, np.nan, np.nan, 13, np.nan],
            "SepsisLabel": [0, 0, 0, 0, 0, 1, 1, 1],
        }
    )


def _score(frame: pd.DataFrame) -> np.ndarray:
    return (frame["HR"].fillna(0).to_numpy(dtype=float) - 70) / 100


def test_duplicate_and_out_of_order_failures_canonicalize_idempotently():
    source = _patient()
    duplicated = perturb_patient(source, FailureScenario.duplicate_observations)
    reordered = perturb_patient(source, FailureScenario.out_of_order)
    pd.testing.assert_frame_equal(duplicated, source)
    pd.testing.assert_frame_equal(reordered, source)


def test_delay_and_dropout_report_alert_stability_metrics():
    reports = evaluate_scenarios(
        {"p1": _patient()},
        _score,
        threshold=0.3,
        scenarios=[FailureScenario.vital_delay_2h, FailureScenario.sensor_dropout],
        seed=7,
    )
    assert [report.scenario for report in reports] == ["vital_delay_2h", "sensor_dropout"]
    assert all(report.rows == 8 for report in reports)
    assert all(0 <= report.alert_flip_rate <= 1 for report in reports)
    assert reports[0].unstable_baseline_alerts > 0
    assert reports[0].retained_positive_sensitivity is not None
    assert reports[0].false_alert_change is not None
