"""Site operations CLI: logical backup/restore, audit verification, credential hashing.

    python -m app.ops_cli backup --out backups/predictrx-2026-10-16.json.gz
    python -m app.ops_cli restore --input backups/predictrx-2026-10-16.json.gz
    python -m app.ops_cli verify-audit
    python -m app.ops_cli new-integration-key --key-id lab-feed --units icu-a --scopes ingest:hl7v2
    python -m app.ops_cli check-config
    python -m app.ops_cli decommission --final-backup final.json.gz --confirm-site-id <SITE_ID> --certificate closeout.json

Backups are logical (JSON rows per table) so they restore across SQLite and PostgreSQL.
They contain identifiable clinical data: store them encrypted, on site, with access control.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import secrets
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import insert, select, text

from app.accounts import AccountStore
from app.core.config import settings
from app.observability import verify_audit_chain
from app.persistence import StateStore
from app.records import RecordStore, metadata, writer_lease

BACKUP_FORMAT = "predictrx-logical-backup/1"
LEASE_KEY = "engine-writer"
CORE_TABLES = ("engine_state", "audit_events")
SKIPPED_TABLES = {"writer_lease"}


def _open(database_url: str) -> tuple[StateStore, RecordStore]:
    state = StateStore(database_url)
    return state, RecordStore(state.engine)


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, separators=(",", ":"), default=str).encode()
    if path.suffix == ".gz":
        data = gzip.compress(data)
    path.write_bytes(data)


def _read(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    if path.suffix == ".gz":
        data = gzip.decompress(data)
    return json.loads(data)


def _digest(tables: dict[str, list[dict[str, Any]]]) -> str:
    return hashlib.sha256(json.dumps(tables, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _active_writer(records: RecordStore) -> dict[str, Any] | None:
    lease = records.lease_info(LEASE_KEY)
    if lease and lease["heartbeat_at"] >= time.time() - settings.writer_lease_seconds:
        return lease
    return None


def _snapshot(state: StateStore) -> dict[str, list[dict[str, Any]]]:
    tables: dict[str, list[dict[str, Any]]] = {}
    with state.engine.connect() as connection:
        with connection.begin():
            for name in CORE_TABLES:
                order = " ORDER BY ordinal" if name == "audit_events" else ""
                tables[name] = [dict(row._mapping) for row in connection.execute(text(f"SELECT * FROM {name}{order}"))]
            for table in metadata.sorted_tables:
                if table.name not in SKIPPED_TABLES:
                    tables[table.name] = [dict(row._mapping) for row in connection.execute(select(table))]
    return tables


def _verified_archive(source: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = _read(source)
    if payload.get("format") != BACKUP_FORMAT:
        raise SystemExit(f"Unsupported backup format: {payload.get('format')!r}")
    if _digest(payload["tables"]) != payload["sha256"]:
        raise SystemExit("Backup checksum mismatch — file is corrupt or was edited.")
    audit = [json.loads(row["payload"]) for row in payload["tables"]["audit_events"]]
    chain = verify_audit_chain(audit)
    if not chain["linkage_valid"] or chain["content_hash_mismatches"]:
        raise SystemExit(f"Audit chain in backup failed verification: {chain}")
    return payload, chain


def _wipe(connection) -> None:
    for table in reversed(metadata.sorted_tables):
        connection.execute(table.delete())
    for name in CORE_TABLES:
        connection.execute(text(f"DELETE FROM {name}"))


def backup(database_url: str, out: Path) -> dict[str, Any]:
    state, records = _open(database_url)
    tables = _snapshot(state)
    audit = [json.loads(row["payload"]) for row in tables["audit_events"]]
    payload = {
        "format": BACKUP_FORMAT,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_dialect": state.engine.dialect.name,
        "active_writer_at_backup": (_active_writer(records) or {}).get("holder"),
        "counts": {name: len(rows) for name, rows in tables.items()},
        "audit_head_hash": audit[-1]["event_hash"] if audit else None,
        "sha256": _digest(tables),
        "tables": tables,
    }
    _write(out, payload)
    return {key: value for key, value in payload.items() if key != "tables"}


def restore(database_url: str, source: Path, force: bool = False) -> dict[str, Any]:
    payload, chain = _verified_archive(source)
    tables = payload["tables"]

    state, records = _open(database_url)
    writer = _active_writer(records)
    if writer:
        raise SystemExit(f"Refusing to restore while writer {writer['holder']} holds the lease. Stop the API first.")
    with state.engine.connect() as connection:
        existing = connection.execute(text("SELECT COUNT(*) FROM audit_events")).scalar_one()
    if existing and not force:
        raise SystemExit(f"Target database already has {existing} audit events. Use --force to replace its contents.")

    by_name = {table.name: table for table in metadata.sorted_tables}
    with state.engine.begin() as connection:
        _wipe(connection)
        for name, rows in tables.items():
            if not rows:
                continue
            if name in CORE_TABLES:
                columns = list(rows[0].keys())
                statement = text(
                    f"INSERT INTO {name} ({', '.join(columns)}) VALUES ({', '.join(':' + column for column in columns)})"
                )
                connection.execute(statement, rows)
            elif name in by_name:
                connection.execute(insert(by_name[name]), rows)
        connection.execute(writer_lease.delete())
    return {"restored_from": str(source), "counts": payload["counts"], "audit": chain}


def decommission(database_url: str, final_backup: Path, confirm_site_id: str, certificate: Path) -> dict[str, Any]:
    """Offboard a site: prove the hospital holds a complete copy, then erase this database."""
    if confirm_site_id != settings.site_id:
        raise SystemExit(f"--confirm-site-id {confirm_site_id!r} does not match SITE_ID {settings.site_id!r}.")
    payload, chain = _verified_archive(final_backup)
    state, records = _open(database_url)
    writer = _active_writer(records)
    if writer:
        raise SystemExit(f"Refusing to decommission while writer {writer['holder']} holds the lease. Stop the API first.")
    live = _snapshot(state)
    if _digest(live) != payload["sha256"]:
        raise SystemExit("Final backup does not match the current database. Take a new backup with the API stopped.")

    with state.engine.begin() as connection:
        _wipe(connection)
        connection.execute(writer_lease.delete())
    if state.engine.dialect.name in {"sqlite", "postgresql"}:
        with state.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.exec_driver_sql("VACUUM" if state.engine.dialect.name == "sqlite" else "VACUUM FULL")
    remaining = {name: len(rows) for name, rows in _snapshot(state).items() if rows}
    if remaining:
        raise SystemExit(f"Erase incomplete; rows remain in {remaining}.")

    from app.services.engine import _active_model_path

    record = {
        "format": "predictrx-decommission-certificate/1",
        "site_id": settings.site_id,
        "decommissioned_at": datetime.now(timezone.utc).isoformat(),
        "database": state.engine.dialect.name,
        "final_backup": {
            "file": final_backup.name,
            "file_sha256": hashlib.sha256(final_backup.read_bytes()).hexdigest(),
            "content_sha256": payload["sha256"],
            "created_at": payload["created_at"],
            "counts": payload["counts"],
        },
        "audit_head_hash_at_closure": payload["audit_head_hash"],
        "audit_events_verified": chain["events_verified"],
        "rows_erased": sum(payload["counts"].values()),
        "rows_remaining": 0,
        "model_sha256": hashlib.sha256(_active_model_path().read_bytes()).hexdigest(),
        "still_required_from_site": [
            "Hand the final backup to the data controller; store it encrypted under the hospital retention schedule.",
            "Destroy the database volume and any other backup copies (docker volume rm, disk crypto-erase).",
            "Revoke integration keys, OIDC client, metrics token, fleet signing key and support accounts.",
            "Remove PredictRx from the hospital reverse proxy and firewall rules.",
        ],
    }
    certificate.parent.mkdir(parents=True, exist_ok=True)
    certificate.write_text(json.dumps(record, indent=2))
    return record


def verify(database_url: str) -> dict[str, Any]:
    state, _ = _open(database_url)
    return verify_audit_chain(state.load_audit())


def new_integration_key(key_id: str, scopes: list[str], units: list[str] | None) -> dict[str, Any]:
    secret = secrets.token_urlsafe(32)
    entry = {"key_id": key_id, "sha256": hashlib.sha256(secret.encode()).hexdigest(), "scopes": scopes, "units": units}
    return {
        "give_to_interface_engine": f"X-Integration-Key: {key_id}.{secret}",
        "add_to_INTEGRATION_API_KEYS": entry,
        "note": "The secret is shown once. Only the SHA-256 goes into server configuration.",
    }


def bootstrap_admin(database_url: str, user_id: str, display_name: str, password: str) -> dict[str, Any]:
    state, records = _open(database_url)
    store = AccountStore(records)
    if store.count():
        raise SystemExit("Refusing to bootstrap: local users already exist. Use the admin user-management screen.")
    try:
        return store.create(
            user_id,
            display_name,
            "admin",
            password,
            units=None,
            actor_id="ops-cli-bootstrap",
            must_change_password=True,
        )
    except ValueError as error:
        raise SystemExit(str(error)) from error


def check_config() -> dict[str, Any]:
    from app.auth import production_security_ready, validate_security_configuration

    from app.integrations.copilot import llm_endpoint

    problems: list[str] = []
    try:
        validate_security_configuration()
    except RuntimeError as error:
        problems.append(str(error))
    llm = llm_endpoint()
    if llm["external"] and not settings.demo_mode and not settings.copilot_external_llm_approved:
        problems.append(
            f"COPILOT_LLM_URL points outside the hospital network ({llm['host']}); calls are refused until "
            "the site approves it with COPILOT_EXTERNAL_LLM_APPROVED=true."
        )
    return {
        "demo_mode": settings.demo_mode,
        "site_mode_at_first_start": settings.site_mode,
        "auth_mode": settings.auth_mode,
        "database": settings.database_url.split("://", 1)[0],
        "integration_keys": len(settings.integration_api_keys),
        "metrics_token_set": bool(settings.metrics_token),
        "copilot_llm": {**llm, "configured": bool(settings.copilot_llm_url),
                        "external_approved": settings.copilot_external_llm_approved},
        "production_security_ready": production_security_ready(),
        "problems": problems,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.ops_cli", description=__doc__.split("\n\n")[0])
    parser.add_argument("--database-url", default=None, help="Defaults to DATABASE_URL")
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("backup", help="Write a logical JSON backup (.json or .json.gz)")
    b.add_argument("--out", type=Path, required=True)
    r = sub.add_parser("restore", help="Restore a logical backup into an empty (or --force) database")
    r.add_argument("--input", type=Path, required=True)
    r.add_argument("--force", action="store_true")
    sub.add_parser("verify-audit", help="Verify the hash-chained audit log")
    k = sub.add_parser("new-integration-key", help="Generate a scoped connector credential")
    k.add_argument("--key-id", required=True)
    k.add_argument("--scopes", default="ingest:json,ingest:fhir,ingest:hl7v2")
    k.add_argument("--units", default=None, help="Comma-separated unit scope; omit for all units")
    u = sub.add_parser("bootstrap-admin", help="Create the first local administrator (only when no users exist)")
    u.add_argument("--user-id", required=True)
    u.add_argument("--display-name", required=True)
    u.add_argument("--password", required=True)
    sub.add_parser("check-config", help="Report whether the configuration is safe for a non-demo site")
    d = sub.add_parser("decommission", help="Offboard: verify the final backup matches, erase all data, write a certificate")
    d.add_argument("--final-backup", type=Path, required=True)
    d.add_argument("--confirm-site-id", required=True)
    d.add_argument("--certificate", type=Path, required=True)
    args = parser.parse_args(argv)
    database_url = args.database_url or settings.database_url

    if args.command == "backup":
        result = backup(database_url, args.out)
    elif args.command == "restore":
        result = restore(database_url, args.input, args.force)
    elif args.command == "verify-audit":
        result = verify(database_url)
    elif args.command == "new-integration-key":
        units = [unit.strip() for unit in args.units.split(",") if unit.strip()] if args.units else None
        result = new_integration_key(args.key_id, [s.strip() for s in args.scopes.split(",") if s.strip()], units)
    elif args.command == "bootstrap-admin":
        result = bootstrap_admin(database_url, args.user_id, args.display_name, args.password)
    elif args.command == "decommission":
        result = decommission(database_url, args.final_backup, args.confirm_site_id, args.certificate)
    else:
        result = check_config()
    print(json.dumps(result, indent=2, default=str))
    if args.command == "verify-audit" and (not result["linkage_valid"] or result["content_hash_mismatches"]):
        return 2
    if args.command == "check-config" and result["problems"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
