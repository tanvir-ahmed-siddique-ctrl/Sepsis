"""Short soak: continuous live-rate ingest for one hospital-sized ICU.

Unlike ``scale_check`` (worst-case 48-hour backfill), this advances one hour
of observations for every bed every tick — the real-time shape of a live feed —
and records latency, error rate and memory-relevant scale counters.

    ../.venv/Scripts/python.exe infra/soak_check.py --beds 20 --ticks 30 --interval 0

Writes docs/evidence/soak-check.{json,md}. Synthetic load only.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import settings  # noqa: E402

ADMIN = {"X-Demo-User": "soak", "X-Demo-Role": "admin"}
OUT = ROOT / "docs" / "evidence"
BASE = datetime(2026, 2, 1, 8, tzinfo=timezone.utc)


def hour_batch(bed: int, hour: int) -> list[dict]:
    stamp = (BASE + timedelta(hours=hour)).isoformat()
    pid = f"soak-{bed:02d}"
    return [
        {"patient_id": pid, "encounter_id": f"{pid}-enc", "timestamp": stamp,
         "code": code, "value": value, "unit": unit, "unit_id": settings.api_unit_id}
        for code, unit, value in (
            ("HR", "bpm", 80 + hour % 20), ("SBP", "mmHg", 120 - hour % 10),
            ("MAP", "mmHg", 80), ("Resp", "breaths/min", 16),
            ("Temp", "degC", 37.0), ("O2Sat", "%", 97),
        )
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--beds", type=int, default=20)
    parser.add_argument("--ticks", type=int, default=30, help="simulated hours advanced")
    parser.add_argument("--interval", type=float, default=0.0, help="seconds to sleep between ticks")
    args = parser.parse_args()

    work = Path(tempfile.mkdtemp(prefix="predictrx-soak-"))
    settings.demo_mode = True
    settings.public_demo_lockdown = False
    settings.writer_lease_enabled = True
    settings.database_url = f"sqlite:///{(work / 'site.db').as_posix()}"

    from fastapi.testclient import TestClient

    from app.main import app

    latencies: list[float] = []
    errors = 0
    observations = 0

    with TestClient(app, headers=ADMIN) as client:
        assert client.put("/v1/site/mode", json={"mode": "silent", "reason": "soak"}).status_code == 200
        # Seed 8 hours so the model has enough history before the soak ticks.
        for bed in range(1, args.beds + 1):
            seed = []
            for hour in range(8):
                seed.extend(hour_batch(bed, hour))
            assert client.post("/v1/observations/batch", json={"observations": seed}).status_code == 200

        started = time.perf_counter()
        for tick in range(args.ticks):
            hour = 8 + tick
            tick_start = time.perf_counter()
            batch = []
            for bed in range(1, args.beds + 1):
                batch.extend(hour_batch(bed, hour))
            response = client.post("/v1/observations/batch", json={"observations": batch})
            if response.status_code != 200:
                errors += 1
            else:
                observations += len(batch)
            latencies.append(time.perf_counter() - tick_start)
            if args.interval:
                time.sleep(args.interval)
        wall = time.perf_counter() - started
        status = client.get("/v1/ops/status").json()
        ready = client.get("/ready")

    report = {
        "format": "predictrx-soak-check/1",
        "load": f"{args.beds} beds x {args.ticks} live-rate ticks (6 vitals/bed/tick)",
        "observations": observations,
        "errors": errors,
        "wall_seconds": round(wall, 2),
        "tick_latency_seconds": {
            "median": round(statistics.median(latencies), 3),
            "p95": round(sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)], 3),
            "max": round(max(latencies), 3),
        },
        "throughput_obs_per_s": round(observations / wall, 1) if wall else None,
        "scale": status.get("scale"),
        "audit_chain_valid": bool(status["audit"]["linkage_valid"] and status["audit"]["content_hash_mismatches"] == 0),
        "ready": ready.status_code == 200,
        "passed": errors == 0 and ready.status_code == 200
        and bool(status["audit"]["linkage_valid"] and status["audit"]["content_hash_mismatches"] == 0),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "soak-check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Soak check (live-rate, synthetic)",
        "",
        f"- Load: {report['load']}",
        f"- Observations accepted: {observations:,} · Errors: {errors}",
        f"- Wall time: {report['wall_seconds']} s · Throughput: {report['throughput_obs_per_s']} obs/s",
        f"- Tick latency (seconds): median {report['tick_latency_seconds']['median']}, "
        f"p95 {report['tick_latency_seconds']['p95']}, max {report['tick_latency_seconds']['max']}",
        f"- Audit chain valid: `{report['audit_chain_valid']}` · /ready: `{report['ready']}`",
        f"- **Passed: `{report['passed']}`**",
        "",
        "Live-rate shape: one new hour of vitals per bed per tick. Distinct from the "
        "48-hour backfill stress in `docs/scalability.md`. Synthetic data only.",
        "",
    ]
    (OUT / "soak-check.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("observations", "errors", "tick_latency_seconds", "passed")}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
