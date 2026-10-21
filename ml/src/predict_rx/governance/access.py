"""Append-only access ledger for protected Dataset B evaluation.

The ledger is an operational guardrail, not a security boundary. Every command
that reads Dataset B should record its purpose before loading the feature file.
"""

from __future__ import annotations

import argparse
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CONFIRMATION_TOKEN = "DATASET_B_AUTHORIZED"


def resolve_authorization(authorize_dataset_b: str, access_reason: str | None = None) -> tuple[str, str]:
    """Return (confirmation, reason) for a Dataset B command.

    Documented CLIs pass a human reason in ``--authorize-dataset-b``. Tests and
    older invocations may pass the confirmation token in that flag and the
    reason in ``--access-reason``. Either form still records the same token.
    """
    if not (authorize_dataset_b or "").strip():
        raise PermissionError("Dataset B access requires --authorize-dataset-b.")
    if authorize_dataset_b.strip() == CONFIRMATION_TOKEN:
        return CONFIRMATION_TOKEN, (access_reason or "authorized Dataset B access")
    return CONFIRMATION_TOKEN, authorize_dataset_b.strip()


class EvaluationAccessLedger:
    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {
                "schema_version": 1,
                "dataset": "PhysioNet Challenge 2019 public training set B",
                "policy": (
                    "No feature selection, tuning, calibration, threshold selection, "
                    "architecture selection, or ablation decisions may use Dataset B."
                ),
                "entries": [],
            }
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data.get("entries"), list):
            raise ValueError(f"Invalid evaluation-access ledger: {self.path}")
        return data

    def record(
        self,
        *,
        model_version: str,
        model_sha256: str,
        purpose: str,
        reason: str,
        authorized_by: str,
        command: str,
        confirmation: str,
        allow_repeat: bool = False,
        occurred_at: str | None = None,
    ) -> dict[str, Any]:
        if confirmation != CONFIRMATION_TOKEN:
            raise PermissionError(
                f"Dataset B access requires the explicit confirmation token {CONFIRMATION_TOKEN!r}."
            )
        ledger = self.read()
        duplicates = [
            entry
            for entry in ledger["entries"]
            if entry["model_version"] == model_version and entry["purpose"] == purpose
        ]
        if duplicates and not allow_repeat:
            raise RuntimeError(
                f"Access already recorded for model={model_version!r}, purpose={purpose!r}. "
                "Use allow_repeat only with a documented reason."
            )
        entry = {
            "access_id": f"setb-{uuid.uuid4().hex[:12]}",
            "occurred_at": occurred_at or datetime.now(timezone.utc).isoformat(),
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "model_version": model_version,
            "model_sha256": model_sha256,
            "purpose": purpose,
            "reason": reason,
            "authorized_by": authorized_by,
            "command": command,
            "repeat_override": bool(duplicates),
        }
        ledger["entries"].append(entry)
        self._write_atomic(ledger)
        return entry

    def _write_atomic(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, self.path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect or append the protected Dataset B access ledger.")
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path("artifacts/governance/evaluation_access.json"),
    )
    subparsers = parser.add_subparsers(dest="action", required=True)
    subparsers.add_parser("status")
    record = subparsers.add_parser("record")
    record.add_argument("--model-version", required=True)
    record.add_argument("--model-sha256", required=True)
    record.add_argument("--purpose", required=True)
    record.add_argument("--reason", required=True)
    record.add_argument("--authorized-by", required=True)
    record.add_argument("--command", required=True)
    record.add_argument("--confirm", required=True)
    record.add_argument("--allow-repeat", action="store_true")
    record.add_argument("--occurred-at")
    args = parser.parse_args()

    ledger = EvaluationAccessLedger(args.ledger)
    if args.action == "status":
        print(json.dumps(ledger.read(), indent=2))
        return
    entry = ledger.record(
        model_version=args.model_version,
        model_sha256=args.model_sha256,
        purpose=args.purpose,
        reason=args.reason,
        authorized_by=args.authorized_by,
        command=args.command,
        confirmation=args.confirm,
        allow_repeat=args.allow_repeat,
        occurred_at=args.occurred_at,
    )
    print(json.dumps(entry, indent=2))


if __name__ == "__main__":
    main()
