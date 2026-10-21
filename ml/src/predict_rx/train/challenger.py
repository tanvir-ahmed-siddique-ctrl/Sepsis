"""A-only, patient-grouped optimized tabular challenger development.

This command never reads Dataset B and keeps the internal Dataset A test split
locked. Hyperparameter selection uses grouped development folds only.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import sqlite3
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import yaml
from sklearn.cluster import KMeans
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold

from predict_rx.eval.metrics import UtilityTable, best_utility_threshold
from predict_rx.features.build import NON_FEATURE_COLS
from predict_rx.features.schema import DEMO_COLS, LAB_COLS, MIN_HOURS_BEFORE_PRED, VITAL_COLS


@dataclass(frozen=True)
class FoldResult:
    fold: int
    auroc: float | None
    auprc: float | None
    normalized_utility: float
    threshold: float
    worst_pseudo_site_auprc: float | None
    fit_patients: int
    calibration_patients: int
    validation_patients: int


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_development_file(path: Path) -> None:
    """Fail before model code if input is missing, corrupt, or contains holdout rows."""
    if not path.exists():
        raise FileNotFoundError(path)
    try:
        parquet = pq.ParquetFile(path)
    except Exception as error:
        raise ValueError(f"Invalid Parquet feature file: {path}: {error}") from error
    if "split" not in parquet.schema_arrow.names:
        raise ValueError("Feature file must contain a patient-level split column.")
    split_values = set(pd.read_parquet(path, columns=["split"])["split"].astype(str).unique())
    forbidden = split_values - {"train", "val", "test"}
    if forbidden or "holdout" in split_values:
        raise ValueError(f"Refusing non-Dataset-A development splits: {sorted(forbidden)}")


def select_feature_columns(frame: pd.DataFrame, family: str) -> list[str]:
    numeric = [
        column
        for column in frame.columns
        if column not in NON_FEATURE_COLS and pd.api.types.is_numeric_dtype(frame[column])
    ]
    physiology = tuple(VITAL_COLS + LAB_COLS)
    current = {column for column in numeric if column in physiology}
    temporal = {
        column
        for column in numeric
        if column.startswith(physiology)
        and not column.endswith(("_missing", "_hours_since"))
        and "_count_" not in column
    }
    care = {
        column
        for column in numeric
        if column.endswith(("_missing", "_hours_since"))
        or "_count_" in column
        or column in {"ICULOS", "HospAdmTime", "Unit1", "Unit2", "labs_measured_24h"}
    }
    clinical = {
        column
        for column in numeric
        if column.startswith(("sofa_", "qsofa_", "sirs_", "shock_index", "sf_ratio", "pulse_pressure"))
    }
    vital_names = tuple(VITAL_COLS)
    vitals_current = {column for column in numeric if column in vital_names}
    vitals_temporal = {
        column
        for column in numeric
        if column.startswith(vital_names)
        and not column.endswith(("_missing", "_hours_since"))
        and "_count_" not in column
    }
    vitals_process = {
        column
        for column in numeric
        if column.startswith(vital_names) and (column.endswith(("_missing", "_hours_since")) or "_count_" in column)
    }
    bedside_context = {column for column in numeric if column in {"Age", "Gender", "ICULOS", "HospAdmTime"}}
    mapping = {
        "low_resource_vitals": vitals_current | vitals_temporal | vitals_process | bedside_context,
        "physiology_current": current,
        "physiology_temporal": current | temporal,
        "vitals_only": vitals_current | vitals_temporal,
        "care_process_only": care,
        "clinical_scores_only": clinical,
        "physiology_plus_care_process": current | temporal | care,
        "all": set(numeric),
    }
    if family not in mapping:
        raise ValueError(f"Unknown feature family: {family}")
    selected = sorted(mapping[family])
    if not selected:
        raise ValueError(f"Feature family {family} selected no columns.")
    return selected


def patient_time_weights(
    frame: pd.DataFrame,
    *,
    desired_window_hours: int = 12,
    desired_window_multiplier: float = 2.0,
    positive_row_multiplier: float = 1.5,
) -> np.ndarray:
    """Balance patient contribution, then emphasize the prespecified onset window."""
    counts = frame.groupby("patient_id")["patient_id"].transform("size").to_numpy(dtype=float)
    weights = 1.0 / counts
    positions = frame.groupby("patient_id", sort=False).cumcount().to_numpy()
    first_positive = (
        pd.Series(
            np.where(frame["SepsisLabel"].to_numpy() == 1, positions, np.nan),
            index=frame.index,
        )
        .groupby(frame["patient_id"])
        .min()
    )
    onset = frame["patient_id"].map(first_positive - (-6)).to_numpy(dtype=float)
    lead = onset - positions
    desired = np.isfinite(lead) & (lead >= 0) & (lead <= desired_window_hours)
    positive = frame["SepsisLabel"].to_numpy(dtype=int) == 1
    weights *= np.where(desired, desired_window_multiplier, 1.0)
    weights *= np.where(positive, positive_row_multiplier, 1.0)
    return weights / weights.mean()


def patient_folds(frame: pd.DataFrame, n_splits: int, seed: int) -> dict[str, int]:
    patient_target = frame.groupby("patient_id", sort=False)["SepsisLabel"].max()
    ids = patient_target.index.to_numpy()
    folds: dict[str, int] = {}
    splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    for fold, (_, valid_index) in enumerate(splitter.split(ids, patient_target.to_numpy())):
        folds.update({str(ids[index]): fold for index in valid_index})
    return folds


def _split_calibration_ids(train: pd.DataFrame, fraction: float, seed: int) -> set[str]:
    patient_target = train.groupby("patient_id", sort=False)["SepsisLabel"].max()
    ids = patient_target.index.to_numpy()
    if len(ids) < 4:
        raise ValueError("At least four development patients are required.")
    splitter = StratifiedKFold(
        n_splits=max(2, min(int(round(1 / fraction)), int(patient_target.value_counts().min()))),
        shuffle=True,
        random_state=seed,
    )
    _, calibration_index = next(splitter.split(ids, patient_target.to_numpy()))
    return {str(ids[index]) for index in calibration_index}


_LGBM_HAS_EVAL_X = "eval_X" in inspect.signature(lgb.LGBMClassifier.fit).parameters


def _sample_params(search: dict[str, list[Any]], rng: np.random.Generator) -> dict[str, Any]:
    return {name: values[int(rng.integers(0, len(values)))] for name, values in search.items()}


def _fit_model(
    family: str,
    params: dict[str, Any],
    fit: pd.DataFrame,
    calibration: pd.DataFrame,
    columns: list[str],
    seed: int,
) -> Any:
    fit_weights = patient_time_weights(fit)
    calibration_weights = patient_time_weights(calibration)
    if family == "lightgbm":
        model = lgb.LGBMClassifier(
            objective="binary",
            random_state=seed,
            n_jobs=-1,
            verbosity=-1,
            **params,
        )
        if _LGBM_HAS_EVAL_X:
            eval_kwargs = {"eval_X": (calibration[columns],), "eval_y": (calibration["SepsisLabel"],)}
        else:
            eval_kwargs = {"eval_set": [(calibration[columns], calibration["SepsisLabel"])]}
        model.fit(
            fit[columns],
            fit["SepsisLabel"],
            sample_weight=fit_weights,
            eval_sample_weight=[calibration_weights],
            eval_metric="average_precision",
            **eval_kwargs,
            callbacks=[lgb.early_stopping(100, verbose=False)],
        )
        return model
    if family == "catboost":
        try:
            from catboost import CatBoostClassifier
        except ImportError as error:
            raise RuntimeError("CatBoost trials require `pip install catboost`.") from error
        model = CatBoostClassifier(
            loss_function="Logloss",
            eval_metric="PRAUC",
            random_seed=seed,
            verbose=False,
            allow_writing_files=False,
            **params,
        )
        model.fit(
            fit[columns],
            fit["SepsisLabel"],
            sample_weight=fit_weights,
            eval_set=(calibration[columns], calibration["SepsisLabel"]),
            early_stopping_rounds=100,
        )
        return model
    raise ValueError(f"Unknown model family: {family}")


def _pseudo_site_labels(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    *,
    clusters: int,
    seed: int,
) -> np.ndarray:
    missing_columns = [column for column in train if column.endswith("_missing")]
    if not missing_columns:
        raw = [column for column in VITAL_COLS + LAB_COLS if column in train]
        train_signature = train.assign(**{f"m:{c}": train[c].isna() for c in raw})
        validation_signature = validation.assign(**{f"m:{c}": validation[c].isna() for c in raw})
        missing_columns = [f"m:{column}" for column in raw]
    else:
        train_signature, validation_signature = train, validation
    train_patient = train_signature.groupby("patient_id")[missing_columns].mean()
    validation_patient = validation_signature.groupby("patient_id")[missing_columns].mean()
    clusters = min(clusters, len(train_patient))
    model = KMeans(n_clusters=clusters, random_state=seed, n_init=10).fit(train_patient)
    patient_labels = pd.Series(model.predict(validation_patient), index=validation_patient.index)
    return validation["patient_id"].map(patient_labels).to_numpy()


def _safe_ranking(y: np.ndarray, probability: np.ndarray) -> tuple[float | None, float | None]:
    if len(np.unique(y)) < 2:
        return None, None
    return float(roc_auc_score(y, probability)), float(average_precision_score(y, probability))


def evaluate_candidate(
    frame: pd.DataFrame,
    folds: dict[str, int],
    *,
    family: str,
    params: dict[str, Any],
    columns: list[str],
    config: dict[str, Any],
) -> tuple[list[FoldResult], pd.DataFrame]:
    predictions: list[pd.DataFrame] = []
    reports: list[FoldResult] = []
    patient_ids = frame["patient_id"].astype(str)
    fold_series = patient_ids.map(folds).to_numpy()
    meta = ["patient_id", "SepsisLabel", "hours_observed"] + [c for c in ("ICULOS",) if c in frame]
    missing_columns = [column for column in frame if column.endswith("_missing")]
    needed = list(dict.fromkeys(meta + columns + missing_columns))
    eligible_all = (frame["hours_observed"] >= MIN_HOURS_BEFORE_PRED).to_numpy()
    for fold in sorted(set(folds.values())):
        in_train = fold_series != fold
        calibration_ids = _split_calibration_ids(
            frame.loc[in_train, ["patient_id", "SepsisLabel"]],
            float(config["calibration_fraction"]),
            int(config["seed"]) + fold,
        )
        is_calibration = patient_ids.isin(calibration_ids).to_numpy()
        fit = frame.loc[in_train & ~is_calibration & eligible_all, needed]
        calibration_all = frame.loc[in_train & is_calibration, needed]
        calibration = calibration_all[calibration_all["hours_observed"] >= MIN_HOURS_BEFORE_PRED]
        validation = frame.loc[~in_train, needed]
        model = _fit_model(family, params, fit, calibration, columns, int(config["seed"]) + fold)

        raw_calibration = model.predict_proba(calibration_all[columns])[:, 1]
        calibration_eligible = (
            calibration_all["hours_observed"].to_numpy() >= MIN_HOURS_BEFORE_PRED
        )
        calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(
            raw_calibration[calibration_eligible],
            calibration_all["SepsisLabel"].to_numpy()[calibration_eligible],
        )
        p_calibration = calibrator.predict(raw_calibration)
        calibration_table = UtilityTable.from_frame(calibration_all)
        threshold, _ = best_utility_threshold(
            calibration_table,
            p_calibration,
            calibration_eligible,
        )

        probability = calibrator.predict(model.predict_proba(validation[columns])[:, 1])
        eligible = validation["hours_observed"].to_numpy() >= MIN_HOURS_BEFORE_PRED
        y = validation["SepsisLabel"].to_numpy()[eligible]
        auroc, auprc = _safe_ranking(y, probability[eligible])
        utility = UtilityTable.from_frame(validation).normalized((probability >= threshold) & eligible)
        pseudo_site = _pseudo_site_labels(
            pd.concat([fit[meta + missing_columns], calibration_all[meta + missing_columns]]),
            validation,
            clusters=int(config["pseudo_sites"]["clusters"]),
            seed=int(config["seed"]) + fold,
        )
        group_auprc = []
        for group in np.unique(pseudo_site):
            mask = eligible & (pseudo_site == group)
            if mask.sum() >= int(config["pseudo_sites"]["minimum_rows_for_metric"]):
                _, score = _safe_ranking(validation["SepsisLabel"].to_numpy()[mask], probability[mask])
                if score is not None:
                    group_auprc.append(score)
        reports.append(
            FoldResult(
                fold=fold,
                auroc=auroc,
                auprc=auprc,
                normalized_utility=float(utility),
                threshold=float(threshold),
                worst_pseudo_site_auprc=min(group_auprc) if group_auprc else None,
                fit_patients=int(fit["patient_id"].nunique()),
                calibration_patients=int(calibration["patient_id"].nunique()),
                validation_patients=int(validation["patient_id"].nunique()),
            )
        )
        predictions.append(
            validation[["patient_id", "ICULOS", "SepsisLabel"]]
            .assign(fold=fold, probability=probability, eligible=eligible)
        )
    return reports, pd.concat(predictions).sort_index()


def _summary(folds: list[FoldResult]) -> dict[str, Any]:
    def mean(name: str) -> float | None:
        values = [getattr(fold, name) for fold in folds if getattr(fold, name) is not None]
        return float(np.mean(values)) if values else None

    worst = [fold.worst_pseudo_site_auprc for fold in folds if fold.worst_pseudo_site_auprc is not None]
    return {
        "mean_auroc": mean("auroc"),
        "mean_auprc": mean("auprc"),
        "mean_normalized_utility": mean("normalized_utility"),
        "worst_pseudo_site_auprc": min(worst) if worst else None,
        "folds": [asdict(fold) for fold in folds],
    }


def _trial_key(summary: dict[str, Any]) -> tuple[float, float, float]:
    return (
        summary["mean_normalized_utility"] or -np.inf,
        summary["mean_auprc"] or -np.inf,
        summary["worst_pseudo_site_auprc"] or -np.inf,
    )


def _prepare_study(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS trials (
            trial_id INTEGER PRIMARY KEY,
            family TEXT NOT NULL,
            feature_family TEXT NOT NULL,
            params_json TEXT NOT NULL,
            metrics_json TEXT NOT NULL,
            elapsed_seconds REAL NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    return connection


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=Path("data/processed/features_setA.parquet"))
    parser.add_argument("--config", type=Path, default=Path("configs/challenger_tabular.yaml"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Continue an interrupted run with the identical config and feature file.",
    )
    args = parser.parse_args()
    if (args.out / "result.json").exists():
        raise SystemExit(f"Refusing to overwrite completed challenger bundle: {args.out}")
    if args.out.exists() and not args.resume:
        raise SystemExit(f"{args.out} exists. Use --resume to continue an interrupted run.")
    validate_development_file(args.features)
    config = yaml.safe_load(args.config.read_text())
    run_identity = {"config_sha256": _sha256(args.config), "feature_file_sha256": _sha256(args.features)}
    identity_path = args.out / "run_identity.json"
    if args.resume and identity_path.exists():
        recorded = json.loads(identity_path.read_text())
        if recorded != run_identity:
            raise SystemExit(f"Resume refused: config or feature file changed since the run started: {recorded}")
    development = pd.read_parquet(args.features, filters=[("split", "in", ["train", "val"])])
    if development.empty:
        raise SystemExit("No Dataset A train/val development rows found.")
    development = development.reset_index(drop=True)
    folds = patient_folds(development, int(config["outer_folds"]), int(config["seed"]))
    args.out.mkdir(parents=True, exist_ok=True)
    identity_path.write_text(json.dumps(run_identity, indent=2) + "\n")
    connection = _prepare_study(args.out / "study.sqlite3")
    completed = {
        int(row[0]): (row[1], row[2], json.loads(row[3]), json.loads(row[4]))
        for row in connection.execute(
            "SELECT trial_id, family, feature_family, params_json, metrics_json FROM trials"
        )
    }
    rng = np.random.default_rng(int(config["seed"]))
    best: dict[str, Any] | None = None
    trial_id = 0

    plans: list[tuple[str, str, dict[str, Any]]] = []
    for family, family_config in config["families"].items():
        for _ in range(int(family_config["trials"])):
            plans.append((family, "all", _sample_params(family_config["search"], rng)))
    default_lgbm = _sample_params(config["families"]["lightgbm"]["search"], np.random.default_rng(config["seed"]))
    for feature_family in config["feature_ablations"]:
        if feature_family != "all":
            plans.append(("lightgbm", feature_family, default_lgbm))

    for family, feature_family, params in plans:
        if trial_id in completed:
            done_family, done_feature_family, done_params, done_summary = completed[trial_id]
            if (done_family, done_feature_family, done_params) != (family, feature_family, params):
                raise SystemExit(f"Resume refused: trial {trial_id} plan differs from the stored study.")
            if best is None or _trial_key(done_summary) > _trial_key(best["metrics"]):
                best = {
                    "trial_id": trial_id,
                    "family": family,
                    "feature_family": feature_family,
                    "params": params,
                    "features": select_feature_columns(development, feature_family),
                    "metrics": done_summary,
                    "oof": None,
                }
            print(f"trial {trial_id:03d} {family}/{feature_family}: resumed from study")
            trial_id += 1
            continue
        started = time.perf_counter()
        columns = select_feature_columns(development, feature_family)
        fold_results, oof = evaluate_candidate(
            development,
            folds,
            family=family,
            params=params,
            columns=columns,
            config=config,
        )
        summary = _summary(fold_results)
        elapsed = time.perf_counter() - started
        connection.execute(
            "INSERT INTO trials VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                trial_id,
                family,
                feature_family,
                json.dumps(params, sort_keys=True),
                json.dumps(summary),
                elapsed,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        connection.commit()
        candidate = {
            "trial_id": trial_id,
            "family": family,
            "feature_family": feature_family,
            "params": params,
            "features": columns,
            "metrics": summary,
            "oof": oof,
        }
        if best is None or _trial_key(summary) > _trial_key(best["metrics"]):
            best = candidate
            oof.to_parquet(args.out / "best_oof.parquet", index=False)
        print(
            f"trial {trial_id:03d} {family}/{feature_family}: "
            f"utility={summary['mean_normalized_utility']:.4f} "
            f"AUPRC={summary['mean_auprc']:.4f} ({elapsed:.1f}s)"
        )
        trial_id += 1
    connection.close()
    assert best is not None
    del best["oof"]
    result = {
        "schema_version": 1,
        "run_id": args.out.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset": "PhysioNet Challenge 2019 Dataset A train+validation only",
        "dataset_b_accessed": False,
        "internal_test_accessed": False,
        "target": "official Challenge-compatible SepsisLabel",
        "feature_file_sha256": _sha256(args.features),
        "config_sha256": _sha256(args.config),
        "seed": config["seed"],
        "trial_count": trial_id,
        "selection_rule": config["selection"],
        "best": best,
        "status": "development_selection_only; internal test remains locked",
    }
    (args.out / "fold_assignments.json").write_text(json.dumps(folds, indent=2) + "\n")
    (args.out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "best"}, indent=2))


if __name__ == "__main__":
    main()
