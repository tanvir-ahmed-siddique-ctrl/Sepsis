import json
import sys

import joblib
import numpy as np
import pandas as pd
import pytest

from predict_rx.train.challenger import (
    patient_folds,
    patient_time_weights,
    select_feature_columns,
    validate_development_file,
)
from predict_rx.train.challenger_gate import check_challenger_gate
from predict_rx.train.freeze import PROTECTED_DIRS
from predict_rx.train.run import validate_training_output


def _frame() -> pd.DataFrame:
    rows = []
    for patient in range(10):
        septic = patient % 2
        for hour in range(1, 7):
            rows.append(
                {
                    "patient_id": f"p{patient}",
                    "split": "train",
                    "ICULOS": hour,
                    "hours_observed": hour,
                    "SepsisLabel": int(septic and hour >= 5),
                    "target": int(septic and hour >= 5),
                    "HR": 80 + hour,
                    "HR_delta_6h": hour / 2,
                    "HR_missing": 0,
                    "HR_hours_since": 0,
                    "labs_measured_24h": hour,
                    "sofa_lite": septic,
                }
            )
    return pd.DataFrame(rows)


def test_feature_ablation_families_are_explicit_and_distinct():
    frame = _frame()
    current = select_feature_columns(frame, "physiology_current")
    temporal = select_feature_columns(frame, "physiology_temporal")
    care = select_feature_columns(frame, "care_process_only")
    assert current == ["HR"]
    assert "HR_delta_6h" in temporal
    assert "HR_delta_6h" in select_feature_columns(frame, "vitals_only")
    assert "labs_measured_24h" not in select_feature_columns(frame, "vitals_only")
    assert {"HR_missing", "HR_hours_since", "labs_measured_24h"}.issubset(care)
    assert "sofa_lite" in select_feature_columns(frame, "clinical_scores_only")


def test_patient_weights_equalize_total_patient_contribution():
    frame = _frame()
    weights = patient_time_weights(frame)
    totals = pd.Series(weights).groupby(frame["patient_id"]).sum()
    # Septic timing weights intentionally alter contribution, but equal-length
    # patients with the same label pattern remain exactly balanced.
    assert totals[["p0", "p2", "p4"]].nunique() == 1
    assert totals[["p1", "p3", "p5"]].nunique() == 1
    assert np.isclose(weights.mean(), 1.0)


def test_grouped_folds_never_split_a_patient():
    frame = _frame()
    folds = patient_folds(frame, n_splits=5, seed=42)
    assert set(folds) == set(frame["patient_id"])
    assert set(folds.values()) == set(range(5))


def test_corrupt_parquet_is_rejected_before_training(tmp_path):
    invalid = tmp_path / "features_setA.parquet"
    invalid.write_text("not parquet")
    with pytest.raises(ValueError, match="Invalid Parquet"):
        validate_development_file(invalid)


def test_freeze_refuses_protected_evidence_directories():
    assert PROTECTED_DIRS == {"latest", "run4_frozen"}


def test_temporal_challenger_gate_fails_closed_without_evidence(tmp_path):
    report = check_challenger_gate(tmp_path)
    assert not report["passed"]
    assert not report["requirements"]["valid_dataset_a"]["passed"]
    assert report["decision"].startswith("Do not start")


def test_graph_hazard_cli_fails_closed(tmp_path, monkeypatch):
    from predict_rx.train.graph_hazard import main

    out = tmp_path / "gate.json"
    monkeypatch.setattr(sys, "argv", ["graph_hazard", "--ml-root", str(tmp_path), "--out", str(out)])
    with pytest.raises(SystemExit) as raised:
        main()
    assert raised.value.code == 2
    report = json.loads(out.read_text())
    assert report["dataset_b_accessed"] is False
    assert report["passed"] is False


def test_freeze_cli_refuses_protected_evidence_directories(tmp_path, monkeypatch):
    from predict_rx.train.freeze import main

    monkeypatch.setattr(sys, "argv", ["freeze", "--model-dir", str(tmp_path / "run4_frozen")])
    with pytest.raises(SystemExit, match="protected evidence"):
        main()


class _SyntheticProbabilityModel:
    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        probability = np.clip((frame["HR"].to_numpy(dtype=float) - 40) / 120, 0.01, 0.99)
        return np.column_stack([1 - probability, probability])


def test_eval_run_holdout_requires_authorization_and_refuses_overwrite(tmp_path, monkeypatch):
    from predict_rx.eval.run import main

    features = tmp_path / "features.parquet"
    frame = pd.DataFrame(
        {
            "patient_id": ["p1"] * 6 + ["p2"] * 6,
            "split": ["holdout"] * 12,
            "SepsisLabel": [0, 0, 0, 1, 1, 1] + [0] * 6,
            "hours_observed": list(range(1, 7)) * 2,
            "HR": [90, 95, 100, 110, 120, 125, 70, 72, 74, 76, 78, 80],
            "Age": [61] * 6 + [74] * 6,
            "Gender": [1] * 6 + [0] * 6,
            "Unit1": [1] * 6 + [0] * 6,
            "Unit2": [0] * 6 + [1] * 6,
        }
    )
    frame.to_parquet(features, index=False)
    model_dir = tmp_path / "challenger"
    model_dir.mkdir()
    bundle = {
        "model": _SyntheticProbabilityModel(),
        "model_version": "synthetic-challenger",
        "frozen": True,
        "thresholds": {"watch": 0.3, "high_risk": 0.7},
    }
    joblib.dump(bundle, model_dir / "model.joblib")
    ledger = tmp_path / "access.json"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "eval.run",
            "--features",
            str(features),
            "--model-dir",
            str(model_dir),
            "--split",
            "holdout",
            "--ledger",
            str(ledger),
        ],
    )
    with pytest.raises(SystemExit, match="authorized-by"):
        main()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "eval.run",
            "--features",
            str(features),
            "--model-dir",
            str(model_dir),
            "--split",
            "holdout",
            "--ledger",
            str(ledger),
            "--authorized-by",
            "Taskin",
            "--authorize-dataset-b",
            "Taskin authorizes this one-time frozen challenger Dataset B evaluation",
        ],
    )
    main()
    report_path = model_dir / "eval_holdout.json"
    assert report_path.exists()
    report = json.loads(report_path.read_text())
    assert report["split"] == "holdout"
    assert "slope" in report["calibration"]
    access = json.loads(ledger.read_text())
    assert access["entries"][0]["purpose"] == "challenger_holdout_eval"

    with pytest.raises(SystemExit, match="Refusing to overwrite"):
        main()


