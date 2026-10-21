from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from predict_rx.governance.access import CONFIRMATION_TOKEN, EvaluationAccessLedger, resolve_authorization
from predict_rx.governance.integrity import PRESERVED_FILES, preserve_frozen_release, sha256_file


def test_sha256_file_matches_hashlib(tmp_path: Path):
    path = tmp_path / "artifact.bin"
    path.write_bytes(b"frozen-evidence")
    assert sha256_file(path) == hashlib.sha256(b"frozen-evidence").hexdigest()


def test_preserve_frozen_release_never_overwrites(tmp_path: Path):
    repo = tmp_path / "repo"
    ml = repo / "ml"
    source = ml / "artifacts" / "models" / "latest"
    destination = ml / "artifacts" / "models" / "run4_frozen"
    source.mkdir(parents=True)
    model = source / "model.joblib"
    model.write_bytes(b"model-bytes")
    model_hash = sha256_file(model)
    frozen = {
        "model_version": "v-test",
        "frozen_at": "2026-01-01T00:00:00+00:00",
        "model_sha256": model_hash,
        "thresholds": {"watch": 0.1, "high_risk": 0.2},
    }
    (source / "FROZEN.json").write_text(json.dumps(frozen), encoding="utf-8")
    for name in PRESERVED_FILES:
        path = source / name
        if not path.exists():
            path.write_text(name, encoding="utf-8")
    (ml / "src" / "predict_rx" / "features").mkdir(parents=True)
    (ml / "src" / "predict_rx" / "features" / "schema.py").write_text("TARGET='label'\n", encoding="utf-8")
    (ml / "src" / "predict_rx" / "explain.py").write_text("", encoding="utf-8")
    (ml / "src" / "predict_rx" / "models.py").write_text("", encoding="utf-8")

    first = preserve_frozen_release(source=source, destination=destination, ml_root=ml, repo_root=repo)
    second = preserve_frozen_release(source=source, destination=destination, ml_root=ml, repo_root=repo)
    assert first["model"]["sha256"] == model_hash
    assert second["model"]["sha256"] == model_hash
    assert (destination / "model.joblib").read_bytes() == b"model-bytes"

    (destination / "model.joblib").write_bytes(b"tampered")
    with pytest.raises(RuntimeError, match="Refusing to overwrite"):
        preserve_frozen_release(source=source, destination=destination, ml_root=ml, repo_root=repo)


def test_dataset_b_access_requires_confirmation_and_blocks_duplicate(tmp_path: Path):
    ledger = EvaluationAccessLedger(tmp_path / "evaluation_access.json")
    kwargs = {
        "model_version": "v-test",
        "model_sha256": "abc",
        "purpose": "baseline_comparison",
        "reason": "Preregistered comparison",
        "authorized_by": "Taskin",
        "command": "python -m predict_rx.eval.baselines_setb",
    }
    with pytest.raises(PermissionError):
        ledger.record(**kwargs, confirmation="no")

    entry = ledger.record(**kwargs, confirmation=CONFIRMATION_TOKEN)
    assert entry["purpose"] == "baseline_comparison"
    assert len(ledger.read()["entries"]) == 1
    with pytest.raises(RuntimeError, match="already recorded"):
        ledger.record(**kwargs, confirmation=CONFIRMATION_TOKEN)


def test_authorize_dataset_b_flag_accepts_reason_or_token():
    confirmation, reason = resolve_authorization("Taskin authorizes this structural Dataset B audit only")
    assert confirmation == CONFIRMATION_TOKEN
    assert "structural" in reason
    confirmation, reason = resolve_authorization(CONFIRMATION_TOKEN, "legacy test reason")
    assert confirmation == CONFIRMATION_TOKEN
    assert reason == "legacy test reason"
