"""Reproducible data-failure simulation for frozen sepsis models.

The simulator measures retrospective prediction/alert stability. It does not
estimate prevented harm and must not be used to tune on Dataset B.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable, Iterable

import joblib
import numpy as np
import pandas as pd

from predict_rx.data import load_patient_psv
from predict_rx.features.engineering import build_patient_features
from predict_rx.features.schema import LAB_COLS, MIN_HOURS_BEFORE_PRED, VITAL_COLS

ScoreFunction = Callable[[pd.DataFrame], np.ndarray]


class FailureScenario(str, Enum):
    vital_delay_2h = "vital_delay_2h"
    vital_delay_6h = "vital_delay_6h"
    vital_delay_12h = "vital_delay_12h"
    missing_lactate = "missing_lactate"
    missing_labs = "missing_labs"
    duplicate_observations = "duplicate_observations"
    late_arriving = "late_arriving"
    out_of_order = "out_of_order"
    sparse_lab_frequency = "sparse_lab_frequency"
    sensor_dropout = "sensor_dropout"


@dataclass(frozen=True)
class ScenarioMetrics:
    scenario: str
    rows: int
    prediction_coverage: float
    abstention_rate: float
    alert_flip_rate: float
    unstable_baseline_alerts: int
    baseline_alerts: int
    perturbed_alerts: int
    retained_positive_sensitivity: float | None
    false_alert_change: int | None
    median_first_alert_timing_change_hours: float | None


def perturb_patient(
    frame: pd.DataFrame,
    scenario: FailureScenario,
    *,
    seed: int = 42,
    time_column: str = "ICULOS",
) -> pd.DataFrame:
    """Apply a deterministic failure while retaining one canonical hourly row."""
    result = frame.copy(deep=True)
    vitals = [column for column in VITAL_COLS if column in result]
    labs = [column for column in LAB_COLS if column in result]

    if scenario.value.startswith("vital_delay_"):
        delay = int(scenario.value.removeprefix("vital_delay_").removesuffix("h"))
        result[vitals] = result[vitals].shift(delay)
    elif scenario == FailureScenario.missing_lactate and "Lactate" in result:
        result["Lactate"] = np.nan
    elif scenario == FailureScenario.missing_labs:
        result[labs] = np.nan
    elif scenario == FailureScenario.sparse_lab_frequency:
        rows_to_mask = np.arange(len(result)) % 3 != 0
        result.loc[rows_to_mask, labs] = np.nan
    elif scenario == FailureScenario.sensor_dropout:
        rng = np.random.default_rng(seed)
        mask = rng.random((len(result), len(vitals))) < 0.30
        result[vitals] = result[vitals].astype(float).mask(mask)
    elif scenario == FailureScenario.duplicate_observations:
        # Ingestion is idempotent by encounter/time/code; its canonical frame is unchanged.
        pass
    elif scenario in {FailureScenario.late_arriving, FailureScenario.out_of_order}:
        # Arrival order may change, but event-time canonicalization must restore chronology.
        if time_column in result:
            result = result.sample(frac=1, random_state=seed).sort_values(time_column, kind="stable")
    return result.reset_index(drop=True)


def evaluate_scenarios(
    patients: dict[str, pd.DataFrame],
    scorer: ScoreFunction,
    *,
    threshold: float,
    scenarios: Iterable[FailureScenario] = tuple(FailureScenario),
    target_column: str | None = "SepsisLabel",
    time_column: str = "ICULOS",
    seed: int = 42,
) -> list[ScenarioMetrics]:
    """Compare each perturbed view with the same patients' baseline predictions."""
    baselines = {patient_id: np.asarray(scorer(frame), dtype=float) for patient_id, frame in patients.items()}
    results: list[ScenarioMetrics] = []
    for scenario in scenarios:
        row_count = flips = unstable = baseline_alerts = perturbed_alerts = covered = 0
        positive_total = positive_alerted = false_change = 0
        has_targets = target_column is not None and all(target_column in frame for frame in patients.values())
        timing_changes: list[float] = []

        for index, (patient_id, frame) in enumerate(patients.items()):
            perturbed = perturb_patient(frame, scenario, seed=seed + index, time_column=time_column)
            baseline_score = baselines[patient_id]
            perturbed_score = np.asarray(scorer(perturbed), dtype=float)
            if len(baseline_score) != len(frame) or len(perturbed_score) != len(frame):
                raise ValueError("Scorer must return one score per canonical hourly row.")

            valid = np.isfinite(baseline_score) & np.isfinite(perturbed_score)
            baseline_flag = baseline_score >= threshold
            perturbed_flag = perturbed_score >= threshold
            row_count += len(frame)
            covered += int(valid.sum())
            flips += int((valid & (baseline_flag != perturbed_flag)).sum())
            unstable += int((valid & baseline_flag & ~perturbed_flag).sum())
            baseline_alerts += int((valid & baseline_flag).sum())
            perturbed_alerts += int((valid & perturbed_flag).sum())

            if has_targets:
                target = frame[target_column].fillna(0).to_numpy(dtype=int).astype(bool)
                positive_total += int((valid & target).sum())
                positive_alerted += int((valid & target & perturbed_flag).sum())
                baseline_false = int((valid & ~target & baseline_flag).sum())
                perturbed_false = int((valid & ~target & perturbed_flag).sum())
                false_change += perturbed_false - baseline_false

            if time_column in frame:
                times = frame[time_column].to_numpy(dtype=float)
                base_times = times[valid & baseline_flag]
                perturbed_times = times[valid & perturbed_flag]
                if len(base_times) and len(perturbed_times):
                    timing_changes.append(float(perturbed_times[0] - base_times[0]))

        coverage = covered / row_count if row_count else 0.0
        results.append(
            ScenarioMetrics(
                scenario=scenario.value,
                rows=row_count,
                prediction_coverage=coverage,
                abstention_rate=1.0 - coverage,
                alert_flip_rate=flips / covered if covered else 0.0,
                unstable_baseline_alerts=unstable,
                baseline_alerts=baseline_alerts,
                perturbed_alerts=perturbed_alerts,
                retained_positive_sensitivity=(
                    positive_alerted / positive_total if has_targets and positive_total else None
                ),
                false_alert_change=false_change if has_targets else None,
                median_first_alert_timing_change_hours=(
                    float(np.median(timing_changes)) if timing_changes else None
                ),
            )
        )
    return results


