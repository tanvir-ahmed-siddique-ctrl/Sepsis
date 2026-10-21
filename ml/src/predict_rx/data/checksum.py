"""CLI: write SHA-256 checksums for raw dataset files."""

from __future__ import annotations

import argparse
from pathlib import Path

from predict_rx.data import write_checksums


def main() -> None:
    parser = argparse.ArgumentParser(description="Checksum PhysioNet raw files")
    parser.add_argument("--root", type=Path, default=Path("data/raw"))
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/checksums/raw_sha256.txt"),
    )
    args = parser.parse_args()
    if not args.root.exists():
        raise SystemExit(
            f"Raw data not found at {args.root}. See ml/README.md for download steps."
        )
    n = write_checksums(args.root, args.out)
    print(f"Wrote {n} checksums → {args.out}")


if __name__ == "__main__":
    main()
