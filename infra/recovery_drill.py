"""Disaster-recovery drill: backup → restore → audit verification → restart.

Runs the real API against a throwaway database, ingests a small synthetic
load, stops the engine, takes an `ops_cli` logical backup, restores it into a
fresh database, verifies the hash-chained audit log, boots the API again and
checks every encounter survived. Synthetic load only; this measures recovery
behaviour, never clinical performance.

    ../.venv/Scripts/python.exe infra/recovery_drill.py

Writes docs/evidence/recovery-drill.json and .md with measured timings.
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import settings  # noqa: E402

ADMIN = {"X-Demo-User": "recovery-drill", "X-Demo-Role": "admin"}
OUT_DIR = ROOT / "docs" / "evidence"


def payload(bed: int, hours: int = 12) -> list[dict]:
    start = datetime(2026, 1, 5, 8, tzinfo=timezone.utc)
    rows = []
    for hour in range(hours):
        stamp = (start + timedelta(hours=hour)).isoformat()
        for code, unit, value in (
            ("HR", "bpm", 88 + hour), ("SBP", "mmHg", 118 - hour), ("MAP", "mmHg", 78),
            ("Resp", "breaths/min", 18), ("Temp", "degC", 37.2), ("O2Sat", "%", 96),
        ):
            rows.append({
                "patient_id": f"drill-{bed:02d}", "encounter_id": f"drill-{bed:02d}-enc",
                "timestamp": stamp, "code": code, "value": value, "unit": unit,
                "unit_id": settings.api_unit_id,
            })
    return rows


def main() -> int:
    work = Path(tempfile.mkdtemp(prefix="predictrx-drill-"))
    db1 = f"sqlite:///{(work / 'site-a.db').as_posix()}"
    db2 = f"sqlite:///{(work / 'site-b.db').as_posix()}"
    backup_file = work / "backup.json.gz"

    settings.demo_mode = True
    settings.public_demo_lockdown = False
    settings.writer_lease_enabled = True
    settings.database_url = db1

    from fastapi.testclient import TestClient

    from app import ops_cli
    from app.main import app

    report: dict = {"format": "predictrx-recovery-drill/1", "load": "2 synthetic beds x 12 hourly observations"}

    phase1_start = time.perf_counter()
    with TestClient(app, headers=ADMIN) as client:
        assert client.put("/v1/site/mode", json={"mode": "silent", "reason": "recovery drill"}).status_code == 200
        for bed in (1, 2):
            response = client.post("/v1/observations/batch", json={"observations": payload(bed)})
            assert response.status_code == 200, response.text[:300]
        before = client.get("/v1/ops/status").json()
        report["before"] = {
            "api_encounters": before["scale"]["api_encounters"],
            "audit_events_verified": before["audit"]["events_verified"],
            "audit_chain_valid": bool(before["audit"]["linkage_valid"] and before["audit"]["content_hash_mismatches"] == 0),
        }
    report["phase1_seconds"] = round(time.perf_counter() - phase1_start, 2)

    started = time.perf_counter()
    backup_result = ops_cli.backup(db1, backup_file)
    report["backup_seconds"] = round(time.perf_counter() - started, 2)
    report["backup_counts"] = backup_result["counts"]
    report["backup_audit_head"] = backup_result["audit_head_hash"]

    started = time.perf_counter()
    restore_result = ops_cli.restore(db2, backup_file)
    report["restore_seconds"] = round(time.perf_counter() - started, 2)
    report["restore_audit"] = restore_result["audit"]

    chain = ops_cli.verify(db2)
    report["audit_verify_after_restore"] = chain
    assert chain["linkage_valid"] and chain["content_hash_mismatches"] == 0

    settings.database_url = db2
    started = time.perf_counter()
    with TestClient(app, headers=ADMIN) as client:
        ready = client.get("/ready")
        after = client.get("/v1/ops/status").json()
    report["recovery_boot_seconds"] = round(time.perf_counter() - started, 2)
    report["ready_after_restore"] = ready.status_code == 200
    report["after"] = {
        "api_encounters": after["scale"]["api_encounters"],
        "audit_events_verified": after["audit"]["events_verified"],
        "audit_chain_valid": bool(after["audit"]["linkage_valid"] and after["audit"]["content_hash_mismatches"] == 0),
    }
    report["rto_seconds_measured"] = round(report["restore_seconds"] + report["recovery_boot_seconds"], 2)
    report["rpo"] = "0 for this drill: backup taken after a clean engine stop. Online backups are transaction-consistent; "
    report["rpo"] += "the accepted data-loss window in production is the time since the last scheduled backup."
    report["passed"] = bool(
        report["ready_after_restore"]
        and report["after"]["api_encounters"] == report["before"]["api_encounters"]
        and report["after"]["audit_events_verified"] == report["before"]["audit_events_verified"]
        and report["after"]["audit_chain_valid"]
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "recovery-drill.json").write_text(json.dumps(report, indent=2))
    lines = [
        "# Recovery drill (measured)",
        "",
        f"- Load: {report['load']}",
        f"- Before: {report['before']['api_encounters']} API encounters, "
        f"{report['before']['audit_events_verified']} audit events, chain valid `{report['before']['audit_chain_valid']}`",
        f"- Backup: {report['backup_seconds']} s · Restore: {report['restore_seconds']} s · "
        f"Reboot after restore: {report['recovery_boot_seconds']} s",
        f"- Measured RTO (restore + reboot): **{report['rto_seconds_measured']} s**",
        f"- RPO: {report['rpo']}",
        f"- After: {report['after']['api_encounters']} API encounters, "
        f"{report['after']['audit_events_verified']} audit events, chain valid `{report['after']['audit_chain_valid']}`, "
        f"/ready OK `{report['ready_after_restore']}`",
        f"- **Drill passed: `{report['passed']}`**",
        "",
        "Generated by `infra/recovery_drill.py` on a throwaway SQLite database with synthetic load.",
        "",
    ]
    (OUT_DIR / "recovery-drill.md").write_text("\n".join(lines))
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
