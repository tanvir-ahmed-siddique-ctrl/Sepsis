"""Cohort-level TrustGate validation (master plan 7E) on Dataset A validation.

Replays every hour of each patient through the frozen model and the backend's
own ``assess_prediction`` policy, then compares interruptive alerts from the
raw threshold with alerts that pass TrustGate:

* at the same hour-level sensitivity (raw threshold raised to match), and
* at the same alert-hour budget.

The claim this supports is retrospective alert stability/burden only. It never
reads Dataset B or the locked Dataset A internal test.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from joblib import Parallel, delayed

from predict_rx.data import load_patient_psv
from predict_rx.eval.metrics import UtilityTable, alert_events, confusion_metrics, patient_detection
from predict_rx.features.engineering import build_patient_features
from predict_rx.features.schema import DEMO_COLS, LAB_COLS, MIN_HOURS_BEFORE_PRED, VITAL_COLS

REQUIRED_VITALS = ("HR", "SBP", "MAP", "O2Sat")
BACKEND_TRUSTGATE = Path(__file__).resolve().parents[4] / "backend" / "app" / "trustgate.py"


def _load_backend_policy():
    name = "backend_trustgate"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, BACKEND_TRUSTGATE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _prepare(raw: pd.DataFrame) -> pd.DataFrame:
    frame = raw.drop(columns=["SepsisLabel", "patient_id"], errors="ignore").copy()
    for column in VITAL_COLS + LAB_COLS + DEMO_COLS:
        if column not in frame:
            frame[column] = np.nan
    return frame


def _features(frame: pd.DataFrame) -> pd.DataFrame:
    features = build_patient_features(frame)
    features["hours_observed"] = np.arange(1, len(features) + 1)
    return features


def perturbation_views(prefix: pd.DataFrame) -> list[pd.DataFrame]:
    """Same three views as ``ScoringEngine._perturbed_probabilities`` in the backend."""
    delayed_vitals = prefix.copy()
    vital_columns = [column for column in REQUIRED_VITALS if column in delayed_vitals]
    if vital_columns:
        delayed_vitals.loc[delayed_vitals.index[-2:], vital_columns] = np.nan

    delayed_labs = prefix.copy()
    lab_columns = [column for column in LAB_COLS if column in delayed_labs]
    if lab_columns:
        delayed_labs.loc[delayed_labs.index[-6:], lab_columns] = np.nan

    no_lactate = prefix.copy()
    if "Lactate" in no_lactate:
        no_lactate["Lactate"] = np.nan
    return [delayed_vitals, delayed_labs, no_lactate]


def score_patient(path: Path, bundle: dict) -> pd.DataFrame:
    policy = _load_backend_policy()
    model = bundle["model"]
    high = float(bundle["thresholds"]["high_risk"])
    watch = float(bundle["thresholds"]["watch"])

    raw = load_patient_psv(path)
    frame = _prepare(raw)
    features = _features(frame)
    probability = model.predict_proba(features)[:, 1].astype(float)

    states: list[str] = []
    stability: list[float] = []
    for index in range(len(frame)):
        hours = index + 1
        freshness = {}
        for variable in REQUIRED_VITALS:
            value = features[f"{variable}_hours_since"].iloc[index]
            freshness[variable] = None if pd.isna(value) else int(float(value) * 60)
        required = list(freshness.values())
        freshness_minutes = max(required) if all(value is not None for value in required) else None
        if hours < MIN_HOURS_BEFORE_PRED:
            prob, band, quality = None, "insufficient_data", "insufficient"
        else:
            prob = float(probability[index])
            band = "high_risk" if prob >= high else "watch" if prob >= watch else "stable"
            if freshness_minutes is None:
                quality = "missing_required_vitals"
            elif freshness_minutes > 120:
                quality = "stale_required_vitals"
            else:
                quality = "ok"
        variants: list[float] = []
        if band == "high_risk":
            prefix = frame.iloc[: index + 1]
            for view in perturbation_views(prefix):
                variants.append(float(model.predict_proba(_features(view).iloc[[-1]])[0, 1]))
        assessment = policy.assess_prediction(
            probability=prob,
            risk_band=band,
            data_quality=quality,
            data_freshness_minutes=freshness_minutes,
            signal_freshness=freshness,
            high_risk_threshold=high,
            perturbed_probabilities=variants,
        )
        states.append(assessment.state.value)
        stability.append(np.nan if assessment.alert_stability is None else assessment.alert_stability)

    return pd.DataFrame(
        {
            "patient_id": path.stem,
            "SepsisLabel": raw["SepsisLabel"].to_numpy(dtype=int),
            "hours_observed": np.arange(1, len(frame) + 1),
            "probability": probability,
            "state": states,
            "alert_stability": stability,
        }
    )


def policy_metrics(frame: pd.DataFrame, pred: np.ndarray, table: UtilityTable) -> dict:
    y = frame["SepsisLabel"].to_numpy()
    return {
        "alert_hours": int(pred.sum()),
        "normalized_utility": table.normalized(pred),
        **confusion_metrics(y, pred),
        **alert_events(frame, pred),
        **patient_detection(frame, pred),
    }


def matched_threshold(probability: np.ndarray, eligible: np.ndarray, y: np.ndarray, *,
                      target_sensitivity: float | None = None, target_alerts: int | None = None) -> float:
    """Lowest raw threshold whose sensitivity (or alert count) does not exceed the target."""
    candidates = np.unique(probability[eligible])[::-1]
    positives = eligible & (y == 1)
    scores = np.sort(probability[positives])[::-1]
    eligible_scores = np.sort(probability[eligible])[::-1]
    best = float(candidates[0])
    for threshold in candidates:
        if target_sensitivity is not None:
            value = np.searchsorted(-scores, -threshold, side="right") / max(len(scores), 1)
            if value > target_sensitivity:
                break
        else:
            value = np.searchsorted(-eligible_scores, -threshold, side="right")
            if value > target_alerts:
                break
        best = float(threshold)
    return best


def _patient_counts(frame: pd.DataFrame, pred: np.ndarray) -> pd.DataFrame:
    ids = frame["patient_id"].to_numpy()
    previous = np.concatenate([[False], pred[:-1]])
    new_patient = np.concatenate([[True], ids[1:] != ids[:-1]])
    event = pred & (~previous | new_patient)
    positions = frame.groupby("patient_id", sort=False).cumcount().to_numpy()
    from predict_rx.eval.metrics import DT_EARLY, DT_LATE, patient_onsets

    onset = frame["patient_id"].map(patient_onsets(frame)).to_numpy()
    true_event = event & ~np.isnan(onset) & (positions >= onset + DT_EARLY) & (positions <= onset + DT_LATE)
    y = frame["SepsisLabel"].to_numpy() == 1
    return pd.DataFrame(
        {
            "false_events": event & ~true_event,
            "hours": 1,
            "positive_hours": y,
            "alerted_positive_hours": y & pred,
        }
    ).groupby(ids, sort=False).sum()


def paired_bootstrap(frame: pd.DataFrame, gated: np.ndarray, raw: np.ndarray, replicates: int, seed: int) -> dict:
    a = _patient_counts(frame, gated)
    b = _patient_counts(frame, raw).reindex(a.index)
    rng = np.random.default_rng(seed)
    n = len(a)
    false_diff, sens_diff = [], []
    av, bv = a.to_numpy(dtype=float), b.to_numpy(dtype=float)
    for _ in range(replicates):
        sample = rng.integers(0, n, n)
        sa, sb = av[sample].sum(0), bv[sample].sum(0)
        false_diff.append(100 * (sa[0] - sb[0]) / sa[1])
        sens_diff.append(sa[3] / sa[2] - sb[3] / sb[2] if sa[2] and sb[2] else np.nan)

    def interval(values: list[float]) -> dict:
        array = np.asarray(values, dtype=float)
        array = array[np.isfinite(array)]
        return {"lower": float(np.quantile(array, 0.025)), "upper": float(np.quantile(array, 0.975))}

    return {
        "method": "patient-level paired bootstrap",
        "replicates": replicates,
        "false_alerts_per_100h_trustgate_minus_raw": interval(false_diff),
        "sensitivity_trustgate_minus_raw": interval(sens_diff),
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/training_setA"))
    parser.add_argument("--features", type=Path, default=Path("data/processed/features_setA.parquet"))
    parser.add_argument("--model", type=Path, default=Path("artifacts/models/run4_frozen/model.joblib"))
    parser.add_argument("--split", default="val", choices=["val"])
    parser.add_argument("--limit", type=int, default=None, help="Smoke-test on the first N patients")
    parser.add_argument("--jobs", type=int, default=-1)
    parser.add_argument("--bootstrap", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=Path("artifacts/experiments/TRUSTGATE-COHORT-01"))
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"Refusing to overwrite immutable result: {args.out}")

    ids = (
        pq.read_table(args.features, columns=["patient_id", "split"], filters=[("split", "==", args.split)])
        .column("patient_id")
        .to_pandas()
        .drop_duplicates()
        .tolist()
    )
    if args.limit:
        ids = ids[: args.limit]
    bundle = joblib.load(args.model)
    parts = Parallel(n_jobs=args.jobs, batch_size=8)(
        delayed(score_patient)(args.raw_dir / f"{patient_id}.psv", bundle) for patient_id in ids
    )
    frame = pd.concat(parts, ignore_index=True)
    eligible = (frame["hours_observed"] >= MIN_HOURS_BEFORE_PRED).to_numpy()
    y = frame["SepsisLabel"].to_numpy()
    probability = frame["probability"].to_numpy()
    high = float(bundle["thresholds"]["high_risk"])
    table = UtilityTable.from_frame(frame)

    raw_alert = eligible & (probability >= high)
    gated_alert = (frame["state"] == "alert").to_numpy()
    review = (frame["state"] == "verify_data").to_numpy()
    gated_sensitivity = confusion_metrics(y[eligible], gated_alert[eligible])["sensitivity"] or 0.0
    t_sens = matched_threshold(probability, eligible, y, target_sensitivity=gated_sensitivity)
    t_budget = matched_threshold(probability, eligible, y, target_alerts=int(gated_alert.sum()))
    raw_matched_sens = eligible & (probability >= t_sens)
    raw_matched_budget = eligible & (probability >= t_budget)

    stability = frame["alert_stability"].to_numpy()
    unstable = raw_alert & np.isfinite(stability) & (stability < 0.8)
    suppressed = raw_alert & ~gated_alert
    states = frame.loc[eligible, "state"].value_counts(normalize=True).to_dict()

    result = {
        "run_id": args.out.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "claim_scope": "retrospective alert burden/stability on Dataset A validation; no clinical-harm claim",
        "dataset": f"PhysioNet 2019 Dataset A split={args.split}",
        "dataset_b_accessed": False,
        "internal_test_accessed": False,
        "patients": len(ids),
        "hours": int(len(frame)),
        "eligible_hours": int(eligible.sum()),
        "model_version": bundle["model_version"],
        "model_sha256": _sha256(args.model),
        "backend_policy_sha256": _sha256(BACKEND_TRUSTGATE),
        "high_risk_threshold": high,
        "state_distribution_eligible_hours": states,
        "raw_high_risk_alerts": int(raw_alert.sum()),
        "unstable_raw_alerts": int(unstable.sum()),
        "suppressed_raw_alerts": int(suppressed.sum()),
        "suppressed_alert_positive_rate": float(y[suppressed].mean()) if suppressed.any() else None,
        "kept_alert_positive_rate": float(y[gated_alert].mean()) if gated_alert.any() else None,
        "verify_data_hours": int(review.sum()),
        "policies": {
            "raw_threshold": policy_metrics(frame, raw_alert, table),
            "trustgate_alert": policy_metrics(frame, gated_alert, table),
            "raw_matched_sensitivity": {"threshold": t_sens, **policy_metrics(frame, raw_matched_sens, table)},
            "raw_matched_alert_budget": {"threshold": t_budget, **policy_metrics(frame, raw_matched_budget, table)},
        },
        "paired_vs_matched_sensitivity": (
            paired_bootstrap(frame, gated_alert, raw_matched_sens, args.bootstrap, args.seed)
            if args.bootstrap
            else {"status": "skipped"}
        ),
        "interpretation_rule": (
            "TrustGate shows a reliability benefit only if, at matched sensitivity, its false alerts per "
            "100 patient-hours are lower than simply raising the raw threshold, with a paired interval "
            "excluding zero."
        ),
    }
    args.out.mkdir(parents=True)
    frame.to_parquet(args.out / "hourly_states.parquet", index=False)
    (args.out / "result.json").write_text(json.dumps(result, indent=2, default=float) + "\n")
    summary = {name: {k: result["policies"][name][k] for k in (
        "alert_hours", "sensitivity", "false_alerts_per_100_patient_hours", "alert_precision",
        "detected_before_onset", "normalized_utility")} for name in result["policies"]}
    print(json.dumps({"output": str(args.out), "summary": summary,
                      "bootstrap": result["paired_vs_matched_sensitivity"]}, indent=2, default=float))


if __name__ == "__main__":
    main()
