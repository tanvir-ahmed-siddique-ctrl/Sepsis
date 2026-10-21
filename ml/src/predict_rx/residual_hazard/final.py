"""Final-fit the selected RESIDUAL-HAZARD-01 candidate without locked data.

Only Dataset A train and validation rows are loaded. The healthy-reference
projector and LightGBM fit on train patients; validation is reserved for
isotonic calibration and fixed raw/EMA operating thresholds.
"""

from __future__ import annotations

import argparse
import hashlib
import json
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
from predict_rx.residual_hazard.features import HealthyResidualProjector
from predict_rx.residual_hazard.models import HealthyResidualModel, fit_lgbm, smooth_ema
from predict_rx.train.challenger import select_feature_columns
from predict_rx.train.run import validate_training_output


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _lf_sha256(path: Path) -> str:
    content = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(content).hexdigest()


def _eligible(frame: pd.DataFrame) -> np.ndarray:
    return frame["hours_observed"].to_numpy() >= MIN_HOURS_BEFORE_PRED


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/residual_hazard_setb.yaml"))
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("artifacts/challengers/RESIDUAL-HAZARD-01/final"),
    )
    args = parser.parse_args()
    validate_training_output(args.out, Path("."))
    config = yaml.safe_load(args.config.read_text())
    source = config["source"]
    final = config["final_fit"]

    cv_path = Path(source["cv_result"])
    development_config = Path(source["development_config"])
    features_path = Path(final["features"])
    if _sha256(cv_path) != source["cv_result_sha256"]:
        raise SystemExit("Selected CV result changed after external preregistration.")
    if _lf_sha256(development_config) != source["development_config_lf_sha256"]:
        raise SystemExit("Development config changed after the selected CV run.")
    if _sha256(features_path) != final["features_sha256"]:
        raise SystemExit("Dataset A feature file changed after external preregistration.")
    cv_result = json.loads(cv_path.read_text())
    if cv_result["feature_stage"]["selected"] != source["selected_features"]:
        raise SystemExit("Preregistered feature candidate does not match the CV selection.")
    if cv_result["selected_risk"] != source["selected_risk"]:
        raise SystemExit("Preregistered risk candidate does not match the CV decision.")
    if cv_result.get("dataset_b_accessed") or cv_result.get("internal_test_accessed"):
        raise SystemExit("Selected development run unexpectedly touched a prohibited split.")

    frame = pd.read_parquet(
        features_path,
        filters=[("split", "in", [final["fit_split"], final["calibration_split"]])],
    )
    observed_splits = set(frame["split"].astype(str))
    prohibited = observed_splits.intersection(map(str, final["prohibited_splits"]))
    if prohibited:
        raise SystemExit(f"Refusing prohibited rows in final fit: {sorted(prohibited)}")
    train = frame[frame["split"] == final["fit_split"]].reset_index(drop=True)
    validation = frame[frame["split"] == final["calibration_split"]].reset_index(drop=True)
    if train.empty or validation.empty:
        raise SystemExit("Final fit requires non-empty Dataset A train and validation splits.")

    seed = int(config["seed"])
    es_ids = _early_stopping_ids(train, float(final["early_stopping_fraction"]), seed)
    is_es = train["patient_id"].astype(str).isin(es_ids).to_numpy()
    train_eligible = _eligible(train)
    fit_mask = ~is_es & train_eligible
    stop_mask = is_es & train_eligible

    projector = HealthyResidualProjector.from_config(final["healthy_residual"]).fit(
        train.loc[fit_mask]
    )
    train_augmented = pd.concat([train, projector.transform(train)], axis=1)
    validation_augmented = pd.concat(
        [validation, projector.transform(validation)], axis=1
    )
    base_columns = select_feature_columns(train, "all")
    residual_columns = list(projector.transform(train.iloc[:1]))
    columns = list(dict.fromkeys(base_columns + residual_columns))
    model = fit_lgbm(
        train_augmented.loc[fit_mask],
        train_augmented.loc[stop_mask],
        columns,
        final["model_params"],
        seed,
    )
    candidate = HealthyResidualModel(model, projector, columns)
    validation_eligible = _eligible(validation)
    raw_validation = candidate.raw_score(validation)
    calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(
        raw_validation[validation_eligible],
        validation["SepsisLabel"].to_numpy()[validation_eligible],
    )
    candidate.calibrator = calibrator
    probability = candidate.predict_proba(validation)[:, 1]

    threshold_args = {
        "min_specificity": float(final["high_risk_min_specificity"]),
        "watch_patient_sensitivity": float(final["watch_patient_sensitivity"]),
    }
    raw_thresholds = validation_thresholds(
        validation, probability, validation_eligible, **threshold_args
    )
    policy = final["alert_policy"]
    if policy["kind"] != "ema":
        raise SystemExit("The preregistered final policy must be EMA.")
    policy_score = smooth_ema(
        probability,
        validation["patient_id"].to_numpy(),
        float(policy["alpha"]),
    )
    policy_thresholds = validation_thresholds(
        validation, policy_score, validation_eligible, **threshold_args
    )

    created_at = datetime.now(timezone.utc).isoformat()
    version = f"residual-healthy-ema-{datetime.now(timezone.utc):%Y%m%d%H%M}"
    bundle = {
        "model": candidate,
        "feature_columns": columns,
        "thresholds": {
            "watch": raw_thresholds["watch"],
            "high_risk": raw_thresholds["high_risk"],
        },
        "alert_policy": {
            "kind": "ema",
            "alpha": float(policy["alpha"]),
            "thresholds": {
                "watch": policy_thresholds["watch"],
                "high_risk": policy_thresholds["high_risk"],
            },
        },
        "model_version": version,
        "trained_at": created_at,
        "params": final["model_params"],
        "selected_features": source["selected_features"],
        "source_cv_sha256": source["cv_result_sha256"],
        "external_config_sha256": _sha256(args.config),
        "frozen": False,
    }
    result = {
        "run_id": f"{config['run_id']}/final",
        "created_at": created_at,
        "dataset": "PhysioNet Challenge 2019 Dataset A train+validation only",
        "dataset_b_accessed": False,
        "internal_test_accessed": False,
        "model_version": version,
        "selected_features": source["selected_features"],
        "alert_policy": bundle["alert_policy"],
        "fit_patients": int(train.loc[fit_mask, "patient_id"].nunique()),
        "early_stopping_patients": int(train.loc[stop_mask, "patient_id"].nunique()),
        "calibration_patients": int(validation["patient_id"].nunique()),
        "best_iteration": int(model.best_iteration_),
        "raw_thresholds": raw_thresholds,
        "policy_thresholds": policy_thresholds,
        "validation_raw": full_report(
            validation, probability, validation_eligible, raw_thresholds
        ),
        "validation_policy": full_report(
            validation, policy_score, validation_eligible, policy_thresholds
        ),
        "note": (
            "Validation metrics are in-sample for isotonic calibration and thresholds. "
            "Dataset A test and Dataset B were not read."
        ),
    }
    args.out.mkdir(parents=True)
    joblib.dump(bundle, args.out / "model.joblib")
    (args.out / "result.json").write_text(
        json.dumps(result, indent=2, default=float) + "\n"
    )
    summary = {
        "output": str(args.out),
        "version": version,
        "best_iteration": result["best_iteration"],
        "validation_raw_auprc": result["validation_raw"]["ranking"]["auprc"],
        "validation_policy_high_risk_utility": result["validation_policy"]["high_risk"][
            "normalized_utility"
        ],
        "dataset_b_accessed": False,
        "internal_test_accessed": False,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
