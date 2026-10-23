"""Select replay cases for the ICU dashboard from Dataset A's internal *test* split.

Selection is rule-based and recorded in the manifest so the demo is not cherry-picked:
  - typical detections: septic patients whose high-risk warning time is closest to the median
  - one missed septic patient (no alert before onset)
  - one non-septic patient with a false alert
  - stable non-septic patients with no alert
Raw PSV files are copied under pseudonymous bed IDs; the output folder is gitignored.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from predict_rx.eval.metrics import DT_EARLY, patient_onsets
from predict_rx.features.schema import MIN_HOURS_BEFORE_PRED


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path, default=Path("data/processed/features_setA.parquet"))
    parser.add_argument("--raw", type=Path, default=Path("data/raw/training_setA"))
    parser.add_argument("--model-dir", type=Path, default=Path("artifacts/models/latest"))
    parser.add_argument("--out", type=Path, default=Path("../demo/cases"))
    parser.add_argument("--typical", type=int, default=8, help="Typical-detection septic beds (default 8 → denser ICU board)")
    parser.add_argument("--stable", type=int, default=14, help="Stable non-septic beds (default 14; +missed +false_alert ≈ 24 total)")
    args = parser.parse_args()

    bundle = joblib.load(args.model_dir / "model.joblib")
    df = pd.read_parquet(args.features)
    df = df[df["split"] == "test"].reset_index(drop=True)
    eligible = (df["hours_observed"] >= MIN_HOURS_BEFORE_PRED).to_numpy()
    prob = bundle["model"].predict_proba(df)[:, 1]
    high = (prob >= bundle["thresholds"]["high_risk"]) & eligible

    pos = df.groupby("patient_id", sort=False).cumcount()
    stay = df.groupby("patient_id").size()
    onset = patient_onsets(df)
    first_alert = pos[high].groupby(df["patient_id"][high]).min()
    rng = np.random.default_rng(7)

    septic = onset.index[(stay.reindex(onset.index) >= 20) & (onset >= 10)]
    lead = (onset.reindex(septic) - first_alert.reindex(septic))
    detected = lead[(lead >= 0) & (lead <= -DT_EARLY)]
    median_lead = float(detected.median())
    typical = (detected - median_lead).abs().sort_values().index[: args.typical].tolist()
    missed_pool = lead[lead.isna() | (lead < 0)].index.tolist()
    missed = rng.choice(missed_pool, 1).tolist() if missed_pool else []

    non_septic = stay.index.difference(onset.index)
    non_septic = non_septic[stay.reindex(non_septic) >= 24]
    false_alert_pool = non_septic.intersection(first_alert.index).tolist()
    false_alert = rng.choice(false_alert_pool, 1).tolist() if false_alert_pool else []
    quiet = non_septic.difference(first_alert.index).tolist()
    stable = rng.choice(quiet, args.stable, replace=False).tolist()

    chosen = (
        [(p, "typical_detection") for p in typical]
        + [(p, "missed_detection") for p in missed]
        + [(p, "false_alert") for p in false_alert]
        + [(p, "stable") for p in stable]
    )

    if args.out.exists():
        shutil.rmtree(args.out)
    args.out.mkdir(parents=True)
    cases = []
    for i, (pid, kind) in enumerate(chosen, start=1):
        bed = f"BED-{i:02d}"
        shutil.copy(args.raw / f"{pid}.psv", args.out / f"{bed}.psv")
        alert_at = first_alert.get(pid)
        anchor = alert_at if alert_at is not None and not np.isnan(alert_at) else onset.get(pid, 12)
        cases.append({
            "bed_id": bed,
            "kind": kind,
            "source_patient": pid,
            "hours": int(stay[pid]),
            "labelled_onset_hour": None if pid not in onset.index else int(onset[pid]),
            "first_high_risk_hour": None if alert_at is None or np.isnan(alert_at) else int(alert_at),
            "replay_start_hour": int(max(2, min(anchor - 6, stay[pid] - 12))),
        })
    manifest = {
        "model_version": bundle["model_version"],
        "source_split": "Dataset A internal test (never used for training, calibration or thresholds)",
        "selection_rule": __doc__.strip(),
        "median_warning_hours_test": median_lead,
        "cases": cases,
    }
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    for c in cases:
        print(c)
    print(f"Wrote {len(cases)} cases -> {args.out}")


if __name__ == "__main__":
    main()
