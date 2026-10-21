"""Atomic active-model pointer and rollback support for frozen bundles."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from predict_rx.governance.integrity import sha256_file


def activate_frozen_model(
    model_dir: Path,
    *,
    registry: Path,
    history: Path,
    activated_by: str,
    reason: str,
) -> dict:
    model_dir = model_dir.resolve()
    model_path = model_dir / "model.joblib"
    frozen_path = model_dir / "FROZEN.json"
    if not model_path.exists() or not frozen_path.exists():
        raise FileNotFoundError("Activation requires model.joblib and FROZEN.json.")
    frozen = json.loads(frozen_path.read_text())
    actual_hash = sha256_file(model_path)
    if actual_hash != frozen["model_sha256"]:
        raise ValueError("Model hash does not match its freeze record.")

    previous = json.loads(registry.read_text()) if registry.exists() else None
    registry_parent = registry.resolve().parent
    try:
        portable_model_path = model_path.relative_to(registry_parent).as_posix()
    except ValueError:
        portable_model_path = model_path.as_posix()
    record = {
        "schema_version": 1,
        "model_version": frozen["model_version"],
        "model_path": portable_model_path,
        "model_sha256": actual_hash,
        "activated_at": datetime.now(timezone.utc).isoformat(),
        "activated_by": activated_by,
        "reason": reason,
        "previous_model_version": previous.get("model_version") if previous else None,
        "previous_model_sha256": previous.get("model_sha256") if previous else None,
        "restart_required": True,
    }
    registry.parent.mkdir(parents=True, exist_ok=True)
    temporary = registry.with_suffix(registry.suffix + ".tmp")
    temporary.write_text(json.dumps(record, indent=2) + "\n")
    os.replace(temporary, registry)
    history.parent.mkdir(parents=True, exist_ok=True)
    with history.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, separators=(",", ":")) + "\n")
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=Path("artifacts/models/ACTIVE.json"))
    parser.add_argument("--history", type=Path, default=Path("artifacts/governance/model_registry.jsonl"))
    parser.add_argument("--activated-by", required=True)
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            activate_frozen_model(
                args.model_dir,
                registry=args.registry,
                history=args.history,
                activated_by=args.activated_by,
                reason=args.reason,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
