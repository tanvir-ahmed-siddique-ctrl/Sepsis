"""Evaluation seed must use only formula-generated records and a separate local account."""

from __future__ import annotations

import importlib.util
import socket
from pathlib import Path

from pydantic import SecretStr

from app.accounts import AccountStore
from app.core.config import settings
from app.services.engine import Engine


def test_synthetic_evaluation_engine_and_account(tmp_path, monkeypatch):
    generator = Path(__file__).resolve().parents[2] / "demo" / "generate_synthetic_eval.py"
    spec = importlib.util.spec_from_file_location("generate_synthetic_eval", generator)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cases = tmp_path / "cases"
    module.generate(cases, count=4)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{(tmp_path / 'evaluation.db').as_posix()}")
    monkeypatch.setattr(settings, "demo_cases_dir", str(cases))
    monkeypatch.setattr(settings, "demo_mode", True)
    monkeypatch.setattr(settings, "public_demo_lockdown", True)
    monkeypatch.setattr(settings, "public_simulation_enabled", False)
    monkeypatch.setattr(settings, "evaluation_runtime", True)
    monkeypatch.setattr(settings, "evaluation_admin_password", SecretStr("evaluation-hospital-secret-123"))
    engine = Engine()
    try:
        assert len([patient for patient in engine.patients.values() if patient.source_mode == "replay"]) == 4
        assert "synthetic" in engine.manifest["source_split"].lower()
        assert AccountStore(engine.records).authenticate_password("eval-admin", "evaluation-hospital-secret-123")
        assert all(patient.replay_meta["labelled_onset_hour"] is None for patient in engine.patients.values() if patient.source_mode == "replay")
    finally:
        engine.close()


def test_local_engine_and_auth_start_without_outbound_network(tmp_path, monkeypatch):
    def blocked(*_args, **_kwargs):
        raise AssertionError("Core local operation attempted an outbound socket")
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{(tmp_path / 'offline.db').as_posix()}")
    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "evaluation_runtime", False)
    monkeypatch.setattr(settings, "site_mode", "silent")
    monkeypatch.setattr(settings, "public_simulation_enabled", False)
    engine = Engine()
    try:
        assert engine.site.state.effective_mode == "silent"
        assert engine.model_version
        assert engine.model_hash
    finally:
        engine.close()
