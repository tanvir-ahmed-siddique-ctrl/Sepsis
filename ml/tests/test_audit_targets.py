from __future__ import annotations

import pandas as pd

from predict_rx.audit.data import audit_feature_file
from predict_rx.audit.targets import build_incident_targets


def test_incident_targets_exclude_onset_and_censor_post_onset():
    frame = pd.DataFrame(
        {
            "patient_id": ["septic"] * 12 + ["control"] * 5,
            "SepsisLabel": [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1] + [0] * 5,
        }
    )
    targets = build_incident_targets(frame)

    # First positive label at position 2 means derived onset at position 8.
    assert targets.loc[2, "incident_hours_to_onset"] == 6
    assert targets.loc[2, "incident_onset_within_6h"] == 1
    assert targets.loc[1, "incident_onset_within_6h"] == 0
    assert targets.loc[7, "incident_onset_within_1h"] == 1
    assert pd.isna(targets.loc[8, "incident_onset_within_12h"])
    assert pd.isna(targets.loc[11, "incident_onset_within_12h"])

    control = targets.iloc[12:]
    assert control["incident_at_risk"].all()
    assert control["incident_onset_within_12h"].eq(0).all()


def test_incident_targets_reject_nonpositive_horizon():
    frame = pd.DataFrame({"patient_id": ["p"], "SepsisLabel": [0]})
    try:
        build_incident_targets(frame, horizons=[0])
    except ValueError as error:
        assert "positive" in str(error)
    else:
        raise AssertionError("Expected invalid horizon to fail")


def test_processed_feature_audit_on_synthetic_parquet(tmp_path):
    path = tmp_path / "features.parquet"
    frame = pd.DataFrame(
        {
            "patient_id": ["p1"] * 4 + ["p2"] * 4,
            "split": ["train"] * 4 + ["val"] * 4,
            "SepsisLabel": [0, 0, 1, 1] + [0] * 4,
            "target": [0, 0, 1, 1] + [0] * 4,
            "ICULOS": [1, 2, 3, 4] * 2,
            "hours_observed": [1, 2, 3, 4] * 2,
            "Age": [60] * 4 + [70] * 4,
            "Gender": [1] * 4 + [0] * 4,
            "HR": [80, 90, 100, 110, 70, 72, 74, 76],
            "HR_missing": [0] * 8,
        }
    )
    frame.to_parquet(path, index=False)
    report, loaded = audit_feature_file(path, full_column_scan=False)
    assert report["rows"] == 8
    assert report["patients"] == 2
    assert report["duplicate_patient_time_rows"] == 0
    assert report["label_reversions_1_to_0"] == 0
    assert loaded["patient_id"].nunique() == 2
