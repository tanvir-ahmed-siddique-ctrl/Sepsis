"""Site-mode round trips must never 500 — including across an engine restart.

Regression cover for the public-demo failure where switching silent -> demo
returned Internal Server Error. The public image now also locks mode changes
(see test_roles), but hospital installations keep audited mode changes, so the
round trip itself must stay healthy with persisted state in between.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings

pytestmark = pytest.mark.skipif(
    not (Path(settings.model_path).exists() and (Path(settings.demo_cases_dir) / "manifest.json").exists()),
    reason="model bundle or demo cases not generated",
)

ADMIN = {"X-Demo-User": "mode-admin", "X-Demo-Role": "admin"}
ACTOR = SimpleNamespace(user_id="mode-test", role="admin")


@pytest.fixture(scope="module")
def client():
    settings.database_url = "sqlite:///:memory:"
    settings.demo_mode = True
    settings.public_demo_lockdown = False
    from app.main import app

    with TestClient(app, headers=ADMIN) as c:
        yield c


def test_silent_demo_roundtrip_twice_never_500(client):
    for _ in range(2):
        silent = client.put("/v1/site/mode", json={"mode": "silent", "reason": "roundtrip test"})
        assert silent.status_code == 200, silent.text
        assert silent.json()["site"]["effective_mode"] == "silent"
        demo = client.put("/v1/site/mode", json={"mode": "demo", "reason": "roundtrip test back"})
        assert demo.status_code == 200, demo.text
        assert demo.json()["site"]["effective_mode"] == "demo"
        status = client.get("/v1/demo/replay/status")
        assert status.status_code == 200
        assert status.json()["patients"], "replay beds must be restored after returning to demo"


def test_mode_roundtrip_survives_engine_restart(tmp_path, monkeypatch):
    from app.services.engine import Engine

    monkeypatch.setattr(settings, "database_url", f"sqlite:///{(tmp_path / 'site.db').as_posix()}")
    monkeypatch.setattr(settings, "demo_mode", True)
    monkeypatch.setattr(settings, "public_demo_lockdown", False)
    monkeypatch.setattr(settings, "writer_lease_enabled", True)

    first = Engine()
    try:
        assert first.site.state.effective_mode == "demo"
        first.set_site_mode("silent", ACTOR, "restart roundtrip", [])
        assert first.site.state.effective_mode == "silent"
    finally:
        first.close()

    second = Engine()
    try:
        # Persisted requested mode is authoritative after restart.
        assert second.site.state.effective_mode == "silent"
        result = second.set_site_mode("demo", ACTOR, "restart roundtrip back", [])
        assert result["effective_mode"] == "demo"
        assert any(p.source_mode == "replay" for p in second.patients.values())

        # Incremental snapshots: an unchanged persist rewrites nothing, and a
        # one-patient change rewrites only that patient's entry.
        api_patients = [p for p in second.patients.values() if p.source_mode == "api"]
        assert api_patients, "seeded api encounters should survive the round trip"
        writes_before = second.snapshot_writes_total
        second._persist_state()
        assert second.snapshot_writes_total == writes_before
        api_patients[0].revision += 1
        second._persist_state()
        assert second.snapshot_writes_total == writes_before + 1
    finally:
        second.close()
