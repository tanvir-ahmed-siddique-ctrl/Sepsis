"""Physician-documented patient context around a frozen, population-level model.

The model only sees the PhysioNet variables. It cannot know that a patient has
chronic kidney disease, is immunosuppressed, is pregnant or is receiving
comfort care. This module never changes a probability. It applies a small,
versioned, deterministic policy after scoring:

* ``baseline`` conditions mark model drivers that may reflect the patient's
  chronic baseline (annotation only; acute-on-chronic deterioration still alerts);
* ``underestimate`` conditions warn that a low score may be falsely reassuring;
* ``out_of_scope`` conditions and comfort care keep alerts shadow-only, because
  the model was not developed for that population or goal of care;
* ``unmodelled`` conditions flag the encounter for subgroup review.

Context expires. When the review is overdue, shadow-only suppression lapses
and standard alerting resumes, so a forgotten entry cannot silence a patient.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

POLICY_VERSION = "clinical-context/v1"
GOALS = {
    "full_treatment": "Full active treatment",
    "limited_escalation": "Limited escalation (documented ceiling of care)",
    "comfort_care": "Comfort-focused care",
}


@dataclass(frozen=True)
class Condition:
    label: str
    effect: str
    signals: frozenset[str]
    note: str


CONDITIONS: dict[str, Condition] = {
    "ckd_dialysis": Condition(
        "Chronic kidney disease / maintenance dialysis",
        "baseline",
        frozenset({"Creatinine", "BUN", "bun_creatinine_ratio", "Potassium", "Phosphate", "HCO3", "Hgb", "Hct"}),
        "Raised creatinine or BUN may be the patient's chronic baseline. Compare with the known baseline; "
        "a new rise can still mean acute injury.",
    ),
    "chronic_liver_disease": Condition(
        "Chronic liver disease / cirrhosis",
        "baseline",
        frozenset({"Bilirubin_total", "Bilirubin_direct", "Platelets", "PTT", "AST", "Alkalinephos", "Fibrinogen"}),
        "Bilirubin, platelets and coagulation may be chronically abnormal; judge the change, not the level.",
    ),
    "chronic_respiratory_failure": Condition(
        "Chronic respiratory failure (COPD/ILD, home oxygen or chronic hypercapnia)",
        "baseline",
        frozenset({"O2Sat", "SaO2", "PaCO2", "HCO3", "FiO2", "Resp", "EtCO2"}),
        "Low SpO2 or high PaCO2 may be the patient's usual state; the documented target range applies.",
    ),
    "haematological_malignancy": Condition(
        "Haematological malignancy or marrow failure",
        "baseline",
        frozenset({"WBC", "Platelets", "Hgb", "Hct"}),
        "Blood counts may be disease- or chemotherapy-driven rather than infection-driven.",
    ),
    "immunosuppressed": Condition(
        "Immunosuppressed (neutropenia, chemotherapy, transplant, high-dose steroids, advanced HIV)",
        "underestimate",
        frozenset({"Temp", "WBC"}),
        "May not mount fever or leukocytosis. A low score can be falsely reassuring.",
    ),
    "rate_controlled": Condition(
        "Rate control or conduction limits (beta-blocker, pacemaker, heart block)",
        "underestimate",
        frozenset({"HR", "shock_index"}),
        "Heart-rate response is blunted, so tachycardia-driven risk may be under-called.",
    ),
    "pregnancy_postpartum": Condition(
        "Pregnancy or within 6 weeks postpartum",
        "out_of_scope",
        frozenset(),
        "Physiology differs and the training cohort did not identify obstetric patients; use the hospital's "
        "obstetric early-warning pathway.",
    ),
    "other_unmodelled": Condition(
        "Other significant condition not represented in model inputs",
        "unmodelled",
        frozenset(),
        "The model has no input for this condition. Rely on clinical judgement; the encounter is flagged for "
        "subgroup review.",
    ),
}


class ContextError(ValueError):
    pass


def catalogue() -> dict:
    return {
        "policy_version": POLICY_VERSION,
        "goals_of_care": [{"code": code, "label": label} for code, label in GOALS.items()],
        "conditions": [
            {"code": code, "label": item.label, "effect": item.effect, "note": item.note}
            for code, item in CONDITIONS.items()
        ],
    }


def build(
    *,
    goals_of_care: str,
    conditions: list[str],
    other_note: str | None,
    reason: str,
    review_hours: int,
    actor_id: str,
    actor_role: str,
    now: datetime | None = None,
) -> dict:
    if goals_of_care not in GOALS:
        raise ContextError(f"Unknown goals of care {goals_of_care!r}")
    unknown = sorted(set(conditions) - set(CONDITIONS))
    if unknown:
        raise ContextError(f"Unknown condition codes: {', '.join(unknown)}")
    note = (other_note or "").strip() or None
    codes = sorted(set(conditions))
    if "other_unmodelled" in codes and not note:
        raise ContextError("Describe the other condition in a short note")
    recorded = now or datetime.now(timezone.utc)
    return {
        "policy_version": POLICY_VERSION,
        "goals_of_care": goals_of_care,
        "conditions": codes,
        "other_note": note,
        "reason": reason.strip(),
        "recorded_by": actor_id,
        "recorded_role": actor_role,
        "recorded_at": recorded.isoformat(),
        "review_due": (recorded + timedelta(hours=review_hours)).isoformat(),
    }


def _overdue(context: dict, now: datetime) -> bool:
    return now >= datetime.fromisoformat(context["review_due"])


def alert_policy(context: dict | None, now: datetime | None = None) -> tuple[str, str | None]:
    """Return ("standard" | "shadow_only", reason) for interruptive alerting."""
    if not context or _overdue(context, now or datetime.now(timezone.utc)):
        return "standard", None
    if context["goals_of_care"] == "comfort_care":
        return "shadow_only", "comfort_care_documented"
    out_of_scope = [code for code in context["conditions"] if CONDITIONS[code].effect == "out_of_scope"]
    if out_of_scope:
        return "shadow_only", f"outside_validated_population:{','.join(out_of_scope)}"
    return "standard", None


def subgroups(context: dict | None) -> list[str]:
    if not context:
        return []
    groups = [f"goals:{context['goals_of_care']}"]
    groups.extend(f"condition:{code}" for code in context["conditions"])
    return groups


def evaluate(
    context: dict | None,
    *,
    factors: list[dict] | None = None,
    risk_band: str | None = None,
    now: datetime | None = None,
) -> dict:
    """Annotate the latest score with context-derived cautions; never edits the score."""
    now = now or datetime.now(timezone.utc)
    policy, policy_reason = alert_policy(context, now)
    if not context:
        return {
            "documented": False,
            "policy_version": POLICY_VERSION,
            "alert_policy": policy,
            "alert_policy_reason": None,
            "cautions": [],
            "driver_annotations": [],
            "subgroups": [],
        }

    overdue = _overdue(context, now)
    cautions: list[str] = []
    if overdue:
        cautions.append("Context review is overdue: any alert suppression has lapsed. Re-confirm or update it.")
    if context["goals_of_care"] == "limited_escalation":
        cautions.append("A ceiling of care is documented. Align any response with the patient's goals of care.")
    if context["goals_of_care"] == "comfort_care" and not overdue:
        cautions.append("Comfort-focused care: interruptive alerts are paused; scores are recorded silently.")

    raising = [factor for factor in (factors or []) if factor.get("direction") == "raises"]
    annotations: list[dict] = []
    for code in context["conditions"]:
        condition = CONDITIONS[code]
        if condition.effect == "baseline":
            for factor in raising:
                if factor["feature"] in condition.signals:
                    annotations.append({
                        "feature": factor["feature"],
                        "condition": code,
                        "effect": "possible_chronic_baseline",
                    })
        elif condition.effect == "underestimate":
            message = f"{condition.label}: {condition.note}"
            if risk_band in {"stable", "watch"}:
                message += " Do not treat the current low or moderate score as reassurance."
            cautions.append(message)
        elif condition.effect == "out_of_scope" and not overdue:
            cautions.append(f"{condition.label}: {condition.note} Alerts are shadow-only for this encounter.")
        elif condition.effect == "unmodelled":
            cautions.append(f"{context.get('other_note') or condition.label}: {condition.note}")

    top_raising = {factor["feature"] for factor in raising[:3]}
    explained = {item["feature"] for item in annotations if item["feature"] in top_raising}
    if len(explained) >= 2:
        cautions.append(
            "Most top risk drivers overlap the documented chronic baseline "
            f"({', '.join(sorted(explained))}). Compare with the patient's own baseline; "
            "acute-on-chronic deterioration remains possible, so the alert is not suppressed."
        )

    return {
        "documented": True,
        "policy_version": POLICY_VERSION,
        "goals_of_care": context["goals_of_care"],
        "goals_label": GOALS[context["goals_of_care"]],
        "conditions": [
            {"code": code, "label": CONDITIONS[code].label, "effect": CONDITIONS[code].effect}
            for code in context["conditions"]
        ],
        "other_note": context.get("other_note"),
        "reason": context["reason"],
        "recorded_by": context["recorded_by"],
        "recorded_role": context["recorded_role"],
        "recorded_at": context["recorded_at"],
        "review_due": context["review_due"],
        "review_overdue": overdue,
        "alert_policy": policy,
        "alert_policy_reason": policy_reason,
        "cautions": cautions,
        "driver_annotations": annotations,
        "subgroups": subgroups(context),
    }
