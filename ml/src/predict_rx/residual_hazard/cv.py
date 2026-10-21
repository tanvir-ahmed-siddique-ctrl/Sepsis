"""RESIDUAL-HAZARD-01: fold-safe additive features, hazards and alert policies.

Dataset A train+validation only. The closed Dataset A test and Dataset B are
never read. Learned feature generators are fitted inside every scored fold;
hazard synthesis uses an additional inner patient-grouped cross-fit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import yaml
from sklearn.isotonic import IsotonicRegression

from predict_rx.eval.metrics import UtilityTable, alert_events, confusion_metrics, patient_detection
from predict_rx.features.build import NON_FEATURE_COLS
from predict_rx.features.schema import MIN_HOURS_BEFORE_PRED
from predict_rx.residual_hazard.features import (
    HealthyResidualProjector,
    OrthoBioProjector,
    sparse_dynamics,
)
from predict_rx.residual_hazard.models import (
    apply_policy,
    calibrate_and_threshold,
    fit_lgbm,
    fit_meta,
    hazard_meta_features,
    select_stateful_policy,
)
from predict_rx.train.challenger import (
    FoldResult,
    _pseudo_site_labels,
    _safe_ranking,
    _split_calibration_ids,
    _summary,
    patient_folds,
    select_feature_columns,
    validate_development_file,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _eligible(frame: pd.DataFrame) -> np.ndarray:
    return frame["hours_observed"].to_numpy() >= MIN_HOURS_BEFORE_PRED


def _outer_masks(
    frame: pd.DataFrame, in_train: np.ndarray, config: dict, fold: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Disjoint fit, risk-calibration and policy-tuning patient masks."""
    calibration_ids = _split_calibration_ids(
        frame.loc[in_train, ["patient_id", "SepsisLabel"]],
        float(config["calibration_fraction"]),
        int(config["seed"]) + fold,
    )
    in_calibration = frame["patient_id"].astype(str).isin(calibration_ids).to_numpy()
    policy_ids = _split_calibration_ids(
        frame.loc[in_calibration, ["patient_id", "SepsisLabel"]],
        float(config["policy_tuning_fraction_of_calibration"]),
        int(config["seed"]) + 100 + fold,
    )
    is_policy = frame["patient_id"].astype(str).isin(policy_ids).to_numpy()
    is_risk_calibration = in_calibration & ~is_policy
    is_fit = in_train & ~in_calibration
    return is_fit, is_risk_calibration, is_policy


def _join_targets(frame: pd.DataFrame, path: Path) -> pd.DataFrame:
    targets = pd.read_parquet(path, filters=[("split", "in", ["train", "val"])]).reset_index(drop=True)
    if len(targets) != len(frame) or not np.array_equal(
        targets["patient_id"].astype(str).to_numpy(), frame["patient_id"].astype(str).to_numpy()
    ):
        raise ValueError("Incident targets are not row-aligned with Dataset A development features.")
    columns = ["incident_at_risk"] + [c for c in targets if c.startswith("incident_onset_within_")]
    return pd.concat([frame, targets[columns]], axis=1)


def _fit_extensions(fit: pd.DataFrame, transform: pd.DataFrame, config: dict) -> dict[str, pd.DataFrame]:
    dynamics = sparse_dynamics(transform, config["dynamics"])
    healthy = HealthyResidualProjector.from_config(config["healthy_residual"]).fit(fit).transform(transform)
    orthobio = OrthoBioProjector.from_config(config["orthobio"]).fit(fit).transform(transform)
    return {"dynamics": dynamics, "healthy": healthy, "orthobio": orthobio}


def _candidate_frame(
    base: pd.DataFrame, extensions: dict[str, pd.DataFrame], candidate: str
) -> tuple[pd.DataFrame, list[str]]:
    include = {
        "reference": [],
        "plus_dynamics": ["dynamics"],
        "plus_healthy_residual": ["healthy"],
        "plus_orthobio": ["orthobio"],
        "safe_stack": ["dynamics", "healthy", "orthobio"],
    }[candidate]
    augmented = pd.concat([base] + [extensions[name] for name in include], axis=1)
    columns = [
        c for c in select_feature_columns(base, "all")
        if not c.startswith("incident_")
    ]
    columns += [c for name in include for c in extensions[name].columns]
    return augmented, list(dict.fromkeys(columns))


