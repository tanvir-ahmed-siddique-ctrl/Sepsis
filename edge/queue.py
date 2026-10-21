"""Append-only JSONL store-and-forward queue with fsync durability."""

from __future__ import annotations

import base64
import json
import os
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass
class QueueItem:
    item_id: str
    payload: bytes
    idempotency_key: str
    attempts: int
    next_attempt: float
    last_error: str | None = None


class AppendOnlyQueue:
    """Persist state transitions as immutable events and rebuild state on startup."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)
        self._lock = threading.RLock()
        self._pending: dict[str, QueueItem] = {}
        self._load()

    def _load(self) -> None:
        lines = self.path.read_bytes().splitlines()
        for index, raw in enumerate(lines):
            try:
                event = json.loads(raw)
            except (UnicodeDecodeError, json.JSONDecodeError):
                if index == len(lines) - 1:
                    continue  # tolerate a crash-truncated final append
                raise RuntimeError(f"queue log is corrupt at line {index + 1}")
            item_id = event["id"]
            if event["event"] == "enqueue":
                self._pending[item_id] = QueueItem(
                    item_id=item_id,
                    payload=base64.b64decode(event["payload"], validate=True),
                    idempotency_key=event["idempotency_key"],
                    attempts=0,
                    next_attempt=float(event["at"]),
                )
            elif event["event"] == "retry" and item_id in self._pending:
                item = self._pending[item_id]
                item.attempts = int(event["attempts"])
                item.next_attempt = float(event["next_attempt"])
                item.last_error = event.get("error")
            elif event["event"] in {"delivered", "failed"}:
                self._pending.pop(item_id, None)

    def _append(self, event: dict[str, object]) -> None:
        encoded = (json.dumps(event, separators=(",", ":"), ensure_ascii=True) + "\n").encode()
        flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
        fd = os.open(self.path, flags, 0o600)
        try:
            written = 0
            while written < len(encoded):
                written += os.write(fd, encoded[written:])
            os.fsync(fd)
        finally:
            os.close(fd)

    def enqueue(self, payload: bytes, idempotency_key: str) -> QueueItem:
        with self._lock:
            now = time.time()
            item = QueueItem(uuid.uuid4().hex, payload, idempotency_key, 0, now)
            self._append({
                "event": "enqueue",
                "id": item.item_id,
                "at": now,
                "idempotency_key": idempotency_key,
                "payload": base64.b64encode(payload).decode("ascii"),
            })
            self._pending[item.item_id] = item
            return QueueItem(**vars(item))

    def mark_delivered(self, item_id: str) -> None:
        with self._lock:
            if item_id not in self._pending:
                return
            self._append({"event": "delivered", "id": item_id, "at": time.time()})
            del self._pending[item_id]

    def mark_failed(self, item_id: str, error: str) -> None:
        with self._lock:
            if item_id not in self._pending:
                return
            self._append({
                "event": "failed",
                "id": item_id,
                "at": time.time(),
                "error": error[:500],
            })
            del self._pending[item_id]

    def mark_retry(self, item_id: str, error: str, next_attempt: float) -> None:
        with self._lock:
            item = self._pending[item_id]
            attempts = item.attempts + 1
            self._append({
                "event": "retry",
                "id": item_id,
                "at": time.time(),
                "attempts": attempts,
                "next_attempt": next_attempt,
                "error": error[:500],
            })
            item.attempts = attempts
            item.next_attempt = next_attempt
            item.last_error = error[:500]

    def due(self, now: float | None = None, limit: int = 100) -> list[QueueItem]:
        with self._lock:
            cutoff = time.time() if now is None else now
            items = sorted(
                (item for item in self._pending.values() if item.next_attempt <= cutoff),
                key=lambda item: (item.next_attempt, item.item_id),
            )
            return [QueueItem(**vars(item)) for item in items[:limit]]

    @property
    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)