def bundle_scorer(bundle: dict) -> ScoreFunction:
    """Build the same causal feature scorer used by the backend."""
    model = bundle["model"]

    def score(frame: pd.DataFrame) -> np.ndarray:
        raw = frame.drop(columns=["SepsisLabel"], errors="ignore")
        features = build_patient_features(raw)
        features["hours_observed"] = np.arange(1, len(features) + 1)
        probabilities = model.predict_proba(features)[:, 1].astype(float)
        probabilities[: min(MIN_HOURS_BEFORE_PRED - 1, len(probabilities))] = np.nan
        return probabilities

    return score


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--patient-list", type=Path, required=True, help="Locked Dataset A patient IDs, one per line")
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(f"Refusing to overwrite immutable result: {args.out}")

    patient_ids = [
        line.strip()
        for line in args.patient_list.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    patients = {
        patient_id: load_patient_psv(args.raw_dir / f"{patient_id}.psv")
        for patient_id in patient_ids
    }
    bundle = joblib.load(args.model)
    metrics = evaluate_scenarios(
        patients,
        bundle_scorer(bundle),
        threshold=float(bundle["thresholds"]["high_risk"]),
        seed=args.seed,
    )
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "claim_scope": "retrospective alert-stability evaluation; no clinical-harm claim",
        "dataset": "Dataset A locked patient list",
        "patient_count": len(patients),
        "patient_list_sha256": _sha256(args.patient_list),
        "model_sha256": _sha256(args.model),
        "model_version": bundle["model_version"],
        "threshold": bundle["thresholds"]["high_risk"],
        "seed": args.seed,
        "scenarios": [asdict(metric) for metric in metrics],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