def _fold_metrics(
    train_for_sites: pd.DataFrame,
    validation: pd.DataFrame,
    probability: np.ndarray,
    threshold: float,
    config: dict,
    fold: int,
) -> FoldResult:
    eligible = _eligible(validation)
    y = validation["SepsisLabel"].to_numpy()
    auroc, auprc = _safe_ranking(y[eligible], probability[eligible])
    utility = UtilityTable.from_frame(validation).normalized((probability >= threshold) & eligible)
    pseudo = _pseudo_site_labels(
        train_for_sites,
        validation,
        clusters=int(config["pseudo_sites"]["clusters"]),
        seed=int(config["seed"]) + fold,
    )
    group_scores = []
    for group in np.unique(pseudo):
        mask = eligible & (pseudo == group)
        if mask.sum() >= int(config["pseudo_sites"]["minimum_rows_for_metric"]):
            _, score = _safe_ranking(y[mask], probability[mask])
            if score is not None:
                group_scores.append(score)
    return FoldResult(
        fold=fold,
        auroc=auroc,
        auprc=auprc,
        normalized_utility=float(utility),
        threshold=float(threshold),
        worst_pseudo_site_auprc=min(group_scores) if group_scores else None,
        fit_patients=int(train_for_sites["patient_id"].nunique()),
        calibration_patients=0,
        validation_patients=int(validation["patient_id"].nunique()),
    )


def _passes(candidate: dict, reference: dict, safety: dict) -> tuple[bool, dict]:
    differences = {
        "utility": candidate["mean_normalized_utility"] - reference["mean_normalized_utility"],
        "auroc": candidate["mean_auroc"] - reference["mean_auroc"],
        "auprc": candidate["mean_auprc"] - reference["mean_auprc"],
        "worst_pseudo_site_auprc": (
            candidate["worst_pseudo_site_auprc"] - reference["worst_pseudo_site_auprc"]
        ),
    }
    checks = {
        "utility": differences["utility"] >= float(safety["minimum_utility_gain"]),
        "auroc": differences["auroc"] >= -float(safety["maximum_auroc_drop"]),
        "auprc": differences["auprc"] >= -float(safety["maximum_auprc_drop"]),
        "worst_pseudo_site": differences["worst_pseudo_site_auprc"]
        >= -float(safety["maximum_worst_pseudo_site_auprc_drop"]),
    }
    return all(checks.values()), {"differences": differences, "checks": checks}