def _synthetic_set_a(n_per_split: dict[str, int], seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for split, count in n_per_split.items():
        for index in range(count):
            septic = index % 3 == 0
            hours = 14
            onset = 8 if septic else None
            for hour in range(1, hours + 1):
                label = int(septic and hour >= onset)
                rows.append(
                    {
                        "patient_id": f"{split}-{index}",
                        "split": split,
                        "SepsisLabel": label,
                        "target": label,
                        "hours_observed": hour,
                        "ICULOS": hour,
                        "HR": 75 + (30 if septic and hour >= 5 else 0) + rng.normal(0, 4),
                        "HR_delta_6h": (8 if septic and hour >= 5 else 0) + rng.normal(0, 1),
                        "HR_missing": 0,
                        "Age": 60,
                        "Gender": index % 2,
                        "Unit1": 1,
                        "Unit2": 0,
                    }
                )
    return pd.DataFrame(rows)


def test_compare_internal_calibrates_on_validation_and_saves_freezable_bundle(tmp_path, monkeypatch):
    from predict_rx.eval.compare_internal import main

    monkeypatch.chdir(tmp_path)
    features = tmp_path / "features_setA.parquet"
    _synthetic_set_a({"train": 60, "val": 30, "test": 30}).to_parquet(features, index=False)
    anchor_dir = tmp_path / "anchor"
    anchor_dir.mkdir()
    joblib.dump(
        {
            "model": _SyntheticProbabilityModel(),
            "feature_columns": ["HR"],
            "model_version": "synthetic-run4",
            "thresholds": {"watch": 0.3, "high_risk": 0.5},
        },
        anchor_dir / "model.joblib",
    )
    challenger_dir = tmp_path / "challenger"
    challenger_dir.mkdir()
    (challenger_dir / "result.json").write_text(
        json.dumps(
            {
                "run_id": "SYNTH",
                "seed": 42,
                "dataset_b_accessed": False,
                "internal_test_accessed": False,
                "selection_rule": {"primary": "synthetic"},
                "best": {
                    "family": "lightgbm",
                    "feature_family": "physiology_temporal",
                    "features": ["HR", "HR_delta_6h"],
                    "params": {"n_estimators": 50, "num_leaves": 5, "min_child_samples": 5, "learning_rate": 0.1},
                },
            }
        )
    )
    out = tmp_path / "final"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "compare_internal",
            "--features", str(features),
            "--challenger", str(challenger_dir),
            "--anchor", str(anchor_dir),
            "--out", str(out),
            "--bootstrap", "5",
        ],
    )
    main()
    report = json.loads((out / "compare_internal.json").read_text())
    assert report["dataset_b_accessed"] is False
    assert report["challenger"]["ranking"]["auroc"] > 0.8
    assert "high_risk" in report["challenger_thresholds"]
    bundle = joblib.load(out / "model.joblib")
    assert bundle["frozen"] is False
    assert bundle["model"].calibrator is not None
    assert json.loads((challenger_dir / "result.json").read_text())["internal_test_accessed"] is True
    with pytest.raises(SystemExit, match="Refusing to overwrite"):
        main()


def test_challenger_resume_reuses_completed_trials(tmp_path, monkeypatch):
    from predict_rx.train.challenger import main

    features = tmp_path / "features_setA.parquet"
    _synthetic_set_a({"train": 40, "val": 20, "test": 5}).to_parquet(features, index=False)
    config = tmp_path / "config.yaml"
    config.write_text(
        """
seed: 42
outer_folds: 2
calibration_fraction: 0.3
selection: {primary: mean_normalized_utility}
families:
  lightgbm:
    trials: 2
    search:
      n_estimators: [30]
      num_leaves: [5]
      min_child_samples: [5]
      learning_rate: [0.1]
feature_ablations: [vitals_only, all]
pseudo_sites: {clusters: 2, minimum_rows_for_metric: 5}
"""
    )
    out = tmp_path / "run"
    argv = ["challenger", "--features", str(features), "--config", str(config), "--out", str(out)]
    monkeypatch.setattr(sys, "argv", argv)
    main()
    result = json.loads((out / "result.json").read_text())
    assert result["trial_count"] == 3
    assert result["dataset_b_accessed"] is False
    with pytest.raises(SystemExit, match="completed"):
        main()

    (out / "result.json").unlink()
    monkeypatch.setattr(sys, "argv", argv + ["--resume"])
    main()
    assert json.loads((out / "result.json").read_text())["trial_count"] == 3


def test_historical_trainer_cannot_overwrite_frozen_or_latest(tmp_path):
    with pytest.raises(ValueError, match="protected evidence"):
        validate_training_output(tmp_path / "artifacts/models/latest", tmp_path)
    with pytest.raises(ValueError, match="protected evidence"):
        validate_training_output(tmp_path / "artifacts/models/run4_frozen", tmp_path)
    safe = tmp_path / "artifacts/experiments/new-run"
    validate_training_output(safe, tmp_path)
