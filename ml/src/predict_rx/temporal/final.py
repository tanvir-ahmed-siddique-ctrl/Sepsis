"""Refit the GRAPH-HAZARD-01 selection into a scoreable bundle (Dataset A only).

Mirrors the Run 4 refit: fit on train patients with 10% held back for early
stopping, isotonic calibration and thresholds on validation patients. When the
development CV chose fusion, a two-input logistic blend of frozen Run 4 and the
temporal model is fit on validation patients (both are out-of-sample there for
model fitting). Never reads the locked internal test or Dataset B.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
import yaml
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from predict_rx.eval.compare_internal import _early_stopping_ids, validation_thresholds
from predict_rx.eval.metrics import full_report
from predict_rx.features.schema import MIN_HOURS_BEFORE_PRED
from predict_rx.governance.integrity import sha256_file
from predict_rx.temporal.data import Normalizer, SequenceData, load_sequences, patient_row_weights
from predict_rx.temporal.models import build_model
from predict_rx.temporal.train import ExperimentSpec, predict, train_model

META_COLUMNS = ["patient_id", "split", "SepsisLabel", "hours_observed"]


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-5, 1 - 1e-5)
    return np.log(p / (1 - p))


class TemporalBundle:
    """Scores sequences with a refit temporal model, optionally fused with Run 4."""

    def __init__(self, directory: Path, device: torch.device | None = None):
        self.directory = Path(directory)
        self.meta = joblib.load(self.directory / "bundle.joblib")
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        spec = self.meta["spec"]
        self.model = build_model(spec["model"], self.meta["n_static"], spec["params"]).to(self.device)
        self.model.load_state_dict(torch.load(self.directory / "model.pt", map_location=self.device))
        self.model.eval()
        self.norm = Normalizer(**{k: np.asarray(v, dtype=np.float32) for k, v in self.meta["normalizer"].items()})

    @property
    def uses_fusion(self) -> bool:
        return self.meta["blend"] is not None

    def temporal_probability(self, data: SequenceData) -> np.ndarray:
        raw = predict(self.model, data, np.arange(len(data.patient_ids)), self.norm, self.device)["challenge"]
        return self.meta["calibrator"].predict(raw)

    def probability(self, data: SequenceData, run4_probability: np.ndarray | None = None) -> np.ndarray:
        temporal = self.temporal_probability(data)
        if not self.uses_fusion:
            return temporal
        if run4_probability is None:
            raise ValueError("Fused bundle needs frozen Run 4 probabilities for the same rows.")
        intercept, w_run4, w_temporal = self.meta["blend"]
        z = intercept + w_run4 * _logit(run4_probability) + w_temporal * _logit(temporal)
        return 1 / (1 + np.exp(-z))


def load_frame(path: Path, split: str, extra: list[str]) -> pd.DataFrame:
    frame = pd.read_parquet(path, columns=list(dict.fromkeys(META_COLUMNS + extra)),
                            filters=[("split", "==", split)])
    return frame.reset_index(drop=True)


def check_alignment(frame: pd.DataFrame, data: SequenceData) -> None:
    if len(frame) != len(data.label) or not (frame["patient_id"].to_numpy()[data.offsets[:-1]] == data.patient_ids).all():
        raise SystemExit("Sequence rows are not aligned with the feature frame.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=Path("data/processed/features_setA.parquet"))
    parser.add_argument("--config", type=Path, default=Path("configs/temporal_graph_hazard.yaml"))
    parser.add_argument("--cv", type=Path, default=Path("artifacts/challengers/GRAPH-HAZARD-01"))
    parser.add_argument("--anchor", type=Path, default=Path("artifacts/models/run4_frozen"))
    parser.add_argument("--early-stopping-fraction", type=float, default=0.1)
    parser.add_argument("--max-epochs", type=int, help="Override epochs (smoke tests only)")
    args = parser.parse_args()
    out = args.cv / "final"
    if out.exists():
        raise SystemExit(f"Refusing to overwrite final bundle: {out}")
    cv_result = json.loads((args.cv / "result.json").read_text())
    if cv_result.get("internal_test_accessed") or cv_result.get("dataset_b_accessed"):
        raise SystemExit("CV run already touched a locked split; aborting.")
    config = yaml.safe_load(args.config.read_text())
    if sha256_file(args.config) != cv_result["config_sha256"]:
        raise SystemExit("Config changed since the CV selection ran.")
    selected = cv_result["selected_temporal"]
    use_fusion = cv_result["final_challenger"] == "fusion_run4_plus_temporal"
    seed = int(config["seed"])
    defaults = config.get("training", {})
    if args.max_epochs:
        defaults = {**defaults, "max_epochs": args.max_epochs}
    spec = ExperimentSpec.from_config(selected, config["experiments"][selected], defaults)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    data = load_sequences(args.features, ("train", "val"))
    train_idx = np.flatnonzero(data.split == "train")
    val_idx = np.flatnonzero(data.split == "val")
    train_ids = pd.DataFrame({"patient_id": data.patient_ids[train_idx]})
    es_ids = _early_stopping_ids(train_ids, args.early_stopping_fraction, seed)
    is_es = np.isin(data.patient_ids[train_idx].astype(str), list(es_ids))
    weights = patient_row_weights(data)
    print(f"refit {selected} on {int((~is_es).sum())} train patients (device={device})", flush=True)
    model, norm, info = train_model(data, train_idx[~is_es], train_idx[is_es], spec, weights=weights,
                                    device=device, seed=seed, log=lambda s: print(s, flush=True))

    anchor = joblib.load(args.anchor / "model.joblib")
    validation = load_frame(args.features, "val", list(anchor["feature_columns"]) if use_fusion else [])
    val_data = load_sequences(args.features, ("val",))
    check_alignment(validation, val_data)
    eligible = (validation["hours_observed"] >= MIN_HOURS_BEFORE_PRED).to_numpy()
    y = validation["SepsisLabel"].to_numpy()
    raw = predict(model, val_data, np.arange(len(val_data.patient_ids)), norm, device)["challenge"]
    calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(raw[eligible], y[eligible])
    temporal = calibrator.predict(raw)

    blend, probability = None, temporal
    if use_fusion:
        run4 = anchor["model"].predict_proba(validation)[:, 1]
        features = np.column_stack([_logit(run4), _logit(temporal)])
        fit = LogisticRegression(C=1.0, max_iter=1000).fit(features[eligible], y[eligible])
        blend = [float(fit.intercept_[0]), *map(float, fit.coef_[0])]
        probability = fit.predict_proba(features)[:, 1]
    refit = config.get("refit", {})
    rules = {"min_specificity": float(refit.get("high_risk_min_specificity", 0.95)),
             "watch_patient_sensitivity": float(refit.get("watch_patient_sensitivity", 0.85))}
    thresholds = validation_thresholds(validation, probability, eligible, **rules)
    temporal_thresholds = validation_thresholds(validation, temporal, eligible, **rules) if use_fusion else thresholds
    version = f"graph-hazard-{selected}-{'fusion-' if use_fusion else ''}{datetime.now(timezone.utc):%Y%m%d%H%M}"
    out.mkdir(parents=True)
    torch.save(model.state_dict(), out / "model.pt")
    joblib.dump({
        "spec": asdict(spec),
        "n_static": 2 * data.static.shape[1],
        "normalizer": norm.as_dict(),
        "calibrator": calibrator,
        "blend": blend,
        "blend_inputs": ["intercept", "logit(run4)", "logit(temporal)"] if use_fusion else None,
        "anchor_version": anchor["model_version"] if use_fusion else None,
        "thresholds": {"watch": thresholds["watch"], "high_risk": thresholds["high_risk"]},
        "model_version": version,
        "frozen": False,
    }, out / "bundle.joblib")
    result = {
        "run_id": f"{args.cv.name}/final",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset": "PhysioNet Challenge 2019 Dataset A train+validation only",
        "dataset_b_accessed": False,
        "internal_test_accessed": False,
        "selected_temporal": selected,
        "final_challenger": cv_result["final_challenger"],
        "model_version": version,
        "refit": {"best_epoch": info["best_epoch"], "early_stopping_auprc": info["best_stop_auprc"],
                  "history": info["history"]},
        "blend_weights_intercept_run4_temporal": blend,
        "thresholds": thresholds,
        "temporal_only_thresholds": temporal_thresholds,
        "validation_report": full_report(validation, probability, eligible, thresholds),
        "validation_report_temporal_only": full_report(validation, temporal, eligible, temporal_thresholds)
        if use_fusion else None,
        "note": "Validation metrics are in-sample for calibration, blend, and thresholds.",
    }
    (out / "result.json").write_text(json.dumps(result, indent=2, default=float) + "\n")
    report = result["validation_report"]
    print(json.dumps({"output": str(out), "version": version, "fusion": use_fusion, "blend": blend,
                      "validation_auprc": report["ranking"]["auprc"],
                      "validation_high_risk_utility": report["high_risk"]["normalized_utility"]},
                     indent=2, default=float))


if __name__ == "__main__":
    main()