def _feature_stage(
    frame: pd.DataFrame, folds: dict[str, int], config: dict, out: Path,
    fold_ids: list[int] | None = None,
) -> dict:
    stage = out / "features"
    stage.mkdir(parents=True, exist_ok=True)
    fold_series = frame["patient_id"].astype(str).map(folds).to_numpy()
    candidates = list(config["feature_candidates"])
    reports: dict[str, list[FoldResult]] = {name: [] for name in candidates}
    run_folds = fold_ids or sorted(set(folds.values()))
    for fold in run_folds:
        cached = stage / f"fold_{fold}.json"
        if cached.exists():
            payload = json.loads(cached.read_text())
            for name in candidates:
                reports[name].append(FoldResult(**payload[name]))
            print(f"feature fold {fold}: resumed", flush=True)
            continue
        started = time.perf_counter()
        in_train = fold_series != fold
        fit_patients, cal_mask, policy_mask = _outer_masks(frame, in_train, config, fold)
        fit_mask = fit_patients & _eligible(frame)
        val_mask = ~in_train
        extensions = _fit_extensions(frame.loc[fit_mask], frame, config["features"])
        payload = {}
        for name in candidates:
            augmented, columns = _candidate_frame(frame, extensions, name)
            fit = augmented.loc[fit_mask]
            calibration = augmented.loc[cal_mask]
            policy_tuning = augmented.loc[policy_mask]
            validation = augmented.loc[val_mask]
            model = fit_lgbm(
                fit, calibration.loc[_eligible(calibration)], columns,
                config["reference"]["params"], int(config["seed"]) + fold,
            )
            raw_cal = model.predict_proba(calibration[columns])[:, 1]
            calibrator, p_cal, threshold = calibrate_and_threshold(
                calibration, raw_cal, _eligible(calibration)
            )
            p_val = calibrator.predict(model.predict_proba(validation[columns])[:, 1])
            p_policy = calibrator.predict(model.predict_proba(policy_tuning[columns])[:, 1])
            report = _fold_metrics(
                frame.loc[in_train],
                frame.loc[val_mask],
                p_val,
                threshold,
                config,
                fold,
            )
            report = FoldResult(
                **{**asdict(report), "calibration_patients": int(calibration["patient_id"].nunique())}
            )
            reports[name].append(report)
            payload[name] = asdict(report)
            pd.DataFrame({
                "row": np.flatnonzero(policy_mask), "patient_id": policy_tuning["patient_id"].to_numpy(),
                "probability": p_policy, "eligible": _eligible(policy_tuning),
            }).to_parquet(stage / f"{name}_cal_fold_{fold}.parquet", index=False)
            pd.DataFrame({
                "row": np.flatnonzero(val_mask), "patient_id": validation["patient_id"].to_numpy(),
                "probability": p_val, "eligible": _eligible(validation),
            }).to_parquet(stage / f"{name}_oof_fold_{fold}.parquet", index=False)
        cached.write_text(json.dumps(payload, indent=2, default=float) + "\n")
        print(f"feature fold {fold}: completed in {time.perf_counter() - started:.0f}s", flush=True)
    summaries = {name: _summary(values) for name, values in reports.items()}
    reference = summaries["reference"]
    gates = {"reference": {"passed": True, "reason": "reference"}}
    eligible = ["reference"]
    for name in candidates[1:]:
        passed, evidence = _passes(summaries[name], reference, config["selection"]["safety"])
        gates[name] = {"passed": passed, **evidence}
        if passed:
            eligible.append(name)
    selected = max(
        eligible,
        key=lambda name: (
            summaries[name]["mean_normalized_utility"],
            summaries[name]["mean_auprc"],
            summaries[name]["worst_pseudo_site_auprc"],
        ),
    )
    result = {"summaries": summaries, "gates_vs_reference": gates, "selected": selected}
    (stage / "result.json").write_text(json.dumps(result, indent=2, default=float) + "\n")
    return result


def _calibrate_horizon(model, stop: pd.DataFrame, score: pd.DataFrame, columns: list[str], target: str):
    stop_mask = stop["incident_at_risk"].fillna(False).to_numpy(bool)
    raw_stop = model.predict_proba(stop[columns])[:, 1]
    calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(
        raw_stop[stop_mask], stop[target].to_numpy(dtype=float, na_value=np.nan)[stop_mask]
    )
    return calibrator.predict(model.predict_proba(score[columns])[:, 1])


