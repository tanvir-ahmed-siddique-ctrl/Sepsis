"""Pure CSV adapter producing the native ObservationBatch JSON shape."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from pathlib import Path
from typing import TextIO

REQUIRED_COLUMNS = {"patient_id", "encounter_id", "timestamp", "code", "value"}
OPTIONAL_COLUMNS = {"unit", "source", "unit_id"}


class CSVLabError(ValueError):
    """A CSV file does not satisfy the lab observation contract."""


def parse_csv_lab(source: str | TextIO) -> dict[str, list[dict[str, object]]]:
    """Parse CSV text or a text stream into an API-ready ObservationBatch mapping."""
    stream = io.StringIO(source) if isinstance(source, str) else source
    reader = csv.DictReader(stream)
    if reader.fieldnames is None:
        raise CSVLabError("CSV header is required")
    fieldnames = [name.lstrip("\ufeff").strip() for name in reader.fieldnames]
    if len(fieldnames) != len(set(fieldnames)):
        raise CSVLabError("CSV column names must be unique")
    missing = REQUIRED_COLUMNS - set(fieldnames)
    if missing:
        raise CSVLabError(f"missing required columns: {', '.join(sorted(missing))}")
    reader.fieldnames = fieldnames

    observations: list[dict[str, object]] = []
    for line_number, row in enumerate(reader, start=2):
        if None in row:
            raise CSVLabError(f"line {line_number}: too many fields")
        values = {key: (value or "").strip() for key, value in row.items()}
        if not any(values.values()):
            continue
        for column in ("patient_id", "encounter_id", "timestamp", "code"):
            if not values[column]:
                raise CSVLabError(f"line {line_number}: {column} is required")
        timestamp = values["timestamp"]
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise CSVLabError(f"line {line_number}: invalid ISO-8601 timestamp") from exc
        try:
            value = float(values["value"]) if values["value"] else None
        except ValueError as exc:
            raise CSVLabError(f"line {line_number}: value must be numeric or blank") from exc
        if value is not None and (value != value or value in {float("inf"), float("-inf")}):
            raise CSVLabError(f"line {line_number}: value must be finite")
        observation: dict[str, object] = {
            "patient_id": values["patient_id"],
            "encounter_id": values["encounter_id"],
            "timestamp": timestamp,
            "code": values["code"],
            "value": value,
            "source": values.get("source") or "csv_lab",
        }
        for optional in ("unit", "unit_id"):
            if values.get(optional):
                observation[optional] = values[optional]
        observations.append(observation)
    return {"observations": observations}


def parse_csv_lab_file(path: str | Path) -> dict[str, list[dict[str, object]]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as stream:
        return parse_csv_lab(stream)

