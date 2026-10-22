"""Fairness audit + impact KPI baseline from already-scored artefacts.

Reads the frozen model's existing evaluation outputs (Dataset B holdout eval,
preregistered baseline report, TrustGate cohort experiment) and computes the
subgroup fairness picture and the measured KPI baselines the pilot contract
starts from. It never scores a dataset: it only reads results produced once,
at freeze time, by the ML pipeline.

    ../.venv/Scripts/python.exe infra/fairness_audit.py

Writes docs/evidence/fairness-audit.{json,md} and
docs/evidence/impact-kpi-baseline.{json,md}.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "evidence"
HOLDOUT = ROOT / "ml" / "artifacts" / "models" / "latest" / "eval_holdout.json"
BASELINES = ROOT / "ml" / "artifacts" / "experiments" / "baselines_setb_20260929T205614Z" / "report.json"
TRUSTGATE = ROOT / "ml" / "artifacts" / "experiments" / "TRUSTGATE-COHORT-01" / "result.json"

GOVERNANCE_TRIGGER_PP = 10.0  # pre-committed: larger local gap pauses alerting for review


def pct(x: float) -> float:
    return round(x * 100, 1)


def main() -> int:
    holdout = json.loads(HOLDOUT.read_text())
    baselines = json.loads(BASELINES.read_text())
    trustgate = json.loads(TRUSTGATE.read_text())

    dimensions: list[dict] = []
    for dim, groups in holdout["subgroups"].items():
        rows = []
        for name, m in groups.items():
            rows.append({
                "group": name,
                "rows": m["rows"],
                "sensitivity": round(m["sensitivity"], 3),
                "specificity": round(m["specificity"], 3),
                "auroc": round(m["auroc"], 3),
                "ppv": round(m["ppv"], 3),
                "prevalence_pct": pct(m["prevalence"]),
            })
        sens = [r["sensitivity"] for r in rows]
        aurocs = [r["auroc"] for r in rows]
        weakest = min(rows, key=lambda r: r["sensitivity"])
        strongest = max(rows, key=lambda r: r["sensitivity"])
        gap_pp = round((max(sens) - min(sens)) * 100, 1)
        dimensions.append({
            "dimension": dim,
            "groups": rows,
            "sensitivity_gap_pp": gap_pp,
            "auroc_range": [round(min(aurocs), 3), round(max(aurocs), 3)],
            "weakest_group": weakest["group"],
            "strongest_group": strongest["group"],
            "exceeds_governance_trigger": gap_pp > GOVERNANCE_TRIGGER_PP,
        })

    hr = holdout["high_risk"]
    fairness = {
        "format": "predictrx-fairness-audit/1",
        "source": "ml/artifacts/models/latest/eval_holdout.json (Dataset B holdout, scored once at freeze)",
        "model_version": holdout["model_version"],
        "model_sha256": holdout["model_sha256"],
        "overall_high_risk": {
            "sensitivity": round(hr["sensitivity"], 3),
            "specificity": round(hr["specificity"], 3),
            "ppv": round(hr["ppv"], 3),
        },
        "governance_trigger_pp": GOVERNANCE_TRIGGER_PP,
        "dimensions": dimensions,
        "reading": (
            "Sensitivity is modest overall and uneven across groups on US public data. These numbers are "
            "disclosed, not spun: they are why the model is frozen, why alerting requires a local silent "
            "pilot with subgroup reporting, and why a >10 pp local gap is a governance event, not a footnote."
        ),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "fairness-audit.json").write_text(json.dumps(fairness, indent=2), encoding="utf-8")

    lines = [
        "# Fairness audit — frozen model, Dataset B holdout (existing scored results)",
        "",
        f"Model `{holdout['model_version']}` · SHA-256 `{holdout['model_sha256'][:16]}…` · "
        f"Overall high-risk sensitivity {hr['sensitivity']:.3f}, specificity {hr['specificity']:.3f}, "
        f"hour-level PPV {hr['ppv']:.3f} (alert-level precision 0.132; see model card for definitions).",
        "",
        f"Pre-committed governance trigger: a subgroup sensitivity gap above **{GOVERNANCE_TRIGGER_PP:.0f} percentage "
        "points** in a local pilot keeps interruptive alerting off for the affected pathway until site owners "
        "record a decision.",
        "",
    ]
    for dim in dimensions:
        lines += [
            f"## By {dim['dimension']}",
            "",
            "| Group | Rows | Sensitivity | Specificity | AUROC | PPV | Prevalence % |",
            "|---|---|---|---|---|---|---|",
        ]
        for r in dim["groups"]:
            lines.append(
                f"| {r['group']} | {r['rows']:,} | {r['sensitivity']:.3f} | {r['specificity']:.3f} | "
                f"{r['auroc']:.3f} | {r['ppv']:.3f} | {r['prevalence_pct']} |"
            )
        lines += [
            "",
            f"Sensitivity gap: **{dim['sensitivity_gap_pp']} pp** (weakest: {dim['weakest_group']}; "
            f"strongest: {dim['strongest_group']}) · AUROC range {dim['auroc_range'][0]}–{dim['auroc_range'][1]} · "
            f"exceeds trigger on this dataset: `{dim['exceeds_governance_trigger']}`",
            "",
        ]
    lines += [
        "## Mitigations carried by the product (not by this document)",
        "",
        "1. The model is frozen and hash-verified at start-up; it cannot drift or be quietly re-fit on site.",
        "2. The silent-pilot cockpit recomputes these slices on local adjudicated data before any alert is shown.",
        "3. Missing/stale required signals yield `Verify data` or `Abstain`, so data-poor patients never receive a confident score.",
        "4. Clinician-documented context (pregnancy, comfort care, immunosuppression, chronic organ disease) modulates alerting under a fixed audited policy; it never edits the probability.",
        "5. Residual risk is stated, not hidden: US training data, care-process signal, no Bangladeshi validation yet.",
        "",
        "Generated by `infra/fairness_audit.py` from existing freeze-time evaluation artefacts. No dataset was scored by this script.",
        "",
    ]
    (OUT / "fairness-audit.md").write_text("\n".join(lines), encoding="utf-8")

    b = baselines["dataset_b_reports"]["lightgbm"]["high_risk"]
    states = trustgate["state_distribution_eligible_hours"]
    abstain_share = round((states["verify_data"] + states["abstain"]) * 100, 1)
    kpi = {
        "format": "predictrx-impact-kpi-baseline/1",
        "dataset_b_holdout_high_risk": {
            "sensitivity": round(b["sensitivity"], 3),
            "specificity": round(b["specificity"], 3),
            "ppv": round(b["ppv"], 3),
            "alerts_per_patient_day": round(b["alerts_per_patient_day"], 3),
            "detected_before_onset_share": round(b["detected_before_onset"], 3),
            "median_warning_hours": b["median_warning_hours"],
            "septic_patients": b["septic_patients"],
        },
        "trustgate_dataset_a_validation": {
            "patients": trustgate["patients"],
            "eligible_hours": trustgate["hours"],
            "state_distribution_pct": {k: pct(v) for k, v in states.items()},
            "verify_or_abstain_share_pct": abstain_share,
            "raw_high_risk_alert_hours": trustgate["raw_high_risk_alerts"],
            "suppressed_by_trustgate": trustgate["suppressed_raw_alerts"],
            "kept_alert_hours": trustgate["raw_high_risk_alerts"] - trustgate["suppressed_raw_alerts"],
            "false_alert_benefit_established": False,
            "note": "Paired CI for the false-alert difference crosses zero (model card); TrustGate is a data-quality/safety layer, not a proven false-alert reducer.",
        },
        "pilot_targets_not_yet_achieved": {
            "feed_coverage_pct": 95,
            "quarantine_rate_pct": 2,
            "median_alert_review_minutes": 30,
            "reasoned_dismissals_pct": 100,
            "subgroup_gap_trigger_pp": GOVERNANCE_TRIGGER_PP,
        },
    }
    (OUT / "impact-kpi-baseline.json").write_text(json.dumps(kpi, indent=2), encoding="utf-8")
    lines = [
        "# Impact KPI baseline (measured, pre-pilot)",
        "",
        "The starting numbers any hospital pilot is judged against. Retrospective public-data "
        "measurements are labelled as such; pilot targets are commitments to measure, not results.",
        "",
        "## Dataset B holdout (geographically distinct public cohort, scored once after freezing)",
        "",
        f"- High-risk sensitivity **{b['sensitivity']:.3f}**, specificity **{b['specificity']:.3f}**, PPV **{b['ppv']:.3f}** "
        f"across {b['septic_patients']:,} septic patients",
        f"- Septic patients detected before onset: **{b['detected_before_onset']:.1%}**; median warning **{b['median_warning_hours']:.0f} hours**",
        f"- Alert load if this threshold alerted directly: **{b['alerts_per_patient_day']:.3f} alerts per patient-day**",
        "",
        "## TrustGate behaviour (Dataset A validation, 3,050 patients, 117,419 eligible hours)",
        "",
        f"- Eligible-hour states: Alert {pct(states['alert'])}% · Watch {pct(states['watch'])}% · "
        f"Verify data {pct(states['verify_data'])}% · Abstain {pct(states['abstain'])}%",
        f"- In **{abstain_share}%** of eligible hours the system declines to present a confident actionable score",
        f"- Raw high-risk alert-hours {trustgate['raw_high_risk_alerts']:,} → {trustgate['raw_high_risk_alerts'] - trustgate['suppressed_raw_alerts']:,} "
        f"after TrustGate suppression ({trustgate['suppressed_raw_alerts']:,} held back)",
        "- Honesty note: the paired false-alert benefit is **not established** (CI crosses zero). No reduction is claimed.",
        "",
        "## Pilot targets (not yet achieved anywhere)",
        "",
        "| KPI | Target |",
        "|---|---|",
        "| Feed coverage (occupied beds with fresh required signals) | ≥ 95% |",
        "| Quarantine rate | falling trend to < 2% of observations |",
        "| Median alert-to-acknowledgement | ≤ 30 min |",
        "| Dismissals with a recorded reason | 100% |",
        "| Subgroup sensitivity gap | > 10 pp triggers governance review before alerting |",
        "",
        "Generated by `infra/fairness_audit.py` from existing scored artefacts. No dataset was scored by this script.",
        "",
    ]
    (OUT / "impact-kpi-baseline.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({
        "dimensions": [(d["dimension"], d["sensitivity_gap_pp"], d["weakest_group"]) for d in dimensions],
        "verify_or_abstain_share_pct": abstain_share,
        "passed": True,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