def _inner_meta_training(
    outer_fit: pd.DataFrame,
    candidate: str,
    config: dict,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    inner_map = patient_folds(outer_fit, int(config["hazard"]["inner_folds"]), seed)
    inner_fold = outer_fit["patient_id"].astype(str).map(inner_map).to_numpy()
    reference_oof = np.full(len(outer_fit), np.nan)
    hazard_oof = np.full((len(outer_fit), len(config["hazard"]["horizons"])), np.nan)
    for inner in sorted(set(inner_map.values())):
        held = inner_fold == inner
        inside = ~held
        stop_ids = _split_calibration_ids(
            outer_fit.loc[inside, ["patient_id", "SepsisLabel"]],
            float(config["calibration_fraction"]),
            seed + inner,
        )
        is_stop = outer_fit["patient_id"].astype(str).isin(stop_ids).to_numpy()
        model_fit = inside & ~is_stop & _eligible(outer_fit)
        model_stop = inside & is_stop
        extensions = _fit_extensions(
            outer_fit.loc[model_fit], outer_fit, config["features"]
        )
        augmented, columns = _candidate_frame(outer_fit, extensions, candidate)
        fit, stop, score = augmented.loc[model_fit], augmented.loc[model_stop], augmented.loc[held]
        reference = fit_lgbm(
            fit, stop.loc[_eligible(stop)], columns, config["reference"]["params"], seed + inner
        )
        ref_calibrator, _, _ = calibrate_and_threshold(
            stop, reference.predict_proba(stop[columns])[:, 1], _eligible(stop)
        )
        reference_oof[held] = ref_calibrator.predict(reference.predict_proba(score[columns])[:, 1])
        for k, horizon in enumerate(config["hazard"]["horizons"]):
            target = f"incident_onset_within_{horizon}h"
            model = fit_lgbm(
                fit, stop, columns, config["hazard"]["params"], seed + 100 * k + inner,
                target=target, at_risk="incident_at_risk",
            )
            hazard_oof[held, k] = _calibrate_horizon(model, stop, score, columns, target)
    if not np.isfinite(reference_oof).all() or not np.isfinite(hazard_oof).all():
        raise RuntimeError("Inner cross-fitting left missing meta-training predictions.")
    return reference_oof, hazard_oof, _eligible(outer_fit)


def _hazard_stage(
    frame: pd.DataFrame,
    folds: dict[str, int],
    candidate: str,
    config: dict,
    out: Path,
    fold_ids: list[int] | None = None,
) -> dict:
    stage = out / "hazard"
    stage.mkdir(parents=True, exist_ok=True)
    fold_series = frame["patient_id"].astype(str).map(folds).to_numpy()
    reports = []
    run_folds = fold_ids or sorted(set(folds.values()))
    for fold in run_folds:
        cached = stage / f"fold_{fold}.json"
        if cached.exists():
            reports.append(FoldResult(**json.loads(cached.read_text())["metrics"]))
            print(f"hazard fold {fold}: resumed", flush=True)
            continue
        started = time.perf_counter()
        in_train = fold_series != fold
        fit_patient_mask, cal_mask, policy_mask = _outer_masks(frame, in_train, config, fold)
        fit_mask = fit_patient_mask & _eligible(frame)
        val_mask = ~in_train
        outer_fit = frame.loc[fit_patient_mask].reset_index(drop=True)
        ref_oof, hazard_oof, meta_eligible = _inner_meta_training(
            outer_fit, candidate, config, int(config["seed"]) + 1000 * fold
        )
        meta_x = hazard_meta_features(ref_oof, hazard_oof)
        meta = fit_meta(
            meta_x, outer_fit["SepsisLabel"].to_numpy(), meta_eligible,
            float(config["hazard"]["meta"]["C"]),
        )

        extensions = _fit_extensions(frame.loc[fit_mask], frame, config["features"])
        augmented, columns = _candidate_frame(frame, extensions, candidate)
        fit = augmented.loc[fit_mask]
        calibration = augmented.loc[cal_mask]
        policy_tuning = augmented.loc[policy_mask]
        validation = augmented.loc[val_mask]
        reference = fit_lgbm(
            fit, calibration.loc[_eligible(calibration)], columns,
            config["reference"]["params"], int(config["seed"]) + fold,
        )
        ref_calibrator, ref_cal, _ = calibrate_and_threshold(
            calibration, reference.predict_proba(calibration[columns])[:, 1], _eligible(calibration)
        )
        ref_val = ref_calibrator.predict(reference.predict_proba(validation[columns])[:, 1])
        ref_policy = ref_calibrator.predict(reference.predict_proba(policy_tuning[columns])[:, 1])
        h_cal, h_policy, h_val = [], [], []
        for k, horizon in enumerate(config["hazard"]["horizons"]):
            target = f"incident_onset_within_{horizon}h"
            model = fit_lgbm(
                fit, calibration, columns, config["hazard"]["params"],
                int(config["seed"]) + fold + 100 * k, target=target, at_risk="incident_at_risk",
            )
            h_cal.append(_calibrate_horizon(model, calibration, calibration, columns, target))
            h_policy.append(_calibrate_horizon(model, calibration, policy_tuning, columns, target))
            h_val.append(_calibrate_horizon(model, calibration, validation, columns, target))
        h_cal = np.column_stack(h_cal)
        h_policy = np.column_stack(h_policy)
        h_val = np.column_stack(h_val)
        raw_cal = meta.predict_proba(hazard_meta_features(ref_cal, h_cal))[:, 1]
        raw_policy = meta.predict_proba(hazard_meta_features(ref_policy, h_policy))[:, 1]
        raw_val = meta.predict_proba(hazard_meta_features(ref_val, h_val))[:, 1]
        calibrator, p_cal, threshold = calibrate_and_threshold(
            calibration, raw_cal, _eligible(calibration)
        )
        p_policy = calibrator.predict(raw_policy)
        p_val = calibrator.predict(raw_val)
        report = _fold_metrics(frame.loc[in_train], frame.loc[val_mask], p_val, threshold, config, fold)
        report = FoldResult(
            **{**asdict(report), "calibration_patients": int(calibration["patient_id"].nunique())}
        )
        reports.append(report)
        payload = {
            "metrics": asdict(report),
            "meta_intercept": meta.intercept_.tolist(),
            "meta_coefficients": meta.coef_.tolist(),
            "elapsed_seconds": time.perf_counter() - started,
        }
        cached.write_text(json.dumps(payload, indent=2, default=float) + "\n")
        pd.DataFrame({
            "row": np.flatnonzero(policy_mask), "patient_id": policy_tuning["patient_id"].to_numpy(),
            "probability": p_policy, "eligible": _eligible(policy_tuning),
        }).to_parquet(stage / f"cal_fold_{fold}.parquet", index=False)
        pd.DataFrame({
            "row": np.flatnonzero(val_mask), "patient_id": validation["patient_id"].to_numpy(),
            "probability": p_val, "eligible": _eligible(validation),
        }).to_parquet(stage / f"oof_fold_{fold}.parquet", index=False)
        print(f"hazard fold {fold}: completed in {time.perf_counter() - started:.0f}s", flush=True)
    result = {"selected_feature_candidate": candidate, "summary": _summary(reports)}
    (stage / "result.json").write_text(json.dumps(result, indent=2, default=float) + "\n")
    return result


def _operating_metrics(frame: pd.DataFrame, decision: np.ndarray) -> dict:
    eligible = _eligible(frame)
    decision = decision & eligible
    y = frame["SepsisLabel"].to_numpy()
    return {
        "normalized_utility": float(UtilityTable.from_frame(frame).normalized(decision)),
        **confusion_metrics(y, decision),
        **alert_events(frame, decision),
        **patient_detection(frame, decision),
    }


def _policy_stage(
    frame: pd.DataFrame,
    folds: dict[str, int],
    probability_source: Path,
    config: dict,
    out: Path,
    fold_ids: list[int] | None = None,
) -> dict:
    stage = out / "policy"
    stage.mkdir(parents=True, exist_ok=True)
    fold_series = frame["patient_id"].astype(str).map(folds).to_numpy()
    reports = []
    run_folds = fold_ids or sorted(set(folds.values()))
    for fold in run_folds:
        cal_scores = pd.read_parquet(probability_source / f"cal_fold_{fold}.parquet")
        val_scores = pd.read_parquet(probability_source / f"oof_fold_{fold}.parquet")
        calibration = frame.iloc[cal_scores["row"].to_numpy()].reset_index(drop=True)
        validation = frame.iloc[val_scores["row"].to_numpy()].reset_index(drop=True)
        p_cal = cal_scores["probability"].to_numpy()
        p_val = val_scores["probability"].to_numpy()
        spec = select_stateful_policy(calibration, p_cal, _eligible(calibration), config["policy"])
        _, cal_decision = apply_policy(spec, p_cal, calibration["patient_id"].to_numpy())
        _, val_decision = apply_policy(spec, p_val, validation["patient_id"].to_numpy())
        raw_spec = select_stateful_policy(
            calibration, p_cal, _eligible(calibration),
            {**config["policy"], "hysteresis_low_ratio": [], "persistence_hours": [], "ema_alpha": []},
        )
        _, raw_val = apply_policy(raw_spec, p_val, validation["patient_id"].to_numpy())
        reports.append({
            "fold": fold, "selected": spec,
            "calibration": _operating_metrics(calibration, cal_decision),
            "validation": _operating_metrics(validation, val_decision),
            "raw_validation": _operating_metrics(validation, raw_val),
        })
    deltas = {
        key: float(np.mean([
            r["validation"][key] - r["raw_validation"][key] for r in reports
        ]))
        for key in ("normalized_utility", "sensitivity", "false_alerts_per_100_patient_hours")
    }
    promoted = (
        deltas["normalized_utility"] >= float(config["selection"]["safety"]["minimum_utility_gain"])
        and deltas["sensitivity"] >= -float(config["policy"]["maximum_sensitivity_drop"])
        and deltas["false_alerts_per_100_patient_hours"]
        <= float(config["policy"]["maximum_false_alert_increase_per_100h"])
    )
    result = {"folds": reports, "mean_selected_minus_raw": deltas, "policy_promoted": promoted}
    (stage / "result.json").write_text(json.dumps(result, indent=2, default=float) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=Path("data/processed/features_setA.parquet"))
    parser.add_argument("--config", type=Path, default=Path("configs/residual_hazard.yaml"))
    parser.add_argument("--out", type=Path, default=Path("artifacts/challengers/RESIDUAL-HAZARD-01"))
    parser.add_argument("--feature-only", action="store_true", help="Stop after additive-feature ablations.")
    parser.add_argument("--folds", type=int, nargs="*", help="Run selected folds (smoke tests only).")
    parser.add_argument("--limit-patients", type=int, help="Stratified patient subsample (smoke tests only).")
    args = parser.parse_args()
    if (args.out / "result.json").exists():
        raise SystemExit(f"Refusing to overwrite completed run: {args.out}")
    validate_development_file(args.features)
    config = yaml.safe_load(args.config.read_text())
    identity = {
        "config_sha256": _sha256(args.config),
        "feature_file_sha256": _sha256(args.features),
        "target_file_sha256": _sha256(Path(config["target_file"])),
        "smoke_folds": args.folds,
        "smoke_limit_patients": args.limit_patients,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    identity_path = args.out / "run_identity.json"
    if identity_path.exists() and json.loads(identity_path.read_text()) != identity:
        raise SystemExit("Resume refused: config, features, or targets changed.")
    identity_path.write_text(json.dumps(identity, indent=2) + "\n")
    frame = pd.read_parquet(args.features, filters=[("split", "in", ["train", "val"])]).reset_index(drop=True)
    frame = _join_targets(frame, Path(config["target_file"]))
    if args.limit_patients:
        patient_target = frame.groupby("patient_id", sort=False)["SepsisLabel"].max()
        sampled = []
        rng = np.random.default_rng(int(config["seed"]))
        for _, group in patient_target.groupby(patient_target):
            n = max(1, round(args.limit_patients * len(group) / len(patient_target)))
            sampled.extend(rng.choice(group.index.to_numpy(), min(n, len(group)), replace=False))
        frame = frame[frame["patient_id"].isin(sampled)].reset_index(drop=True)
    fold_map = json.loads(Path(config["fold_assignments"]).read_text())
    if set(frame["patient_id"].astype(str)) - set(fold_map):
        raise ValueError("Fold assignment file does not cover all development patients.")

    feature_result = _feature_stage(frame, fold_map, config, args.out, args.folds)
    if args.feature_only:
        print(json.dumps(feature_result, indent=2, default=float))
        return
    hazard_result = _hazard_stage(
        frame, fold_map, feature_result["selected"], config, args.out, args.folds
    )
    feature_summary = feature_result["summaries"][feature_result["selected"]]
    hazard_passed, hazard_gate = _passes(
        hazard_result["summary"], feature_summary, config["selection"]["safety"]
    )
    source = args.out / "hazard" if hazard_passed else args.out / "features"
    if not hazard_passed:
        # Feature-stage paths are candidate-prefixed; expose a stable policy input view.
        policy_input = args.out / "selected_risk"
        policy_input.mkdir(exist_ok=True)
        for fold in (args.folds or sorted(set(fold_map.values()))):
            for kind, prefix in (("cal", "cal"), ("oof", "oof")):
                original = args.out / "features" / f"{feature_result['selected']}_{prefix}_fold_{fold}.parquet"
                (policy_input / f"{kind}_fold_{fold}.parquet").write_bytes(original.read_bytes())
        source = policy_input
    policy_result = _policy_stage(frame, fold_map, source, config, args.out, args.folds)
    result = {
        "run_id": args.out.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset": "PhysioNet Challenge 2019 Dataset A train+validation only",
        "dataset_b_accessed": False,
        "internal_test_accessed": False,
        **identity,
        "feature_stage": feature_result,
        "hazard_stage": hazard_result,
        "hazard_gate": {"passed": hazard_passed, **hazard_gate},
        "selected_risk": "hazard_stack" if hazard_passed else feature_result["selected"],
        "policy_stage": policy_result,
        "status": "development complete; no closed-test or Dataset B access permitted",
    }
    (args.out / "result.json").write_text(json.dumps(result, indent=2, default=float) + "\n")
    print(json.dumps({
        "selected_features": feature_result["selected"],
        "hazard_gate": result["hazard_gate"],
        "selected_risk": result["selected_risk"],
        "policy_promoted": policy_result["policy_promoted"],
    }, indent=2, default=float))


if __name__ == "__main__":
    main()
