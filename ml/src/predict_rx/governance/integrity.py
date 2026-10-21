"""Preserve and verify immutable evidence artifacts without rewriting them."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

PRESERVED_FILES = (
    "model.joblib",
    "FROZEN.json",
    "metrics.json",
    "eval_holdout.json",
    "eval_log_setB.txt",
)
DEPENDENCIES = (
    "numpy",
    "pandas",
    "polars",
    "pyarrow",
    "scikit-learn",
    "lightgbm",
    "shap",
    "joblib",
    "pydantic",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_tree(paths: Iterable[Path], root: Path) -> str:
    digest = hashlib.sha256()
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(child for child in path.rglob("*") if child.is_file())
        elif path.is_file():
            files.append(path)
    for path in sorted(set(files), key=lambda item: item.as_posix()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256_file(path)))
    return digest.hexdigest()


def _file_record(path: Path) -> dict[str, object]:
    return {
        "path": path.as_posix(),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def _optional_file_record(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"path": path.as_posix(), "status": "missing"}
    return {"status": "present", **_file_record(path)}


def _git_commit(repo_root: Path) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return "unavailable:not-a-git-repository"


def _dependency_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in DEPENDENCIES:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "not-installed"
    return versions


def _copy_without_overwrite(source: Path, destination: Path) -> None:
    if destination.exists():
        if sha256_file(source) != sha256_file(destination):
            raise RuntimeError(f"Refusing to overwrite non-identical evidence artifact: {destination}")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    if sha256_file(source) != sha256_file(destination):
        destination.unlink(missing_ok=True)
        raise RuntimeError(f"Hash mismatch after preserving {source.name}")


def preserve_frozen_release(
    *,
    source: Path,
    destination: Path,
    ml_root: Path,
    repo_root: Path,
) -> dict[str, object]:
    source = source.resolve()
    destination = destination.resolve()
    ml_root = ml_root.resolve()
    repo_root = repo_root.resolve()
    frozen_path = source / "FROZEN.json"
    if not frozen_path.exists():
        raise FileNotFoundError(f"Missing freeze record: {frozen_path}")
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    model_path = source / "model.joblib"
    actual_model_hash = sha256_file(model_path)
    if actual_model_hash != frozen["model_sha256"]:
        raise RuntimeError(
            f"Frozen model hash mismatch: expected {frozen['model_sha256']}, got {actual_model_hash}"
        )

    for name in PRESERVED_FILES:
        artifact = source / name
        if not artifact.exists():
            raise FileNotFoundError(f"Required frozen evidence file is missing: {artifact}")
        _copy_without_overwrite(artifact, destination / name)

    manifest_path = destination / "MANIFEST.v2.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["model"]["sha256"] != actual_model_hash:
            raise RuntimeError(f"Existing strengthened manifest conflicts with {model_path}")
        return manifest

    source_package = ml_root / "src" / "predict_rx"
    config_paths = [ml_root / "configs" / "splits.yaml", ml_root / "configs" / "train_lightgbm.yaml"]
    raw_checksum_path = ml_root / "data" / "checksums" / "raw_sha256.txt"
    split_path = ml_root / "data" / "processed" / "features_setA.splits.json"
    feature_a = ml_root / "data" / "processed" / "features_setA.parquet"
    feature_b = ml_root / "data" / "processed" / "features_setB.parquet"

    manifest: dict[str, object] = {
        "schema_version": 2,
        "artifact_status": "immutable_evidence_copy",
        "preserved_at": datetime.now(timezone.utc).isoformat(),
        "source_directory": source.as_posix(),
        "destination_directory": destination.as_posix(),
        "model": {
            "version": frozen["model_version"],
            "frozen_at": frozen["frozen_at"],
            "sha256": actual_model_hash,
            "thresholds": frozen["thresholds"],
            "target_definition": (
                "Official PhysioNet Challenge 2019 SepsisLabel view; labels turn positive "
                "six hours before defined onset and remain positive afterward."
            ),
            "calibration_dataset": "Dataset A validation patients only",
            "threshold_selection_dataset": "Dataset A validation patients only",
        },
        "artifacts": {
            name: _file_record(destination / name)
            for name in PRESERVED_FILES
        },
        "data_provenance": {
            "raw_checksum_manifest": _optional_file_record(raw_checksum_path),
            "split_manifest": _optional_file_record(split_path),
            "processed_features_set_a": _optional_file_record(feature_a),
            "processed_features_set_b": _optional_file_record(feature_b),
        },
        "configuration": {
            path.name: _optional_file_record(path)
            for path in config_paths
        },
        "code": {
            "predict_rx_tree_sha256": sha256_tree([source_package], ml_root),
            "feature_pipeline_tree_sha256": sha256_tree(
                [source_package / "features", source_package / "explain.py", source_package / "models.py"],
                ml_root,
            ),
        },
        "environment": {
            "git_commit": _git_commit(repo_root),
            "python": sys.version,
            "platform": platform.platform(),
            "dependencies": _dependency_versions(),
        },
        "evaluation": {
            "dataset_b_wording": (
                "Site-held-out retrospective validation on a geographically distinct "
                "public hospital cohort."
            ),
            "dataset_b_is_public_training_set_b": True,
            "dataset_b_is_secret_hospital_c": False,
            "prospective_validation": False,
            "clinical_outcome_improvement_validated": False,
        },
        "provenance_limitations": [
            "The current workspace is not a Git repository, so a source commit cannot be recorded.",
            "Processed feature hashes are marked missing when local parquet files are unavailable.",
            "This preservation manifest was reconstructed from surviving frozen artifacts.",
        ],
    }
    destination.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (destination / ".immutable").write_text(
        "Do not train, calibrate, threshold, or evaluate in this directory.\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Preserve the frozen evidence bundle byte-for-byte.")
    parser.add_argument("--source", type=Path, default=Path("artifacts/models/latest"))
    parser.add_argument("--destination", type=Path, default=Path("artifacts/models/run4_frozen"))
    parser.add_argument("--ml-root", type=Path, default=Path("."))
    parser.add_argument("--repo-root", type=Path, default=Path(".."))
    args = parser.parse_args()
    manifest = preserve_frozen_release(
        source=args.source,
        destination=args.destination,
        ml_root=args.ml_root,
        repo_root=args.repo_root,
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
