"""Unit shift roster — who is on this shift (transparency, not attendance payroll).

Hospital already takes attendance elsewhere. This roster answers: “who is expected
on *this* ICU shift?” for handoff and open-alert ownership. Editable via UI or CSV.
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime, time, timezone
from typing import Any
from zoneinfo import ZoneInfo

from app.records import utc_now

CONFIG_KEY = "shift_roster"

DEFAULT_SHIFTS = [
    {"id": "morning", "label": "Morning", "start": "07:00", "end": "15:00"},
    {"id": "evening", "label": "Evening", "start": "15:00", "end": "23:00"},
    {"id": "night", "label": "Night", "start": "23:00", "end": "07:00"},
]

CSV_HEADERS = ("user_id", "display_name", "role", "shift_id", "unit_id", "active")

DEFAULT_ASSIGNMENTS = [
    {"id": "demo-morning-doctor", "user_id": "sim-clinician-01", "display_name": "Dr Samira Khan", "role": "clinician", "shift_id": "morning", "unit_id": "icu-api", "active": True},
    {"id": "demo-morning-nurse", "user_id": "sim-nurse-01", "display_name": "Nusrat RN", "role": "nurse", "shift_id": "morning", "unit_id": "icu-api", "active": True},
    {"id": "demo-evening-doctor", "user_id": "sim-clinician-02", "display_name": "Dr Arif Rahman", "role": "clinician", "shift_id": "evening", "unit_id": "icu-api", "active": True},
    {"id": "demo-evening-nurse", "user_id": "sim-nurse-01", "display_name": "Nusrat RN", "role": "nurse", "shift_id": "evening", "unit_id": "icu-api", "active": True},
    {"id": "demo-night-doctor", "user_id": "sim-clinician-01", "display_name": "Dr Samira Khan", "role": "clinician", "shift_id": "night", "unit_id": "icu-api", "active": True},
    {"id": "demo-night-nurse", "user_id": "sim-nurse-02", "display_name": "Farhana RN", "role": "nurse", "shift_id": "night", "unit_id": "icu-api", "active": True},
]


def _parse_hhmm(value: str) -> time:
    hour, minute = value.strip().split(":")
    return time(int(hour), int(minute))


def _in_window(now: time, start: time, end: time) -> bool:
    if start <= end:
        return start <= now < end
    # Overnight window (e.g. 23:00–07:00)
    return now >= start or now < end


def default_document(*, demo: bool = False) -> dict[str, Any]:
    return {
        "version": 1,
        "timezone": "Asia/Dhaka",
        "shifts": list(DEFAULT_SHIFTS),
        "assignments": list(DEFAULT_ASSIGNMENTS) if demo else [],
        "updated_at": None,
        "updated_by": None,
        "note": (
            "Transparency roster for the current ICU shift — not payroll attendance. "
            "Edit here or import CSV; hospital HR systems remain the source of truth for attendance."
        ),
    }


def load(engine: Any) -> dict[str, Any]:
    stored = engine.records.load_config(CONFIG_KEY)
    if not stored:
        from app.core.config import settings

        return default_document(demo=settings.demo_mode)
    body = default_document()
    body.update({k: v for k, v in stored.items() if k in body or k in {"version", "timezone", "shifts", "assignments", "updated_at", "updated_by", "note"}})
    if not body.get("shifts"):
        body["shifts"] = list(DEFAULT_SHIFTS)
    if not isinstance(body.get("assignments"), list):
        body["assignments"] = []
    return body


def save(engine: Any, document: dict[str, Any], actor_id: str) -> dict[str, Any]:
    document = {
        **default_document(),
        **document,
        "updated_at": utc_now(),
        "updated_by": actor_id,
    }
    engine.records.save_config(CONFIG_KEY, document, actor_id)
    return document


def current_shift_id(document: dict[str, Any], *, at: datetime | None = None) -> str | None:
    tz_name = document.get("timezone") or "Asia/Dhaka"
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc
    moment = at.astimezone(tz) if at else datetime.now(tz)
    clock = moment.timetz().replace(tzinfo=None)
    for shift in document.get("shifts") or []:
        try:
            start = _parse_hhmm(str(shift["start"]))
            end = _parse_hhmm(str(shift["end"]))
        except (KeyError, ValueError):
            continue
        if _in_window(clock, start, end):
            return str(shift["id"])
    return None


def current_staff(document: dict[str, Any], *, unit_id: str | None = None) -> dict[str, Any]:
    shift_id = current_shift_id(document)
    shift = next((s for s in document.get("shifts") or [] if s.get("id") == shift_id), None)
    people = [
        row
        for row in document.get("assignments") or []
        if row.get("active", True)
        and row.get("shift_id") == shift_id
        and (unit_id is None or row.get("unit_id") in {None, "", unit_id})
    ]
    return {
        "timezone": document.get("timezone"),
        "shift": shift,
        "shift_id": shift_id,
        "staff": people,
        "count": len(people),
        "note": document.get("note"),
    }


def upsert_assignment(document: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    assignments = list(document.get("assignments") or [])
    row_id = str(row.get("id") or "").strip() or f"asg-{uuid.uuid4().hex[:10]}"
    cleaned = {
        "id": row_id,
        "user_id": str(row.get("user_id") or "").strip(),
        "display_name": str(row.get("display_name") or "").strip(),
        "role": str(row.get("role") or "clinician").strip() or "clinician",
        "shift_id": str(row.get("shift_id") or "").strip(),
        "unit_id": str(row.get("unit_id") or "").strip() or None,
        "active": bool(row.get("active", True)),
    }
    if not cleaned["user_id"] or not cleaned["display_name"] or not cleaned["shift_id"]:
        raise ValueError("user_id, display_name and shift_id are required")
    replaced = False
    for index, existing in enumerate(assignments):
        if existing.get("id") == row_id or (
            existing.get("user_id") == cleaned["user_id"] and existing.get("shift_id") == cleaned["shift_id"]
        ):
            assignments[index] = cleaned
            replaced = True
            break
    if not replaced:
        assignments.append(cleaned)
    document["assignments"] = assignments
    return cleaned


def delete_assignment(document: dict[str, Any], assignment_id: str) -> bool:
    before = len(document.get("assignments") or [])
    document["assignments"] = [row for row in document.get("assignments") or [] if row.get("id") != assignment_id]
    return len(document["assignments"]) < before


def parse_csv(payload: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(payload))
    if not reader.fieldnames:
        raise ValueError("CSV header is required")
    headers = {name.lstrip("\ufeff").strip().lower(): name for name in reader.fieldnames}
    missing = [h for h in ("user_id", "display_name", "shift_id") if h not in headers]
    if missing:
        raise ValueError(f"CSV missing columns: {', '.join(missing)}")
    rows: list[dict[str, Any]] = []
    for raw in reader:
        if not any((value or "").strip() for value in raw.values()):
            continue
        active_raw = (raw.get(headers.get("active", "active")) or "true").strip().lower()
        rows.append({
            "user_id": (raw.get(headers["user_id"]) or "").strip(),
            "display_name": (raw.get(headers["display_name"]) or "").strip(),
            "role": (raw.get(headers.get("role", "role")) or "clinician").strip() or "clinician",
            "shift_id": (raw.get(headers["shift_id"]) or "").strip(),
            "unit_id": (raw.get(headers.get("unit_id", "unit_id")) or "").strip() or None,
            "active": active_raw not in {"0", "false", "no", "n"},
        })
    return rows


def csv_template() -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(CSV_HEADERS))
    writer.writeheader()
    writer.writerow({
        "user_id": "dr-rahim",
        "display_name": "Dr Rahim",
        "role": "clinician",
        "shift_id": "morning",
        "unit_id": "icu-a",
        "active": "true",
    })
    writer.writerow({
        "user_id": "rn-fatima",
        "display_name": "Fatima RN",
        "role": "nurse",
        "shift_id": "morning",
        "unit_id": "icu-a",
        "active": "true",
    })
    return buf.getvalue()
