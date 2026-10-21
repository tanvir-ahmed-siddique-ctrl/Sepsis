"""Preregistered Dataset B comparison for rule, logistic, and frozen Run 4.

All fitting, calibration, and threshold selection happen on Dataset A. Dataset
B is loaded only after baseline artifacts and operating points are frozen.
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import joblib
import matplotlib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import yaml
from sklearn.impute import SimpleImputer
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from predict_rx.eval.bootstrap import patient_paired_bootstrap
from predict_rx.eval.metrics import (
    UtilityTable,
    alert_events,
    best_utility_threshold,
    calibration_diagnostics,
    full_report,
    patient_sensitivity_threshold,
)
from predict_rx.features.schema import MIN_HOURS_BEFORE_PRED
from predict_rx.governance.access import EvaluationAccessLedger, resolve_authorization
from predict_rx.governance.integrity import sha256_file
from predict_rx.train.run import clinical_rule_score, fit_isotonic

MODEL_NAMES = ("clinical_rule", "logistic", "lightgbm")
PARITY_TOLERANCE = 1e-5


def _read_features(path: Path, feature_columns: list[str]) -> pd.DataFrame:
    available = set(pq.ParquetFile(path).schema_arrow.names)
    required_meta = ["patient_id", "split", "SepsisLabel", "target", "hours_observed"]
    columns = list(dict.fromkeys(required_meta + feature_columns))
    missing = [column for column in columns if column not in available]
    if missing:
        raise ValueError(f"{path} is missing {len(missing)} required columns; first: {missing[:10]}")
    return pd.read_parquet(path, columns=columns)


def _threshold_matching_specificity(
    probability: np.ndarray,
    labels: np.ndarray,
    eligible: np.ndarray,
    target_specificity: float,
) -> float:
    negatives = probability[eligible & (labels == 0)]
    return float(np.quantile(negatives, target_specificity, method="higher"))


def _threshold_matching_alert_burden(
    frame: pd.DataFrame,
    probability: np.ndarray,
    eligible: np.ndarray,
    target_alerts_per_patient_day: float,
) -> float:
    candidates = np.unique(np.quantile(probability[eligible], np.linspace(0.5, 0.9999, 500)))
    best_threshold = float(candidates[-1])
    best_difference = float("inf")
    for threshold in candidates:
        burden = alert_events(frame, (probability >= threshold) & eligible)["alerts_per_patient_day"]
        difference = abs(burden - target_alerts_per_patient_day)
        if difference < best_difference:
            best_threshold = float(threshold)
            best_difference = difference
    return best_threshold


def _validation_operating_points(
    frame: pd.DataFrame,
    probability: np.ndarray,
    eligible: np.ndarray,
    *,
    min_specificity: float,
    watch_patient_sensitivity: float,
    anchor_specificity: float,
    anchor_alert_burden: float,
) -> dict[str, float]:
    labels = frame["SepsisLabel"].to_numpy(dtype=int)
    table = UtilityTable.from_frame(frame)
    utility_optimal, _ = best_utility_threshold(table, probability, eligible)
    high_risk, _ = best_utility_threshold(
        table,
        probability,
        eligible,
        labels,
        min_specificity,
    )
    watch = min(
        utility_optimal,
        patient_sensitivity_threshold(frame, probability, eligible, watch_patient_sensitivity),
        high_risk,
    )
    return {
        "watch": float(max(watch, 0.0)),
        "high_risk": float(high_risk),
        "utility_optimal": float(utility_optimal),
        "matched_anchor_specificity": _threshold_matching_specificity(
            probability,
            labels,
            eligible,
            anchor_specificity,
        ),
        "matched_anchor_alert_burden": _threshold_matching_alert_burden(
            frame,
            probability,
            eligible,
            anchor_alert_burden,
        ),
    }


def _reliability_plot(
    diagnostics: dict[str, dict[str, Any]],
    destination: Path,
) -> None:
    fig, axis = plt.subplots(figsize=(6.5, 5.5))
    axis.plot([0, 1], [0, 1], linestyle="--", color="black", linewidth=1, label="Perfect calibration")
    for name, values in diagnostics.items():
        reliability = values["reliability"]
        axis.plot(
            [row["mean_predicted"] for row in reliability],
            [row["observed_rate"] for row in reliability],
            marker="o",
            linewidth=1.5,
            label=name.replace("_", " ").title(),
        )
    axis.set_xlabel("Mean predicted probability")
    axis.set_ylabel("Observed positive-hour rate")
    axis.set_title("Dataset B reliability — 10 equal-mass bins")
    axis.legend()
    axis.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(destination, dpi=180)
    plt.close(fig)


def _anchor_parity_check(report: dict[str, Any], historical_path: Path) -> dict[str, Any]:
    historical = json.loads(historical_path.read_text(encoding="utf-8"))
    checks = {
        "rows": (report["ranking"]["rows"], historical["ranking"]["rows"]),
        "patients": (report["patients"], historical["patients"]),
        "auroc": (report["ranking"]["auroc"], historical["ranking"]["auroc"]),
        "auprc": (report["ranking"]["auprc"], historical["ranking"]["auprc"]),
        "brier": (report["ranking"]["brier"], historical["ranking"]["brier"]),
        "high_risk_utility": (
            report["high_risk"]["normalized_utility"],
            historical["high_risk"]["normalized_utility"],
        ),
    }
    differences = {
        name: {
            "recomputed": current,
            "historical": expected,
            "absolute_difference": abs(current - expected),
        }
        for name, (current, expected) in checks.items()
    }
    exact = {"rows", "patients"}
    failed = {
        name: values
        for name, values in differences.items()
        if values["absolute_difference"] > (0 if name in exact else PARITY_TOLERANCE)
    }
    if failed:
        raise RuntimeError(f"Frozen Run 4 Dataset B parity check failed: {failed}")
    return {
        "status": "pass",
        "tolerance": PARITY_TOLERANCE,
        "tolerance_rationale": (
            "Rows and patients must match exactly. Continuous metrics allow float32 "
            "feature-rebuild rounding; Dataset A internal-test parity after the 2026-09-30 "
            "rebuild differed by at most 4e-7 with identical utility."
        ),
        "metrics": differences,
    }


def run(args: argparse.Namespace) -> Path:
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    model_path = args.model_dir / "model.joblib"
    frozen_record = json.loads((args.model_dir / "FROZEN.json").read_text(encoding="utf-8"))
    model_hash = sha256_file(model_path)
    if model_hash != frozen_record["model_sha256"]:
        raise RuntimeError("Frozen model hash does not match FROZEN.json.")
    bundle = joblib.load(model_path)
    if not bundle.get("frozen"):
        raise RuntimeError("Refusing Dataset B baseline evaluation for a non-frozen anchor.")
    feature_columns = list(bundle["feature_columns"])

    run_id = f"baselines_setb_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    output = args.out or Path("artifacts/experiments") / run_id
    if output.exists():
        raise RuntimeError(f"Refusing to overwrite result bundle: {output}")
    output.mkdir(parents=True)

    frame_a = _read_features(args.set_a, feature_columns)
    if (frame_a["split"] == "holdout").any():
        raise RuntimeError("Dataset A feature file unexpectedly contains holdout rows.")
    train = frame_a[frame_a["split"] == "train"]
    validation = frame_a[frame_a["split"] == "val"]
    eligible_train = (train["hours_observed"] >= MIN_HOURS_BEFORE_PRED).to_numpy()
    eligible_validation = (validation["hours_observed"] >= MIN_HOURS_BEFORE_PRED).to_numpy()
    training_rows = train[eligible_train]

    logistic = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(
                    max_iter=int(config["training"]["logistic_max_iter"]),
                    class_weight=config["training"]["logistic_class_weight"],
                    random_state=int(config["seed"]),
                ),
            ),
        ]
    )
    logistic.fit(training_rows[feature_columns], training_rows["SepsisLabel"].to_numpy(dtype=int))

    raw_validation = {
        "clinical_rule": clinical_rule_score(validation),
        "logistic": logistic.predict_proba(validation[feature_columns])[:, 1],
        "lightgbm": bundle["model"].predict_proba(validation)[:, 1],
    }
    calibration: dict[str, IsotonicRegression | None] = {
        "clinical_rule": fit_isotonic(
            raw_validation["clinical_rule"][eligible_validation],
            validation["SepsisLabel"].to_numpy(dtype=int)[eligible_validation],
        ),
        "logistic": fit_isotonic(
            raw_validation["logistic"][eligible_validation],
            validation["SepsisLabel"].to_numpy(dtype=int)[eligible_validation],
        ),
        "lightgbm": None,
    }
    validation_probability = {
        name: (
            raw_validation[name]
            if calibration[name] is None
            else calibration[name].predict(raw_validation[name])
        )
        for name in MODEL_NAMES
    }
    anchor_validation_report = full_report(
        validation,
        validation_probability["lightgbm"],
        eligible_validation,
        {"high_risk": float(bundle["thresholds"]["high_risk"])},
    )
    anchor_specificity = anchor_validation_report["high_risk"]["specificity"]
    anchor_alert_burden = anchor_validation_report["high_risk"]["alerts_per_patient_day"]
    thresholds = {
        name: (
            {
                "watch": float(bundle["thresholds"]["watch"]),
                "high_risk": float(bundle["thresholds"]["high_risk"]),
                "matched_anchor_specificity": float(bundle["thresholds"]["high_risk"]),
                "matched_anchor_alert_burden": float(bundle["thresholds"]["high_risk"]),
            }
            if name == "lightgbm"
            else _validation_operating_points(
                validation,
                validation_probability[name],
                eligible_validation,
                min_specificity=float(config["thresholds"]["high_risk_min_specificity"]),
                watch_patient_sensitivity=float(config["thresholds"]["watch_patient_sensitivity"]),
                anchor_specificity=float(anchor_specificity),
                anchor_alert_burden=float(anchor_alert_burden),
            )
        )
        for name in MODEL_NAMES
    }
    validation_reports = {
        name: full_report(
            validation,
            validation_probability[name],
            eligible_validation,
            thresholds[name],
        )
        for name in MODEL_NAMES
    }
    baseline_artifact = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset_a_sha256": sha256_file(args.set_a),
        "anchor_model_version": bundle["model_version"],
        "anchor_model_sha256": model_hash,
        "feature_columns": feature_columns,
        "clinical_rule": "Fixed five-component SIRS-style score; no fitted training parameters.",
        "logistic_pipeline": logistic,
        "calibrators": calibration,
        "thresholds": thresholds,
        "validation_reports": validation_reports,
    }
    baseline_path = output / "baseline_models.joblib"
    joblib.dump(baseline_artifact, baseline_path)
    (output / "preregistered_release_rule.json").write_text(
        json.dumps(config["release_rule"], indent=2) + "\n",
        encoding="utf-8",
    )
    del frame_a, train, training_rows, validation, raw_validation, validation_probability
    gc.collect()

    command = " ".join([sys.executable, "-m", "predict_rx.eval.baselines_setb", *sys.argv[1:]])
    confirmation, reason = resolve_authorization(args.authorize_dataset_b, args.access_reason)
    access_entry = EvaluationAccessLedger(args.ledger).record(
        model_version=bundle["model_version"],
        model_sha256=model_hash,
        purpose="baseline_comparison",
        reason=reason,
        authorized_by=args.authorized_by,
        command=command,
        confirmation=confirmation,
        allow_repeat=args.allow_repeat,
    )

    frame_b = _read_features(args.set_b, feature_columns)
    if set(frame_b["split"].unique()) != {"holdout"}:
        raise RuntimeError("Dataset B must contain only split='holdout'.")
    eligible_b = (frame_b["hours_observed"] >= MIN_HOURS_BEFORE_PRED).to_numpy()
    expected_rows = int(config["eligibility"]["expected_dataset_b_eligible_rows"])
    expected_patients = int(config["eligibility"]["expected_dataset_b_patients"])
    if int(eligible_b.sum()) != expected_rows or frame_b["patient_id"].nunique() != expected_patients:
        raise RuntimeError(
            f"Dataset B eligibility mismatch: expected {expected_rows:,} rows and "
            f"{expected_patients:,} patients; "
            f"got {int(eligible_b.sum()):,} rows and {frame_b['patient_id'].nunique():,} patients."
        )
    raw_b = {
        "clinical_rule": clinical_rule_score(frame_b),
        "logistic": logistic.predict_proba(frame_b[feature_columns])[:, 1],
        "lightgbm": bundle["model"].predict_proba(frame_b)[:, 1],
    }
    probability_b = {
        name: raw_b[name] if calibration[name] is None else calibration[name].predict(raw_b[name])
        for name in MODEL_NAMES
    }
    reports = {
        name: full_report(frame_b, probability_b[name], eligible_b, thresholds[name])
        for name in MODEL_NAMES
    }
    labels_b = frame_b["SepsisLabel"].to_numpy(dtype=int)[eligible_b]
    calibration_report = {
        name: calibration_diagnostics(labels_b, probability_b[name][eligible_b])
        for name in MODEL_NAMES
    }
    parity = _anchor_parity_check(reports["lightgbm"], args.model_dir / "eval_holdout.json")
    bootstrap_replicates = (
        args.bootstrap if args.bootstrap is not None else int(config["bootstrap_replicates"])
    )
    bootstrap = (
        patient_paired_bootstrap(
            frame_b,
            probability_b,
            eligible_b,
            {name: thresholds[name]["high_risk"] for name in MODEL_NAMES},
            anchor="lightgbm",
            replicates=bootstrap_replicates,
            seed=int(config["seed"]),
            confidence=float(config["confidence_level"]),
        )
        if bootstrap_replicates > 0
        else {"status": "skipped", "replicates": 0}
    )
    _reliability_plot(calibration_report, output / "reliability_dataset_b.png")

    anchor = reports["lightgbm"]
    primary_pass = {
        comparator: {
            "auprc": anchor["ranking"]["auprc"] > reports[comparator]["ranking"]["auprc"],
            "high_risk_utility": (
                anchor["high_risk"]["normalized_utility"]
                > reports[comparator]["high_risk"]["normalized_utility"]
            ),
        }
        for comparator in ("clinical_rule", "logistic")
    }
    result = {
        "schema_version": 1,
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset_b_claim": (
            "Site-held-out retrospective validation on a geographically distinct public hospital cohort."
        ),
        "dataset_b_sha256": sha256_file(args.set_b),
        "dataset_a_sha256": baseline_artifact["dataset_a_sha256"],
        "anchor_model_version": bundle["model_version"],
        "anchor_model_sha256": model_hash,
        "config_path": args.config.as_posix(),
        "config_sha256": sha256_file(args.config),
        "baseline_artifact_sha256": sha256_file(baseline_path),
        "evaluation_access": access_entry,
        "validation_threshold_selection": validation_reports,
        "dataset_b_reports": reports,
        "calibration": calibration_report,
        "bootstrap": bootstrap,
        "frozen_anchor_parity": parity,
        "release_rule": config["release_rule"],
        "release_rule_primary_results": primary_pass,
        "decision_curve": {
            "status": "deliberately_not_reported",
            "reason": config["release_rule"]["decision_curve"],
        },
    }
    (output / "report.json").write_text(json.dumps(result, indent=2, default=float) + "\n", encoding="utf-8")
    (output / ".immutable").write_text(
        "This bundle records a protected Dataset B comparison. Do not overwrite or tune from it.\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "run_id": run_id,
                "output": str(output),
                "release_rule_primary_results": primary_pass,
            },
            indent=2,
        )
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the preregistered Dataset B baseline comparison.")
    parser.add_argument("--set-a", type=Path, default=Path("data/processed/features_setA.parquet"))
    parser.add_argument("--set-b", type=Path, default=Path("data/processed/features_setB.parquet"))
    parser.add_argument("--model-dir", type=Path, default=Path("artifacts/models/run4_frozen"))
    parser.add_argument("--config", type=Path, default=Path("configs/baselines_setb.yaml"))
    parser.add_argument("--out", type=Path)
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path("artifacts/governance/evaluation_access.json"),
    )
    parser.add_argument("--authorized-by", required=True)
    parser.add_argument("--authorize-dataset-b", required=True)
    parser.add_argument(
        "--access-reason",
        default=(
            "Preregistered Phase 1 comparison of A-trained clinical-rule and logistic "
            "baselines against frozen Run 4 on identical Dataset B rows."
        ),
    )
    parser.add_argument("--allow-repeat", action="store_true")
    parser.add_argument("--bootstrap", type=int)
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
