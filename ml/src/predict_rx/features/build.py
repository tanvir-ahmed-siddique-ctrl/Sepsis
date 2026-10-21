"""Build feature matrices from raw PSV files.

Historical target: PhysioNet 2019 `SepsisLabel`, which becomes positive six
hours before defined onset and stays positive afterward. It is retained for
Challenge-compatible comparison, not described as a pure incident six-hour
hazard. All patient hours are kept so utility scoring sees complete stays.
"""

from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from tqdm import tqdm

from predict_rx.data import load_patient_psv
from predict_rx.data.splits import assign_patient_splits, load_split_config
from predict_rx.features.engineering import build_patient_features
from predict_rx.features.schema import LABEL_COL, TARGET_COL

NON_FEATURE_COLS = {"patient_id", "split", LABEL_COL, TARGET_COL}


def _process_file(path: Path) -> pd.DataFrame | None:
    df = load_patient_psv(path)
    if "Age" in df and df["Age"].iloc[0] < 18:
        return None
    feat = build_patient_features(df)
    feat["hours_observed"] = np.arange(1, len(feat) + 1)
    num_cols = [
        c for c in feat.columns
        if c not in NON_FEATURE_COLS and pd.api.types.is_numeric_dtype(feat[c])
    ]
    numeric = pd.DataFrame(feat[num_cols].to_numpy(np.float32), columns=num_cols)
    meta = pd.DataFrame({
        "patient_id": feat["patient_id"],
        LABEL_COL: feat[LABEL_COL].astype(np.int8),
        TARGET_COL: feat[LABEL_COL].astype(np.int8),
    })
    return pd.concat([meta, numeric], axis=1)


def build_dataset(paths: list[Path], split_map: dict[str, str], workers: int) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for feat in tqdm(pool.map(_process_file, paths, chunksize=64), total=len(paths), desc="patients"):
            if feat is None:
                continue
            feat["split"] = split_map[feat["patient_id"].iloc[0]]
            frames.append(feat)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def write_dataset_streaming(
    paths: list[Path],
    split_map: dict[str, str],
    workers: int,
    out: Path,
    patients_per_row_group: int = 256,
) -> dict[str, dict[str, float]]:
    """Stream patient features into Parquet row groups, then atomically rename.

    Keeps peak memory bounded and never leaves a truncated file at ``out``.
    """
    temporary = out.with_name(out.name + ".partial")
    temporary.unlink(missing_ok=True)
    writer: pq.ParquetWriter | None = None
    schema: pa.Schema | None = None
    columns: list[str] = []
    pending: list[pd.DataFrame] = []
    summary: dict[str, dict[str, float]] = {}

    def flush() -> None:
        nonlocal writer, schema, columns
        if not pending:
            return
        batch = pd.concat(pending, ignore_index=True)
        pending.clear()
        if schema is None:
            columns = list(batch.columns)
            schema = pa.Table.from_pandas(batch, preserve_index=False).schema
            writer = pq.ParquetWriter(temporary, schema, compression="zstd")
        missing = set(columns) ^ set(batch.columns)
        if missing:
            raise RuntimeError(f"Inconsistent feature columns across patients: {sorted(missing)[:10]}")
        writer.write_table(pa.Table.from_pandas(batch[columns], schema=schema, preserve_index=False))

    try:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for feat in tqdm(pool.map(_process_file, paths, chunksize=64), total=len(paths), desc="patients"):
                if feat is None:
                    continue
                split = split_map[feat["patient_id"].iloc[0]]
                feat["split"] = split
                stats = summary.setdefault(split, {"rows": 0, "positive_rows": 0, "patients": 0})
                stats["rows"] += len(feat)
                stats["positive_rows"] += int(feat[TARGET_COL].sum())
                stats["patients"] += 1
                pending.append(feat)
                if len(pending) >= patients_per_row_group:
                    flush()
        flush()
    finally:
        if writer is not None:
            writer.close()
    if schema is None:
        raise SystemExit("No eligible adult patients were found.")
    pq.ParquetFile(temporary)
    os.replace(temporary, out)
    for stats in summary.values():
        stats["positive_rate"] = stats["positive_rows"] / stats["rows"] if stats["rows"] else 0.0
    return summary


def _valid_parquet(path: Path) -> bool:
    try:
        return pq.ParquetFile(path).metadata.num_rows > 0
    except Exception:
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=Path("data/raw/training_setA"))
    parser.add_argument("--split-config", type=Path, default=Path("configs/splits.yaml"))
    parser.add_argument("--out", type=Path, default=Path("data/processed/features_setA.parquet"))
    parser.add_argument(
        "--holdout",
        action="store_true",
        help="Label every patient split='holdout' (Dataset B: untouched until model freeze).",
    )
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing valid Parquet file. Corrupt files are always replaceable.",
    )
    args = parser.parse_args()

    if not args.raw.exists():
        raise SystemExit(
            f"Raw path missing: {args.raw}\n"
            "Download PhysioNet Challenge 2019 data into ml/data/raw/ first."
        )
    if args.out.exists() and _valid_parquet(args.out) and not args.overwrite:
        raise SystemExit(f"Refusing to overwrite valid feature file {args.out}; pass --overwrite deliberately.")

    paths = sorted(args.raw.rglob("*.psv"))
    patient_ids = [p.stem for p in paths]
    if args.holdout:
        split_map = {pid: "holdout" for pid in patient_ids}
    else:
        split_map = assign_patient_splits(patient_ids, load_split_config(args.split_config))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    split_path = args.out.with_suffix(".splits.json")
    try:
        recorded = json.loads(split_path.read_text()) if split_path.exists() else None
    except json.JSONDecodeError:
        recorded = None
    if recorded is not None and recorded != split_map:
        raise SystemExit(
            f"Patient split differs from the recorded {split_path}. "
            "Refusing to silently change historical train/val/test membership."
        )
    if recorded is None:
        split_path.write_text(json.dumps(split_map, indent=2, sort_keys=True))

    summary = write_dataset_streaming(paths, split_map, args.workers, args.out)
    metadata = pq.ParquetFile(args.out).metadata
    print(f"Wrote {metadata.num_rows:,} rows, {metadata.num_columns} columns -> {args.out}")
    print(pd.DataFrame(summary).T[["patients", "rows", "positive_rate"]].to_string())


if __name__ == "__main__":
    main()
