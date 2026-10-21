"""Gate expensive temporal/Graph-Hazard work behind required evidence phases."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pyarrow.parquet as pq


def check_challenger_gate(ml_root: Path) -> dict:
    requirements: dict[str, dict] = {}

    set_a = ml_root / "data/processed/features_setA.parquet"
    try:
        parquet = pq.ParquetFile(set_a)
        data_valid = parquet.metadata.num_rows > 0
        data_detail = f"{parquet.metadata.num_rows} rows"
    except Exception as error:
        data_valid = False
        data_detail = f"{type(error).__name__}: {error}"
    requirements["valid_dataset_a"] = {"passed": data_valid, "detail": data_detail}

    patterns = {
        "baseline_bundle": "artifacts/experiments/baselines_setb_*/report.json",
        "data_target_audit": "artifacts/experiments/data_target_audit_*/report.json",
        "tabular_challenger": "artifacts/challengers/*/result.json",
    }
    for name, pattern in patterns.items():
        matches = list(ml_root.glob(pattern))
        requirements[name] = {
            "passed": bool(matches),
            "detail": [path.relative_to(ml_root).as_posix() for path in matches],
        }

    backend_marker = ml_root.parent / "backend/tests/test_trustgate.py"
    requirements["critical_backend_and_trustgate_tests_present"] = {
        "passed": backend_marker.exists(),
        "detail": backend_marker.as_posix(),
    }
    passed = all(item["passed"] for item in requirements.values())
    return {
        "gate_version": 1,
        "passed": passed,
        "requirements": requirements,
        "decision": (
            "Temporal and Graph-Hazard challengers may enter bounded A-only development."
            if passed
            else "Do not start temporal or Graph-Hazard training; complete unmet evidence gates first."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ml-root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = check_challenger_gate(args.ml_root.resolve())
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
