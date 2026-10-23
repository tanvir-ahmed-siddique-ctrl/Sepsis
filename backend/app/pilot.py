"""Silent-pilot evidence: local metrics, threshold simulation, readiness gates, exports.

Everything here is read-only with respect to the model: thresholds can be *simulated*
on recorded predictions, but the frozen model and its validation-selected thresholds
are never changed by this module.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml

from app.auth import production_security_ready
from app.core.config import settings
from app.habit_fingerprint import assess as assess_habit
from app.records import (
    RETENTION_TABLES,
    connector_events,
    connector_spool,
    export_log,
    feedback_records,
    outcome_records,
    prediction_records,
    utc_now,
)

REQUIRED_SIGNALS = ("HR", "SBP", "MAP", "O2Sat")
AGE_BANDS = ((18, 44, "18-44"), (45, 64, "45-64"), (65, 79, "65-79"), (80, 200, "80+"))
CALIBRATION_EDGES = (0.0, 0.02, 0.05, 0.1, 0.2, 1.0000001)
DEFAULT_SIMULATION_GRID = (0.02, 0.03, 0.05, 0.08, 0.1, 0.15, 0.2, 0.3)
PILOT_MODES = {"silent", "live-disabled", "live"}


def _ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _median(values: Iterable[float]) -> float | None:
    values = list(values)
    return round(statistics.median(values), 3) if values else None


def _quantile(values: Iterable[float], q: float) -> float | None:
    values = sorted(values)
    if not values:
        return None
    index = min(len(values) - 1, max(0, int(round(q * (len(values) - 1)))))
    return round(values[index], 3)


def _rate(numerator: float, denominator: float, digits: int = 4) -> float | None:
    return round(numerator / denominator, digits) if denominator else None


def latest_predictions(engine: Any, unit_id: str | None = None) -> list[dict[str, Any]]:
    conditions = [prediction_records.c.unit_id == unit_id] if unit_id else []
    rows = engine.records.select(prediction_records, *conditions)
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (row["encounter_key"], row["source_time"])
        if key not in latest or row["input_revision"] > latest[key]["input_revision"]:
            latest[key] = row
    ordered = sorted(latest.values(), key=lambda row: (row["encounter_key"], row["source_time"]))
    for row in ordered:
        row["details"] = json.loads(row["payload"])
    return ordered


def latest_outcomes(engine: Any) -> dict[str, dict[str, Any]]:
    rows = engine.records.select(outcome_records, order_by=outcome_records.c.recorded_at)
    return {row["encounter_key"]: row for row in rows}


def _alert_starts(rows: list[dict[str, Any]]) -> dict[str, list[datetime]]:
    starts: dict[str, dict[str, datetime]] = defaultdict(dict)
    for row in rows:
        if row["alert_id"]:
            time_ = _ts(row["source_time"])
            current = starts[row["encounter_key"]].get(row["alert_id"])
            if current is None or time_ < current:
                starts[row["encounter_key"]][row["alert_id"]] = time_
    return {key: sorted(values.values()) for key, values in starts.items()}


def _episode_starts(rows: list[dict[str, Any]], threshold: float) -> dict[str, list[datetime]]:
    starts: dict[str, list[datetime]] = defaultdict(list)
    previous: dict[str, bool] = {}
    for row in rows:
        flagged = (
            row["probability"] is not None
            and row["probability"] >= threshold
            and row["data_quality"] == "ok"
        )
        key = row["encounter_key"]
        if flagged and not previous.get(key, False):
            starts[key].append(_ts(row["source_time"]))
        previous[key] = flagged
    return starts


def _detection(
    starts: dict[str, list[datetime]],
    outcomes: dict[str, dict[str, Any]],
    encounters: set[str],
) -> dict[str, Any]:
    before = timedelta(hours=settings.label_onset_window_before_hours)
    after = timedelta(hours=settings.label_onset_window_after_hours)
    septic = [o for key, o in outcomes.items() if key in encounters and o["adjudication"] == "sepsis" and o["onset_time"]]
    negative = [o for key, o in outcomes.items() if key in encounters and o["adjudication"] == "no_sepsis"]
    detected = 0
    leads: list[float] = []
    for outcome in septic:
        onset = _ts(outcome["onset_time"])
        in_window = [t for t in starts.get(outcome["encounter_key"], []) if onset - before <= t <= onset + after]
        if in_window:
            detected += 1
            leads.append((onset - min(in_window)).total_seconds() / 3600)
    false_encounters = sum(1 for outcome in negative if starts.get(outcome["encounter_key"]))
    return {
        "adjudicated_sepsis": len(septic),
        "adjudicated_no_sepsis": len(negative),
        "detected": detected,
        "sensitivity": _rate(detected, len(septic)),
        "median_lead_hours": _median(leads),
        "no_sepsis_encounters_with_alert": false_encounters,
        "false_alert_encounter_rate": _rate(false_encounters, len(negative)),
        "window": f"{settings.label_onset_window_before_hours} h before to "
                  f"{settings.label_onset_window_after_hours} h after adjudicated onset",
    }


def _calibration(rows: list[dict[str, Any]], outcomes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    labelled: list[tuple[float, int]] = []
    for row in rows:
        outcome = outcomes.get(row["encounter_key"])
        if row["probability"] is None or outcome is None or outcome["adjudication"] == "indeterminate":
            continue
        if outcome["adjudication"] == "sepsis":
            if not outcome["onset_time"]:
                continue
            label = int(_ts(row["source_time"]) >= _ts(outcome["onset_time"]) - timedelta(hours=6))
        else:
            label = 0
        labelled.append((float(row["probability"]), label))
    positives = sum(label for _, label in labelled)
    if len(labelled) < 20 or positives == 0:
        return {
            "status": "insufficient_labels",
            "labelled_hours": len(labelled),
            "positive_hours": positives,
            "label_definition": "Challenge-compatible: positive from 6 h before adjudicated onset onward.",
        }
    mean_predicted = sum(p for p, _ in labelled) / len(labelled)
    prevalence = positives / len(labelled)
    bins = []
    for low, high in zip(CALIBRATION_EDGES, CALIBRATION_EDGES[1:]):
        members = [(p, y) for p, y in labelled if low <= p < high]
        if members:
            bins.append({
                "range": [low, min(high, 1.0)],
                "n": len(members),
                "mean_predicted": round(sum(p for p, _ in members) / len(members), 4),
                "observed_rate": round(sum(y for _, y in members) / len(members), 4),
            })
    return {
        "status": "computed",
        "labelled_hours": len(labelled),
        "positive_hours": positives,
        "prevalence": round(prevalence, 4),
        "mean_predicted": round(mean_predicted, 4),
        "calibration_in_the_large": round(mean_predicted - prevalence, 4),
        "brier": round(sum((p - y) ** 2 for p, y in labelled) / len(labelled), 5),
        "bins": bins,
        "label_definition": "Challenge-compatible: positive from 6 h before adjudicated onset onward.",
    }


def _group_metrics(rows: list[dict[str, Any]], outcomes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    encounters = {row["encounter_key"] for row in rows}
    alerts = {row["alert_id"] for row in rows if row["alert_id"]}
    covered = sum(row["trust_state"] in {"alert", "watch"} for row in rows)
    detection = _detection(_alert_starts(rows), outcomes, encounters)
    return {
        "encounters": len(encounters),
        "patient_hours": len(rows),
        "coverage": _rate(covered, len(rows)),
        "alerts": len(alerts),
        "alerts_per_100_patient_hours": _rate(100 * len(alerts), len(rows), 3),
        "adjudicated_sepsis": detection["adjudicated_sepsis"],
        "sensitivity": detection["sensitivity"],
    }


def _age_band(age: int | None) -> str:
    if age is None:
        return "unknown"
    return next((label for low, high, label in AGE_BANDS if low <= age <= high), "unknown")


def compute_metrics(
    engine: Any,
    unit_id: str | None = None,
    thresholds: list[float] | None = None,
    pilot_only: bool = False,
) -> dict[str, Any]:
    rows = latest_predictions(engine, unit_id)
    if pilot_only:
        rows = [row for row in rows if row["site_mode"] in PILOT_MODES and row["ingest_mode"] == "realtime"]
    outcomes = latest_outcomes(engine)
    encounters = {row["encounter_key"] for row in rows}
    hours = len(rows)
    trust_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        trust_counts[row["trust_state"]] += 1
    scored = [row for row in rows if row["probability"] is not None]

    missing = {signal: 0 for signal in REQUIRED_SIGNALS}
    stale = {signal: 0 for signal in REQUIRED_SIGNALS}
    for row in rows:
        freshness = row["details"].get("signal_freshness", {})
        for signal in REQUIRED_SIGNALS:
            value = freshness.get(signal)
            if value is None:
                missing[signal] += 1
            elif value > 120:
                stale[signal] += 1

    alert_ids = {row["alert_id"]: row["alert_disposition"] for row in rows if row["alert_id"]}
    shadow = sum(1 for disposition in alert_ids.values() if disposition == "shadow")
    scored_times = [_ts(row["scored_at"]) for row in rows]
    pilot_days = (max(scored_times) - min(scored_times)).total_seconds() / 86400 if scored_times else 0.0

    with engine.lock:
        api_keys = {key for key, patient in engine.patients.items() if patient.source_mode == "api"}
        api_alerts = [
            alert for alert in engine.alerts.values()
            if alert.get("encounter_key") in api_keys and (unit_id is None or alert.get("unit_id") == unit_id)
        ]
    ack_minutes = []
    for alert in api_alerts:
        if alert.get("actions") and alert.get("raised_at"):
            first = _ts(alert["actions"][0]["at"])
            ack_minutes.append(max(0.0, (first - _ts(alert["raised_at"])).total_seconds() / 60))
    sla = settings.alert_review_sla_minutes
    now = datetime.now(timezone.utc)
    overdue_open = sum(
        1 for alert in api_alerts
        if alert["status"] == "open" and alert.get("raised_at")
        and (now - _ts(alert["raised_at"])).total_seconds() / 60 > sla
    )

    feedback = engine.records.select(feedback_records)
    feedback_counts: dict[str, int] = defaultdict(int)
    workflow_counts: dict[str, int] = defaultdict(int)
    for item in feedback:
        if item["encounter_key"] in encounters or not encounters:
            feedback_counts[item["usefulness"]] += 1
            for tag in json.loads(item["workflow"]):
                workflow_counts[tag] += 1

    events = engine.records.select(connector_events)
    realtime_events = [e for e in events if not e["backfill"] and e["status"] in {"processed", "partial", "replayed"}]

    sexes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    ages: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        sexes[row["sex"] or "unknown"].append(row)
        ages[_age_band(row["age"])].append(row)

    grid = sorted(set(thresholds or DEFAULT_SIMULATION_GRID) | set(engine.thresholds.values()))
    simulation = []
    for threshold in grid:
        starts = _episode_starts(rows, threshold)
        episodes = sum(len(values) for values in starts.values())
        flagged_hours = sum(
            1 for row in rows
            if row["probability"] is not None and row["probability"] >= threshold and row["data_quality"] == "ok"
        )
        detection = _detection(starts, outcomes, encounters)
        simulation.append({
            "threshold": round(threshold, 4),
            "is_current_high_risk": abs(threshold - engine.thresholds["high_risk"]) < 1e-9,
            "is_current_watch": abs(threshold - engine.thresholds["watch"]) < 1e-9,
            "flagged_hour_rate": _rate(flagged_hours, hours),
            "episodes": episodes,
            "episodes_per_100_patient_hours": _rate(100 * episodes, hours, 3),
            "sensitivity": detection["sensitivity"],
            "false_alert_encounter_rate": detection["false_alert_encounter_rate"],
        })

    daily: dict[str, dict[str, Any]] = {}
    for row in rows:
        day = row["source_time"][:10]
        bucket = daily.setdefault(day, {"date": day, "hours": 0, "prob_sum": 0.0, "prob_n": 0,
                                        "shift_sum": 0.0, "missing_required": 0, "alerts": set()})
        bucket["hours"] += 1
        if row["probability"] is not None:
            bucket["prob_sum"] += row["probability"]
            bucket["prob_n"] += 1
        bucket["shift_sum"] += row["input_shift"] or 0.0
        freshness = row["details"].get("signal_freshness", {})
        if any(freshness.get(signal) is None for signal in REQUIRED_SIGNALS):
            bucket["missing_required"] += 1
        if row["alert_id"]:
            bucket["alerts"].add(row["alert_id"])
    quarantine_by_day: dict[str, int] = defaultdict(int)
    for event in events:
        quarantine_by_day[event["received_at"][:10]] += event["quarantined"]
    trends = [
        {
            "date": bucket["date"],
            "patient_hours": bucket["hours"],
            "mean_probability": _rate(bucket["prob_sum"], bucket["prob_n"]),
            "mean_input_shift": _rate(bucket["shift_sum"], bucket["hours"]),
            "missing_required_rate": _rate(bucket["missing_required"], bucket["hours"]),
            "alerts": len(bucket["alerts"]),
            "quarantined_received_that_day": quarantine_by_day.get(bucket["date"], 0),
        }
        for bucket in sorted(daily.values(), key=lambda item: item["date"])
    ]

    return {
        "generated_at": utc_now(),
        "scope": {"unit_id": unit_id, "pilot_only": pilot_only},
        "site_mode": engine.site.state.effective_mode,
        "model_version": engine.model_version,
        "model_hash": engine.model_hash,
        "thresholds": engine.thresholds,
        "volume": {
            "encounters": len(encounters),
            "patient_hours": hours,
            "scored_hours": len(scored),
            "pilot_days": round(pilot_days, 2),
            "first_scored_at": min(scored_times).isoformat() if scored_times else None,
            "last_scored_at": max(scored_times).isoformat() if scored_times else None,
        },
        "coverage": {
            "covered_rate": _rate(trust_counts["alert"] + trust_counts["watch"], hours),
            "trust_states": dict(trust_counts),
            "insufficient_history_rate": _rate(sum(r["risk_band"] == "insufficient_data" for r in rows), hours),
        },
        "missingness": {
            signal: {"missing_rate": _rate(missing[signal], hours), "stale_over_2h_rate": _rate(stale[signal], hours)}
            for signal in REQUIRED_SIGNALS
        },
        "latency": {
            "median_processing_ms": _median(e["processing_ms"] for e in realtime_events if e["processing_ms"] is not None),
            "p95_processing_ms": _quantile((e["processing_ms"] for e in realtime_events if e["processing_ms"] is not None), 0.95),
            "median_source_lag_minutes": _median(e["lag_seconds"] / 60 for e in realtime_events if e["lag_seconds"] is not None),
            "p95_source_lag_minutes": _quantile((e["lag_seconds"] / 60 for e in realtime_events if e["lag_seconds"] is not None), 0.95),
        },
        "alert_burden": {
            "alerts": len(alert_ids),
            "shadow_alerts": shadow,
            "interruptive_alerts": len(alert_ids) - shadow,
            "alerts_per_100_patient_hours": _rate(100 * len(alert_ids), hours, 3),
            "alerts_per_encounter_day": _rate(len(alert_ids), hours / 24 if hours else 0, 3),
        },
        "detection": _detection(_alert_starts(rows), outcomes, encounters),
        "calibration": _calibration(rows, outcomes),
        "subgroups": {
            "sex": {key: _group_metrics(value, outcomes) for key, value in sorted(sexes.items())},
            "age_band": {key: _group_metrics(value, outcomes) for key, value in sorted(ages.items())},
        },
        "review": {
            "sla_minutes": sla,
            "acknowledged_alerts": len(ack_minutes),
            "median_minutes_to_first_action": _median(ack_minutes),
            "p90_minutes_to_first_action": _quantile(ack_minutes, 0.9),
            "within_sla_rate": _rate(sum(m <= sla for m in ack_minutes), len(ack_minutes)),
            "open_past_sla": overdue_open,
        },
        "feedback": {"usefulness": dict(feedback_counts), "workflow": dict(workflow_counts), "total": sum(feedback_counts.values())},
        "threshold_simulation": {
            "note": "Simulation on recorded predictions only. The frozen model and its validation-selected "
                    "thresholds are unchanged; perturbation stability is not re-simulated.",
            "rows": simulation,
        },
        "trends": trends,
    }


def _gate(gate: str, passed: bool, value: Any, target: Any, detail: str) -> dict[str, Any]:
    return {"gate": gate, "passed": bool(passed), "value": value, "target": target, "detail": detail}


def evaluate_gates(engine: Any, connector_health: list[dict[str, Any]]) -> list[dict[str, Any]]:
    metrics = compute_metrics(engine, pilot_only=True)
    evidence = yaml.safe_load(Path(settings.passport_evidence_path).read_text())
    local_evidence = bool(evidence.get("local_site_evidence", False))
    volume = metrics["volume"]
    detection = metrics["detection"]
    burden = metrics["alert_burden"]["alerts_per_100_patient_hours"]
    connected = [item for item in connector_health if item["state"] != "never_connected"]
    feeds_ok = bool(connected) and all(item["state"] in {"healthy", "degraded"} for item in connected)
    adjudicated = detection["adjudicated_sepsis"] + detection["adjudicated_no_sepsis"]
    sensitivity = detection["sensitivity"]
    habit = assess_habit(engine)
    habit_ok = bool(habit["gate_ready"])
    return [
        _gate("local_retrospective_validation", local_evidence, local_evidence, True,
              "A local retrospective validation must be recorded in the site passport evidence."),
        _gate("silent_pilot_duration", volume["pilot_days"] >= settings.pilot_min_days,
              volume["pilot_days"], settings.pilot_min_days, "Days of real-time silent scoring."),
        _gate("silent_pilot_encounters", volume["encounters"] >= settings.pilot_min_encounters,
              volume["encounters"], settings.pilot_min_encounters, "Distinct encounters scored in silent mode."),
        _gate("adjudicated_outcomes", adjudicated >= settings.pilot_min_adjudicated,
              adjudicated, settings.pilot_min_adjudicated, "Chart-review adjudications (sepsis or no sepsis)."),
        _gate("sensitivity_floor",
              sensitivity is not None and detection["adjudicated_sepsis"] >= 10 and sensitivity >= settings.pilot_min_sensitivity,
              sensitivity, settings.pilot_min_sensitivity,
              "Shadow-alert sensitivity on ≥10 adjudicated sepsis encounters."),
        _gate("alert_burden_budget", burden is not None and burden <= settings.pilot_max_alerts_per_100h,
              burden, settings.pilot_max_alerts_per_100h, "Shadow alerts per 100 patient-hours."),
        _gate("feeds_healthy", feeds_ok, [f"{c['connector']}:{c['state']}" for c in connected], "healthy",
              "Every connected feed is healthy or degraded, none stale or circuit-open."),
        _gate("measurement_habit_stable", habit_ok, habit["comparison"].get("reason"), "within_tolerance",
              habit["comparison"].get("detail") or "S6 habit fingerprint vs commissioning baseline."),
        _gate("governance_signoff", engine.site.state.governance_signoff is not None,
              engine.site.state.governance_signoff, "recorded", "Clinical governance / ethics approval recorded."),
        _gate("production_security", production_security_ready(), production_security_ready(), True,
              "DEMO_MODE=false with non-default secrets or OIDC."),
    ]


def _pseudonym(value: str | None) -> str | None:
    if value is None:
        return None
    return hmac.new(settings.export_salt.encode(), value.encode(), hashlib.sha256).hexdigest()[:20]


def build_export(engine: Any, actor: Any, reason: str, unit_id: str | None = None) -> dict[str, Any]:
    rows = latest_predictions(engine, unit_id)
    outcomes = engine.records.select(outcome_records, order_by=outcome_records.c.recorded_at)
    feedback = engine.records.select(feedback_records, order_by=feedback_records.c.recorded_at)
    events = engine.records.select(connector_events, order_by=connector_events.c.received_at)
    keys = {row["encounter_key"] for row in rows}
    body = {
        "export_version": "1.0.0",
        "created_at": utc_now(),
        "created_by": actor.user_id,
        "site_id": engine.site.state.site_id,
        "site_mode": engine.site.state.effective_mode,
        "model_version": engine.model_version,
        "model_hash": engine.model_hash,
        "pseudonymisation": "HMAC-SHA256(export_salt, id)[:20]; free-text notes and comments excluded",
        "predictions": [
            {
                "encounter": _pseudonym(row["encounter_key"]),
                "unit_id": row["unit_id"],
                "source_time": row["source_time"],
                "scored_at": row["scored_at"],
                "hour": row["hour"],
                "probability": row["probability"],
                "risk_band": row["risk_band"],
                "trust_state": row["trust_state"],
                "data_quality": row["data_quality"],
                "freshness_minutes": row["freshness_minutes"],
                "input_shift": row["input_shift"],
                "site_mode": row["site_mode"],
                "ingest_mode": row["ingest_mode"],
                "alert": _pseudonym(row["alert_id"]),
                "alert_disposition": row["alert_disposition"],
                "age_band": _age_band(row["age"]),
                "sex": row["sex"],
            }
            for row in rows
        ],
        "outcomes": [
            {
                "encounter": _pseudonym(item["encounter_key"]),
                "adjudication": item["adjudication"],
                "onset_time": item["onset_time"],
                "criteria": item["criteria"],
                "recorded_at": item["recorded_at"],
            }
            for item in outcomes
            if unit_id is None or item["encounter_key"] in keys
        ],
        "feedback": [
            {
                "encounter": _pseudonym(item["encounter_key"]),
                "alert": _pseudonym(item["alert_id"]),
                "role": item["role"],
                "usefulness": item["usefulness"],
                "workflow": json.loads(item["workflow"]),
                "recorded_at": item["recorded_at"],
            }
            for item in feedback
            if unit_id is None or item["encounter_key"] in keys
        ],
        "connector_events": [
            {key: event[key] for key in ("connector", "received_at", "status", "received", "accepted",
                                         "quarantined", "duplicates", "lag_seconds", "processing_ms", "backfill")}
            for event in events
        ],
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    counts = {name: len(body[name]) for name in ("predictions", "outcomes", "feedback", "connector_events")}
    export_id = f"export-{digest[:16]}"
    engine.records.insert(
        export_log,
        {
            "export_id": export_id,
            "created_at": body["created_at"],
            "created_by": actor.user_id,
            "sha256": digest,
            "counts": json.dumps(counts),
            "reason": reason,
        },
    )
    with engine.lock:
        engine._require_writable()
        engine._log("pilot_export_created", {
            "export_id": export_id, "sha256": digest, "actor": actor.user_id,
            "actor_role": actor.role, "reason": reason, "counts": counts, "unit_id": unit_id,
        })
    return {"export_id": export_id, "sha256": digest, "counts": counts, "export": body}


def apply_retention(engine: Any, actor: Any) -> dict[str, int]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=settings.retention_days)).isoformat()
    deleted: dict[str, int] = {}
    with engine.lock:
        engine._require_writable()
        for name, (table, column) in RETENTION_TABLES.items():
            deleted[name] = engine.records.delete(table, table.c[column] < cutoff)
        deleted["connector_spool"] = engine.records.delete(
            connector_spool, connector_spool.c.status != "pending", connector_spool.c.updated_at < cutoff
        )
        engine._log("retention_applied", {
            "actor": actor.user_id, "actor_role": actor.role,
            "retention_days": settings.retention_days, "cutoff": cutoff, "deleted": deleted,
        })
    return deleted
