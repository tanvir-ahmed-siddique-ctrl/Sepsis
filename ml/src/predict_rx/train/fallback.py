"""Low-resource vitals-only fallback model (Dataset A only).

Selects hyperparameters with the same patient-grouped folds and rule as the
tabular challenger, then refits like Run 4: train patients fit (10% held back
for early stopping), isotonic calibration and thresholds on validation
patients. The locked internal test and Dataset B are never read here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import yaml
from sklearn.isotonic import IsotonicRegression

from predict_rx.eval.compare_internal import _early_stopping_ids, validation_thresholds
from predict_rx.eval.metrics import full_report
from predict_rx.features.schema import MIN_HOURS_BEFORE_PRED
from predict_rx.models import CalibratedEnsemble
from predict_rx.train.challenger import (
    _fit_model,
    _sample_params,
    _summary,
    _trial_key,
    evaluate_candidate,
    patient_folds,
    select_feature_columns,
    validate_development_file,
)
from predict_rx.train.run import validate_training_output


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=Path("data/processed/features_setA.parquet"))
    parser.add_argument("--config", type=Path, default=Path("configs/fallback_low_resource.yaml"))
    parser.add_argument("--out", type=Path, default=Path("artifacts/fallback/LOWRES-FALLBACK-01"))
    parser.add_argument("--trials", type=int, default=None, help="Override trial count (smoke tests only)")
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"Refusing to overwrite fallback bundle: {args.out}")
    validate_training_output(args.out, Path("."))
    validate_development_file(args.features)
    config = yaml.safe_load(args.config.read_text())
    seed = int(config["seed"])

    development = pd.read_parquet(args.features, filters=[("split", "in", ["train", "val"])]).reset_index(drop=True)
    columns = select_feature_columns(development, config["feature_family"])
    folds = patient_folds(development, int(config["outer_folds"]), seed)
    search = config["families"]["lightgbm"]["search"]
    trials = args.trials or int(config["families"]["lightgbm"]["trials"])
    rng = np.random.default_rng(seed)

    history, best = [], None
    for trial_id in range(trials):
        params = _sample_params(search, rng)
        started = time.perf_counter()
        fold_results, _ = evaluate_candidate(
            development, folds, family="lightgbm", params=params, columns=columns, config=config
        )
        summary = _summary(fold_results)
        record = {"trial_id": trial_id, "params": params, "metrics": summary,
                  "elapsed_seconds": time.perf_counter() - started}
        history.append(record)
        if best is None or _trial_key(summary) > _trial_key(best["metrics"]):
            best = record
        print(f"fallback trial {trial_id:02d}: utility={summary['mean_normalized_utility']:.4f} "
              f"AUPRC={summary['mean_auprc']:.4f} ({record['elapsed_seconds']:.1f}s)")

    refit = config["refit"]
    train = development[development["split"] == "train"]
    validation = development[development["split"] == "val"]
    es_ids = _early_stopping_ids(train, float(refit["early_stopping_fraction"]), seed)
    is_es = train["patient_id"].astype(str).isin(es_ids).to_numpy()
    train_eligible = (train["hours_observed"] >= MIN_HOURS_BEFORE_PRED).to_numpy()
    model = _fit_model("lightgbm", best["params"], train[~is_es & train_eligible],
                       train[is_es & train_eligible], columns, seed)
    validation_eligible = (validation["hours_observed"] >= MIN_HOURS_BEFORE_PRED).to_numpy()
    raw_validation = model.predict_proba(validation[columns])[:, 1]
    calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(
        raw_validation[validation_eligible], validation["SepsisLabel"].to_numpy()[validation_eligible]
    )
    fallback = CalibratedEnsemble([model], columns, calibrator)
    probability = fallback.calibrate(raw_validation)
    thresholds = validation_thresholds(
        validation, probability, validation_eligible,
        min_specificity=float(refit["high_risk_min_specificity"]),
        watch_patient_sensitivity=float(refit["watch_patient_sensitivity"]),
    )
    version = f"lowres-fallback-{datetime.now(timezone.utc):%Y%m%d%H%M}"
    args.out.mkdir(parents=True)
    joblib.dump(
        {
            "model": fallback,
            "uncertainty_model": fallback,
            "feature_columns": columns,
            "thresholds": {"watch": thresholds["watch"], "high_risk": thresholds["high_risk"]},
            "model_version": version,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "params": best["params"],
            "family": "lightgbm",
            "feature_family": config["feature_family"],
            "ensemble": False,
            "frozen": False,
            "intended_use": "low-resource fallback when routine labs are unavailable",
        },
        args.out / "model.joblib",
    )
    result = {
        "run_id": args.out.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset": "PhysioNet Challenge 2019 Dataset A train+validation only",
        "dataset_b_accessed": False,
        "internal_test_accessed": False,
        "feature_file_sha256": _sha256(args.features),
        "config_sha256": _sha256(args.config),
        "feature_family": config["feature_family"],
        "feature_count": len(columns),
        "features": columns,
        "trials": history,
        "selected_trial": best["trial_id"],
        "thresholds": thresholds,
        "validation_report": full_report(validation, probability, validation_eligible, thresholds),
        "model_version": version,
        "note": "Validation metrics are in-sample for calibration/thresholds; the locked test is scored "
                "only in the final multi-candidate comparison.",
    }
    (args.out / "result.json").write_text(json.dumps(result, indent=2, default=float) + "\n")
    report = result["validation_report"]
    print(json.dumps({
        "output": str(args.out),
        "features": len(columns),
        "selected_trial": best["trial_id"],
        "cv": {k: best["metrics"][k] for k in ("mean_auroc", "mean_auprc", "mean_normalized_utility")},
        "validation_high_risk": {k: report["high_risk"][k] for k in (
            "normalized_utility", "sensitivity", "specificity", "false_alerts_per_100_patient_hours")},
    }, indent=2, default=float))


if __name__ == "__main__":
    main()
