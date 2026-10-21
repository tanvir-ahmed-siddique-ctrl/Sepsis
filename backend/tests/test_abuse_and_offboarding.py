"""Abuse limits (rate budgets, body size) and site decommissioning."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.ratelimit import LIMITER, RateLimiter

pytestmark = pytest.mark.skipif(
    not (Path(settings.model_path).exists() and (Path(settings.demo_cases_dir) / "manifest.json").exists()),
    reason="model bundle or demo cases not generated",
)

ADMIN = {"X-Demo-User": "abuse-admin", "X-Demo-Role": "admin"}


@pytest.fixture(scope="module")
def client():
    settings.database_url = "sqlite:///:memory:"
    settings.demo_mode = True
    from app.main import app

    with TestClient(app, headers=ADMIN) as c:
        yield c


@pytest.fixture(autouse=True)
def fresh_budgets():
    LIMITER.reset()
    yield
    LIMITER.reset()


def test_fixed_window_budget():
    limiter = RateLimiter()
    assert all(limiter.hit("api", "a", 3, now=120.0) is None for _ in range(3))
    assert limiter.hit("api", "a", 3, now=150.0) == pytest.approx(30.0)
    assert limiter.hit("api", "b", 3, now=150.0) is None
    assert limiter.hit("api", "a", 3, now=180.0) is None


def test_api_budget_is_per_client_and_spares_health(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_per_minute", 3)
    assert [client.get("/v1/model").status_code for _ in range(3)] == [200, 200, 200]
    limited = client.get("/v1/model")
    assert limited.status_code == 429 and int(limited.headers["Retry-After"]) >= 1
    other = client.get("/v1/model", headers={"X-Demo-User": "someone-else", "X-Demo-Role": "admin"})
    assert other.status_code == 200
    assert client.get("/health").status_code == 200
    monkeypatch.setattr(settings, "rate_limit_per_minute", 10_000)
    assert 'predictrx_requests_rejected_total{bucket="api",reason="rate_limited"}' in client.get("/metrics").text


def test_login_guessing_is_limited_by_address(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_login_per_minute", 2)
    codes = [client.post("/v1/auth/login", json={"username": f"u{i}", "password": "x" * 12}).status_code
             for i in range(3)]
    assert codes[-1] == 429 and 429 not in codes[:2]


def test_oversized_body_rejected_before_parsing(client, monkeypatch):
    monkeypatch.setattr(settings, "max_request_bytes", 1024)
    response = client.post("/v1/integrations/csv/lab", content=b"x" * 2048, headers={"Content-Type": "text/csv"})
    assert response.status_code == 413


def test_decommission_requires_matching_final_backup(tmp_path, monkeypatch):
    from app import ops_cli
    from app.schemas import ObservationIn
    from app.services.engine import Engine

    url = f"sqlite:///{(tmp_path / 'site.db').as_posix()}"
    monkeypatch.setattr(settings, "database_url", url)
    t0 = datetime(2026, 7, 1, tzinfo=timezone.utc)

    def admit(patient: str) -> None:
        engine = Engine()
        try:
            engine.ingest([
                ObservationIn(patient_id=patient, encounter_id="e1", unit_id="icu-b", timestamp=t0 + timedelta(hours=h),
                              code=code, value=value)
                for h in range(3) for code, value in (("HR", 95), ("MAP", 70), ("SBP", 110), ("O2Sat", 95))
            ])
        finally:
            engine.close()

    admit("closeout-a")
    stale = tmp_path / "stale.json.gz"
    ops_cli.backup(url, stale)
    admit("closeout-b")
    certificate = tmp_path / "closeout.json"

    with pytest.raises(SystemExit, match="does not match SITE_ID"):
        ops_cli.decommission(url, stale, "some-other-site", certificate)
    with pytest.raises(SystemExit, match="does not match the current database"):
        ops_cli.decommission(url, stale, settings.site_id, certificate)

    final = tmp_path / "final.json.gz"
    summary = ops_cli.backup(url, final)
    record = ops_cli.decommission(url, final, settings.site_id, certificate)
    assert record["rows_remaining"] == 0 and record["rows_erased"] == sum(summary["counts"].values())
    assert record["audit_head_hash_at_closure"] == summary["audit_head_hash"]
    assert json.loads(certificate.read_text())["final_backup"]["content_sha256"] == summary["sha256"]
    assert sum(ops_cli.backup(url, tmp_path / "after.json")["counts"].values()) == 0

    ops_cli.restore(f"sqlite:///{(tmp_path / 'archive-check.db').as_posix()}", final)
