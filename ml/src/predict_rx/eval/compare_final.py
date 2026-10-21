"""Second, final use of the locked Dataset A internal test (GRAPH-HAZARD-01).

Scores frozen Run 4 and the single preselected challenger (the refit
GRAPH-HAZARD-01 bundle) once, with each model's own validation thresholds, and
applies the preregistered `locked_test_rule`. The temporal-only model (when the
challenger is a fusion) and the low-resource fallback are reported descriptively
and cannot be promoted from this run. Dataset B is never read.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import yaml

from predict_rx.eval.bootstrap import patient_paired_bootstrap
from predict_rx.eval.metrics import UtilityTable, full_report
from predict_rx.features.schema import MIN_HOURS_BEFORE_PRED
from predict_rx.governance.integrity import sha256_file
from predict_rx.temporal.data import load_sequences
from predict_rx.temporal.final import TemporalBundle, check_alignment, load_frame
from predict_rx.train.run import validate_training_output


def apply_rule(rule: dict, paired: dict, reports: dict) -> dict:
    lower = {m: (paired.get(m) or {}).get("lower") for m in rule["require_any_lower_bound_above_zero"]}
    credible = any(v is not None and v > 0 for v in lower.values())
    auroc_drop = reports["run4"]["ranking"]["auroc"] - reports["challenger"]["ranking"]["auroc"]
    utility_gap = (reports["challenger"]["high_risk"]["normalized_utility"]
                   - reports["run4"]["high_risk"]["normalized_utility"])
    checks = {
        "credible_paired_gain": {"passed": credible, "lower_bounds": lower},
        "auroc_not_materially_worse": {"passed": auroc_drop <= float(rule["max_auroc_point_drop"]),
                                       "run4_minus_challenger": auroc_drop},
        "utility_point_not_worse": {"passed": (utility_gap >= 0) or not rule["require_utility_point_not_worse"],
                                    "challenger_minus_run4": utility_gap},
    }
    passed = all(c["passed"] for c in checks.values())
    return {"checks": checks, "advance_to_dataset_b": passed,
            "decision": "advance: freeze challenger and ask the user to run the one-time Dataset B comparison"
            if passed else "reject: frozen Run 4 stays primary"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=Path("data/processed/features_setA.parquet"))
    parser.add_argument("--config", type=Path, default=Path("configs/temporal_graph_hazard.yaml"))
    parser.add_argument("--challenger", type=Path, default=Path("artifacts/challengers/GRAPH-HAZARD-01/final"))
    parser.add_argument("--fallback", type=Path, default=Path("artifacts/fallback/LOWRES-FALLBACK-01"))
    parser.add_argument("--anchor", type=Path, default=Path("artifacts/models/run4_frozen"))
    parser.add_argument("--out", type=Path, default=Path("artifacts/experiments/compare_final_GRAPH-HAZARD-01"))
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"Refusing to overwrite locked comparison: {args.out}")
    validate_training_output(args.out, Path("."))
    config = yaml.safe_load(args.config.read_text())
    rule = config["locked_test_rule"]
    challenger_result_path = args.challenger / "result.json"
    challenger_result = json.loads(challenger_result_path.read_text())
    if challenger_result.get("internal_test_accessed") or challenger_result.get("dataset_b_accessed"):
        raise SystemExit("Challenger already consumed a locked split; aborting.")

    anchor = joblib.load(args.anchor / "model.joblib")
    bundle = TemporalBundle(args.challenger)
    fallback = joblib.load(args.fallback / "model.joblib") if (args.fallback / "model.joblib").exists() else None
    extra = list(anchor["feature_columns"]) + (list(fallback["feature_columns"]) if fallback else [])
    test = load_frame(args.features, "test", extra)
    if test.empty:
        raise SystemExit("Locked Dataset A test rows are required.")
    data = load_sequences(args.features, ("test",))
    check_alignment(test, data)
    eligible = (test["hours_observed"] >= MIN_HOURS_BEFORE_PRED).to_numpy()
    table = UtilityTable.from_frame(test)

    run4 = anchor["model"].predict_proba(test)[:, 1]
    temporal = bundle.temporal_probability(data)
    probabilities = {"run4": run4, "challenger": bundle.probability(data, run4)}
    thresholds = {"run4": {k: float(anchor["thresholds"][k]) for k in ("watch", "high_risk")},
                  "challenger": bundle.meta["thresholds"]}
    if bundle.uses_fusion:
        temporal_thresholds = challenger_result["temporal_only_thresholds"]
        probabilities["temporal_only"] = temporal
        thresholds["temporal_only"] = {k: temporal_thresholds[k] for k in ("watch", "high_risk")}
    if fallback:
        probabilities["lowres_fallback"] = fallback["model"].predict_proba(test)[:, 1]
        thresholds["lowres_fallback"] = fallback["thresholds"]

    reports = {name: full_report(test, p, eligible, thresholds[name], table) for name, p in probabilities.items()}
    bootstrap = patient_paired_bootstrap(
        test, probabilities, eligible, {n: t["high_risk"] for n, t in thresholds.items()},
        anchor="challenger", replicates=int(rule["bootstrap_replicates"]), seed=int(config["seed"]),
    )
    decision = apply_rule(rule, bootstrap["paired_differences_anchor_minus_comparator"]["run4"], reports)
    comparison = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset": "PhysioNet Challenge 2019 Dataset A internal test (second and final use)",
        "dataset_b_accessed": False,
        "internal_test_accessed": True,
        "features_sha256": sha256_file(args.features),
        "config_sha256": sha256_file(args.config),
        "anchor_version": anchor["model_version"],
        "challenger_version": bundle.meta["model_version"],
        "challenger_kind": challenger_result["final_challenger"],
        "selected_temporal": challenger_result["selected_temporal"],
        "thresholds": thresholds,
        "reports": reports,
        "paired_bootstrap": bootstrap,
        "locked_test_rule": rule,
        "decision": decision,
        "note": "temporal_only and lowres_fallback are descriptive only and cannot be promoted from this run.",
    }
    args.out.mkdir(parents=True)
    (args.out / "compare_final.json").write_text(json.dumps(comparison, indent=2, default=float) + "\n")
    challenger_result["internal_test_accessed"] = True
    challenger_result_path.write_text(json.dumps(challenger_result, indent=2, default=float) + "\n")
    summary = {name: {"auroc": r["ranking"]["auroc"], "auprc": r["ranking"]["auprc"],
                      "high_risk_utility": r["high_risk"]["normalized_utility"],
                      "sensitivity": r["high_risk"]["sensitivity"], "specificity": r["high_risk"]["specificity"]}
               for name, r in reports.items()}
    print(json.dumps({"output": str(args.out), "test": summary, "decision": decision}, indent=2, default=float))


if __name__ == "__main__":
    main()
