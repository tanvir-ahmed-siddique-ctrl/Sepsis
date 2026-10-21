"""Train baselines and the LightGBM early-warning model on Dataset A.

Patient-level roles inside Dataset A:
  train  → model fitting (10% of train patients held back for early stopping)
  val    → model selection, isotonic calibration, alert thresholds
  test   → honest internal estimate, touched once per run
Dataset B is never read here.
"""

from __future__ import annotations

import argparse
import json
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
import yaml
from sklearn.impute import SimpleImputer
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from predict_rx.eval.metrics import (
    UtilityTable,
    best_utility_threshold,
    expected_calibration_error,
    full_report,
    patient_sensitivity_threshold,
    subgroup_report,
)
from predict_rx.features.build import NON_FEATURE_COLS
from predict_rx.features.schema import MIN_HOURS_BEFORE_PRED, TARGET_COL
from predict_rx.models import CalibratedEnsemble

# EtCO2 is never recorded in Dataset A; its all-empty columns are expected.
warnings.filterwarnings("ignore", message="Skipping features without any observed values")


def feature_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in NON_FEATURE_COLS and pd.api.types.is_numeric_dtype(df[c])]


def validate_training_output(path: Path, ml_root: Path) -> None:
    protected = {
        (ml_root / "artifacts/models/latest").resolve(),
        (ml_root / "artifacts/models/run4_frozen").resolve(),
    }
    if path.resolve() in protected:
        raise ValueError(f"Refusing to train into protected evidence directory: {path}")
    if path.exists() and any(path.iterdir()):
        raise FileExistsError(f"Refusing to overwrite non-empty training output: {path}")


def clinical_rule_score(df: pd.DataFrame) -> np.ndarray:
    """SIRS-style criteria count plus shock index, scaled to [0, 1]."""
    checks = [
        (df["Temp"] > 38.0) | (df["Temp"] < 36.0),
        df["HR"] > 90,
        df["Resp"] > 20,
        (df["WBC"] > 12) | (df["WBC"] < 4),
        df["shock_index"] > 0.9,
    ]
    return np.sum([c.fillna(False).to_numpy(dtype=float) for c in checks], axis=0) / len(checks)


def fit_isotonic(raw: np.ndarray, y: np.ndarray) -> IsotonicRegression:
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    iso.fit(raw, y)
    return iso


