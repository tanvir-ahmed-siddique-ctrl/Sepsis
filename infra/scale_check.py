"""Single-site scale check: how much can one hospital instance carry?

Boots the real API against a throwaway SQLite file, switches to silent mode,
ingests hourly vitals (+ 6-hourly labs) for N synthetic beds through the public
native-JSON endpoint, then measures ingest throughput, scoring time, read
latency, snapshot persistence and restart recovery. Synthetic load only — this
is an engineering capacity check, never clinical evidence.

    ../.venv/Scripts/python.exe infra/scale_check.py --beds 30 --hours 48

Run from the repository root or backend/; it inserts backend/ on sys.path.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import settings  # noqa: E402

ADMIN = {"X-Demo-User": "scale-check", "X-Demo-Role": "admin"}
VITALS = (
    ("HR", "bpm", 88),
    ("SBP", "mmHg", 118),
    ("MAP", "mmHg", 78),
    ("Resp", "breaths/min", 18),
    ("Temp", "degC", 37.2),
    ("O2Sat", "%", 96),
)
LABS = (
    ("Lactate", "mmol/L", 1.4),
    ("Creatinine", "mg/dL", 1.0),
    ("WBC", "10^3/uL", 9.0),
    ("Platelets", "10^3/uL", 220),
)


def observations(bed: int, hours: int, start: datetime) -> list[dict]:
    rows: list[dict] = []
    deteriorating = bed % 3 == 0
    for hour in range(hours):
        drift = hour / max(hours - 1, 1) if deteriorating else 0.0
        wobble = math.sin(hour * 1.3 + bed)
        stamp = (start + timedelta(hours=hour)).isoformat()
        for code, unit, base in VITALS:
            value = base * (1 + 0.25 * drift) + wobble if code == "HR" else base + drift * (6 if code == "Resp" else -4 if code in {"SBP", "MAP", "O2Sat"} else 0.8) + wobble * 0.3
            rows.append({
                "patient_id": f"scale-{bed:03d}", "encounter_id": f"scale-{bed:03d}-enc",
                "timestamp": stamp, "code": code, "value": round(float(value), 2), "unit": unit,
                "unit_id": settings.api_unit_id,
            })
        if hour % 6 == 0:
            for code, unit, base in LABS:
                rows.append({
                    "patient_id": f"scale-{bed:03d}", "encounter_id": f"scale-{bed:03d}-enc",
                    "timestamp": stamp, "code": code, "value": round(float(base * (1 + 0.8 * drift)), 2), "unit": unit,
                    "unit_id": settings.api_unit_id,
                })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--beds", type=int, default=30)
    parser.add_argument("--hours", type=int, default=48)
    args = parser.parse_args()

    db_path = Path(tempfile.mkdtemp(prefix="predictrx-scale-")) / "scale.db"
    settings.database_url = f"sqlite:///{db_path.as_posix()}"
    settings.demo_mode = True
    settings.public_demo_lockdown = False
    settings.writer_lease_enabled = True

    from fastapi.testclient import TestClient

    from app.main import app
    from app.services.engine import get_engine

    start = datetime(2026, 1, 5, 8, tzinfo=timezone.utc)
    report: dict = {"beds": args.beds, "hours_per_bed": args.hours, "database": "sqlite (throwaway file)"}

    boot_started = time.perf_counter()
    with TestClient(app, headers=ADMIN) as client:
        report["boot_seconds"] = round(time.perf_counter() - boot_started, 2)
        mode = client.put("/v1/site/mode", json={"mode": "silent", "reason": "scale check"})
        assert mode.status_code == 200, mode.text

        ingest_seconds = []
        total_observations = 0
        for bed in range(1, args.beds + 1):
            payload = observations(bed, args.hours, start)
            total_observations += len(payload)
            began = time.perf_counter()
            response = client.post("/v1/observations/batch", json={"observations": payload})
            ingest_seconds.append(time.perf_counter() - began)
            assert response.status_code == 200, response.text[:300]
            assert response.json()["quarantined"] == [], response.text[:300]
        report["observations_ingested"] = total_observations
        report["ingest_seconds_total"] = round(sum(ingest_seconds), 2)
        report["ingest_observations_per_second"] = round(total_observations / sum(ingest_seconds), 1)
        report["ingest_batch_seconds_median"] = round(statistics.median(ingest_seconds), 3)

        engine = get_engine()
        with engine.lock:
            scored = sum(len(p.predictions) for p in engine.patients.values() if p.source_mode == "api" and p.patient_id.startswith("scale-"))
            report["scale_bed_predictions"] = scored
            report["snapshot_last_persist_ms"] = engine.snapshot_last_persist_ms
            report["snapshot_writes_total"] = engine.snapshot_writes_total
            report["snapshot_kb_written_total"] = round(engine.snapshot_bytes_written_total / 1024, 1)
            report["audit_events"] = len(engine.audit)

        read_seconds = []
        for _ in range(5):
            began = time.perf_counter()
            overview = client.get(f"/v1/units/{settings.api_unit_id}/overview")
            read_seconds.append(time.perf_counter() - began)
            assert overview.status_code == 200, overview.text[:200]
        report["unit_overview_seconds_median"] = round(statistics.median(read_seconds), 3)
        report["database_mb"] = round(db_path.stat().st_size / 1e6, 2) if db_path.exists() else None

    restart_started = time.perf_counter()
    with TestClient(app, headers=ADMIN) as client:
        report["restart_boot_seconds"] = round(time.perf_counter() - restart_started, 2)
        status = client.get("/v1/ops/status")
        assert status.status_code == 200, status.text[:200]
        report["ops_scale_after_restart"] = status.json()["scale"]
        # Silent mode blinds bedside cards by design, so encounter recovery is
        # verified from operator metadata, not the clinical board.
        report["api_encounters_after_restart"] = status.json()["scale"]["api_encounters"]

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
