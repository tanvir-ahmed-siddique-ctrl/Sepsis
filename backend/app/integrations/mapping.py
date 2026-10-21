"""Versioned code and unit mapping registry shared by every connector."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.services.clinical_contract import SPECS

LOINC_SYSTEMS = {"http://loinc.org", "LN", "LNC", "LOINC"}


def normalize_unit(unit: str | None) -> str:
    return "" if unit is None else unit.strip().replace(" ", "").lower()


@dataclass(frozen=True)
class CodeMapping:
    code: str
    display: str
    target: str
    conversions: dict[str, tuple[float, float]]

    @property
    def canonical_unit(self) -> str | None:
        return SPECS[self.target].canonical_unit


@dataclass(frozen=True)
class Converted:
    value: float | None
    unit: str | None
    error: str | None = None


class MappingRegistry:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        raw = self.path.read_bytes()
        self.sha256 = hashlib.sha256(raw).hexdigest()
        self.document: dict[str, Any] = json.loads(raw)
        self.version = self.document["version"]
        self.entries: dict[str, CodeMapping] = {}
        for entry in self.document["entries"]:
            if entry["target"] not in SPECS:
                raise ValueError(f"Mapping target {entry['target']} is not in the clinical contract")
            self.entries[entry["code"]] = CodeMapping(
                code=entry["code"],
                display=entry["display"],
                target=entry["target"],
                conversions={
                    normalize_unit(unit): (float(factor), float(offset))
                    for unit, (factor, offset) in entry["units"].items()
                },
            )

    def lookup(self, system: str | None, code: str | None) -> CodeMapping | None:
        if not code or (system or "http://loinc.org") not in LOINC_SYSTEMS:
            return None
        return self.entries.get(code)

    def convert(self, mapping: CodeMapping, value: float | None, unit: str | None) -> Converted:
        if value is None:
            return Converted(None, mapping.canonical_unit, "missing_value")
        key = normalize_unit(unit)
        if key not in mapping.conversions:
            return Converted(value, unit, f"unit_unmapped:{unit or 'none'}")
        factor, offset = mapping.conversions[key]
        return Converted(round(value * factor + offset, 6), mapping.canonical_unit)

    def describe(self) -> dict[str, Any]:
        return {
            "registry_id": self.document["registry_id"],
            "version": self.version,
            "status": self.document["status"],
            "sha256": self.sha256,
            "target_contract": self.document["target_contract"],
            "entries": [
                {
                    "code": mapping.code,
                    "system": "http://loinc.org",
                    "display": mapping.display,
                    "target": mapping.target,
                    "canonical_unit": mapping.canonical_unit,
                    "accepted_units": sorted(self.document_units(mapping.code)),
                }
                for mapping in self.entries.values()
            ],
        }

    def document_units(self, code: str) -> list[str]:
        entry = next(item for item in self.document["entries"] if item["code"] == code)
        return list(entry["units"])
