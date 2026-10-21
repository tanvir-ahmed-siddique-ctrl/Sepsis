"""One-time Dataset B comparison of frozen Run 4 and Residual-Hazard candidate.

This command is intentionally user-run. It records authorization before loading
Dataset B and refuses overwrite or repeat access.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
import yaml

from predict_rx.eval.bootstrap import patient_paired_bootstrap
from predict_rx.eval.metrics import UtilityTable, full_report
from predict_rx.features.schema import MIN_HOURS_BEFORE_PRED
from predict_rx.governance.access import EvaluationAccessLedger, resolve_authorization
from predict_rx.residual_hazard.models import smooth_ema


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply_external_rule(rule: dict, paired: dict, reports: dict) -> dict:
    required = list(rule["require_any_paired_95ci_lower_above_zero"])
    lower = {metric: (paired.get(metric) or {}).get("lower") for metric in required}
    credible_gain = any(value is not None and value > 0 for value in lower.values())
    challenger = reports["candidate_system"]
    run4 = reports["run4"]
    utility_gap = (
        challenger["high_risk"]["normalized_utility"]
        - run4["high_risk"]["normalized_utility"]
    )
    auroc_drop = run4["ranking"]["auroc"] - challenger["ranking"]["auroc"]
    sensitivity_gap = (
        challenger["high_risk"]["sensitivity"] - run4["high_risk"]["sensitivity"]
    )
    false_alert_gap = (
        challenger["high_risk"]["false_alerts_per_100_patient_hours"]
        - run4["high_risk"]["false_alerts_per_100_patient_hours"]
    )
    checks = {
        "credible_paired_gain": {
            "passed": credible_gain,
            "candidate_minus_run4_95ci_lower_bounds": lower,
        },
        "utility_point_not_worse": {
            "passed": utility_gap >= 0
            or not bool(rule["require_high_risk_utility_point_not_worse"]),
            "candidate_minus_run4": utility_gap,
        },
        "auroc_not_materially_worse": {
            "passed": auroc_drop <= float(rule["maximum_auroc_point_drop"]),
            "run4_minus_candidate": auroc_drop,
        },
        "sensitivity_not_materially_worse": {
            "passed": sensitivity_gap >= -float(rule["maximum_sensitivity_point_drop"]),
            "candidate_minus_run4": sensitivity_gap,
        },
        "false_alerts_not_materially_worse": {
            "passed": false_alert_gap
            <= float(rule["maximum_false_alert_increase_per_100h"]),
            "candidate_minus_run4": false_alert_gap,
        },
    }
    promoted = all(item["passed"] for item in checks.values())
    return {
        "checks": checks,
        "promote_candidate": promoted,
        "decision": (
            "promote candidate as the stronger retrospectively validated system"
            if promoted
            else "reject candidate; frozen Run 4 remains primary"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/residual_hazard_setb.yaml"))
    parser.add_argument("--features", type=Path, default=Path("data/processed/features_setB.parquet"))
    parser.add_argument("--authorized-by", required=True)
    parser.add_argument("--authorize-dataset-b", required=True)
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path("artifacts/governance/evaluation_access.json"),
    )
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text())
    external = config["external_comparison"]
    candidate_dir = Path(external["candidate"])
    anchor_dir = Path(external["anchor"])
    out = candidate_dir / "compare_setb.json"
    if out.exists():
        raise SystemExit(f"Refusing to overwrite one-time comparison: {out}")
    if not args.features.exists():
        raise SystemExit(f"Missing Dataset B feature file: {args.features}")

    candidate_path = candidate_dir / "model.joblib"
    anchor_path = anchor_dir / "model.joblib"
    candidate = joblib.load(candidate_path)
    run4 = joblib.load(anchor_path)
    if not candidate.get("frozen"):
        raise SystemExit("Candidate is not frozen.")
    if candidate.get("external_config_sha256") != _sha256(args.config):
        raise SystemExit("External comparison config changed after candidate final fit.")
    frozen_record = json.loads((candidate_dir / "FROZEN.json").read_text())
    candidate_hash = _sha256(candidate_path)
    if candidate_hash != frozen_record["model_sha256"]:
        raise SystemExit("Frozen candidate hash does not match FROZEN.json.")
    if _sha256(anchor_path) != "a7dcf5f4b2f00927c17d2468cba144b3db4642ccb5a9c946b484958a0413532d":
        raise SystemExit("Frozen Run 4 integrity check failed.")
    final_result_path = candidate_dir / "result.json"
    final_result = json.loads(final_result_path.read_text())
    if final_result.get("dataset_b_accessed"):
        raise SystemExit("Candidate has already accessed Dataset B.")

    confirmation, reason = resolve_authorization(args.authorize_dataset_b)
    command = "python -m predict_rx.residual_hazard.compare_setb"
    access = EvaluationAccessLedger(args.ledger).record(
        model_version=candidate["model_version"],
        model_sha256=candidate_hash,
        purpose="residual_hazard_one_time_setb_comparison",
        reason=reason,
        authorized_by=args.authorized_by,
        command=command,
        confirmation=confirmation,
    )

    frame = pd.read_parquet(args.features, filters=[("split", "==", "holdout")])
    if frame.empty:
        raise SystemExit("No Dataset B holdout rows found.")
    if set(frame["split"].astype(str)) != {"holdout"}:
        raise SystemExit("External comparison loaded rows outside Dataset B holdout.")
    eligible = (frame["hours_observed"] >= MIN_HOURS_BEFORE_PRED).to_numpy()
    table = UtilityTable.from_frame(frame)

    run4_probability = run4["model"].predict_proba(frame)[:, 1]
    candidate_probability = candidate["model"].predict_proba(frame)[:, 1]
    policy = candidate["alert_policy"]
    if policy["kind"] != "ema":
        raise SystemExit("Frozen candidate policy differs from preregistration.")
    candidate_system_score = smooth_ema(
        candidate_probability,
        frame["patient_id"].to_numpy(),
        float(policy["alpha"]),
    )
    run4_thresholds = {
        key: float(run4["thresholds"][key]) for key in ("watch", "high_risk")
    }
    raw_candidate_thresholds = {
        key: float(candidate["thresholds"][key]) for key in ("watch", "high_risk")
    }
    policy_thresholds = {
        key: float(policy["thresholds"][key]) for key in ("watch", "high_risk")
    }
    reports = {
        "run4": full_report(
            frame, run4_probability, eligible, run4_thresholds, table
        ),
        "candidate_raw": full_report(
            frame,
            candidate_probability,
            eligible,
            raw_candidate_thresholds,
            table,
        ),
        "candidate_system": full_report(
            frame,
            candidate_system_score,
            eligible,
            policy_thresholds,
            table,
        ),
    }
    bootstrap = patient_paired_bootstrap(
        frame,
        {"candidate": candidate_system_score, "run4": run4_probability},
        eligible,
        {
            "candidate": policy_thresholds["high_risk"],
            "run4": run4_thresholds["high_risk"],
        },
        anchor="candidate",
        replicates=int(external["bootstrap_replicates"]),
        seed=int(config["seed"]),
    )
    paired = bootstrap["paired_differences_anchor_minus_comparator"]["run4"]
    decision = apply_external_rule(external["release_rule"], paired, reports)
    comparison = {
        "run_id": config["run_id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset": external["dataset"],
        "dataset_b_accessed": True,
        "internal_test_accessed": False,
        "access_ledger_entry": access,
        "features_sha256": _sha256(args.features),
        "candidate_model_sha256": candidate_hash,
        "run4_model_sha256": _sha256(anchor_path),
        "candidate_version": candidate["model_version"],
        "run4_version": run4["model_version"],
        "reports": reports,
        "paired_bootstrap_candidate_minus_run4": bootstrap,
        "release_rule": external["release_rule"],
        "decision": decision,
        "note": (
            "Dataset B was already known to the overall project through Run 4, "
            "but was unseen during this candidate's selection and final fit. "
            "No post-result tuning or repeat Dataset B access is permitted."
        ),
    }
    out.write_text(json.dumps(comparison, indent=2, default=float) + "\n")
    final_result["dataset_b_accessed"] = True
    final_result["dataset_b_comparison"] = {
        "artifact": str(out),
        "decision": decision,
    }
    final_result_path.write_text(json.dumps(final_result, indent=2, default=float) + "\n")
    summary = {
        name: {
            "auroc": report["ranking"]["auroc"],
            "auprc": report["ranking"]["auprc"],
            "high_risk_utility": report["high_risk"]["normalized_utility"],
        }
        for name, report in reports.items()
    }
    print(json.dumps({"reports": summary, "decision": decision}, indent=2, default=float))


if __name__ == "__main__":
    main()
