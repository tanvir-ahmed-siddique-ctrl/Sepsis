"""Load and validate PhysioNet Challenge 2019 patient PSV files."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd


REQUIRED_HINT_COLS = {"HR", "ICULOS", "SepsisLabel"}


def load_patient_psv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep="|")
    missing = REQUIRED_HINT_COLS - set(df.columns)
    if missing:
        raise ValueError(f"{path.name} missing columns: {sorted(missing)}")
    df = df.copy()
    df["patient_id"] = path.stem
    return df


def iter_patients(raw_dir: Path):
    paths = sorted(raw_dir.rglob("*.psv"))
    for path in paths:
        yield load_patient_psv(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_checksums(root: Path, out_file: Path) -> int:
    files = sorted(p for p in root.rglob("*") if p.is_file())
    lines = []
    for path in files:
        rel = path.relative_to(root)
        lines.append(f"{sha256_file(path)}  {rel.as_posix()}")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text("\n".join(lines) + ("\n" if lines else ""))
    return len(lines)
