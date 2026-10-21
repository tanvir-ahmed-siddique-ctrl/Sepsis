"""Reproducible processed-data, target, and leakage audit."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from predict_rx.audit.targets import build_incident_targets, incident_target_manifest
from predict_rx.features.build import NON_FEATURE_COLS
from predict_rx.features.schema import DEMO_COLS, LAB_COLS, MIN_HOURS_BEFORE_PRED, VITAL_COLS
from predict_rx.governance.integrity import sha256_file
from predict_rx.governance.access import EvaluationAccessLedger, resolve_authorization

PLAUSIBLE_RANGES = {
    "HR": (20, 300),
    "O2Sat": (0, 100),
    "Temp": (25, 45),
    "SBP": (30, 300),
    "MAP": (20, 250),
    "DBP": (10, 200),
    "Resp": (2, 80),
    "EtCO2": (0, 100),
    "Age": (18, 120),
}
SOURCE_LEAKAGE_PATTERNS = {
    "negative_shift": re.compile(r"shift\s*\(\s*-\d+"),
    "centered_window": re.compile(r"center\s*=\s*True"),
    "backfill": re.compile(r"\.bfill\s*\("),
}


def _feature_family(column: str) -> str:
    if column in set(VITAL_COLS + LAB_COLS + DEMO_COLS):
        return "physiology_or_context_current"
    if column.endswith(("_missing", "_hours_since")) or "_count_" in column:
        return "missingness_or_care_process"
    if any(token in column for token in ("_mean_", "_std_", "_min_", "_max_", "_delta_", "_slope_", "_rise_")):
        return "temporal_trend"
    if column.startswith(("sofa", "qsofa", "sirs", "shock_index", "pulse_pressure")):
        return "clinical_score"
    return "other_engineered"


def _all_empty_columns(path: Path, batch_size: int = 8192) -> list[str]:
    parquet = pq.ParquetFile(path)
    non_null = np.zeros(len(parquet.schema_arrow.names), dtype=np.int64)
    for batch in parquet.iter_batches(batch_size=batch_size):
        for index, column in enumerate(batch.columns):
            non_null[index] += len(column) - column.null_count
    return [
        name
        for name, count in zip(parquet.schema_arrow.names, non_null, strict=True)
        if count == 0
    ]


def _checksum_manifest_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"status": "missing", "path": path.as_posix()}
    counts: Counter[str] = Counter()
    malformed = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            malformed += 1
            continue
        relative = parts[1].replace("\\", "/")
        if "training_setA/" in relative:
            counts["training_setA"] += 1
        elif "training_setB/" in relative:
            counts["training_setB"] += 1
        else:
            counts["other"] += 1
    return {
        "status": "present",
        "path": path.as_posix(),
        "sha256": sha256_file(path),
        "entries": dict(counts),
        "malformed_lines": malformed,
    }


def _source_leakage_scan(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    return {
        name: [match.group(0) for match in pattern.finditer(text)]
        for name, pattern in SOURCE_LEAKAGE_PATTERNS.items()
    }


def audit_feature_file(path: Path, *, full_column_scan: bool = True) -> tuple[dict[str, Any], pd.DataFrame]:
    if not path.exists():
        raise FileNotFoundError(path)
    parquet = pq.ParquetFile(path)
    columns = parquet.schema_arrow.names
    time_col = "ICULOS" if "ICULOS" in columns else "hours_observed"
    structural = [
        column
        for column in (
            "patient_id",
            "split",
            "SepsisLabel",
            "ICULOS",
            "hours_observed",
            "Age",
            "Gender",
            "Unit1",
            "Unit2",
            "HospAdmTime",
        )
        if column in columns
    ]
    frame = pd.read_parquet(path, columns=structural)
    required = {"patient_id", "split", "SepsisLabel", time_col}
    missing_required = sorted(required - set(frame.columns))
    if missing_required:
        raise ValueError(f"{path} is missing required columns: {missing_required}")

    grouped = frame.groupby("patient_id", sort=False)
    labels = frame["SepsisLabel"].fillna(0).astype(int)
    label_diff = labels.groupby(frame["patient_id"], sort=False).diff().fillna(labels)
    patient_transitions = label_diff.eq(1).groupby(frame["patient_id"], sort=False).sum()
    time_diff = frame[time_col].groupby(frame["patient_id"], sort=False).diff()
    static_columns = [column for column in ("Age", "Gender", "Unit1", "Unit2", "HospAdmTime") if column in frame]
    static_inconsistent = {
        column: int((grouped[column].nunique(dropna=True) > 1).sum())
        for column in static_columns
    }
    feature_columns = [column for column in columns if column not in NON_FEATURE_COLS]
    suspicious_names = [
        column
        for column in feature_columns
        if re.search(r"(target|label|future|next_|onset)", column, flags=re.IGNORECASE)
    ]
    ranges: dict[str, Any] = {}
    for column, (lower, upper) in PLAUSIBLE_RANGES.items():
        if column not in frame:
            continue
        observed = frame[column].dropna()
        ranges[column] = {
            "observed": int(len(observed)),
            "below_plausible": int((observed < lower).sum()),
            "above_plausible": int((observed > upper).sum()),
            "minimum": float(observed.min()) if len(observed) else None,
            "maximum": float(observed.max()) if len(observed) else None,
            "plausible_range": [lower, upper],
        }
    incident = build_incident_targets(frame)
    target_summary = {}
    for column in [name for name in incident if name.startswith("incident_onset_within_")]:
        target_summary[column] = {
            "at_risk_rows": int(incident[column].notna().sum()),
            "positive_rows": int(incident[column].fillna(0).sum()),
        }
    report = {
        "path": path.as_posix(),
        "sha256": sha256_file(path),
        "rows": int(parquet.metadata.num_rows),
        "columns": len(columns),
        "patients": int(frame["patient_id"].nunique()),
        "split_rows": {str(key): int(value) for key, value in frame["split"].value_counts().items()},
        "split_patients": {
            str(key): int(value)
            for key, value in frame.groupby("split")["patient_id"].nunique().items()
        },
        "septic_patients": int(grouped["SepsisLabel"].max().fillna(0).astype(bool).sum()),
        "eligible_rows": int((frame["hours_observed"] >= MIN_HOURS_BEFORE_PRED).sum())
        if "hours_observed" in frame
        else None,
        "duplicate_patient_time_rows": int(frame.duplicated(["patient_id", time_col]).sum()),
        "non_chronological_steps": int((time_diff < 0).sum()),
        "duplicate_or_zero_time_steps": int((time_diff == 0).sum()),
        "label_reversions_1_to_0": int((label_diff < 0).sum()),
        "patients_with_multiple_positive_transitions": int((patient_transitions > 1).sum()),
        "adult_exclusion_violations": int((frame["Age"].dropna() < 18).sum()) if "Age" in frame else None,
        "static_inconsistency_by_patient_count": static_inconsistent,
        "plausible_range_findings": ranges,
        "feature_families": dict(Counter(_feature_family(column) for column in feature_columns)),
        "suspicious_feature_names": suspicious_names,
        "all_empty_columns": _all_empty_columns(path) if full_column_scan else "scan_skipped",
        "incident_targets": target_summary,
    }
    return report, frame


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit processed features and derive incident targets.")
    parser.add_argument("--set-a", type=Path, default=Path("data/processed/features_setA.parquet"))
    parser.add_argument("--set-b", type=Path, default=Path("data/processed/features_setB.parquet"))
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw"))
    parser.add_argument("--checksum-manifest", type=Path, default=Path("data/checksums/raw_sha256.txt"))
    parser.add_argument("--feature-source", type=Path, default=Path("src/predict_rx/features/engineering.py"))
    parser.add_argument("--out", type=Path)
    parser.add_argument("--skip-full-column-scan", action="store_true")
    parser.add_argument("--targets-out", type=Path)
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path("artifacts/governance/evaluation_access.json"),
    )
    parser.add_argument("--authorized-by", required=True)
    parser.add_argument("--authorize-dataset-b", required=True)
    parser.add_argument("--allow-repeat", action="store_true")
    parser.add_argument(
        "--access-reason",
        default=(
            "Phase 2 structural data/target audit only; no model selection, calibration, "
            "thresholding, feature selection, or architecture decisions use Dataset B."
        ),
    )
    args = parser.parse_args()

    run_id = f"data_target_audit_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    output = args.out or Path("artifacts/experiments") / run_id
    if output.exists():
        raise SystemExit(f"Refusing to overwrite existing audit bundle: {output}")
    report_a, frame_a = audit_feature_file(args.set_a, full_column_scan=not args.skip_full_column_scan)
    confirmation, reason = resolve_authorization(args.authorize_dataset_b, args.access_reason)
    access_entry = EvaluationAccessLedger(args.ledger).record(
        model_version="no-model:data-audit-v1",
        model_sha256="not-applicable",
        purpose="data_integrity_audit",
        reason=reason,
        authorized_by=args.authorized_by,
        command=" ".join([sys.executable, "-m", "predict_rx.audit.data", *sys.argv[1:]]),
        confirmation=confirmation,
        allow_repeat=args.allow_repeat,
    )
    report_b, frame_b = audit_feature_file(args.set_b, full_column_scan=not args.skip_full_column_scan)
    overlap = set(frame_a["patient_id"].astype(str)) & set(frame_b["patient_id"].astype(str))
    report = {
        "schema_version": 1,
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "official_target": (
            "PhysioNet Challenge-compatible SepsisLabel. This view includes post-onset positive rows "
            "and is not an incident six-hour hazard probability."
        ),
        "incident_target_manifest": incident_target_manifest(),
        "dataset_a": report_a,
        "dataset_b": report_b,
        "evaluation_access": access_entry,
        "patient_id_overlap_a_b": len(overlap),
        "raw_data": {
            "root": args.raw_root.as_posix(),
            "status": "present" if args.raw_root.exists() else "missing_blocked",
        },
        "checksum_manifest": _checksum_manifest_summary(args.checksum_manifest),
        "source_leakage_scan": _source_leakage_scan(args.feature_source),
        "interpretation": {
            "care_process_features_are_present": report_a["feature_families"].get(
                "missingness_or_care_process", 0
            )
            > 0,
            "care_process_predictive_strength": "requires Dataset A-only ablation; not inferred from names",
            "dataset_b_used_for_model_selection": False,
        },
    }
    output.mkdir(parents=True)
    (output / "report.json").write_text(json.dumps(report, indent=2, default=float) + "\n", encoding="utf-8")
    (output / "incident_target_manifest.json").write_text(
        json.dumps(incident_target_manifest(), indent=2) + "\n",
        encoding="utf-8",
    )

    if args.targets_out:
        if args.targets_out.exists():
            raise SystemExit(f"Refusing to overwrite incident targets: {args.targets_out}")
        combined = pd.concat(
            [
                pd.concat([frame_a[["patient_id", "split"]], build_incident_targets(frame_a)], axis=1),
                pd.concat([frame_b[["patient_id", "split"]], build_incident_targets(frame_b)], axis=1),
            ],
            ignore_index=True,
        )
        args.targets_out.parent.mkdir(parents=True, exist_ok=True)
        combined.to_parquet(args.targets_out, index=False)
    print(json.dumps({"run_id": run_id, "report": str(output / "report.json")}, indent=2))


if __name__ == "__main__":
    main()
