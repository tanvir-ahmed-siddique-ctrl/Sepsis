from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import yaml

from predict_rx.eval.baselines_setb import run
from predict_rx.eval.metrics import full_report


class SyntheticProbabilityModel:
    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        probability = np.clip((frame["HR"].to_numpy(dtype=float) - 40) / 120, 0.01, 0.99)
        return np.column_stack([1 - probability, probability])


def _patient(patient_id: str, split: str, septic: bool, base: float) -> pd.DataFrame:
    hours = np.arange(1, 9)
    labels = np.array([0, 0, 1, 1, 1, 1, 1, 1]) if septic else np.zeros(8, dtype=int)
    return pd.DataFrame(
        {
            "patient_id": patient_id,
            "split": split,
            "SepsisLabel": labels,
            "target": labels,
            "hours_observed": hours,
            "Temp": 37 + (0.8 if septic else 0),
            "HR": base + hours,
            "Resp": 18 + (5 if septic else 0),
            "WBC": 8 + (6 if septic else 0),
            "shock_index": 0.6 + (0.5 if septic else 0),
        }
    )


def test_baseline_bundle_runs_end_to_end_on_synthetic_fixture(tmp_path: Path):
    set_a = pd.concat(
        [
            _patient("tr-s1", "train", True, 105),
            _patient("tr-s2", "train", True, 100),
            _patient("tr-n1", "train", False, 65),
            _patient("tr-n2", "train", False, 70),
            _patient("va-s1", "val", True, 102),
            _patient("va-s2", "val", True, 98),
            _patient("va-n1", "val", False, 66),
            _patient("va-n2", "val", False, 72),
        ],
        ignore_index=True,
    )
    set_b = pd.concat(
        [
            _patient("b-s1", "holdout", True, 101),
            _patient("b-s2", "holdout", True, 96),
            _patient("b-n1", "holdout", False, 64),
            _patient("b-n2", "holdout", False, 71),
        ],
        ignore_index=True,
    )
    set_a_path = tmp_path / "set_a.parquet"
    set_b_path = tmp_path / "set_b.parquet"
    set_a.to_parquet(set_a_path, index=False)
    set_b.to_parquet(set_b_path, index=False)

    model_dir = tmp_path / "run4_frozen"
    model_dir.mkdir()
    model_path = model_dir / "model.joblib"
    bundle = {
        "model": SyntheticProbabilityModel(),
        "feature_columns": ["Temp", "HR", "Resp", "WBC", "shock_index", "hours_observed"],
        "thresholds": {"watch": 0.3, "high_risk": 0.5},
        "model_version": "synthetic-frozen",
        "frozen": True,
    }
    joblib.dump(bundle, model_path)
    model_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()
    (model_dir / "FROZEN.json").write_text(
        json.dumps(
            {
                "model_version": "synthetic-frozen",
                "frozen_at": "2026-01-01T00:00:00+00:00",
                "model_sha256": model_hash,
                "thresholds": bundle["thresholds"],
            }
        ),
        encoding="utf-8",
    )
    eligible_b = (set_b["hours_observed"] >= 4).to_numpy()
    historical = full_report(
        set_b,
        bundle["model"].predict_proba(set_b)[:, 1],
        eligible_b,
        bundle["thresholds"],
    )
    (model_dir / "eval_holdout.json").write_text(json.dumps(historical), encoding="utf-8")

    config = {
        "seed": 42,
        "bootstrap_replicates": 0,
        "confidence_level": 0.95,
        "eligibility": {
            "expected_dataset_b_eligible_rows": int(eligible_b.sum()),
            "expected_dataset_b_patients": int(set_b["patient_id"].nunique()),
        },
        "training": {"logistic_max_iter": 100, "logistic_class_weight": "balanced"},
        "thresholds": {"high_risk_min_specificity": 0.5, "watch_patient_sensitivity": 0.5},
        "release_rule": {
            "primary": "synthetic test",
            "secondary": "synthetic test",
            "decision_curve": "not valid for synthetic official-label view",
        },
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    output = tmp_path / "result"
    args = argparse.Namespace(
        set_a=set_a_path,
        set_b=set_b_path,
        model_dir=model_dir,
        config=config_path,
        out=output,
        ledger=tmp_path / "access.json",
        authorized_by="test",
        authorize_dataset_b="DATASET_B_AUTHORIZED",
        access_reason="synthetic fixture",
        allow_repeat=False,
        bootstrap=0,
    )
    result_path = run(args)
    report = json.loads((result_path / "report.json").read_text(encoding="utf-8"))
    assert set(report["dataset_b_reports"]) == {"clinical_rule", "logistic", "lightgbm"}
    assert report["frozen_anchor_parity"]["status"] == "pass"
    assert (result_path / "reliability_dataset_b.png").exists()