def lgbm(params: dict, seed: int, n_estimators: int) -> lgb.LGBMClassifier:
    return lgb.LGBMClassifier(
        objective="binary",
        n_estimators=n_estimators,
        learning_rate=params["learning_rate"],
        num_leaves=params["num_leaves"],
        min_child_samples=params["min_child_samples"],
        subsample=params["subsample"],
        subsample_freq=1,
        colsample_bytree=params["colsample_bytree"],
        reg_lambda=params["reg_lambda"],
        scale_pos_weight=params["scale_pos_weight"],
        random_state=seed,
        n_jobs=-1,
        verbose=-1,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, default=Path("data/processed/features_setA.parquet"))
    parser.add_argument("--config", type=Path, default=Path("configs/train_lightgbm.yaml"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    if not args.features.exists():
        raise SystemExit(f"Missing features: {args.features}. Run features.build first.")
    validate_training_output(args.out, Path("."))
    cfg = yaml.safe_load(args.config.read_text())
    rng = np.random.default_rng(cfg["seed"])

    df = pd.read_parquet(args.features)
    if (df["split"] == "holdout").any():
        raise SystemExit("Refusing to train on holdout (Dataset B) rows.")
    cols = feature_columns(df)
    eligible_all = (df["hours_observed"] >= MIN_HOURS_BEFORE_PRED).to_numpy()
    print(f"{len(df):,} rows · {len(cols)} features · eligible rows {eligible_all.mean():.1%}")

    parts = {s: df[df["split"] == s] for s in ("train", "val", "test")}
    elig = {s: (parts[s]["hours_observed"] >= MIN_HOURS_BEFORE_PRED).to_numpy() for s in parts}
    tables = {s: UtilityTable.from_frame(parts[s]) for s in ("val", "test")}

    train_ids = parts["train"]["patient_id"].unique()
    es_ids = set(rng.choice(train_ids, size=int(0.1 * len(train_ids)), replace=False))
    is_es = parts["train"]["patient_id"].isin(es_ids).to_numpy()
    fit = parts["train"][~is_es & elig["train"]]
    es = parts["train"][is_es & elig["train"]]
    X_fit, y_fit = fit[cols], fit[TARGET_COL].to_numpy()
    X_es, y_es = es[cols], es[TARGET_COL].to_numpy()
    X_val = parts["val"][cols]
    y_val_elig = parts["val"][TARGET_COL].to_numpy()[elig["val"]]

    results: dict = {"candidates": {}}

    def score_on_val(raw_val: np.ndarray) -> dict:
        _, u = best_utility_threshold(tables["val"], raw_val, elig["val"])
        return {"val_utility": u, "val_auprc": float(average_precision_score(y_val_elig, raw_val[elig["val"]]))}

    # --- LightGBM sweep (selection on validation utility) ---
    base = cfg["lightgbm"]
    best_name, best_model, best_params, best_score = None, None, None, None
    for i, override in enumerate(cfg["sweep"]):
        params = {**base, **override}
        name = f"lgbm_{i}"
        t0 = time.time()
        model = lgbm(params, cfg["seed"], params["max_estimators"])
        model.fit(X_fit, y_fit, eval_X=X_es, eval_y=y_es, eval_metric=cfg["early_stopping_metric"],
                  callbacks=[lgb.early_stopping(params["early_stopping_rounds"], verbose=False)])
        s = score_on_val(model.predict_proba(X_val)[:, 1])
        s.update(params=override, best_iteration=int(model.best_iteration_), seconds=round(time.time() - t0, 1))
        results["candidates"][name] = s
        print(f"{name} {override} → utility {s['val_utility']:.4f} AUPRC {s['val_auprc']:.4f} "
              f"iters {s['best_iteration']} ({s['seconds']}s)")
        key = (s["val_utility"], s["val_auprc"])
        if best_score is None or key > best_score:
            best_name, best_model, best_params, best_score = name, model, params, key
    print(f"Selected {best_name}")

    single = CalibratedEnsemble([best_model], cols)

    # --- Five-member patient-bootstrap ensemble with the selected params ---
    fit_ids = fit["patient_id"].to_numpy()
    uniq = np.unique(fit_ids)
    row_index = pd.Series(np.arange(len(fit))).groupby(fit_ids).apply(np.asarray)
    members = []
    for seed in range(cfg["ensemble_members"]):
        sample = np.random.default_rng(seed).choice(uniq, size=len(uniq), replace=True)
        idx = np.concatenate(row_index.loc[sample].to_list())
        m = lgbm(best_params, seed, int(best_model.best_iteration_))
        m.fit(X_fit.iloc[idx], y_fit[idx])
        members.append(m)
        print(f"ensemble member {seed + 1}/{cfg['ensemble_members']} trained")
    ensemble = CalibratedEnsemble(members, cols)

    def calibrated_val(model: CalibratedEnsemble) -> tuple[CalibratedEnsemble, dict]:
        raw = model.raw_score(X_val)
        model.calibrator = fit_isotonic(raw[elig["val"]], y_val_elig)
        p = model.calibrate(raw)
        _, u = best_utility_threshold(tables["val"], p, elig["val"])
        return model, {"utility": u, "ece": expected_calibration_error(y_val_elig, p[elig["val"]])}

    single, s_single = calibrated_val(single)
    ensemble, s_ens = calibrated_val(ensemble)
    use_ensemble = (s_ens["utility"] - s_single["utility"] >= 0.01) and (s_ens["ece"] - s_single["ece"] <= 0.01)
    final = ensemble if use_ensemble else single
    results["ensemble_decision"] = {"single": s_single, "ensemble": s_ens, "use_ensemble": use_ensemble}
    print(f"single {s_single} · ensemble {s_ens} → use_ensemble={use_ensemble}")

    # --- Baselines, calibrated and thresholded the same way ---
    logistic = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=500, class_weight="balanced")),
    ])
    logistic.fit(X_fit, y_fit)
    scorers = {
        "clinical_rule": lambda d: clinical_rule_score(d),
        "logistic": lambda d: logistic.predict_proba(d[cols])[:, 1],
        "lightgbm": lambda d: final.raw_score(d),
    }

    reports: dict = {}
    thresholds_by_model: dict = {}
    for name, scorer in scorers.items():
        raw_val = scorer(parts["val"])
        iso = final.calibrator if name == "lightgbm" else fit_isotonic(raw_val[elig["val"]], y_val_elig)
        p_val = iso.predict(raw_val)
        labels_val = parts["val"]["SepsisLabel"].to_numpy()
        utility_opt, _ = best_utility_threshold(tables["val"], p_val, elig["val"])
        high, _ = best_utility_threshold(tables["val"], p_val, elig["val"], labels_val, cfg["high_risk_min_specificity"])
        watch = min(utility_opt,
                    patient_sensitivity_threshold(parts["val"], p_val, elig["val"], cfg["watch_patient_sensitivity"]),
                    high)
        thresholds = {"watch": float(max(watch, 0.0)), "high_risk": float(high)}
        thresholds_by_model[name] = thresholds
        operating_points = {**thresholds, "utility_optimal": float(utility_opt)}
        p_test = iso.predict(scorer(parts["test"]))
        reports[name] = {
            "val": full_report(parts["val"], p_val, elig["val"], operating_points, tables["val"]),
            "test": full_report(parts["test"], p_test, elig["test"], operating_points, tables["test"]),
        }
        r = reports[name]["test"]
        print(f"[test] {name:13s} AUROC {r['ranking']['auroc']:.3f} AUPRC {r['ranking']['auprc']:.3f} "
              f"ECE {r['ranking']['ece']:.4f} utility(opt) {r['utility_optimal']['normalized_utility']:.3f} "
              f"utility(high) {r['high_risk']['normalized_utility']:.3f}")
    results["reports"] = reports

    thresholds = thresholds_by_model["lightgbm"]
    p_test = final.predict_proba(parts["test"])[:, 1]
    results["subgroups_test"] = subgroup_report(parts["test"], p_test, elig["test"], thresholds["high_risk"])

    lg, lr, cr = (reports[n]["test"] for n in ("lightgbm", "logistic", "clinical_rule"))
    results["release_criteria_internal_test"] = {
        "beats_baselines_utility": lg["utility_optimal"]["normalized_utility"] > max(
            lr["utility_optimal"]["normalized_utility"], cr["utility_optimal"]["normalized_utility"]),
        "beats_baselines_auprc": lg["ranking"]["auprc"] > max(lr["ranking"]["auprc"], cr["ranking"]["auprc"]),
        "auprc_lift_vs_logistic": lg["ranking"]["auprc"] / lr["ranking"]["auprc"] - 1,
        "ece_le_0_05": lg["ranking"]["ece"] <= 0.05,
    }

    sample = parts["test"][elig["test"]].sample(200, random_state=0)
    t0 = time.perf_counter()
    for i in range(len(sample)):
        final.predict_proba(sample.iloc[[i]])
    results["cpu_latency_ms_per_prediction"] = (time.perf_counter() - t0) / len(sample) * 1000

    shap_rows = parts["val"][elig["val"]].sample(5000, random_state=0)
    mean_abs = np.abs(final.contributions(shap_rows))[:, :-1].mean(axis=0)
    order = np.argsort(mean_abs)[::-1][:25]
    results["global_shap_top25"] = {cols[i]: float(mean_abs[i]) for i in order}

    version = f"v0.2.0-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"
    args.out.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": final,
            "uncertainty_model": ensemble,
            "feature_columns": cols,
            "thresholds": thresholds,
            "model_version": version,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "params": best_params,
            "ensemble": use_ensemble,
            "frozen": False,
        },
        args.out / "model.joblib",
    )
    results["model_version"] = version
    results["thresholds"] = thresholds
    (args.out / "metrics.json").write_text(json.dumps(results, indent=2, default=float))
    stale = args.out / "val_metrics.json"
    if stale.exists():
        stale.unlink()
    print(json.dumps(results["release_criteria_internal_test"], indent=2, default=float))
    print(f"latency {results['cpu_latency_ms_per_prediction']:.1f} ms · saved {version} → {args.out}")


if __name__ == "__main__":
    main()
