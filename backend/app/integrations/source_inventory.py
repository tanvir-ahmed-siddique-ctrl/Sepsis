"""Hospital source inventory: bounded, non-patient commissioning declarations.

This is a planning record. A declared interface never counts as a working feed,
and no source-inventory field authorizes clinical alerts.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.records import utc_now

CONFIG_KEY = "source_inventory"
REQUIRED_VITALS = frozenset({"HR", "SBP", "MAP", "O2Sat"})
SIGNALS = ("HR", "SBP", "MAP", "O2Sat", "Temp", "Resp", "WBC", "Lactate", "Creatinine", "Platelets")
METHOD_TIER = {"none": "L0", "manual": "L0", "csv_lab": "L1", "hl7v2_oru": "L2",
               "fhir_r4": "L3", "vendor_adapter": "L4"}


class SourceEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,39}$")
    kind: Literal["ehr", "lis", "monitor", "manual", "interface_engine"]
    label: str = Field(min_length=1, max_length=80)
    method: Literal["none", "manual", "csv_lab", "hl7v2_oru", "fhir_r4", "vendor_adapter"]
    signals: list[Literal["HR", "SBP", "MAP", "O2Sat", "Temp", "Resp", "WBC", "Lactate", "Creatinine", "Platelets"]] = Field(default_factory=list, max_length=10)
    expected_interval_minutes: int | None = Field(default=None, ge=1, le=1440)
    timestamp_basis: Literal["measurement", "result", "receipt", "unknown"] = "unknown"
    export_confirmed: bool = False
    test_message_verified: bool = False
    manual_chart_dry_run_verified: bool = False
    correction_path_verified: bool = False
    owner_role: Literal["icu", "nursing", "lab", "biomed", "it", "unknown"] = "unknown"

    @field_validator("label")
    @classmethod
    def clean_label(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ord(char) < 32 for char in value):
            raise ValueError("Source label must be one line")
        return value

    @model_validator(mode="after")
    def no_false_verification(self) -> "SourceEntry":
        if self.test_message_verified and not self.export_confirmed:
            raise ValueError("A test message cannot be verified before export is confirmed")
        if self.method in {"none", "manual"} and self.test_message_verified:
            raise ValueError("A manual or unavailable source has no connector test message")
        if self.method != "manual" and self.manual_chart_dry_run_verified:
            raise ValueError("Manual chart dry run applies only to a manual source")
        return self


class SourceInventoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sources: list[SourceEntry] = Field(max_length=20)

    @model_validator(mode="after")
    def unique_ids(self) -> "SourceInventoryRequest":
        ids = [source.source_id for source in self.sources]
        if len(ids) != len(set(ids)):
            raise ValueError("Source IDs must be unique")
        return self


def load(engine: Any) -> dict[str, Any]:
    stored = engine.records.load_config(CONFIG_KEY)
    return stored or {"version": 1, "sources": [], "updated_at": None, "updated_by": None}


def save(engine: Any, body: SourceInventoryRequest, actor: Any) -> dict[str, Any]:
    document = {"version": 1, "sources": [source.model_dump() for source in body.sources],
                "updated_at": utc_now(), "updated_by": actor.user_id}
    with engine.lock:
        engine._require_writable()
        engine.records.save_config(CONFIG_KEY, document, actor.user_id)
        engine._log("source_inventory_updated", {
            "actor": actor.user_id,
            "actor_role": actor.role,
            "source_count": len(body.sources),
            "source_ids": [source.source_id for source in body.sources],
        })
    return document


def assess(document: dict[str, Any], connector_health: list[dict[str, Any]], *, mapping_ready: bool = False,
           simulation_mode: bool = False) -> dict[str, Any]:
    sources = [SourceEntry.model_validate(source) for source in document.get("sources", [])]
    by_connector = {item["connector"]: item for item in connector_health}
    represented: set[str] = set()
    hourly_vitals: set[str] = set()
    rows = []
    for source in sources:
        active_feed = by_connector.get(source.method, {}).get("state")
        source_test_ready = (source.manual_chart_dry_run_verified if source.method == "manual"
                             else source.export_confirmed and source.test_message_verified)
        usable_declaration = (
            source_test_ready
            and source.timestamp_basis in {"measurement", "result"}
            and source.owner_role != "unknown"
        )
        if usable_declaration:
            represented.update(source.signals)
            if source.expected_interval_minutes is not None and source.expected_interval_minutes <= 60:
                hourly_vitals.update(REQUIRED_VITALS.intersection(source.signals))
        rows.append({
            "source_id": source.source_id,
            "tier": METHOD_TIER[source.method],
            "connector_state": active_feed if source.method not in {"none", "manual"} else None,
            "declared_test_ready": usable_declaration,
            "feed_observed": active_feed in {"healthy", "degraded"} and not simulation_mode if active_feed else False,
            "next_action": (
                "Choose an export or manual charting path" if source.method == "none"
                else "Assign a source owner role" if source.owner_role == "unknown"
                else "Complete a bedside chart dry run" if source.method == "manual" and not source.manual_chart_dry_run_verified
                else "Confirm export" if source.method not in {"manual", "none"} and not source.export_confirmed
                else "Verify measurement/result timestamps" if source.timestamp_basis in {"unknown", "receipt"}
                else "Run and verify a non-patient test message" if source.method not in {"manual", "none"} and not source.test_message_verified
                else "Verify hourly vital cadence before relying on model freshness" if REQUIRED_VITALS.intersection(source.signals) and (source.expected_interval_minutes is None or source.expected_interval_minutes > 60)
                else "Check the connector feed" if source.method not in {"manual", "none"} and active_feed not in {"healthy", "degraded"}
                else "Review and sign the current mapping registry" if source.method not in {"manual", "none"} and not mapping_ready
                else "Verify corrected and retracted observations" if not source.correction_path_verified
                else "Measure actual signal coverage and lag on approved data"
            ),
        })
    missing = sorted(REQUIRED_VITALS - represented)
    slow = sorted((REQUIRED_VITALS & represented) - hourly_vitals)
    needs_feed = any(source.method not in {"manual", "none"} and row["declared_test_ready"]
                     and not row["feed_observed"] for source, row in zip(sources, rows))
    needs_mapping = any(source.method not in {"manual", "none"} and row["declared_test_ready"]
                        for source, row in zip(sources, rows))
    return {
        "sources": rows,
        "missing_required_vitals": missing,
        "required_vitals_without_hourly_source": slow,
        "declared_required_vitals_covered": not missing and bool(sources),
        "observed_connected_sources": sum(row["feed_observed"] for row in rows),
        "mapping_registry_signed_off": mapping_ready,
        "highest_declared_tier": max((row["tier"] for row in rows if row["declared_test_ready"]), default="L0"),
        "next_stage": (
            "inventory" if not sources else
            "verify_source_tests" if not any(row["declared_test_ready"] for row in rows) else
            "close_vital_gaps" if missing else
            "check_vital_cadence" if slow else
            "connect_feed" if needs_feed else
            "sign_mappings" if needs_mapping and not mapping_ready else
            "measure_local_coverage"
        ),
        "scope": "Declarations and connector activity only. Not measured data coverage, local model validation or live-alert authorization.",
    }
