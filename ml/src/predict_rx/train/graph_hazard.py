"""Fail-closed Graph-Hazard entry point.

Temporal/organ-graph challengers (`predict_rx.temporal`) are not trained until
Dataset B baselines, the data/target audit, and an A-only tabular challenger exist.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from predict_rx.train.challenger_gate import check_challenger_gate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ml-root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, default=Path("artifacts/governance/graph_hazard_gate.json"))
    args = parser.parse_args()
    report = check_challenger_gate(args.ml_root.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        **report,
        "architecture": "Sentinel Graph-Hazard lives in predict_rx.temporal; run predict_rx.temporal.cv "
                        "only when this gate passes.",
        "dataset_b_accessed": False,
    }
    args.out.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))
    raise SystemExit(0 if report["passed"] else 2)


if __name__ == "__main__":
    main()
