"""S6 Transfer Shield — measurement habit fingerprint.

Compares current vital observation cadence (median inter-observation minutes
per required signal) against a commissioning baseline. A >2× shift fails the
readiness gate so interruptive alerts stay off until habits are re-checked.
"""

from __future__ import annotations

import statistics
from datetime import datetime
from typing import Any

from app.records import utc_now

REQUIRED_SIGNALS = ("HR", "SBP", "MAP", "O2Sat")
HABIT_CONFIG_KEY = "habit_fingerprint"
MAX_RATIO = 2.0
MIN_INTERVALS_PER_SIGNAL = 5


def _parse_ts(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _intervals_minutes(times: list[datetime]) -> list[float]:
    ordered = sorted(times)
    out: list[float] = []
    for previous, current in zip(ordered, ordered[1:]):
        delta = (current - previous).total_seconds() / 60.0
        if delta > 0:
            out.append(delta)
    return out


def compute_fingerprint(engine: Any) -> dict[str, Any]:
    """Build current site habit fingerprint from in-memory encounter observations."""
    per_signal: dict[str, list[float]] = {signal: [] for signal in REQUIRED_SIGNALS}
    encounters_sampled = 0
    for patient in engine.patients.values():
        if patient.status != "admitted":
            continue
        meta = getattr(patient, "observation_meta", None) or {}
        by_signal: dict[str, list[datetime]] = {signal: [] for signal in REQUIRED_SIGNALS}
        for (_hour, code), payload in meta.items():
            if code not in by_signal:
                continue
            stamp = _parse_ts(payload.get("source_time") or "")
            if stamp is not None:
                by_signal[code].append(stamp)
        used = False
        for signal, times in by_signal.items():
            intervals = _intervals_minutes(times)
            if intervals:
                per_signal[signal].extend(intervals)
                used = True
        if used:
            encounters_sampled += 1

    cadence: dict[str, dict[str, Any]] = {}
    for signal, intervals in per_signal.items():
        if len(intervals) < MIN_INTERVALS_PER_SIGNAL:
            cadence[signal] = {
                "median_interval_minutes": None,
                "intervals": len(intervals),
                "status": "insufficient",
            }
        else:
            cadence[signal] = {
                "median_interval_minutes": round(statistics.median(intervals), 2),
                "intervals": len(intervals),
                "status": "ok",
            }
    return {
        "computed_at": utc_now(),
        "encounters_sampled": encounters_sampled,
        "signals": cadence,
        "policy": f"Live mode requires a commissioning baseline; current median interval must stay within {MAX_RATIO}× of baseline per signal.",
    }


def compare_to_baseline(current: dict[str, Any], baseline: dict[str, Any] | None) -> dict[str, Any]:
    if not baseline or not isinstance(baseline.get("signals"), dict):
        return {
            "stable": False,
            "reason": "commissioning_baseline_missing",
            "shifts": [],
            "detail": "Record a commissioning habit fingerprint before authorizing live alerts.",
        }
    shifts: list[dict[str, Any]] = []
    for signal in REQUIRED_SIGNALS:
        now = (current.get("signals") or {}).get(signal) or {}
        was = (baseline.get("signals") or {}).get(signal) or {}
        current_med = now.get("median_interval_minutes")
        baseline_med = was.get("median_interval_minutes")
        if current_med is None or baseline_med is None or baseline_med <= 0:
            shifts.append({
                "signal": signal,
                "status": "insufficient",
                "baseline_minutes": baseline_med,
                "current_minutes": current_med,
                "ratio": None,
            })
            continue
        ratio = max(current_med / baseline_med, baseline_med / current_med)
        status = "shifted" if ratio > MAX_RATIO else "stable"
        shifts.append({
            "signal": signal,
            "status": status,
            "baseline_minutes": baseline_med,
            "current_minutes": current_med,
            "ratio": round(ratio, 3),
        })
    hard_shifts = [row for row in shifts if row["status"] == "shifted"]
    insufficient = [row for row in shifts if row["status"] == "insufficient"]
    if hard_shifts:
        return {
            "stable": False,
            "reason": "habit_shift_detected",
            "shifts": shifts,
            "detail": f"{len(hard_shifts)} signal(s) exceed {MAX_RATIO}× cadence shift vs commissioning.",
        }
    if insufficient:
        return {
            "stable": False,
            "reason": "insufficient_current_intervals",
            "shifts": shifts,
            "detail": "Not enough current intervals to confirm habit stability on every required signal.",
        }
    return {
        "stable": True,
        "reason": "within_tolerance",
        "shifts": shifts,
        "detail": f"All required signals within {MAX_RATIO}× of commissioning cadence.",
    }


def load_baseline(engine: Any) -> dict[str, Any] | None:
    return engine.records.load_config(HABIT_CONFIG_KEY)


def save_baseline(engine: Any, fingerprint: dict[str, Any], actor_id: str) -> dict[str, Any]:
    body = {
        **fingerprint,
        "recorded_by": actor_id,
        "recorded_at": utc_now(),
        "kind": "commissioning_baseline",
    }
    engine.records.save_config(HABIT_CONFIG_KEY, body, actor_id)
    return body


def assess(engine: Any) -> dict[str, Any]:
    current = compute_fingerprint(engine)
    baseline = load_baseline(engine)
    comparison = compare_to_baseline(current, baseline)
    return {
        "current": current,
        "baseline": baseline,
        "comparison": comparison,
        "gate_ready": bool(comparison["stable"]),
    }
