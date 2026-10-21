"""Machine-readable repository and evidence preflight checks."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from predict_rx.governance.integrity import sha256_file


def _json_check(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": path.as_posix(), "status": "missing"}
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return {
            "path": path.as_posix(),
            "status": "invalid",
            "sha256": sha256_file(path),
            "error": f"{type(error).__name__}: {error}",
        }
    return {"path": path.as_posix(), "status": "valid", "sha256": sha256_file(path)}


def _parquet_check(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": path.as_posix(), "status": "missing"}
    try:
        parquet = pq.ParquetFile(path)
        return {
            "path": path.as_posix(),
            "status": "valid",
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
            "rows": int(parquet.metadata.num_rows),
            "columns": int(parquet.metadata.num_columns),
        }
    except Exception as error:  # PyArrow exposes format-specific exception subclasses.
        return {
            "path": path.as_posix(),
            "status": "invalid",
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
            "error": f"{type(error).__name__}: {error}",
        }


def _git_status(repo_root: Path) -> dict[str, Any]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        return {"status": "available", "commit": commit}
    except (FileNotFoundError, subprocess.CalledProcessError):
        return {"status": "unavailable", "reason": "not-a-git-repository"}


def build_preflight(ml_root: Path, repo_root: Path) -> dict[str, Any]:
    latest = ml_root / "artifacts" / "models" / "latest"
    frozen = ml_root / "artifacts" / "models" / "run4_frozen"
    latest_record = json.loads((latest / "FROZEN.json").read_text(encoding="utf-8"))
    model_checks = {}
    for name, directory in (("latest", latest), ("run4_frozen", frozen)):
        model_path = directory / "model.joblib"
        actual = sha256_file(model_path) if model_path.exists() else None
        model_checks[name] = {
            "path": model_path.as_posix(),
            "status": "valid" if actual == latest_record["model_sha256"] else "invalid",
            "expected_sha256": latest_record["model_sha256"],
            "actual_sha256": actual,
        }
    checks = {
        "models": model_checks,
        "evidence_json": {
            "latest_frozen": _json_check(latest / "FROZEN.json"),
            "latest_metrics": _json_check(latest / "metrics.json"),
            "latest_holdout": _json_check(latest / "eval_holdout.json"),
            "strengthened_manifest": _json_check(frozen / "MANIFEST.v2.json"),
            "evaluation_access": _json_check(
                ml_root / "artifacts" / "governance" / "evaluation_access.json"
            ),
        },
        "processed_data": {
            "set_a": _parquet_check(ml_root / "data" / "processed" / "features_setA.parquet"),
            "set_b": _parquet_check(ml_root / "data" / "processed" / "features_setB.parquet"),
            "set_a_splits": _json_check(
                ml_root / "data" / "processed" / "features_setA.splits.json"
            ),
            "set_b_splits": _json_check(
                ml_root / "data" / "processed" / "features_setB.splits.json"
            ),
        },
        "source": {
            "predict_rx": "present" if (ml_root / "src" / "predict_rx").is_dir() else "missing",
            "frontend_components": (
                "present" if (repo_root / "frontend" / "components" / "AppNav.tsx").is_file() else "missing"
            ),
        },
        "git": _git_status(repo_root),
    }
    failures = []
    for group in ("models", "evidence_json", "processed_data"):
        for name, result in checks[group].items():
            if result["status"] != "valid":
                failures.append(f"{group}.{name}:{result['status']}")
    return {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "critical_failures": failures,
        "ready_for_data_heavy_evaluation": not failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Check source, evidence, and processed-data integrity.")
    parser.add_argument("--ml-root", type=Path, default=Path("."))
    parser.add_argument("--repo-root", type=Path, default=Path(".."))
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("artifacts/governance/preflight.json"),
    )
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()
    report = build_preflight(args.ml_root.resolve(), args.repo_root.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["critical_failures"] and not args.report_only:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
