"""Row-level pilot evidence, connector, and governance records.

These tables sit beside the engine restart snapshot. Prediction, outcome, feedback,
handoff-note and export rows are append-only; ownership and site configuration are
mutable but every change is also written to the hash-chained audit log.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy import (
    Column,
    Float,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    and_,
    delete,
    insert,
    or_,
    select,
    update,
)
from sqlalchemy.engine import Engine as SqlEngine
from sqlalchemy.exc import IntegrityError

metadata = MetaData()

site_config = Table(
    "site_config",
    metadata,
    Column("config_key", String(64), primary_key=True),
    Column("payload", Text, nullable=False),
    Column("updated_at", String(64), nullable=False),
    Column("updated_by", String(128), nullable=False),
)

writer_lease = Table(
    "writer_lease",
    metadata,
    Column("lease_key", String(64), primary_key=True),
    Column("holder", String(256), nullable=False),
    Column("acquired_at", Float, nullable=False),
    Column("heartbeat_at", Float, nullable=False),
)

prediction_records = Table(
    "prediction_records",
    metadata,
    Column("record_id", String(64), primary_key=True),
    Column("site_id", String(128), nullable=False),
    Column("unit_id", String(128), nullable=False),
    Column("encounter_key", String(300), nullable=False),
    Column("patient_id", String(128), nullable=False),
    Column("encounter_id", String(128), nullable=False),
    Column("source_time", String(64), nullable=False),
    Column("scored_at", String(64), nullable=False),
    Column("hour", Integer, nullable=False),
    Column("probability", Float),
    Column("risk_band", String(32), nullable=False),
    Column("trust_state", String(32), nullable=False),
    Column("data_quality", String(64), nullable=False),
    Column("freshness_minutes", Integer),
    Column("input_shift", Float),
    Column("input_revision", Integer, nullable=False),
    Column("model_version", String(128), nullable=False),
    Column("site_mode", String(32), nullable=False),
    Column("ingest_mode", String(32), nullable=False),
    Column("alert_id", String(64)),
    Column("alert_disposition", String(32), nullable=False),
    Column("age", Integer),
    Column("sex", String(8)),
    Column("processing_ms", Float),
    Column("payload", Text, nullable=False),
    Index("ix_prediction_records_encounter", "encounter_key", "source_time"),
    Index("ix_prediction_records_scored", "scored_at"),
)

feedback_records = Table(
    "feedback_records",
    metadata,
    Column("feedback_id", String(64), primary_key=True),
    Column("alert_id", String(64)),
    Column("encounter_key", String(300), nullable=False),
    Column("user_id", String(128), nullable=False),
    Column("role", String(32), nullable=False),
    Column("usefulness", String(32), nullable=False),
    Column("workflow", Text, nullable=False),
    Column("comment", Text),
    Column("recorded_at", String(64), nullable=False),
)

outcome_records = Table(
    "outcome_records",
    metadata,
    Column("outcome_id", String(64), primary_key=True),
    Column("encounter_key", String(300), nullable=False),
    Column("adjudication", String(32), nullable=False),
    Column("onset_time", String(64)),
    Column("criteria", String(64), nullable=False),
    Column("adjudicator", String(128), nullable=False),
    Column("notes", Text),
    Column("recorded_at", String(64), nullable=False),
    Index("ix_outcome_records_encounter", "encounter_key"),
)

connector_events = Table(
    "connector_events",
    metadata,
    Column("event_id", String(64), primary_key=True),
    Column("connector", String(64), nullable=False),
    Column("received_at", String(64), nullable=False),
    Column("status", String(32), nullable=False),
    Column("received", Integer, nullable=False),
    Column("accepted", Integer, nullable=False),
    Column("quarantined", Integer, nullable=False),
    Column("duplicates", Integer, nullable=False),
    Column("max_source_time", String(64)),
    Column("lag_seconds", Float),
    Column("processing_ms", Float),
    Column("error", Text),
    Column("idempotency_key", String(200)),
    Column("actor", String(160), nullable=False),
    Column("backfill", Integer, nullable=False),
    Index("ix_connector_events_connector", "connector", "received_at"),
)

ingest_requests = Table(
    "ingest_requests",
    metadata,
    Column("idempotency_key", String(200), primary_key=True),
    Column("connector", String(64), nullable=False),
    Column("request_sha256", String(64), nullable=False),
    Column("response", Text, nullable=False),
    Column("created_at", String(64), nullable=False),
)

connector_spool = Table(
    "connector_spool",
    metadata,
    Column("spool_id", String(64), primary_key=True),
    Column("connector", String(64), nullable=False),
    Column("received_at", String(64), nullable=False),
    Column("updated_at", String(64), nullable=False),
    Column("payload", Text, nullable=False),
    Column("status", String(32), nullable=False),
    Column("attempts", Integer, nullable=False),
    Column("last_error", Text),
    Column("actor", String(160), nullable=False),
    Column("backfill", Integer, nullable=False),
    Column("idempotency_key", String(200)),
)

bed_ownership = Table(
    "bed_ownership",
    metadata,
    Column("encounter_key", String(300), primary_key=True),
    Column("owner", String(128), nullable=False),
    Column("role", String(32), nullable=False),
    Column("shift_label", String(64)),
    Column("claimed_at", String(64), nullable=False),
)

handoff_notes = Table(
    "handoff_notes",
    metadata,
    Column("note_id", String(64), primary_key=True),
    Column("encounter_key", String(300), nullable=False),
    Column("user_id", String(128), nullable=False),
    Column("note", Text, nullable=False),
    Column("recorded_at", String(64), nullable=False),
)

local_protocols = Table(
    "local_protocols",
    metadata,
    Column("entry_id", String(64), primary_key=True),
    Column("payload", Text, nullable=False),
    Column("status", String(32), nullable=False),
    Column("submitted_by", String(128), nullable=False),
    Column("submitted_at", String(64), nullable=False),
    Column("approved_by", String(128)),
    Column("approved_at", String(64)),
)

export_log = Table(
    "export_log",
    metadata,
    Column("export_id", String(64), primary_key=True),
    Column("created_at", String(64), nullable=False),
    Column("created_by", String(128), nullable=False),
    Column("sha256", String(64), nullable=False),
    Column("counts", Text, nullable=False),
    Column("reason", Text, nullable=False),
)

site_users = Table(
    "site_users",
    metadata,
    Column("user_id", String(64), primary_key=True),
    Column("display_name", String(128), nullable=False),
    Column("role", String(32), nullable=False),
    Column("units", Text),
    Column("password_hash", Text, nullable=False),
    Column("pin_hash", Text),
    Column("totp_secret", Text),
    Column("must_change_password", Integer, nullable=False),
    Column("disabled", Integer, nullable=False),
    Column("failed_logins", Integer, nullable=False),
    Column("locked_until", String(64)),
    Column("created_at", String(64), nullable=False),
    Column("updated_at", String(64), nullable=False),
    Column("created_by", String(128), nullable=False),
    Column("last_login_at", String(64)),
)

revoked_tokens = Table(
    "revoked_tokens",
    metadata,
    Column("jti", String(160), primary_key=True),
    Column("user_id", String(64), nullable=False),
    Column("revoked_at", String(64), nullable=False),
    Column("reason", String(64), nullable=False),
    Index("ix_revoked_tokens_user", "user_id"),
)

care_units = Table(
    "care_units",
    metadata,
    Column("unit_id", String(64), primary_key=True),
    Column("label", String(128), nullable=False),
    Column("kind", String(16), nullable=False),
    Column("news2_scale_default", Integer, nullable=False),
    Column("created_at", String(64), nullable=False),
    Column("updated_at", String(64), nullable=False),
)

encounters = Table(
    "encounters",
    metadata,
    Column("encounter_key", String(300), primary_key=True),
    Column("patient_id", String(128), nullable=False),
    Column("encounter_id", String(128), nullable=False),
    Column("display_name", String(128), nullable=False),
    Column("bed_id", String(64)),
    Column("unit_id", String(64), nullable=False),
    Column("kind", String(16), nullable=False),
    Column("status", String(16), nullable=False),
    Column("age", Integer),
    Column("sex", String(8)),
    Column("hypercapnic_scale2", Integer, nullable=False),
    Column("admitted_at", String(64), nullable=False),
    Column("admitted_by", String(128), nullable=False),
    Column("discharged_at", String(64)),
    Column("discharged_by", String(128)),
    Index("ix_encounters_unit_status", "unit_id", "status"),
)

news2_records = Table(
    "news2_records",
    metadata,
    Column("record_id", String(64), primary_key=True),
    Column("encounter_key", String(300), nullable=False),
    Column("scored_at", String(64), nullable=False),
    Column("source_time", String(64), nullable=False),
    Column("score", Integer),
    Column("complete", Integer, nullable=False),
    Column("urgency", String(16)),
    Column("frequency_minutes", Integer),
    Column("payload", Text, nullable=False),
    Index("ix_news2_records_encounter", "encounter_key", "source_time"),
)

RETENTION_TABLES = {
    "prediction_records": (prediction_records, "scored_at"),
    "connector_events": (connector_events, "received_at"),
    "ingest_requests": (ingest_requests, "created_at"),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RecordStore:
    def __init__(self, engine: SqlEngine) -> None:
        self.engine = engine
        metadata.create_all(engine)

    # ---------- generic helpers ----------
    def insert(self, table: Table, row: dict[str, Any]) -> bool:
        try:
            with self.engine.begin() as connection:
                connection.execute(insert(table).values(**row))
            return True
        except IntegrityError:
            return False

    def insert_many_ignore(self, table: Table, rows: Iterable[dict[str, Any]]) -> int:
        rows = list(rows)
        if not rows:
            return 0
        dialect = self.engine.dialect.name
        if dialect in {"sqlite", "postgresql"}:
            if dialect == "sqlite":
                from sqlalchemy.dialects.sqlite import insert as dialect_insert
            else:
                from sqlalchemy.dialects.postgresql import insert as dialect_insert
            with self.engine.begin() as connection:
                connection.execute(dialect_insert(table).on_conflict_do_nothing(), rows)
            return len(rows)
        return sum(self.insert(table, row) for row in rows)

    def select(
        self,
        table: Table,
        *conditions: Any,
        order_by: Any = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        statement = select(table)
        if conditions:
            statement = statement.where(and_(*conditions))
        if order_by is not None:
            statement = statement.order_by(order_by)
        if limit is not None:
            statement = statement.limit(limit)
        with self.engine.connect() as connection:
            return [dict(row._mapping) for row in connection.execute(statement)]

    def upsert(self, table: Table, key_column: str, row: dict[str, Any]) -> None:
        key = row[key_column]
        with self.engine.begin() as connection:
            updated = connection.execute(
                update(table).where(table.c[key_column] == key).values(**row)
            ).rowcount
            if not updated:
                connection.execute(insert(table).values(**row))

    def delete(self, table: Table, *conditions: Any) -> int:
        if not conditions:
            raise ValueError("Refusing an unconditional delete on an evidence table.")
        with self.engine.begin() as connection:
            return connection.execute(delete(table).where(and_(*conditions))).rowcount

    # ---------- site configuration ----------
    def load_config(self, key: str) -> dict[str, Any] | None:
        rows = self.select(site_config, site_config.c.config_key == key)
        return json.loads(rows[0]["payload"]) if rows else None

    def save_config(self, key: str, payload: dict[str, Any], updated_by: str) -> None:
        self.upsert(
            site_config,
            "config_key",
            {
                "config_key": key,
                "payload": json.dumps(payload, separators=(",", ":"), default=str),
                "updated_at": utc_now(),
                "updated_by": updated_by,
            },
        )

    # ---------- single-writer lease ----------
    def acquire_lease(self, key: str, holder: str, ttl_seconds: float) -> bool:
        now = time.time()
        with self.engine.begin() as connection:
            taken = connection.execute(
                update(writer_lease)
                .where(
                    and_(
                        writer_lease.c.lease_key == key,
                        or_(
                            writer_lease.c.holder == holder,
                            writer_lease.c.heartbeat_at < now - ttl_seconds,
                        ),
                    )
                )
                .values(holder=holder, acquired_at=now, heartbeat_at=now)
            ).rowcount
        if taken:
            return True
        try:
            with self.engine.begin() as connection:
                connection.execute(
                    insert(writer_lease).values(
                        lease_key=key, holder=holder, acquired_at=now, heartbeat_at=now
                    )
                )
            return True
        except IntegrityError:
            return False

    def renew_lease(self, key: str, holder: str) -> bool:
        with self.engine.begin() as connection:
            return bool(
                connection.execute(
                    update(writer_lease)
                    .where(and_(writer_lease.c.lease_key == key, writer_lease.c.holder == holder))
                    .values(heartbeat_at=time.time())
                ).rowcount
            )

    def release_lease(self, key: str, holder: str) -> None:
        self.delete(writer_lease, writer_lease.c.lease_key == key, writer_lease.c.holder == holder)

    def lease_info(self, key: str) -> dict[str, Any] | None:
        rows = self.select(writer_lease, writer_lease.c.lease_key == key)
        return rows[0] if rows else None
