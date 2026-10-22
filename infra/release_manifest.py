"""Generate a verifiable release manifest for a PredictRx Sentinel build.

The manifest binds the source tree, the frozen model and the deployment
artefacts into one auditable record. Anyone can re-check every hash:

    ../.venv/Scripts/python.exe infra/release_manifest.py
    ../.venv/Scripts/python.exe infra/release_manifest.py --verify

Writes docs/evidence/release-manifest.json and .md. It records facts only —
no clinical, customer or deployment claim is made by this tool.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "evidence"

KEY_FILES = (
    "ml/artifacts/models/ACTIVE.json",
    "backend/requirements.txt",
    "frontend/package.json",
    "frontend/package-lock.json",
    "infra/Dockerfile.demo",
    "infra/Dockerfile.api",
    "infra/Dockerfile.web",
    "docker-compose.yml",
    "docker-compose.site.yml",
    "AGENTS.md",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=30, check=True
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return "unknown"


def build_manifest() -> dict:
    registry = json.loads((ROOT / "ml/artifacts/models/ACTIVE.json").read_text())
    model_path = ROOT / "ml/artifacts/models" / registry["model_path"]
    cases_dir = ROOT / "demo/cases"
    dirty = git("status", "--porcelain")
    return {
        "format": "predictrx-release-manifest/1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "commit": git("rev-parse", "HEAD"),
            "branch": git("branch", "--show-current"),
            "working_tree_dirty": bool(dirty),
            "uncommitted_files": [line[3:] for line in dirty.splitlines() if line],
        },
        "frozen_model": {
            "version": registry["model_version"],
            "path": registry["model_path"],
            "registry_sha256": registry["model_sha256"],
            "file_sha256": sha256(model_path) if model_path.exists() else None,
            "hash_matches_registry": bool(model_path.exists()) and sha256(model_path) == registry["model_sha256"],
            "activated_at": registry.get("activated_at"),
            "activated_by": registry.get("activated_by"),
        },
        "replay_cases": {
            "bed_files": sorted(path.name for path in cases_dir.glob("BED-*.psv")) if cases_dir.exists() else [],
            "manifest_sha256": sha256(cases_dir / "manifest.json") if (cases_dir / "manifest.json").exists() else None,
            "provenance": "PhysioNet/CinC 2019 Dataset A internal test split, de-identified, CC BY 4.0; "
                          "raw cases are gitignored and copied only into demo images",
        },
        "key_files": {
            rel: (sha256(ROOT / rel) if (ROOT / rel).exists() else None) for rel in KEY_FILES
        },
        "rollback": {
            "procedure": "Redeploy the previous release image/compose bundle, restore the pre-upgrade "
                         "ops_cli backup, then run `ops_cli verify-audit` and GET /ready before reopening the site.",
            "model_rollback": "Point ACTIVE.json at the previous frozen artefact only through the audited "
                              "model-registry procedure; start-up rejects any hash mismatch.",
        },
    }


def verify(manifest: dict) -> list[str]:
    problems = []
    if not manifest["frozen_model"]["hash_matches_registry"]:
        problems.append("Frozen model file hash does not match ACTIVE.json registry.")
    for rel, recorded in manifest["key_files"].items():
        path = ROOT / rel
        current = sha256(path) if path.exists() else None
        if current != recorded:
            problems.append(f"Key file changed since manifest: {rel}")
    return problems


def render_markdown(manifest: dict) -> str:
    model = manifest["frozen_model"]
    lines = [
        "# Release manifest",
        "",
        f"- Generated: `{manifest['generated_at']}`",
        f"- Source commit: `{manifest['source']['commit']}` (branch `{manifest['source']['branch']}`, "
        f"working tree dirty: `{manifest['source']['working_tree_dirty']}`)",
        f"- Frozen model: `{model['version']}` — file SHA-256 `{model['file_sha256']}` "
        f"(matches registry: `{model['hash_matches_registry']}`)",
        f"- Replay beds in demo cases: {len(manifest['replay_cases']['bed_files'])} "
        f"({', '.join(manifest['replay_cases']['bed_files'])})",
        "",
        "## Key file hashes",
        "",
        "| File | SHA-256 |",
        "|---|---|",
        *[f"| `{rel}` | `{digest}` |" for rel, digest in manifest["key_files"].items()],
        "",
        "## Rollback",
        "",
        manifest["rollback"]["procedure"],
        "",
        manifest["rollback"]["model_rollback"],
        "",
        "Regenerate and verify with `infra/release_manifest.py` and `infra/release_manifest.py --verify`.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--verify", action="store_true", help="Check an existing manifest instead of writing one")
    args = parser.parse_args()
    manifest_path = OUT_DIR / "release-manifest.json"
    if args.verify:
        if not manifest_path.exists():
            print("No manifest found. Run without --verify first.", file=sys.stderr)
            return 1
        problems = verify(json.loads(manifest_path.read_text()))
        if problems:
            print("\n".join(f"FAIL: {problem}" for problem in problems))
            return 1
        print("Release manifest verified: frozen model and key files match.")
        return 0
    manifest = build_manifest()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2))
    (OUT_DIR / "release-manifest.md").write_text(render_markdown(manifest))
    print(json.dumps({"manifest": str(manifest_path), "model_hash_matches": manifest["frozen_model"]["hash_matches_registry"],
                      "commit": manifest["source"]["commit"], "dirty": manifest["source"]["working_tree_dirty"]}, indent=2))
    return 0 if manifest["frozen_model"]["hash_matches_registry"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
