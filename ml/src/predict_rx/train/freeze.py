"""Freeze the current model: after this, Dataset B may be scored exactly once per version."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib


PROTECTED_DIRS = {"latest", "run4_frozen"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.model_dir.name in PROTECTED_DIRS:
        raise SystemExit(
            f"Refusing to freeze into protected evidence directory {args.model_dir}. "
            "Freeze a challenger directory instead."
        )

    path = args.model_dir / "model.joblib"
    bundle = joblib.load(path)
    if bundle.get("frozen"):
        raise SystemExit(f"{bundle['model_version']} is already frozen.")
    bundle["frozen"] = True
    bundle["frozen_at"] = datetime.now(timezone.utc).isoformat()
    joblib.dump(bundle, path)
    record = {
        "model_version": bundle["model_version"],
        "frozen_at": bundle["frozen_at"],
        "model_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "thresholds": bundle["thresholds"],
    }
    (args.model_dir / "FROZEN.json").write_text(json.dumps(record, indent=2))
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
