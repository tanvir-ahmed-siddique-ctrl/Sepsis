"""SQL-backed prototype persistence.

The same store runs on SQLite for local/offline use and PostgreSQL when
``DATABASE_URL`` points to a Postgres instance. Audit events are append-only;
mutable engine state is saved as a restart snapshot.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool


class StateStore:
    def __init__(self, database_url: str) -> None:
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        pool_options = {"poolclass": StaticPool} if database_url in {"sqlite://", "sqlite:///:memory:"} else {}
        self.engine: Engine = create_engine(
            database_url,
            future=True,
            pool_pre_ping=True,
            connect_args=connect_args,
            **pool_options,
        )
        self._create_schema()

    def _create_schema(self) -> None:
        statements = (
            """
            CREATE TABLE IF NOT EXISTS engine_state (
                state_key VARCHAR(64) PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at VARCHAR(64) NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                audit_id VARCHAR(64) PRIMARY KEY,
                ordinal BIGINT NOT NULL UNIQUE,
                event_hash VARCHAR(64) NOT NULL UNIQUE,
                previous_hash VARCHAR(64) NOT NULL,
                recorded_at VARCHAR(64) NOT NULL,
                payload TEXT NOT NULL
            )
            """,
        )
        with self.engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))

    def healthy(self) -> bool:
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def load_state(self) -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                text("SELECT payload FROM engine_state WHERE state_key = :key"),
                {"key": "engine-v1"},
            ).first()
        return None if row is None else json.loads(row[0])

    def save_state(self, state: dict[str, Any]) -> None:
        payload = json.dumps(state, separators=(",", ":"), allow_nan=False)
        now = datetime.now(timezone.utc).isoformat()
        with self.engine.begin() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM engine_state WHERE state_key = :key"),
                {"key": "engine-v1"},
            ).first()
            if exists:
                connection.execute(
                    text(
                        "UPDATE engine_state SET payload = :payload, updated_at = :updated_at "
                        "WHERE state_key = :key"
                    ),
                    {"key": "engine-v1", "payload": payload, "updated_at": now},
                )
            else:
                connection.execute(
                    text(
                        "INSERT INTO engine_state (state_key, payload, updated_at) "
                        "VALUES (:key, :payload, :updated_at)"
                    ),
                    {"key": "engine-v1", "payload": payload, "updated_at": now},
                )

    def load_audit(self) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                text("SELECT payload FROM audit_events ORDER BY ordinal")
            ).all()
        return [json.loads(row[0]) for row in rows]

    def append_audit(self, event: dict[str, Any]) -> None:
        payload = json.dumps(event, separators=(",", ":"), allow_nan=False)
        try:
            with self.engine.begin() as connection:
                ordinal = connection.execute(
                    text("SELECT COALESCE(MAX(ordinal), 0) + 1 FROM audit_events")
                ).scalar_one()
                connection.execute(
                    text(
                        "INSERT INTO audit_events "
                        "(audit_id, ordinal, event_hash, previous_hash, recorded_at, payload) "
                        "VALUES (:audit_id, :ordinal, :event_hash, :previous_hash, :recorded_at, :payload)"
                    ),
                    {
                        "audit_id": event["audit_id"],
                        "ordinal": ordinal,
                        "event_hash": event["event_hash"],
                        "previous_hash": event["previous_hash"],
                        "recorded_at": event["recorded_at"],
                        "payload": payload,
                    },
                )
        except IntegrityError:
            # Deterministic audit IDs make retries idempotent.
            return
