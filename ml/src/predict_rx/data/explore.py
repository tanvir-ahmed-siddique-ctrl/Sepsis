"""CLI: quick exploration of downloaded patient files."""

from __future__ import annotations

import argparse
from pathlib import Path

from predict_rx.data import iter_patients


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("data/raw"))
    parser.add_argument("--n", type=int, default=10)
    args = parser.parse_args()
    if not args.root.exists():
        raise SystemExit(f"Missing {args.root}. Download PhysioNet data first.")

    sepsis_hours = 0
    patients = 0
    hours = 0
    for i, df in enumerate(iter_patients(args.root)):
        if i >= args.n:
            break
        patients += 1
        hours += len(df)
        sepsis_hours += int((df["SepsisLabel"] == 1).sum())
        print(
            f"{df['patient_id'].iloc[0]}: {len(df)}h, "
            f"sepsis_hours={int((df['SepsisLabel']==1).sum())}, "
            f"age={df['Age'].iloc[0] if 'Age' in df else '?'}"
        )
    print(f"\nSampled {patients} patients · {hours} hours · {sepsis_hours} sepsis-labelled hours")


if __name__ == "__main__":
    main()
