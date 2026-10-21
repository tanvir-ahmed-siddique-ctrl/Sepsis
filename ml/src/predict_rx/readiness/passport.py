"""Generate a conservative Hospital Readiness Passport from site evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class RecommendedMode(str, Enum):
    do_not_deploy = "Do not deploy"
    retrospective_validation = "Retrospective validation"
    silent_pilot = "Silent pilot"
    controlled_pilot_candidate = "Controlled pilot candidate"


@dataclass(frozen=True)
class PassportDecision:
    mode: RecommendedMode
    blockers: list[str]
    next_actions: list[str]


def decide_mode(evidence: dict[str, Any]) -> PassportDecision:
    """Apply explicit gates; absence of evidence never counts as passing."""
    blockers: list[str] = []
    actions: list[str] = []
    integrity = evidence.get("integrity", {})
    schema = evidence.get("schema", {})
    metrics = evidence.get("metrics", {})
    local = bool(evidence.get("local_site_evidence", False))

    if integrity.get("critical_failures"):
        blockers.append("critical_data_integrity_failures")
    if float(schema.get("required_field_coverage", 0)) < 0.95:
        blockers.append("required_field_coverage_below_95_percent")
    if not schema.get("units_validated", False):
        blockers.append("clinical_units_not_validated")
    if not schema.get("encounter_identity_validated", False):
        blockers.append("encounter_identity_not_validated")
    if blockers:
        actions.extend(
            [
                "Resolve integrity and schema blockers before model evaluation.",
                "Do not enable scores or alerts at this site.",
            ]
        )
        return PassportDecision(RecommendedMode.do_not_deploy, blockers, actions)

    required_metrics = ("auroc", "auprc", "brier", "calibration_slope", "false_alerts_per_100h")
    missing_metrics = [metric for metric in required_metrics if metrics.get(metric) is None]
    if not local or missing_metrics:
        if not local:
            blockers.append("no_local_retrospective_validation")
        if missing_metrics:
            blockers.append("missing_required_metrics:" + ",".join(missing_metrics))
        actions.extend(
            [
                "Run retrospective local validation without live clinician alerts.",
                "Assess calibration, prevalence, alert burden, subgroups, and threshold transfer.",
            ]
        )
        return PassportDecision(RecommendedMode.retrospective_validation, blockers, actions)

    if not evidence.get("subgroup_evidence_complete", False):
        blockers.append("subgroup_evidence_incomplete")
    if not evidence.get("failure_simulation_complete", False):
        blockers.append("failure_simulation_incomplete")
    if not evidence.get("local_threshold_reviewed", False):
        blockers.append("local_threshold_not_reviewed")
    if not evidence.get("silent_pilot_completed", False):
        actions.extend(
            [
                "Run a time-limited silent pilot with no interruptive alerts.",
                "Review unstable alerts, workflow fit, drift, and alert burden with clinicians.",
            ]
        )
        return PassportDecision(RecommendedMode.silent_pilot, blockers, actions)

    approvals = evidence.get("approvals", {})
    if not approvals.get("ethics_data_use", False):
        blockers.append("ethics_or_data_use_approval_missing")
    if not approvals.get("clinical_owner", False):
        blockers.append("clinical_owner_missing")
    if not evidence.get("prospective_protocol_defined", False):
        blockers.append("prospective_protocol_missing")
    if blockers:
        actions.append("Keep the system silent until governance and pilot-protocol gates pass.")
        return PassportDecision(RecommendedMode.silent_pilot, blockers, actions)

    actions.extend(
        [
            "Consider a controlled pilot; this is not approval for autonomous clinical use.",
            "Maintain human review, rollback, drift monitoring, and prospective outcome evaluation.",
        ]
    )
    return PassportDecision(RecommendedMode.controlled_pilot_candidate, [], actions)


def generate_passport(evidence: dict[str, Any]) -> dict[str, Any]:
    decision = decide_mode(evidence)
    canonical = json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    return {
        "passport_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "site_id": evidence.get("site_id", "unknown-site"),
        "model_version": evidence.get("model_version"),
        "evidence_sha256": hashlib.sha256(canonical).hexdigest(),
        "recommended_mode": decision.mode.value,
        "blockers": decision.blockers,
        "next_actions": decision.next_actions,
        "sections": {
            "cohort_and_prevalence": evidence.get("cohort", {}),
            "discrimination_and_calibration": evidence.get("metrics", {}),
            "alert_burden": evidence.get("alert_burden", {}),
            "measurement_shift": evidence.get("measurement_shift", {}),
            "subgroups": evidence.get("subgroups", {}),
            "threshold_transfer": evidence.get("threshold_transfer", {}),
            "baseline_comparison": evidence.get("baseline_comparison", {}),
            "schema_and_units": evidence.get("schema", {}),
        },
        "limitations": [
            "A readiness recommendation is not regulatory or clinical approval.",
            "Retrospective performance does not establish clinical outcome improvement.",
            "Local silent/prospective evaluation is required before interruptive use.",
        ],
    }


def render_markdown(passport: dict[str, Any]) -> str:
    blockers = "\n".join(f"- {item}" for item in passport["blockers"]) or "- None recorded"
    actions = "\n".join(f"- {item}" for item in passport["next_actions"])
    limitations = "\n".join(f"- {item}" for item in passport["limitations"])
    return (
        f"# Hospital Readiness Passport — {passport['site_id']}\n\n"
        f"**Recommended mode:** {passport['recommended_mode']}\n\n"
        f"**Model:** {passport.get('model_version') or 'not specified'}\n\n"
        "## Blockers\n"
        f"{blockers}\n\n"
        "## Required next actions\n"
        f"{actions}\n\n"
        "## Limitations\n"
        f"{limitations}\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    evidence = yaml.safe_load(args.evidence.read_text())
    passport = generate_passport(evidence)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.with_suffix(".json").write_text(json.dumps(passport, indent=2) + "\n")
    args.out.with_suffix(".md").write_text(render_markdown(passport))
    print(json.dumps(passport, indent=2))


if __name__ == "__main__":
    main()
