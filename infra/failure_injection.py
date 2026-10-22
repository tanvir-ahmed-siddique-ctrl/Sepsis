"""Failure-injection run: prove the system fails predictably, never silently.

Injects the failure modes a hospital feed actually produces — duplicate
deliveries, late/out-of-order results, unknown units, implausible values,
malformed payloads, unauthorised writers, a stale feed — plus two boot-time
database failures, and records what the system observably did with each one.
Synthetic data only, on a throwaway database.

    ../.venv/Scripts/python.exe infra/failure_injection.py

Writes docs/evidence/failure-injection.json and .md. Exit 0 iff every
scenario behaved as required.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import settings  # noqa: E402

ADMIN = {"X-Demo-User": "failure-injection", "X-Demo-Role": "admin"}
NURSE = {"X-Demo-User": "failure-injection-nurse", "X-Demo-Role": "nurse"}
OUT_DIR = ROOT / "docs" / "evidence"
BASE = datetime(2026, 1, 5, 8, tzinfo=timezone.utc)

results: list[dict] = []


def record(scenario: str, injected: str, expected: str, observed: str, passed: bool) -> None:
    results.append({
        "scenario": scenario, "injected": injected, "expected": expected,
        "observed": observed, "passed": bool(passed),
    })
    print(f"{'PASS' if passed else 'FAIL'}  {scenario}: {observed}")


def vitals(patient: str, hour: int, *, hr: int = 88) -> list[dict]:
    stamp = (BASE + timedelta(hours=hour)).isoformat()
    return [
        {"patient_id": patient, "encounter_id": f"{patient}-enc", "timestamp": stamp,
         "code": code, "value": value, "unit": unit, "unit_id": settings.api_unit_id}
        for code, unit, value in (
            ("HR", "bpm", hr), ("SBP", "mmHg", 118), ("MAP", "mmHg", 78),
            ("Resp", "breaths/min", 18), ("Temp", "degC", 37.2), ("O2Sat", "%", 96),
        )
    ]


def hours_payload(patient: str, hours: range) -> list[dict]:
    rows: list[dict] = []
    for hour in hours:
        rows.extend(vitals(patient, hour, hr=88 + hour))
    return rows


def counts(body: dict) -> tuple[int, int, int]:
    def n(value: object) -> int:
        return len(value) if isinstance(value, (list, dict)) else int(value or 0)

    return (
        n(body.get("accepted", 0)),
        n(body.get("quarantined", 0)),
        n(body.get("duplicates", body.get("duplicates_ignored", 0))),
    )


def bed_card(client, patient: str) -> dict:
    overview = client.get(f"/v1/units/{settings.api_unit_id}/overview", headers=ADMIN).json()
    for card in overview.get("patients", []):
        if card.get("encounter_id") == f"{patient}-enc":
            return card
    return {}


def audit_events(client) -> int:
    return int(client.get("/v1/ops/status", headers=ADMIN).json()["audit"]["events_verified"])


def boot_probe(name: str, database_url: str) -> None:
    env = dict(os.environ, DEMO_MODE="true", DATABASE_URL=database_url, PYTHONPATH=str(ROOT / "backend"))
    code = (
        "from fastapi.testclient import TestClient\n"
        "from app.main import app\n"
        "with TestClient(app) as client:\n"
        "    print(client.get('/ready').status_code)\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code], cwd=str(ROOT), env=env,
        capture_output=True, text=True, timeout=300,
    )
    tail = (proc.stderr or proc.stdout).strip().splitlines()
    record(
        name,
        f"API boot with database_url={database_url!r}",
        "boot refuses to serve: non-zero exit with a database error, no silent fallback",
        f"exit={proc.returncode}; last error line: {tail[-1][:160] if tail else '(none)'}",
        proc.returncode != 0 and any("database" in line.lower() or "sqlite" in line.lower() for line in tail),
    )


def main() -> int:
    work = Path(tempfile.mkdtemp(prefix="predictrx-failures-"))
    settings.demo_mode = True
    settings.public_demo_lockdown = False
    settings.writer_lease_enabled = True
    settings.database_url = f"sqlite:///{(work / 'site.db').as_posix()}"

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        client.headers.update(ADMIN)
        assert client.put("/v1/site/mode", json={"mode": "silent", "reason": "failure injection"}).status_code == 200

        # Baseline: a healthy bed with 12 fresh hourly observations.
        base = client.post("/v1/observations/batch", json={"observations": hours_payload("fail-01", range(12))})
        accepted, _, _ = counts(base.json())
        record("baseline_ingest", "12 hourly full-vital sets for one bed",
               "all accepted, HTTP 200", f"HTTP {base.status_code}, accepted={accepted}",
               base.status_code == 200 and accepted == 72)

        # 1. Exact duplicate delivery, with an idempotency key. The safety
        # property is that nothing new is stored, whatever body is returned.
        first = client.post("/v1/observations/batch", headers={"Idempotency-Key": "fi-batch-1"},
                            json={"observations": vitals("fail-02", 0)})
        events_after_first = audit_events(client)
        second = client.post("/v1/observations/batch", headers={"Idempotency-Key": "fi-batch-1"},
                             json={"observations": vitals("fail-02", 0)})
        events_after_second = audit_events(client)
        a1, _, _ = counts(first.json())
        a2, _, d2 = counts(second.json())
        record("duplicate_with_idempotency_key", "identical batch sent twice with Idempotency-Key: fi-batch-1",
               "second delivery stores nothing new (audit log does not grow)",
               f"first accepted={a1}; second HTTP {second.status_code}, accepted={a2}, duplicates={d2}; "
               f"audit events {events_after_first} -> {events_after_second}",
               first.status_code == 200 and second.status_code in (200, 409)
               and events_after_second == events_after_first)

        # 2. Duplicate delivery without any key (engine-level dedupe).
        again = client.post("/v1/observations/batch", json={"observations": hours_payload("fail-01", range(12))})
        a3, _, d3 = counts(again.json())
        record("duplicate_without_key", "baseline batch re-sent with no idempotency key",
               "engine dedupes by encounter/code/timestamp; nothing double-counted",
               f"HTTP {again.status_code}, accepted={a3}, duplicates={d3}",
               again.status_code == 200 and a3 == 0 and d3 > 0)

        # 3. Late, out-of-order lab result arriving after later data exists.
        late = client.post("/v1/observations/batch", json={"observations": [
            {"patient_id": "fail-01", "encounter_id": "fail-01-enc",
             "timestamp": (BASE + timedelta(hours=3)).isoformat(), "code": "Lactate",
             "value": 2.4, "unit": "mmol/L", "unit_id": settings.api_unit_id},
        ]})
        a4, q4, _ = counts(late.json())
        card = bed_card(client, "fail-01")
        record("late_out_of_order_result", "Lactate timestamped hour 3 sent after hours 0-11 exist",
               "accepted as history (or explicitly quarantined); board still serves the bed",
               f"HTTP {late.status_code}, accepted={a4}, quarantined={q4}, bed visible={bool(card)}",
               late.status_code == 200 and bool(card))

        # 4. Unknown unit must be quarantined, never silently scored.
        bad_unit = client.post("/v1/observations/batch", json={"observations": [
            {"patient_id": "fail-01", "encounter_id": "fail-01-enc",
             "timestamp": (BASE + timedelta(hours=12)).isoformat(), "code": "HR",
             "value": 90, "unit": "furlongs/fortnight", "unit_id": settings.api_unit_id},
        ]})
        a5, q5, _ = counts(bad_unit.json())
        record("unknown_unit_quarantined", "HR 90 with unit 'furlongs/fortnight'",
               "quarantined for human mapping review; not accepted into scoring",
               f"HTTP {bad_unit.status_code}, accepted={a5}, quarantined={q5}",
               bad_unit.status_code == 200 and q5 >= 1 and a5 == 0)

        # 5. Physiologically implausible value.
        crazy = client.post("/v1/observations/batch", json={"observations": [
            {"patient_id": "fail-01", "encounter_id": "fail-01-enc",
             "timestamp": (BASE + timedelta(hours=12)).isoformat(), "code": "HR",
             "value": 9999, "unit": "bpm", "unit_id": settings.api_unit_id},
        ]})
        a6, q6, _ = counts(crazy.json())
        record("implausible_value_quarantined", "HR 9999 bpm",
               "quarantined by plausibility checks; not accepted into scoring",
               f"HTTP {crazy.status_code}, accepted={a6}, quarantined={q6}",
               crazy.status_code == 200 and q6 >= 1 and a6 == 0)

        # 6. Malformed payloads are rejected with 4xx and the service stays up.
        malformed = client.post("/v1/observations/batch", json={"observations": [{"code": "HR", "value": "very-high"}]})
        garbage = client.post("/v1/observations/batch", content=b"{not json",
                              headers={"Content-Type": "application/json"})
        ready = client.get("/ready")
        record("malformed_payload_rejected", "wrong-typed observation and invalid JSON body",
               "both rejected 4xx; /ready still 200 afterwards",
               f"wrong-type HTTP {malformed.status_code}, garbage HTTP {garbage.status_code}, /ready {ready.status_code}",
               malformed.status_code == 422 and garbage.status_code in (400, 422) and ready.status_code == 200)

        # 7. A clinical role may not write the feed.
        refused = client.post("/v1/observations/batch", headers=NURSE,
                              json={"observations": vitals("fail-03", 0)})
        record("unauthorised_writer_refused", "nurse role attempts to POST observations",
               "403; ingestion is admin/integration-key only",
               f"HTTP {refused.status_code}", refused.status_code == 403)

        # 8. Stale feed: 6-hour gap, then a single-signal update. Required
        # signals are now hours old inside the stream, so the score must be
        # marked stale and TrustGate must not present it as alertable.
        client.post("/v1/observations/batch", json={"observations": hours_payload("fail-stale", range(12))})
        before = bed_card(client, "fail-stale")
        gap = client.post("/v1/observations/batch", json={"observations": [
            {"patient_id": "fail-stale", "encounter_id": "fail-stale-enc",
             "timestamp": (BASE + timedelta(hours=18)).isoformat(), "code": "HR",
             "value": 132, "unit": "bpm", "unit_id": settings.api_unit_id},
        ]})
        after = bed_card(client, "fail-stale")
        record("stale_feed_not_alertable", "full vitals hours 0-11, then one HR at hour 18 (6h gap)",
               "freshness degrades, trust state is verify/abstain, never 'alert' on stale data",
               f"before trust={before.get('trust_state')}; after trust={after.get('trust_state')}, "
               f"freshness_min={after.get('data_freshness_minutes')}, ingest HTTP {gap.status_code}",
               gap.status_code == 200 and after.get("trust_state") in ("verify_data", "abstain"))

    # 9-10. Boot-time database failures must fail loudly (separate processes).
    boot_probe("db_unavailable_at_boot", f"sqlite:///{(work / 'missing-dir' / 'site.db').as_posix()}")
    corrupt = work / "corrupt.db"
    corrupt.write_bytes(b"this is not a sqlite database" * 16)
    boot_probe("corrupt_db_at_boot", f"sqlite:///{corrupt.as_posix()}")

    report = {
        "format": "predictrx-failure-injection/1",
        "load": "synthetic failure-injection beds on a throwaway SQLite database",
        "scenarios": results,
        "passed": all(item["passed"] for item in results),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "failure-injection.json").write_text(json.dumps(report, indent=2))
    lines = [
        "# Failure-injection run (measured)", "",
        "| Scenario | Injected failure | Expected | Observed | Result |",
        "|---|---|---|---|---|",
    ]
    for item in results:
        lines.append(
            f"| {item['scenario']} | {item['injected']} | {item['expected']} | "
            f"{item['observed']} | {'PASS' if item['passed'] else 'FAIL'} |"
        )
    lines += ["", f"**All scenarios passed: `{report['passed']}`**", "",
              "Generated by `infra/failure_injection.py` with synthetic data on a throwaway database.", ""]
    (OUT_DIR / "failure-injection.md").write_text("\n".join(lines))
    print(json.dumps({"scenarios": len(results), "passed": report["passed"]}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
