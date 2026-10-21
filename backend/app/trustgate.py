"""Deterministic reliability policy between model scores and interruptions.

The frozen model remains unchanged. TrustGate decides whether a score is safe
enough to interrupt a clinician, needs data verification, or should abstain.
Its input-shift value is a transparent data-availability proxy, not a learned
out-of-distribution probability.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Iterable


class TrustState(str, Enum):
    alert = "alert"
    watch = "watch"
    verify_data = "verify_data"
    abstain = "abstain"


@dataclass(frozen=True)
class TrustAssessment:
    state: TrustState
    reasons: list[str]
    prediction_covered: bool
    input_shift_score: float
    alert_stability: float | None
    perturbation_max_delta: float | None
    perturbations_evaluated: int
    disagreement_validated: bool = False

    def as_dict(self) -> dict:
        result = asdict(self)
        result["state"] = self.state.value
        return result


def data_availability_shift(signal_freshness: dict[str, int | None]) -> float:
    """Return a bounded, interpretable proxy for required-vital availability."""
    required = ("HR", "SBP", "MAP", "O2Sat")
    values = [signal_freshness.get(signal) for signal in required]
    missing_fraction = sum(value is None for value in values) / len(values)
    stale_fraction = sum(value is not None and value > 120 for value in values) / len(values)
    return round(min(1.0, 0.7 * missing_fraction + 0.3 * stale_fraction), 6)


def assess_prediction(
    *,
    probability: float | None,
    risk_band: str,
    data_quality: str,
    data_freshness_minutes: int | None,
    signal_freshness: dict[str, int | None],
    high_risk_threshold: float,
    perturbed_probabilities: Iterable[float] = (),
    disagreement: float | None = None,
    disagreement_validated: bool = False,
) -> TrustAssessment:
    """Apply the preregistered V1 gate without changing model probabilities."""
    del disagreement  # Exposed separately, but not gated until it is validated.
    shift = data_availability_shift(signal_freshness)
    variants = [float(value) for value in perturbed_probabilities]
    if probability is None:
        return TrustAssessment(
            state=TrustState.abstain,
            reasons=["minimum_history_not_met"],
            prediction_covered=False,
            input_shift_score=shift,
            alert_stability=None,
            perturbation_max_delta=None,
            perturbations_evaluated=0,
            disagreement_validated=disagreement_validated,
        )

    baseline_alert = probability >= high_risk_threshold
    stability = (
        sum((value >= high_risk_threshold) == baseline_alert for value in variants) / len(variants)
        if variants
        else None
    )
    max_delta = max((abs(value - probability) for value in variants), default=None)
    reasons: list[str] = []

    if data_freshness_minutes is not None and data_freshness_minutes > 720:
        reasons.append("required_vitals_over_12h_old")
    if shift >= 0.8:
        reasons.append("severe_required_vital_shift")
    if reasons:
        return TrustAssessment(
            TrustState.abstain,
            reasons,
            False,
            shift,
            stability,
            max_delta,
            len(variants),
            disagreement_validated,
        )

    if data_quality != "ok":
        reasons.append(data_quality)
    if shift > 0.5:
        reasons.append("required_vital_availability_shift")
    if baseline_alert and stability is None:
        reasons.append("alert_stability_not_evaluated")
    elif baseline_alert and stability < 0.8:
        reasons.append("alert_unstable_under_perturbation")

    if reasons:
        state = TrustState.verify_data
    elif risk_band == "high_risk":
        state = TrustState.alert
        reasons = ["high_risk_score_passed_reliability_gate"]
    else:
        state = TrustState.watch
        reasons = ["passive_monitoring_no_interruptive_alert"]

    return TrustAssessment(
        state=state,
        reasons=reasons,
        prediction_covered=state not in {TrustState.abstain, TrustState.verify_data},
        input_shift_score=shift,
        alert_stability=stability,
        perturbation_max_delta=max_delta,
        perturbations_evaluated=len(variants),
        disagreement_validated=disagreement_validated,
    )
