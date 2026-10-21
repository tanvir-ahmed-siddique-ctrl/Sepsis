"""Evaluate a saved model on a feature file using its stored thresholds.

Dataset B (split='holdout') is only scored for a frozen model — see train.freeze.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import joblib
import pandas as pd

from predict_rx.eval.metrics import full_report, subgroup_report
from predict_rx.features.schema import MIN_HOURS_BEFORE_PRED
from predict_rx.governance.access import EvaluationAccessLedger, resolve_authorization


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, default=Path("data/processed/features_setB.parquet"))
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--split", default="holdout")
    parser.add_argument("--ledger", type=Path, default=Path("artifacts/governance/evaluation_access.json"))
    parser.add_argument("--authorized-by")
    parser.add_argument("--authorize-dataset-b")
    parser.add_argument("--allow-repeat", action="store_true")
    args = parser.parse_args()

    model_path = args.model_dir / "model.joblib"
    bundle = joblib.load(model_path)
    out = args.model_dir / f"eval_{args.split}.json"
    if out.exists():
        raise SystemExit(f"Refusing to overwrite existing evaluation artifact: {out}")
    if args.split == "holdout":
        if not bundle.get("frozen"):
            raise SystemExit("Model is not frozen. Freeze the challenger before touching Dataset B.")
        if not args.authorized_by or not args.authorize_dataset_b:
            raise SystemExit("Dataset B evaluation requires --authorized-by and --authorize-dataset-b.")
        confirmation, reason = resolve_authorization(args.authorize_dataset_b)
        EvaluationAccessLedger(args.ledger).record(
            model_version=bundle["model_version"],
            model_sha256=hashlib.sha256(model_path.read_bytes()).hexdigest(),
            purpose="challenger_holdout_eval",
            reason=reason,
            authorized_by=args.authorized_by,
            command="python -m predict_rx.eval.run",
            confirmation=confirmation,
            allow_repeat=args.allow_repeat,
        )

    df = pd.read_parquet(args.features)
    df = df[df["split"] == args.split]
    if df.empty:
        raise SystemExit(f"No rows for split={args.split}")
    eligible = (df["hours_observed"] >= MIN_HOURS_BEFORE_PRED).to_numpy()
    prob = bundle["model"].predict_proba(df)[:, 1]
    thresholds = bundle["thresholds"]
    report = {
        "model_version": bundle["model_version"],
        "model_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
        "split": args.split,
        "features_file": str(args.features),
        **full_report(df, prob, eligible, thresholds),
        "subgroups": subgroup_report(df, prob, eligible, thresholds["high_risk"]),
    }
    out.write_text(json.dumps(report, indent=2, default=float))
    r = report
    print(f"AUROC {r['ranking']['auroc']:.3f} · AUPRC {r['ranking']['auprc']:.3f} · ECE {r['ranking']['ece']:.4f} · "
          f"utility {r['high_risk']['normalized_utility']:.3f} → {out}")


if __name__ == "__main__":
    main()
