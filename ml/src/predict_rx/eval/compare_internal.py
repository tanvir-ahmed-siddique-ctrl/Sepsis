"""Locked Dataset A internal-test comparison of frozen Run 4 vs a challenger.

The selected challenger configuration is refit exactly like Run 4:
fit on Dataset A train patients (10% of them held back for early stopping),
isotonic calibration and operating thresholds on Dataset A validation patients,
then one score on the locked Dataset A internal test. Dataset B is never read.

The output directory contains a ``model.joblib`` bundle that can be frozen
with ``predict_rx.train.freeze`` and later scored once on Dataset B.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.isotonic import IsotonicRegression

from predict_rx.eval.bootstrap import patient_paired_bootstrap
from predict_rx.eval.metrics import (
    UtilityTable,
    best_utility_threshold,
    full_report,
    patient_sensitivity_threshold,
)
from predict_rx.features.schema import MIN_HOURS_BEFORE_PRED
from predict_rx.governance.integrity import sha256_file
from predict_rx.models import CalibratedEnsemble
from predict_rx.train.challenger import _fit_model
from predict_rx.train.run import validate_training_output

META_COLUMNS = ["patient_id", "split", "SepsisLabel", "target", "hours_observed"]


def _eligible(frame: pd.DataFrame) -> np.ndarray:
    return (frame["hours_observed"] >= MIN_HOURS_BEFORE_PRED).to_numpy()


def _early_stopping_ids(train: pd.DataFrame, fraction: float, seed: int) -> set[str]:
    ids = np.array(sorted(train["patient_id"].astype(str).unique()))
    rng = np.random.default_rng(seed)
    return set(rng.choice(ids, size=max(1, int(fraction * len(ids))), replace=False))


def validation_thresholds(
    validation: pd.DataFrame,
    probability: np.ndarray,
    eligible: np.ndarray,
    *,
    min_specificity: float,
    watch_patient_sensitivity: float,
) -> dict[str, float]:
    """Same preregistered rules used for Run 4 and the Dataset B baselines."""
    table = UtilityTable.from_frame(validation)
    labels = validation["SepsisLabel"].to_numpy()
    utility_optimal, _ = best_utility_threshold(table, probability, eligible)
    high_risk, _ = best_utility_threshold(table, probability, eligible, labels, min_specificity)
    watch = min(
        utility_optimal,
        patient_sensitivity_threshold(validation, probability, eligible, watch_patient_sensitivity),
        high_risk,
    )
    return {
        "watch": float(max(watch, 0.0)),
        "high_risk": float(high_risk),
        "utility_optimal": float(utility_optimal),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=Path("data/processed/features_setA.parquet"))
    parser.add_argument("--challenger", type=Path, required=True)
    parser.add_argument("--anchor", type=Path, default=Path("artifacts/models/run4_frozen"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--early-stopping-fraction", type=float, default=0.1)
    parser.add_argument("--high-risk-min-specificity", type=float, default=0.95)
    parser.add_argument("--watch-patient-sensitivity", type=float, default=0.85)
    parser.add_argument("--bootstrap", type=int, default=500)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"Refusing to overwrite locked comparison: {args.out}")
    validate_training_output(args.out, Path("."))

    result_path = args.challenger / "result.json"
    result = json.loads(result_path.read_text())
    if result.get("dataset_b_accessed"):
        raise SystemExit("Challenger bundle already accessed Dataset B; aborting.")
    if result.get("internal_test_accessed"):
        raise SystemExit("Internal test already consumed for this challenger.")

    anchor = joblib.load(args.anchor / "model.joblib")
    best = result["best"]
    columns = list(best["features"])
    needed = list(dict.fromkeys(META_COLUMNS + columns + list(anchor["feature_columns"])))
    available = set(pq.ParquetFile(args.features).schema_arrow.names)
    frame = pd.read_parquet(args.features, columns=[c for c in needed if c in available])
    if "holdout" in set(frame["split"].astype(str)):
        raise SystemExit("Refusing a feature file that contains Dataset B/holdout rows.")
    train = frame[frame["split"] == "train"]
    validation = frame[frame["split"] == "val"]
    test = frame[frame["split"] == "test"]
    if train.empty or validation.empty or test.empty:
        raise SystemExit("Dataset A train, val, and locked test rows are all required.")
    seed = int(result["seed"])

    es_ids = _early_stopping_ids(train, args.early_stopping_fraction, seed)
    is_es = train["patient_id"].astype(str).isin(es_ids).to_numpy()
    train_eligible = _eligible(train)
    model = _fit_model(
        best["family"],
        best["params"],
        train[~is_es & train_eligible],
        train[is_es & train_eligible],
        columns,
        seed,
    )

    validation_eligible = _eligible(validation)
    raw_validation = model.predict_proba(validation[columns])[:, 1]
    calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(
        raw_validation[validation_eligible],
        validation["SepsisLabel"].to_numpy()[validation_eligible],
    )
    challenger = CalibratedEnsemble([model], columns, calibrator)
    challenger_validation = challenger.calibrate(raw_validation)
    thresholds = validation_thresholds(
        validation,
        challenger_validation,
        validation_eligible,
        min_specificity=args.high_risk_min_specificity,
        watch_patient_sensitivity=args.watch_patient_sensitivity,
    )

    eligible = _eligible(test)
    challenger_prob = challenger.predict_proba(test)[:, 1]
    anchor_prob = anchor["model"].predict_proba(test)[:, 1]
    anchor_thresholds = {
        "watch": float(anchor["thresholds"]["watch"]),
        "high_risk": float(anchor["thresholds"]["high_risk"]),
    }
    table = UtilityTable.from_frame(test)
    bootstrap = (
        patient_paired_bootstrap(
            test,
            {"challenger": challenger_prob, "run4": anchor_prob},
            eligible,
            {"challenger": thresholds["high_risk"], "run4": anchor_thresholds["high_risk"]},
            anchor="challenger",
            replicates=args.bootstrap,
            seed=seed,
        )
        if args.bootstrap > 0
        else {"status": "skipped", "replicates": 0}
    )
    version = f"challenger-{result.get('run_id', args.challenger.name)}-{datetime.now(timezone.utc):%Y%m%d%H%M}"
    comparison = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset": "PhysioNet Challenge 2019 Dataset A internal test",
        "dataset_b_accessed": False,
        "internal_test_accessed": True,
        "features_sha256": sha256_file(args.features),
        "anchor_version": anchor["model_version"],
        "challenger_version": version,
        "challenger_run_id": result.get("run_id"),
        "challenger_family": best["family"],
        "challenger_feature_family": best.get("feature_family"),
        "selection_rule": result.get("selection_rule"),
        "refit_protocol": (
            "train patients fit (10% held back for early stopping); isotonic calibration "
            "and thresholds on validation patients; one locked internal-test score"
        ),
        "challenger_thresholds": thresholds,
        "anchor_thresholds": anchor_thresholds,
        "validation": {
            "challenger": full_report(validation, challenger_validation, validation_eligible, thresholds),
        },
        "anchor": full_report(test, anchor_prob, eligible, anchor_thresholds, table),
        "challenger": full_report(test, challenger_prob, eligible, thresholds, table),
        "paired_bootstrap_challenger_minus_run4": bootstrap,
        "note": (
            "Promotion still requires a later one-time Dataset B comparison. "
            "This locked A-test result is not external evidence."
        ),
    }
    args.out.mkdir(parents=True)
    joblib.dump(
        {
            "model": challenger,
            "uncertainty_model": challenger,
            "feature_columns": columns,
            "thresholds": {"watch": thresholds["watch"], "high_risk": thresholds["high_risk"]},
            "model_version": version,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "params": best["params"],
            "family": best["family"],
            "ensemble": False,
            "frozen": False,
        },
        args.out / "model.joblib",
    )
    (args.out / "compare_internal.json").write_text(json.dumps(comparison, indent=2, default=float) + "\n")
    result["internal_test_accessed"] = True
    result_path.write_text(json.dumps(result, indent=2) + "\n")
    summary = {
        name: {
            "auroc": comparison[name]["ranking"]["auroc"],
            "auprc": comparison[name]["ranking"]["auprc"],
            "high_risk_utility": comparison[name]["high_risk"]["normalized_utility"],
        }
        for name in ("anchor", "challenger")
    }
    print(json.dumps({"output": str(args.out), "dataset_b_accessed": False, "test": summary}, indent=2))


if __name__ == "__main__":
    main()
