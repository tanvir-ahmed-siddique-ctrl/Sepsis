"""GRAPH-HAZARD-01: grouped-CV ablation ladder for temporal challengers (Dataset A only).

Uses the TABULAR-AONLY-01 fold assignments, calibration-patient split, isotonic
calibration, threshold rule, and metrics, so every row of the ablation table
is comparable with the optimized tree model. Also reports a cross-fitted
tree + temporal fusion from out-of-fold predictions. Never reads the locked
internal test or Dataset B. Resumable per (experiment, fold).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import torch
import yaml
from sklearn.linear_model import LogisticRegression

from predict_rx.eval.metrics import UtilityTable, best_utility_threshold
from predict_rx.temporal.data import HORIZONS, load_sequences, patient_row_weights
from predict_rx.temporal.train import ExperimentSpec, evaluate_fold, predict, train_model
from predict_rx.train.challenger import _pseudo_site_labels, _safe_ranking, _split_calibration_ids
from predict_rx.train.challenger_gate import check_challenger_gate


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_meta(path: Path) -> pd.DataFrame:
    names = pq.ParquetFile(path).schema_arrow.names
    columns = ["patient_id", "SepsisLabel", "hours_observed", "ICULOS"] + [c for c in names if c.endswith("_missing")]
    frame = pq.read_table(path, columns=columns + ["split"], filters=[("split", "in", ["train", "val"])]).to_pandas()
    frame["eligible"] = frame["hours_observed"] >= 4
    return frame.drop(columns=["split"]).reset_index(drop=True)


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-5, 1 - 1e-5)
    return np.log(p / (1 - p))


def fused_oof(meta: pd.DataFrame, fold_of_row: np.ndarray, tree: np.ndarray, temporal: np.ndarray,
              clusters: int, min_rows: int, seed: int) -> dict:
    """Cross-fitted two-input logistic blend; weights never see the scored fold."""
    features = np.column_stack([_logit(tree), _logit(temporal)])
    eligible = meta["eligible"].to_numpy()
    y = meta["SepsisLabel"].to_numpy()
    folds, weights = [], []
    for fold in np.unique(fold_of_row):
        scored = fold_of_row == fold
        others = ~scored
        blend = LogisticRegression(C=1.0, max_iter=1000).fit(features[others & eligible], y[others & eligible])
        weights.append([float(blend.intercept_[0]), *map(float, blend.coef_[0])])
        other_prob = blend.predict_proba(features[others])[:, 1]
        threshold, _ = best_utility_threshold(UtilityTable.from_frame(meta[others]), other_prob, eligible[others])
        probability = blend.predict_proba(features[scored])[:, 1]
        validation = meta[scored]
        e = eligible[scored]
        auroc, auprc = _safe_ranking(y[scored][e], probability[e])
        utility = UtilityTable.from_frame(validation).normalized((probability >= threshold) & e)
        missing = [c for c in meta if c.endswith("_missing")]
        sites = _pseudo_site_labels(meta[others][["patient_id"] + missing], validation[["patient_id"] + missing],
                                    clusters=clusters, seed=seed + int(fold))
        group = [s for g in np.unique(sites) if (e & (sites == g)).sum() >= min_rows
                 for s in [_safe_ranking(y[scored][e & (sites == g)], probability[e & (sites == g)])[1]] if s is not None]
        folds.append({"fold": int(fold), "auroc": auroc, "auprc": auprc, "normalized_utility": float(utility),
                      "threshold": float(threshold), "worst_pseudo_site_auprc": min(group) if group else None})
    return {**summarize(folds), "blend_weights_intercept_tree_temporal": weights}


def summarize(folds: list[dict]) -> dict:
    def mean(key):
        values = [f[key] for f in folds if f.get(key) is not None]
        return float(np.mean(values)) if values else None

    worst = [f["worst_pseudo_site_auprc"] for f in folds if f.get("worst_pseudo_site_auprc") is not None]
    summary = {
        "mean_auroc": mean("auroc"),
        "mean_auprc": mean("auprc"),
        "mean_normalized_utility": mean("normalized_utility"),
        "worst_pseudo_site_auprc": min(worst) if worst else None,
        "folds": folds,
    }
    for key in ("incident_6h_auroc", "incident_6h_auprc", "best_epoch", "train_seconds"):
        if any(key in f for f in folds):
            summary[f"mean_{key}"] = mean(key)
    return summary


def _key(summary: dict) -> tuple:
    return tuple(summary.get(k) if summary.get(k) is not None else -np.inf
                 for k in ("mean_normalized_utility", "mean_auprc", "worst_pseudo_site_auprc"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=Path("data/processed/features_setA.parquet"))
    parser.add_argument("--config", type=Path, default=Path("configs/temporal_graph_hazard.yaml"))
    parser.add_argument("--out", type=Path, default=Path("artifacts/challengers/GRAPH-HAZARD-01"))
    parser.add_argument("--only", nargs="*", help="Run a subset of experiments (smoke tests)")
    parser.add_argument("--folds", type=int, nargs="*", help="Run a subset of folds (smoke tests)")
    parser.add_argument("--max-epochs", type=int, help="Override epochs (smoke tests)")
    parser.add_argument("--limit-patients", type=int, help="Subsample development patients (smoke tests)")
    args = parser.parse_args()
    if (args.out / "result.json").exists():
        raise SystemExit(f"Refusing to overwrite completed run: {args.out}")
    gate = check_challenger_gate(Path(".").resolve())
    if not gate["passed"]:
        raise SystemExit("Challenger gate not passed; run predict_rx.train.challenger_gate first.")
    config = yaml.safe_load(args.config.read_text())
    identity = {"config_sha256": _sha256(args.config), "feature_file_sha256": _sha256(args.features),
                "smoke": bool(args.only or args.folds or args.max_epochs or args.limit_patients)}
    args.out.mkdir(parents=True, exist_ok=True)
    identity_path = args.out / "run_identity.json"
    if identity_path.exists() and json.loads(identity_path.read_text()) != identity:
        raise SystemExit("Resume refused: config, feature file, or smoke flags changed since the run started.")
    identity_path.write_text(json.dumps(identity, indent=2) + "\n")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"device={device}", flush=True)
    data = load_sequences(args.features, ("train", "val"))
    meta = load_meta(args.features)
    if len(meta) != len(data.label) or not (meta["patient_id"].to_numpy()[data.offsets[:-1]] == data.patient_ids).all():
        raise SystemExit("Sequence rows are not aligned with the feature file.")
    fold_map = json.loads(Path(config["fold_assignments"]).read_text())
    patient_fold = np.array([fold_map[str(p)] for p in data.patient_ids])
    patients = np.arange(len(data.patient_ids))
    if args.limit_patients:
        patients = np.random.default_rng(0).choice(patients, args.limit_patients, replace=False)
    weights = patient_row_weights(data)
    fold_of_row = np.repeat(patient_fold, data.lengths())
    seed = int(config["seed"])
    defaults = config.get("training", {})
    if args.max_epochs:
        defaults = {**defaults, "max_epochs": args.max_epochs}
    clusters = int(config["pseudo_sites"]["clusters"])
    min_rows = int(config["pseudo_sites"]["minimum_rows_for_metric"])
    fold_ids = args.folds if args.folds else sorted(set(patient_fold.tolist()))

    summaries: dict[str, dict] = {}
    for name, payload in config["experiments"].items():
        if args.only and name not in args.only:
            continue
        spec = ExperimentSpec.from_config(name, payload, defaults)
        exp_dir = args.out / name
        exp_dir.mkdir(exist_ok=True)
        fold_reports = []
        for fold in fold_ids:
            report_path = exp_dir / f"fold_{fold}.json"
            if report_path.exists():
                fold_reports.append(json.loads(report_path.read_text()))
                print(f"{name} fold {fold}: resumed", flush=True)
                continue
            print(f"{name} fold {fold}: training", flush=True)
            in_train = patients[patient_fold[patients] != fold]
            held_out = patients[patient_fold[patients] == fold]
            train_rows = data.rows_for(np.sort(in_train))
            calibration_ids = _split_calibration_ids(
                meta.iloc[train_rows][["patient_id", "SepsisLabel"]],
                float(config["calibration_fraction"]), seed + fold,
            )
            is_cal = np.isin(data.patient_ids[in_train], list(calibration_ids))
            fit_patients, stop_patients = in_train[~is_cal], in_train[is_cal]
            started = time.perf_counter()
            model, norm, info = train_model(data, fit_patients, stop_patients, spec, weights=weights,
                                            device=device, seed=seed + fold,
                                            log=lambda s: print(s, flush=True))
            elapsed = time.perf_counter() - started
            calibration_scores = predict(model, data, stop_patients, norm, device)
            validation_scores = predict(model, data, held_out, norm, device)
            calibration_rows = data.rows_for(np.sort(stop_patients))
            validation_rows = data.rows_for(np.sort(held_out))
            metrics, probability = evaluate_fold(
                meta, calibration_scores["challenge"], calibration_rows,
                validation_scores["challenge"], validation_rows, train_rows,
                clusters=clusters, min_rows=min_rows, seed=seed + fold,
            )
            at_risk = np.isfinite(data.incident[validation_rows, 2]) & data.eligible[validation_rows]
            incident_auroc, incident_auprc = _safe_ranking(
                data.incident[validation_rows, 2][at_risk], validation_scores["hazard"][at_risk, 2]
            )
            report = {"fold": int(fold), **metrics, "incident_6h_auroc": incident_auroc,
                      "incident_6h_auprc": incident_auprc, "best_epoch": info["best_epoch"],
                      "train_seconds": elapsed, "history": info["history"],
                      "parameters": int(sum(p.numel() for p in model.parameters()))}
            oof = pd.DataFrame({
                "row": validation_rows, "patient_id": meta["patient_id"].to_numpy()[validation_rows],
                "fold": fold, "raw": validation_scores["challenge"], "probability": probability,
                **{f"hazard_{h}h": validation_scores["hazard"][:, k] for k, h in enumerate(HORIZONS)},
            })
            oof.to_parquet(exp_dir / f"oof_fold_{fold}.parquet", index=False)
            report_path.write_text(json.dumps(report, indent=2, default=float) + "\n")
            fold_reports.append(report)
            print(f"{name} fold {fold}: utility={metrics['normalized_utility']:.4f} "
                  f"AUPRC={metrics['auprc']:.4f} incident6h_AUROC={incident_auroc} ({elapsed:.0f}s)", flush=True)
            del model
            torch.cuda.empty_cache()
        summaries[name] = summarize([{k: v for k, v in r.items() if k != "history"} for r in fold_reports])

    result = {
        "run_id": args.out.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset": "PhysioNet Challenge 2019 Dataset A train+validation only",
        "dataset_b_accessed": False,
        "internal_test_accessed": False,
        **identity,
        "experiments": summaries,
    }
    complete = not identity["smoke"] and all(name in summaries for name in config["experiments"])
    if complete:
        candidates = {name: summaries[name] for name in config["selection"]["candidates"]}
        best = max(candidates, key=lambda name: _key(candidates[name]))
        tree = pd.read_parquet(config["tree_oof"])
        oof = pd.concat(pd.read_parquet(p) for p in sorted((args.out / best).glob("oof_fold_*.parquet")))
        oof = oof.sort_values("row")
        if not (tree["patient_id"].to_numpy() == oof["patient_id"].to_numpy()).all():
            raise SystemExit("Tree OOF rows are not aligned with temporal OOF rows.")
        fusion = fused_oof(meta, fold_of_row, tree["probability"].to_numpy(), oof["probability"].to_numpy(),
                           clusters, min_rows, seed)
        margin = float(config["selection"]["fusion_min_utility_gain"])
        use_fusion = (fusion["mean_normalized_utility"] or -np.inf) >= (summaries[best]["mean_normalized_utility"] + margin)
        result.update({
            "tree_reference": config["tree_reference"],
            "fusion_tree_plus_best_temporal": fusion,
            "selected_temporal": best,
            "final_challenger": "fusion_run4_plus_temporal" if use_fusion else "temporal_only",
            "selection_rule": config["selection"],
            "status": "development selection complete; locked internal test not yet accessed",
        })
        (args.out / "result.json").write_text(json.dumps(result, indent=2, default=float) + "\n")
    else:
        (args.out / "partial_result.json").write_text(json.dumps(result, indent=2, default=float) + "\n")
    table = {name: {k: s[k] for k in ("mean_normalized_utility", "mean_auprc", "mean_auroc", "worst_pseudo_site_auprc")}
             for name, s in summaries.items()}
    print(json.dumps({"experiments": table, "selected_temporal": result.get("selected_temporal"),
                      "final_challenger": result.get("final_challenger"),
                      "fusion": {k: result.get("fusion_tree_plus_best_temporal", {}).get(k)
                                 for k in ("mean_normalized_utility", "mean_auprc")}}, indent=2, default=float))


if __name__ == "__main__":
    main()
