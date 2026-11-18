"""Streaming risk engine: hourly observations in → calibrated risk, alerts and audit out.

Each patient keeps a raw hourly observation table. On every new hour the full
past-only feature pipeline is re-run and the latest row is scored. Live
encounter state is restart-persisted in SQLite/PostgreSQL; audit events are
append-only and hash chained; silent-pilot prediction rows are append-only.

Exactly one process may write. A database lease enforces this: a second
instance starts read-only and refuses mutations, so horizontal API scaling is
disabled until state moves fully to row-level records.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import socket
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from predict_rx.explain import explain_rows
from predict_rx.features.engineering import build_patient_features
from predict_rx.features.schema import DEMO_COLS, LAB_COLS, MIN_HOURS_BEFORE_PRED, VITAL_COLS

from app import clinical_context
from app.core.config import settings
from app.observability import METRICS, AuditVerifier
from app.persistence import StateStore
from app.news2 import score as news2_score
from app.records import (
    RecordStore,
    bed_ownership,
    care_units,
    connector_events,
    encounters,
    handoff_notes,
    news2_records,
    prediction_records,
    utc_now,
)
from app.services.clinical_contract import validate_observation
from app.site import SiteManager
from app.trustgate import TrustState, assess_prediction

BAND_ORDER = {"insufficient_data": 0, "stable": 1, "watch": 2, "high_risk": 3}
TREND_VARS = ["HR", "SBP", "MAP", "Resp", "Temp", "O2Sat", "Lactate", "WBC", "Creatinine", "Platelets"]
REQUIRED_SIGNALS = ("HR", "SBP", "MAP", "O2Sat")
MATRIX_SIGNALS = ("HR", "SBP", "MAP", "O2Sat", "Resp", "Temp", "Lactate", "WBC", "Creatinine", "Platelets", "Bilirubin_total")
ACTIVE_ALERT_STATUSES = {"open", "silent"}
REPLAY_EPOCH = datetime(2026, 12, 26, 7, 0, tzinfo=timezone.utc)
LEASE_KEY = "engine-writer"


class ReadOnlyError(RuntimeError):
    """This instance does not hold the writer lease (or lost it)."""


class ModeError(RuntimeError):
    """The requested operation is not available in the current site mode."""


@dataclass
class Patient:
    encounter_key: str
    patient_id: str
    encounter_id: str
    display_name: str
    unit_id: str
    source_mode: str
    age: int | None = None
    sex: str | None = None
    raw: pd.DataFrame = field(default_factory=pd.DataFrame)
    source: pd.DataFrame | None = None  # full stay for replay cases
    cursor: int = 0
    predictions: list[dict] = field(default_factory=list)
    replay_meta: dict = field(default_factory=dict)
    static_values: dict[str, float] = field(default_factory=dict)
    observation_meta: dict[tuple[int, str], dict] = field(default_factory=dict)
    icu_start_hour: int | None = None
    segment_start_hour: int | None = None
    revision: int = 0
    bed_id: str | None = None
    kind: str = "icu"
    status: str = "admitted"
    hypercapnic_scale2: bool = False
    admitted_at: str | None = None
    discharged_at: str | None = None
    news2: list[dict] = field(default_factory=list)
    context: dict | None = None


class Engine:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        model_path = _active_model_path()
        bundle = joblib.load(model_path)
        self.model = bundle["model"]
        self.uncertainty_model = bundle.get("uncertainty_model", bundle["model"])
        self.thresholds = bundle["thresholds"]
        self.model_version = bundle["model_version"]
        self.frozen = bool(bundle.get("frozen"))
        self.model_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()
        self.store = StateStore(settings.database_url)
        self.records = RecordStore(self.store.engine)
        self.writer_id = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"
        self.read_only_reason: str | None = None
        if settings.writer_lease_enabled and not self.records.acquire_lease(LEASE_KEY, self.writer_id, settings.writer_lease_seconds):
            self.read_only_reason = "another_writer_holds_lease"
        self.site = SiteManager(self.records)
        self.patients: dict[str, Patient] = {}
        self.alerts: dict[str, dict] = {}
        self.audit: list[dict] = self.store.load_audit()
        self.audit_verifier = AuditVerifier()
        self.manifest: dict = {}
        self.ownership: dict[str, dict] = {row["encounter_key"]: row for row in self.records.select(bed_ownership)}
        self.units: dict[str, dict] = {row["unit_id"]: row for row in self.records.select(care_units)}
        self._ensure_default_units()
        self._pending_records: list[dict] = []
        self._snapshot_hashes: dict[str, str] = {}
        self._snapshot_keys: set[str] = set()
        self.snapshot_last_persist_ms: float | None = None
        self.snapshot_writes_total = 0
        self.snapshot_bytes_written_total = 0
        self._force_shadow = False
        self._stop = threading.Event()
        self._restore_state()
        if self.read_only_reason is None:
            self.reset_replay()
            if settings.public_demo_lockdown:
                self._seed_public_staff()
        if self.read_only_reason is None and settings.writer_lease_enabled:
            self._heartbeat = threading.Thread(target=self._heartbeat_loop, name="writer-lease", daemon=True)
            self._heartbeat.start()

    # ---------- lifecycle and writer lease ----------
    @property
    def read_only(self) -> bool:
        return self.read_only_reason is not None

    def _require_writable(self) -> None:
        if self.read_only_reason is not None:
            raise ReadOnlyError(self.read_only_reason)

    def _heartbeat_loop(self) -> None:
        interval = max(5.0, settings.writer_lease_seconds / 3)
        while not self._stop.wait(interval):
            with self.lock:
                if self.read_only_reason is None and settings.writer_lease_enabled and not self.records.renew_lease(LEASE_KEY, self.writer_id):
                    self.read_only_reason = "writer_lease_lost"

    def close(self) -> None:
        self._stop.set()
        with self.lock:
            if self.read_only_reason is None and settings.writer_lease_enabled:
                self.records.release_lease(LEASE_KEY, self.writer_id)
                self.read_only_reason = "engine_closed"
        self.store.engine.dispose()

    # ---------- site mode ----------
    def set_site_mode(self, mode: str, actor: Any, reason: str, gates: list[dict]) -> dict:
        with self.lock:
            self._require_writable()
            previous = self.site.state.effective_mode
            state = self.site.set_mode(mode, actor.user_id, gates)
            self._log(
                "site_mode_changed",
                {
                    "actor": actor.user_id,
                    "actor_role": actor.role,
                    "requested_mode": mode,
                    "previous_mode": previous,
                    "effective_mode": state.effective_mode,
                    "reason": reason,
                    "failed_gates": [g["gate"] for g in gates if not g["passed"]],
                },
            )
            if state.effective_mode == "demo" and previous != "demo":
                self.reset_replay()
            elif state.effective_mode != "demo":
                self._drop_replay()
            self._persist_state()
            return state.as_dict()

    def record_site_config_change(self, event: str, actor: Any, detail: dict) -> None:
        with self.lock:
            self._require_writable()
            self.site.save(actor.user_id)
            self._log(event, {"actor": actor.user_id, "actor_role": actor.role, **detail})

    # ---------- care units and ADT ----------
    def _ensure_default_units(self) -> None:
        defaults = (
            (settings.demo_unit_id, "Demo ICU", "icu"),
            (settings.api_unit_id, "API ICU", "icu"),
            ("ward-demo-1", "Demo Ward", "ward"),
        )
        for unit_id, label, kind in defaults:
            if unit_id in self.units:
                continue
            row = {
                "unit_id": unit_id,
                "label": label,
                "kind": kind,
                "news2_scale_default": 1,
                "created_at": utc_now(),
                "updated_at": utc_now(),
            }
            self.units[unit_id] = row
            if not self.read_only:
                self.records.insert(care_units, row)

    def unit_kind(self, unit_id: str) -> str:
        return str(self.units.get(unit_id, {}).get("kind") or "icu")

    def _ensure_bed_available(self, unit_id: str, bed_id: str | None, *, exclude: str | None = None) -> None:
        if not bed_id:
            return
        occupied = next(
            (
                patient
                for patient in self.patients.values()
                if patient.encounter_key != exclude
                and patient.status == "admitted"
                and patient.unit_id == unit_id
                and (patient.bed_id or "").casefold() == bed_id.casefold()
            ),
            None,
        )
        if occupied:
            raise ValueError(f"Bed {bed_id} is already occupied in {unit_id}")

    def save_unit(self, unit_id: str, label: str, kind: str, actor: Any, news2_scale_default: int = 1) -> dict:
        if kind not in {"icu", "ward"}:
            raise ValueError("Unit kind must be icu or ward")
        if news2_scale_default != 1:
            raise ValueError("NEWS2 SpO2 Scale 2 cannot be a unit default; select it for an individual patient only")
        with self.lock:
            self._require_writable()
            previous = self.units.get(unit_id)
            if previous and previous["kind"] != kind and any(
                patient.unit_id == unit_id and patient.status == "admitted"
                for patient in self.patients.values()
            ):
                raise ValueError("Discharge or transfer active encounters before changing a unit between ward and ICU")
            row = {
                "unit_id": unit_id,
                "label": label,
                "kind": kind,
                "news2_scale_default": news2_scale_default,
                "created_at": previous["created_at"] if previous else utc_now(),
                "updated_at": utc_now(),
            }
            self.records.upsert(care_units, "unit_id", row)
            self.units[unit_id] = row
            self._log("care_unit_saved", {
                "actor": actor.user_id,
                "actor_role": actor.role,
                "unit_id": unit_id,
                "kind": kind,
                "news2_scale_default": news2_scale_default,
            })
            return row

    def _upsert_encounter(self, patient: Patient, actor_id: str = "system") -> None:
        existing = self.records.select(encounters, encounters.c.encounter_key == patient.encounter_key)
        row = {
            "encounter_key": patient.encounter_key,
            "patient_id": patient.patient_id,
            "encounter_id": patient.encounter_id,
            "display_name": patient.display_name,
            "bed_id": patient.bed_id,
            "unit_id": patient.unit_id,
            "kind": patient.kind,
            "status": patient.status,
            "age": patient.age,
            "sex": patient.sex,
            "hypercapnic_scale2": int(patient.hypercapnic_scale2),
            "admitted_at": patient.admitted_at or utc_now(),
            "admitted_by": existing[0]["admitted_by"] if existing else actor_id,
            "discharged_at": patient.discharged_at,
            "discharged_by": existing[0]["discharged_by"] if existing else None,
        }
        self.records.upsert(encounters, "encounter_key", row)

    def admit_encounter(
        self,
        *,
        patient_id: str,
        encounter_id: str,
        display_name: str,
        unit_id: str,
        bed_id: str | None,
        age: int | None,
        sex: str | None,
        hypercapnic_scale2: bool,
        actor: Any,
    ) -> Patient:
        with self.lock:
            self._require_writable()
            if unit_id not in self.units:
                raise ValueError("Unknown care unit")
            self._ensure_bed_available(unit_id, bed_id)
            key = self._encounter_key(patient_id, encounter_id)
            existing = self.patients.get(key)
            if existing and existing.status != "discharged":
                raise ValueError("Encounter is already admitted")
            patient = Patient(
                encounter_key=key,
                patient_id=patient_id,
                encounter_id=encounter_id,
                display_name=display_name,
                unit_id=unit_id,
                source_mode="api",
                age=age,
                sex=sex,
                bed_id=bed_id,
                kind=self.unit_kind(unit_id),
                status="admitted",
                hypercapnic_scale2=hypercapnic_scale2,
                admitted_at=utc_now(),
            )
            self.patients[key] = patient
            self._upsert_encounter(patient, actor.user_id)
            self._log("encounter_admitted", {
                "actor": actor.user_id,
                "actor_role": actor.role,
                "encounter_key": key,
                "unit_id": unit_id,
                "bed_id": bed_id,
                "kind": patient.kind,
            })
            self._persist_state()
            return patient

    def transfer_encounter(self, patient: Patient, unit_id: str, bed_id: str | None, actor: Any) -> Patient:
        with self.lock:
            self._require_writable()
            if unit_id not in self.units:
                raise ValueError("Unknown care unit")
            self._ensure_bed_available(unit_id, bed_id, exclude=patient.encounter_key)
            previous = {"unit_id": patient.unit_id, "bed_id": patient.bed_id, "kind": patient.kind}
            patient.unit_id = unit_id
            patient.bed_id = bed_id
            patient.kind = self.unit_kind(unit_id)
            if previous["kind"] != patient.kind:
                patient.segment_start_hour = None
                patient.icu_start_hour = None
                patient.predictions = []
                patient.news2 = []
                if patient.kind == "ward":
                    for alert in self.alerts.values():
                        if (
                            alert.get("encounter_key") == patient.encounter_key
                            and alert.get("status") in ACTIVE_ALERT_STATUSES
                        ):
                            alert["status"] = "superseded"
                            alert.setdefault("actions", []).append({
                                "user_id": actor.user_id,
                                "role": actor.role,
                                "action": "superseded",
                                "reason": "Transferred out of ICU model scope",
                                "at": utc_now(),
                            })
            self._upsert_encounter(patient, actor.user_id)
            self._log("encounter_transferred", {
                "actor": actor.user_id,
                "actor_role": actor.role,
                "encounter_key": patient.encounter_key,
                "from": previous,
                "to": {"unit_id": unit_id, "bed_id": bed_id, "kind": patient.kind},
            })
            self._persist_state()
            return patient

    def discharge_encounter(self, patient: Patient, actor: Any) -> Patient:
        with self.lock:
            self._require_writable()
            patient.status = "discharged"
            patient.discharged_at = utc_now()
            self.records.upsert(
                encounters,
                "encounter_key",
                {
                    **self.records.select(encounters, encounters.c.encounter_key == patient.encounter_key)[0],
                    "status": "discharged",
                    "discharged_at": patient.discharged_at,
                    "discharged_by": actor.user_id,
                },
            )
            closed_alerts = 0
            for alert in self.alerts.values():
                if (
                    alert.get("encounter_key") == patient.encounter_key
                    and alert.get("status") in ACTIVE_ALERT_STATUSES
                ):
                    alert["status"] = "discharged"
                    alert.setdefault("actions", []).append({
                        "user_id": actor.user_id,
                        "role": actor.role,
                        "action": "discharged",
                        "reason": "Encounter discharged",
                        "at": patient.discharged_at,
                    })
                    closed_alerts += 1
            self._log("encounter_discharged", {
                "actor": actor.user_id,
                "actor_role": actor.role,
                "encounter_key": patient.encounter_key,
                "alerts_closed": closed_alerts,
            })
            self._persist_state()
            return patient

    def set_news2_scale(
        self,
        patient: Patient,
        hypercapnic_scale2: bool,
        reason: str,
        actor: Any,
    ) -> Patient:
        with self.lock:
            self._require_writable()
            if patient.kind != "ward":
                raise ValueError("NEWS2 SpO2 scales apply only to ward encounters")
            if patient.status != "admitted":
                raise ValueError("Cannot change NEWS2 scale after discharge")
            previous = patient.hypercapnic_scale2
            patient.hypercapnic_scale2 = hypercapnic_scale2
            self._upsert_encounter(patient, actor.user_id)
            if not patient.raw.empty:
                self._score_news2(patient)
            self._log("news2_scale_changed", {
                "actor": actor.user_id,
                "actor_role": actor.role,
                "encounter_key": patient.encounter_key,
                "previous_scale": 2 if previous else 1,
                "new_scale": 2 if hypercapnic_scale2 else 1,
                "reason": reason,
            })
            self._persist_state()
            return patient

    def set_clinical_context(self, patient: Patient, context: dict, actor: Any) -> dict:
        with self.lock:
            self._require_writable()
            if patient.status != "admitted":
                raise ValueError("Cannot document context after discharge")
            patient.context = context
            policy, policy_reason = clinical_context.alert_policy(context)
            paused = 0
            if policy == "shadow_only":
                for alert in self.alerts.values():
                    if alert.get("encounter_key") == patient.encounter_key and alert.get("status") == "open":
                        alert["status"] = "superseded"
                        alert.setdefault("actions", []).append({
                            "user_id": actor.user_id,
                            "role": actor.role,
                            "action": "superseded",
                            "reason": f"Clinical context: {policy_reason}",
                            "at": utc_now(),
                        })
                        paused += 1
            self._log("clinical_context_updated", {
                "actor": actor.user_id,
                "actor_role": actor.role,
                "patient_id": patient.patient_id,
                "encounter_key": patient.encounter_key,
                "goals_of_care": context["goals_of_care"],
                "conditions": context["conditions"],
                "has_other_note": context.get("other_note") is not None,
                "reason": context["reason"],
                "review_due": context["review_due"],
                "alert_policy": policy,
                "open_alerts_paused": paused,
                "policy_version": context["policy_version"],
            })
            self._persist_state()
            return context

    def _latest_value(self, patient: Patient, code: str) -> float | None:
        if code not in patient.raw:
            return None
        frame = patient.raw
        if patient.segment_start_hour is not None:
            frame = frame.loc[frame["_hour"] >= patient.segment_start_hour]
        values = frame[code].dropna()
        return None if values.empty else float(values.iloc[-1])

    def _score_news2(self, patient: Patient) -> dict:
        scale = 2 if patient.hypercapnic_scale2 else 1
        avpu_value = self._latest_value(patient, "AVPU")
        avpu = None if avpu_value is None else {0: "A", 1: "V", 2: "P", 3: "U"}.get(int(avpu_value))
        result = news2_score(
            respiration_rate=self._latest_value(patient, "Resp"),
            spo2=self._latest_value(patient, "O2Sat"),
            on_oxygen=(
                None
                if self._latest_value(patient, "OxygenTherapy") is None
                else bool(self._latest_value(patient, "OxygenTherapy"))
            ),
            systolic_bp=self._latest_value(patient, "SBP"),
            heart_rate=self._latest_value(patient, "HR"),
            consciousness=avpu,
            temperature=self._latest_value(patient, "Temp"),
            scale=scale,
        )
        source_hour = int(patient.raw["_hour"].max())
        source_time = datetime.fromtimestamp(source_hour * 3600, tz=timezone.utc)
        result.update({
            "source_time": source_time.isoformat(),
            "scored_at": utc_now(),
            "due_at": (
                (source_time + timedelta(minutes=result["frequency_minutes"])).isoformat()
                if result["frequency_minutes"] is not None
                else None
            ),
        })
        record_id = hashlib.sha256(
            f"{patient.encounter_key}|{source_hour}|{patient.revision + 1}|news2".encode()
        ).hexdigest()[:32]
        patient.revision += 1
        patient.news2.append(result)
        self.records.insert(
            news2_records,
            {
                "record_id": record_id,
                "encounter_key": patient.encounter_key,
                "scored_at": result["scored_at"],
                "source_time": result["source_time"],
                "score": result["score"],
                "complete": int(result["complete"]),
                "urgency": result["urgency"],
                "frequency_minutes": result["frequency_minutes"],
                "payload": json.dumps(result, separators=(",", ":"), default=str),
            },
        )
        self._log("news2_scored", {
            "encounter_key": patient.encounter_key,
            "score": result["score"],
            "complete": result["complete"],
            "urgency": result["urgency"],
            "scale": scale,
            "missing": result["missing"],
        })
        return result

    # ---------- replay ----------
    def _drop_replay(self) -> set[str]:
        replay_keys = {key for key, patient in self.patients.items() if patient.source_mode == "replay"}
        for key in replay_keys:
            del self.patients[key]
        for alert_id in [a_id for a_id, alert in self.alerts.items() if alert.get("encounter_key") in replay_keys]:
            del self.alerts[alert_id]
        return replay_keys

    def reset_replay(self) -> None:
        with self.lock:
            self._require_writable()
            self._drop_replay()
            if self.site.state.effective_mode != "demo":
                return
            cases_dir = Path(settings.demo_cases_dir)
            manifest_path = cases_dir / "manifest.json"
            if not manifest_path.exists():
                return
            self.manifest = json.loads(manifest_path.read_text())
            for case in self.manifest["cases"]:
                src = pd.read_csv(cases_dir / f"{case['bed_id']}.psv", sep="|")
                p = Patient(
                    encounter_key=case["bed_id"],
                    patient_id=case["bed_id"],
                    encounter_id=f"replay-{case['bed_id']}",
                    display_name=case["bed_id"].replace("BED-", "Bed "),
                    unit_id=settings.demo_unit_id,
                    source_mode="replay",
                    age=int(src["Age"].iloc[0]),
                    sex={0: "F", 1: "M"}.get(int(src["Gender"].iloc[0])),
                    source=src.drop(columns=["SepsisLabel"]),
                    replay_meta={
                        "labelled_onset_hour": case["labelled_onset_hour"],
                        "kind": case["kind"],
                    },
                )
                self.patients[p.patient_id] = p
                for _ in range(case["replay_start_hour"]):
                    self._advance(p, emit_alerts=False)
            # The public competition build defaults to the real, de-identified
            # PhysioNet replay cohort only. Synthetic commissioning beds are an
            # explicit opt-in for connector drills, never mixed into the primary
            # clinical experience.
            if settings.public_simulation_enabled:
                self._seed_demo_care_workflow()
            self._log(
                "replay_reset",
                {"cases": sum(patient.source_mode == "replay" for patient in self.patients.values())},
            )
            self._persist_state()

    def _seed_demo_care_workflow(self) -> None:
        """Populate the non-model workflows with disclosed synthetic encounters.

        The ICU replay beds remain the held-out, de-identified demonstration
        cases. These additional encounters exist only to exercise the bedside
        charting, integration and NEWS2 screens on the public competition link.
        They are never model evidence, evaluation data or hospital data.
        """
        seeded_keys = {
            key for key, patient in self.patients.items()
            if patient.replay_meta.get("public_demo_seed")
        }
        for key in seeded_keys:
            del self.patients[key]
        for alert_id in [
            key for key, alert in self.alerts.items()
            if alert.get("encounter_key") in seeded_keys
        ]:
            del self.alerts[alert_id]

        now_hour = int(datetime.now(timezone.utc).timestamp() // 3600)
        replay_sources = [patient for patient in self.patients.values() if patient.source_mode == "replay"]
        if not replay_sources:
            return

        # A Synthea-style commissioning feed, made from the same permitted
        # de-identified feature schema as the replay. It has an API source
        # mode so it appears in bedside charting and integration telemetry.
        source = replay_sources[0].source
        if source is not None and len(source) >= 12:
            # Ten generated beds make the charting and command-centre workflow
            # representative of an ICU. They are synthetic commissioning data.
            for index in range(10):
                raw = source.iloc[-12:].copy().reset_index(drop=True)
                raw["_hour"] = np.arange(now_hour - 11, now_hour + 1)
                raw["HR"] = raw["HR"].fillna(82) + index * 2
                raw["SBP"] = raw["SBP"].fillna(118) - index * 2
                raw["MAP"] = raw["MAP"].fillna(76) - index
                raw["Resp"] = raw["Resp"].fillna(18) + index
                raw["O2Sat"] = raw["O2Sat"].fillna(97) - min(index, 5)
                raw["Temp"] = raw["Temp"].fillna(37.0) + index * 0.08
                raw["Lactate"] = raw["Lactate"].fillna(1.2) + index * 0.24
                if index >= 7:
                    # Generated deterioration pattern for alert-workflow drills.
                    raw.loc[raw.index[-4:], ["HR", "SBP", "MAP", "Resp", "O2Sat", "Temp", "Lactate"]] = [
                        132 + index, 84 - index, 58 - index / 2, 30 + index, 89, 39.1, 4.8 + index / 4
                    ]
                age = 42 + index * 4
                gender = index % 2
                bed = f"A-{index + 1:02d}"
                icu = Patient(
                    encounter_key=f"SIM-ICU-{index + 1:02d}--SIM-ICU-{index + 1:02d}-ENC",
                    patient_id=f"SIM-ICU-{index + 1:02d}",
                    encounter_id=f"SIM-ICU-{index + 1:02d}-ENC",
                    display_name=f"Simulation ICU {bed}", unit_id=settings.api_unit_id,
                    source_mode="api", age=age, sex={0: "F", 1: "M"}.get(gender), raw=raw,
                    static_values={"Age": float(age), "Gender": float(gender)},
                    icu_start_hour=now_hour - 11, segment_start_hour=now_hour - 11, bed_id=bed, kind="icu",
                    admitted_at=(datetime.now(timezone.utc) - timedelta(hours=12 + index)).isoformat(),
                    replay_meta={"public_demo_seed": True, "data_class": "synthetic commissioning feed"},
                )
                self.patients[icu.encounter_key] = icu
                self._score(icu, emit_alerts=True, raw_frame=raw, audit_event="synthetic_feed_prediction")
                self._upsert_encounter(icu, "demo-seed")

        # Ward encounters use the published NEWS2 rule only. They never enter
        # the frozen ICU sepsis model.
        ward_rows = (
            ("SIM-WARD-01", "Simulation Ward B-11", "B-11", 72, "F", 24, 92, 96, 37.7, 108, 1.0, 10.8, 1.1, 205),
            ("SIM-WARD-02", "Simulation Ward B-12", "B-12", 58, "M", 30, 89, 94, 38.5, 99, 2.8, 14.2, 1.5, 178),
            ("SIM-WARD-03", "Simulation Ward B-14", "B-14", 67, "F", 18, 96, 98, 36.9, 124, 0.9, 7.6, 0.8, 242),
        )
        for index, (patient_id, label, bed, age, sex, resp, sbp, spo2, temp, hr, lactate, wbc, creatinine, platelets) in enumerate(ward_rows):
            hours = np.arange(now_hour - 5, now_hour + 1)
            raw = pd.DataFrame({
                "_hour": hours,
                "Resp": [resp - 1, resp, resp, resp + 1, resp, resp],
                "O2Sat": [spo2 + 1, spo2, spo2, spo2, spo2, spo2],
                "OxygenTherapy": [1 if spo2 <= 94 else 0] * 6,
                "SBP": [sbp + 3, sbp + 2, sbp + 1, sbp, sbp, sbp],
                "MAP": [max(45, sbp - 25)] * 6,
                "HR": [hr - 3, hr - 2, hr - 1, hr, hr, hr],
                "Temp": [temp - 0.2, temp - 0.1, temp, temp, temp, temp],
                "AVPU": [0] * 6,
                "Lactate": [lactate] * 6,
                "WBC": [wbc] * 6,
                "Creatinine": [creatinine] * 6,
                "Platelets": [platelets] * 6,
            })
            ward = Patient(
                encounter_key=f"{patient_id}--{patient_id}-ENC",
                patient_id=patient_id,
                encounter_id=f"{patient_id}-ENC",
                display_name=label,
                unit_id="ward-demo-1",
                source_mode="api",
                age=age,
                sex=sex,
                raw=raw,
                static_values={"Age": float(age), "Gender": 0.0 if sex == "F" else 1.0},
                segment_start_hour=now_hour - 5,
                bed_id=bed,
                kind="ward",
                admitted_at=(datetime.now(timezone.utc) - timedelta(hours=6 + index)).isoformat(),
                replay_meta={"public_demo_seed": True, "data_class": "synthetic commissioning feed"},
            )
            self.patients[ward.encounter_key] = ward
            self._score_news2(ward)
            self._upsert_encounter(ward, "demo-seed")
        # Commissioning telemetry: one real native_json ingest so Integration Hub
        # shows a genuine connector event (not a decorative badge).
        try:
            from app.auth import Actor
            from app.integrations.service import get_integration_service
            from app.schemas import ObservationBatch, ObservationIn
            from app.services.clinical_contract import SPECS

            sample = next(
                (p for p in self.patients.values() if p.replay_meta.get("public_demo_seed") and p.kind == "icu"),
                None,
            )
            if sample is not None and not sample.raw.empty:
                last = sample.raw.iloc[-1]
                stamp = datetime.now(timezone.utc)
                rows = []
                for code in ("HR", "SBP", "MAP", "O2Sat"):
                    if code in sample.raw.columns and pd.notna(last[code]):
                        rows.append(ObservationIn(
                            patient_id=sample.patient_id,
                            encounter_id=sample.encounter_id,
                            timestamp=stamp,
                            code=code,
                            value=float(last[code]),
                            unit=SPECS[code].canonical_unit,
                            source="simulation-relay",
                            unit_id=sample.unit_id,
                        ))
                if rows:
                    get_integration_service(self).submit(
                        "native_json",
                        ObservationBatch(observations=rows).model_dump_json(),
                        Actor(user_id="simulation-relay", role="integration", auth_mode="simulation"),
                        idempotency_key=f"commissioning-seed-{now_hour}",
                    )
        except Exception as error:  # noqa: BLE001 — seed must not block demo boot
            print(f"commissioning connector seed skipped: {error!r}", flush=True)

    def _seed_public_staff(self) -> None:
        """Create named, scoped commissioning accounts with unrevealed random secrets."""
        from app.accounts import AccountStore

        accounts = AccountStore(self.records)
        roster = (
            ("sim-admin", "Simulation site administrator", "admin", None),
            ("sim-clinician-01", "Simulation ICU clinician 01", "clinician", [settings.api_unit_id]),
            ("sim-clinician-02", "Simulation ICU clinician 02", "clinician", [settings.api_unit_id]),
            ("sim-nurse-01", "Simulation ICU nurse 01", "nurse", [settings.api_unit_id]),
            ("sim-nurse-02", "Simulation ward nurse 02", "nurse", ["ward-demo-1"]),
        )
        for user_id, display_name, role, units in roster:
            if accounts.get(user_id):
                continue
            accounts.create(user_id, display_name, role, secrets.token_urlsafe(32),
                            units=units, actor_id="simulation-commissioning")
        if settings.evaluation_runtime and settings.evaluation_admin_password and not accounts.get("eval-admin"):
            accounts.create("eval-admin", "Synthetic evaluation administrator", "admin",
                            settings.evaluation_admin_password.get_secret_value(), units=None,
                            actor_id="evaluation-bootstrap", must_change_password=False)

    def step(self, hours: int = 1) -> dict:
        with self.lock:
            self._require_writable()
            if self.site.state.effective_mode != "demo":
                raise ModeError("Replay is only available in demo mode.")
            advanced = 0
            for p in self.patients.values():
                for _ in range(hours):
                    if p.source is not None and p.cursor < len(p.source):
                        self._advance(p, emit_alerts=True)
                        advanced += 1
            self._persist_state()
            return {"advanced_patient_hours": advanced, "open_alerts": self.open_alert_count()}

    def advance_public_simulation(self) -> None:
        """Push synthetic SIM vitals through the real ingest/connector path each tick.

        Values are still disclosed synthetic commissioning data — but lag,
        quarantine, and Integration Hub telemetry come from the same
        ``IntegrationService.submit`` path a hospital feed would use.
        """
        from app.auth import Actor
        from app.integrations.service import get_integration_service
        from app.schemas import ObservationBatch, ObservationIn
        from app.services.clinical_contract import SPECS

        with self.lock:
            self._require_writable()
            candidates = [p for p in self.patients.values() if p.replay_meta.get("public_demo_seed") and p.kind == "icu"]
            if not candidates:
                return
            tick = int(time.time() // max(10, settings.public_simulation_interval_seconds))
            phase = tick % 5 - 2
            start = (tick * 3) % len(candidates)
            actor = Actor(user_id="simulation-relay", role="integration", auth_mode="simulation")
            stamp = datetime.now(timezone.utc)
            batch: list[ObservationIn] = []
            for offset in range(min(3, len(candidates))):
                patient = candidates[(start + offset) % len(candidates)]
                last = patient.raw.iloc[-1]
                for field, change in (("HR", 3.0), ("SBP", -2.0), ("MAP", -1.4), ("Resp", 1.0), ("Temp", 0.08), ("O2Sat", -0.3)):
                    if field not in patient.raw.columns or field not in SPECS:
                        continue
                    base = float(last[field]) if pd.notna(last[field]) else float(SPECS[field].minimum + 10)
                    batch.append(ObservationIn(
                        patient_id=patient.patient_id,
                        encounter_id=patient.encounter_id,
                        timestamp=stamp,
                        code=field,
                        value=base + phase * change,
                        unit=SPECS[field].canonical_unit,
                        source="simulation-relay",
                        unit_id=patient.unit_id,
                    ))
            wards = [p for p in self.patients.values() if p.replay_meta.get("public_demo_seed") and p.kind == "ward"]
            if wards:
                ward = wards[tick % len(wards)]
                last = ward.raw.iloc[-1]
                for field, change in (("Resp", 1.0), ("HR", 2.0), ("SBP", -2.0), ("O2Sat", -0.5)):
                    if field not in ward.raw.columns or field not in SPECS:
                        continue
                    base = float(last[field]) if pd.notna(last[field]) else 90.0
                    batch.append(ObservationIn(
                        patient_id=ward.patient_id,
                        encounter_id=ward.encounter_id,
                        timestamp=stamp,
                        code=field,
                        value=base + phase * change,
                        unit=SPECS[field].canonical_unit,
                        source="simulation-relay",
                        unit_id=ward.unit_id,
                    ))
            if not batch:
                return
            # Leave the engine lock before submit — submit re-enters via RLock on ingest.
        service = get_integration_service(self)
        service.submit(
            "native_json",
            ObservationBatch(observations=batch).model_dump_json(),
            actor,
            idempotency_key=f"sim-tick-{tick}",
        )

    def _advance(self, p: Patient, emit_alerts: bool) -> None:
        row = p.source.iloc[[p.cursor]]
        p.raw = pd.concat([p.raw, row], ignore_index=True)
        p.cursor += 1
        self._score(p, emit_alerts)

    # ---------- ingestion ----------
    def ingest(
        self,
        observations: list[Any],
        actor: Any | None = None,
        *,
        connector: str = "native_json",
        backfill: bool = False,
        mapping_rejections: list[dict] | None = None,
    ) -> dict:
        """Validate, merge, and idempotently rescore encounter-scoped observations."""
        started = time.perf_counter()
        with self.lock:
            self._require_writable()
            earliest: dict[str, int] = {}
            accepted = duplicates = 0
            quarantined: list[dict] = []
            max_source_time: datetime | None = None
            for issue in mapping_rejections or []:
                self._log("observation_quarantined", {**issue, "connector": connector})
                quarantined.append(issue)
            for ob in observations:
                if ob.timestamp.tzinfo is None:
                    quarantined.append(self._quarantine(ob, "timestamp_requires_timezone", connector))
                    continue
                checked = validate_observation(ob.code, ob.value, ob.unit)
                if not checked.accepted:
                    quarantined.append(self._quarantine(ob, checked.error or "invalid_observation", connector))
                    continue
                encounter_key = self._encounter_key(ob.patient_id, ob.encounter_id)
                unit_id = getattr(ob, "unit_id", None) or settings.api_unit_id
                if not settings.demo_mode and unit_id not in self.units:
                    quarantined.append(self._quarantine(ob, "unknown_care_unit", connector))
                    continue
                p = self.patients.get(encounter_key)
                if p is None:
                    kind = self.unit_kind(unit_id)
                    p = Patient(
                        encounter_key=encounter_key,
                        patient_id=ob.patient_id,
                        encounter_id=ob.encounter_id,
                        display_name=ob.patient_id,
                        unit_id=unit_id,
                        source_mode="api",
                        kind=kind,
                        status="admitted",
                        admitted_at=utc_now(),
                    )
                    self.patients[encounter_key] = p
                    self._upsert_encounter(p)
                hour = int(ob.timestamp.astimezone(timezone.utc).timestamp() // 3600)
                if p.status == "discharged":
                    quarantined.append(self._quarantine(ob, "encounter_discharged", connector))
                    continue
                elif getattr(ob, "unit_id", None) and ob.unit_id != p.unit_id:
                    if not p.raw.empty and hour < int(p.raw["_hour"].max()):
                        quarantined.append(self._quarantine(ob, "late_unit_change", connector))
                        continue
                    next_kind = self.unit_kind(ob.unit_id)
                    self._log(
                        "encounter_unit_changed",
                        {
                            "patient_id": p.patient_id,
                            "encounter_id": p.encounter_id,
                            "encounter_key": p.encounter_key,
                            "from_unit": p.unit_id,
                            "to_unit": ob.unit_id,
                            "connector": connector,
                        },
                    )
                    p.unit_id = ob.unit_id
                    if p.kind != next_kind:
                        p.segment_start_hour = hour
                        p.icu_start_hour = None
                        p.predictions = []
                        p.news2 = []
                        if next_kind == "ward":
                            for alert in self.alerts.values():
                                if (
                                    alert.get("encounter_key") == p.encounter_key
                                    and alert.get("status") in ACTIVE_ALERT_STATUSES
                                ):
                                    alert["status"] = "superseded"
                                    alert.setdefault("actions", []).append({
                                        "user_id": getattr(actor, "user_id", "system"),
                                        "role": getattr(actor, "role", "integration"),
                                        "action": "superseded",
                                        "reason": "Transferred out of ICU model scope",
                                        "at": utc_now(),
                                    })
                    p.kind = next_kind
                    self._upsert_encounter(p, getattr(actor, "user_id", "system"))
                if p.segment_start_hour is None:
                    p.segment_start_hour = hour
                if ob.code == "ICULOS" and checked.value is not None:
                    inferred_start = hour - int(checked.value) + 1
                    p.icu_start_hour = (
                        inferred_start
                        if p.icu_start_hour is None
                        else min(p.icu_start_hour, inferred_start)
                    )
                elif p.icu_start_hour is None:
                    p.icu_start_hour = hour
                if p.raw.empty or hour not in set(p.raw["_hour"]):
                    new = pd.DataFrame([{"_hour": hour}])
                    p.raw = pd.concat([p.raw, new], ignore_index=True).sort_values("_hour").reset_index(drop=True)
                mask = p.raw["_hour"] == hour
                previous = p.raw.loc[mask, ob.code].iloc[0] if ob.code in p.raw else np.nan
                if (pd.isna(previous) and checked.value is None) or (
                    not pd.isna(previous) and checked.value is not None and float(previous) == float(checked.value)
                ):
                    duplicates += 1
                    self._log(
                        "observation_duplicate_ignored",
                        {
                            "patient_id": p.patient_id,
                            "encounter_id": p.encounter_id,
                            "encounter_key": p.encounter_key,
                            "code": ob.code,
                            "source_time": ob.timestamp.isoformat(),
                        },
                    )
                    continue
                was_late = bool(len(p.raw) and hour < int(p.raw["_hour"].max()))
                p.raw.loc[mask, ob.code] = checked.value
                p.observation_meta[(hour, ob.code)] = {
                    "unit": checked.canonical_unit,
                    "source": ob.source,
                    "connector": connector,
                    "source_time": ob.timestamp.isoformat(),
                    "received_at": utc_now(),
                    "warning": checked.warning,
                }
                if ob.code in set(DEMO_COLS) - {"ICULOS"} and checked.value is not None:
                    p.static_values[ob.code] = float(checked.value)
                    if ob.code == "Age":
                        p.age = int(checked.value)
                    elif ob.code == "Gender":
                        p.sex = {0: "F", 1: "M"}.get(int(checked.value))
                accepted += 1
                stamp = ob.timestamp.astimezone(timezone.utc)
                max_source_time = stamp if max_source_time is None else max(max_source_time, stamp)
                earliest[encounter_key] = min(hour, earliest.get(encounter_key, hour))
                self._log(
                    "observation_late_accepted" if was_late else "observation_accepted",
                    {
                        "patient_id": p.patient_id,
                        "encounter_id": p.encounter_id,
                        "encounter_key": p.encounter_key,
                        "code": ob.code,
                        "source": ob.source,
                        "connector": connector,
                        "source_time": ob.timestamp.isoformat(),
                        "unit": checked.canonical_unit,
                        "validation_warning": checked.warning,
                    },
                )
            self._force_shadow = backfill
            try:
                rescored: list[tuple[Patient, int]] = []
                for encounter_key, first_hour in earliest.items():
                    patient = self.patients[encounter_key]
                    self._upsert_encounter(patient, getattr(actor, "user_id", "system"))
                    if patient.kind == "ward":
                        self._score_news2(patient)
                    else:
                        rescored.append((patient, self._recompute_api_patient(patient, first_hour)))
            finally:
                self._force_shadow = False
            processing_ms = (time.perf_counter() - started) * 1000
            for patient, start in rescored:
                self._queue_prediction_records(
                    patient, patient.predictions[start:], "backfill" if backfill else "realtime", processing_ms
                )
            self._log(
                "observation_batch_processed",
                {
                    "actor": getattr(actor, "user_id", "system"),
                    "actor_role": getattr(actor, "role", "system"),
                    "connector": connector,
                    "backfill": backfill,
                    "received": len(observations) + len(mapping_rejections or []),
                    "accepted": accepted,
                    "duplicates_ignored": duplicates,
                    "quarantined": len(quarantined),
                    "encounters_rescored": len(earliest),
                },
            )
            self._persist_state()
            return {
                "patients_rescored": len(earliest),
                "accepted": accepted,
                "duplicates_ignored": duplicates,
                "quarantined": quarantined,
                "max_source_time": max_source_time.isoformat() if max_source_time else None,
                "processing_ms": round(processing_ms, 2),
            }

    @staticmethod
    def _encounter_key(patient_id: str, encounter_id: str) -> str:
        return f"{patient_id}--{encounter_id}"

    def _quarantine(self, observation: Any, reason: str, connector: str = "native_json") -> dict:
        issue = {
            "patient_id": observation.patient_id,
            "encounter_id": observation.encounter_id,
            "code": observation.code,
            "source_time": observation.timestamp.isoformat(),
            "reason": reason,
        }
        self._log("observation_quarantined", {**issue, "connector": connector})
        return issue

    def _materialize_api_timeline(self, patient: Patient) -> pd.DataFrame:
        observed = patient.raw.sort_values("_hour").reset_index(drop=True)
        if patient.segment_start_hour is not None:
            observed = observed.loc[observed["_hour"] >= patient.segment_start_hour].reset_index(drop=True)
        first_observed = int(observed["_hour"].min())
        start = min(patient.icu_start_hour or first_observed, first_observed)
        end = int(observed["_hour"].max())
        timeline = pd.DataFrame({"_hour": np.arange(start, end + 1, dtype=int)})
        timeline = timeline.merge(observed, on="_hour", how="left", sort=True)
        timeline["ICULOS"] = timeline["_hour"] - start + 1
        for code, value in patient.static_values.items():
            timeline[code] = timeline[code].fillna(value) if code in timeline else value
        return timeline

    def _recompute_api_patient(self, patient: Patient, first_hour: int) -> int:
        timeline = self._materialize_api_timeline(patient)
        patient.revision += 1
        retained = [
            prediction
            for prediction in patient.predictions
            if prediction.get("source_hour", -1) < first_hour
        ]
        patient.predictions = retained
        start = len(retained)
        for size in range(start + 1, len(timeline) + 1):
            self._score(
                patient,
                emit_alerts=False,
                upto=size,
                raw_frame=timeline,
                audit_event="prediction_recomputed",
            )
        self._reconcile_alerts(patient)
        return start

    def _queue_prediction_records(
        self, patient: Patient, predictions: list[dict], ingest_mode: str, processing_ms: float
    ) -> None:
        scored_at = utc_now()
        site_mode = self.site.state.effective_mode
        for prediction in predictions:
            alert_id = prediction.get("alert_id")
            disposition = "none"
            if alert_id and alert_id in self.alerts:
                disposition = "shadow" if self.alerts[alert_id]["status"] == "silent" else "interruptive"
            key = f"{patient.encounter_key}|{prediction.get('source_hour')}|{prediction['input_revision']}|{self.model_version}"
            trust = prediction.get("trustgate", {})
            self._pending_records.append(
                {
                    "record_id": hashlib.sha256(key.encode()).hexdigest()[:32],
                    "site_id": self.site.state.site_id,
                    "unit_id": patient.unit_id,
                    "encounter_key": patient.encounter_key,
                    "patient_id": patient.patient_id,
                    "encounter_id": patient.encounter_id,
                    "source_time": prediction["timestamp"],
                    "scored_at": scored_at,
                    "hour": int(prediction["hour"]),
                    "probability": prediction["probability"],
                    "risk_band": prediction["risk_band"],
                    "trust_state": trust.get("state", "abstain"),
                    "data_quality": prediction["data_quality"],
                    "freshness_minutes": prediction["data_freshness_minutes"],
                    "input_shift": trust.get("input_shift_score"),
                    "input_revision": int(prediction["input_revision"]),
                    "model_version": self.model_version,
                    "site_mode": site_mode,
                    "ingest_mode": ingest_mode,
                    "alert_id": alert_id,
                    "alert_disposition": disposition,
                    "age": patient.age,
                    "sex": patient.sex,
                    "processing_ms": round(processing_ms, 3),
                    "payload": json.dumps(
                        _json_safe(
                            {
                                "signal_freshness": prediction.get("signal_freshness_minutes", {}),
                                "trust_reasons": trust.get("reasons", []),
                                "uncertainty": prediction.get("uncertainty"),
                                "context_subgroups": clinical_context.subgroups(patient.context),
                            }
                        ),
                        separators=(",", ":"),
                    ),
                }
            )

    # ---------- scoring ----------
    def _score(
        self,
        p: Patient,
        emit_alerts: bool,
        upto: int | None = None,
        raw_frame: pd.DataFrame | None = None,
        audit_event: str = "prediction",
    ) -> dict:
        started = time.perf_counter()
        try:
            pred = self._score_inner(p, upto, raw_frame)
        except Exception:
            METRICS.inference_failed()
            raise
        METRICS.observe_inference(time.perf_counter() - started)
        if not p.predictions:
            previous = "insufficient_data"
        else:
            previous_prediction = p.predictions[-1]
            previous = previous_prediction["risk_band"]
            if (
                previous == "high_risk"
                and previous_prediction.get("trustgate", {}).get("state") != TrustState.alert.value
            ):
                previous = "watch"
        p.predictions.append(pred)
        pred["scored_at"] = utc_now()
        self._log(audit_event, {
            "patient_id": p.patient_id,
            "encounter_id": p.encounter_id,
            "encounter_key": p.encounter_key,
            "hour": pred["hour"],
            "source_time": pred["timestamp"],
            "probability": pred["probability"],
            "risk_band": pred["risk_band"],
            "input_revision": p.revision,
        })
        if emit_alerts:
            self._maybe_alert(p, pred, previous)
        return pred

    def _score_inner(self, p: Patient, upto: int | None, raw_frame: pd.DataFrame | None) -> dict:
        source_frame = raw_frame if raw_frame is not None else p.raw
        selected = source_frame.iloc[:upto].copy()
        source_hour = (
            int(selected["_hour"].iloc[-1])
            if "_hour" in selected and not pd.isna(selected["_hour"].iloc[-1])
            else None
        )
        raw = selected.drop(columns=["_hour"], errors="ignore")
        for col in VITAL_COLS + LAB_COLS + DEMO_COLS:
            if col not in raw:
                raw[col] = np.nan
        feats = build_patient_features(raw)
        feats["hours_observed"] = np.arange(1, len(feats) + 1)
        last = feats.iloc[[-1]]
        hours = len(feats)
        hour_idx = hours - 1
        signal_freshness: dict[str, int | None] = {}
        for variable in VITAL_COLS + LAB_COLS:
            column = f"{variable}_hours_since"
            value = last[column].iloc[0] if column in last else np.nan
            signal_freshness[variable] = None if pd.isna(value) else int(float(value) * 60)
        required_freshness = [signal_freshness[variable] for variable in REQUIRED_SIGNALS]
        freshness_minutes = max(required_freshness) if all(value is not None for value in required_freshness) else None

        if hours < MIN_HOURS_BEFORE_PRED:
            pred = {"probability": None, "uncertainty": None, "risk_band": "insufficient_data",
                    "data_quality": "insufficient", "factors": []}
        else:
            prob = float(self.model.predict_proba(last)[0, 1])
            unc = float(self.uncertainty_model.uncertainty(last)[0])
            if prob >= self.thresholds["high_risk"]:
                band = "high_risk"
            elif prob >= self.thresholds["watch"]:
                band = "watch"
            else:
                band = "stable"
            if freshness_minutes is None:
                quality = "missing_required_vitals"
            elif freshness_minutes > 120:
                quality = "stale_required_vitals"
            else:
                quality = "ok"
            pred = {"probability": prob, "uncertainty": unc, "risk_band": band, "data_quality": quality,
                    "factors": explain_rows(self.model, last)[0]}

        perturbations = (
            self._perturbed_probabilities(raw)
            if pred["risk_band"] == "high_risk"
            else []
        )
        trustgate = assess_prediction(
            probability=pred["probability"],
            risk_band=pred["risk_band"],
            data_quality=pred["data_quality"],
            data_freshness_minutes=freshness_minutes,
            signal_freshness=signal_freshness,
            high_risk_threshold=self.thresholds["high_risk"],
            perturbed_probabilities=perturbations,
            disagreement=pred["uncertainty"],
            disagreement_validated=False,
        )
        if p.source_mode == "api" and source_hour is not None:
            timestamp = datetime.fromtimestamp(source_hour * 3600, tz=timezone.utc)
        else:
            timestamp = REPLAY_EPOCH + timedelta(hours=hour_idx)
        pred.update({
            "hour": int(raw["ICULOS"].iloc[-1]) if "ICULOS" in raw and not pd.isna(raw["ICULOS"].iloc[-1]) else hours,
            "index": hour_idx,
            "source_hour": source_hour,
            "timestamp": timestamp.isoformat(),
            "data_freshness_minutes": freshness_minutes,
            "signal_freshness_minutes": signal_freshness,
            "vitals": {v: _clean(last[v].iloc[0]) for v in TREND_VARS if v in last},
            "model_version": self.model_version,
            "alert_id": None,
            "input_revision": p.revision,
            "trustgate": trustgate.as_dict(),
        })
        return pred

    def _perturbed_probabilities(self, raw: pd.DataFrame) -> list[float]:
        """Stress an alert candidate under three plausible missing/delayed views."""
        scenarios: list[pd.DataFrame] = []

        delayed_vitals = raw.copy()
        vital_columns = [column for column in REQUIRED_SIGNALS if column in delayed_vitals]
        if vital_columns:
            delayed_vitals.loc[delayed_vitals.index[-2:], vital_columns] = np.nan
        scenarios.append(delayed_vitals)

        delayed_labs = raw.copy()
        lab_columns = [column for column in LAB_COLS if column in delayed_labs]
        if lab_columns:
            delayed_labs.loc[delayed_labs.index[-6:], lab_columns] = np.nan
        scenarios.append(delayed_labs)

        no_lactate = raw.copy()
        if "Lactate" in no_lactate:
            no_lactate["Lactate"] = np.nan
        scenarios.append(no_lactate)

        probabilities: list[float] = []
        for scenario in scenarios:
            features = build_patient_features(scenario)
            features["hours_observed"] = np.arange(1, len(features) + 1)
            probabilities.append(float(self.model.predict_proba(features.iloc[[-1]])[0, 1]))
        return probabilities

    def _alert_is_interruptive(self, p: Patient) -> bool:
        if self._force_shadow:
            return False
        if clinical_context.alert_policy(p.context)[0] == "shadow_only":
            return False
        return p.source_mode == "replay" or self.site.state.interruptive_alerts_enabled

    def _maybe_alert(self, p: Patient, pred: dict, previous: str) -> None:
        band = pred["risk_band"]
        if (
            band != "high_risk"
            or pred.get("trustgate", {}).get("state") != TrustState.alert.value
            or BAND_ORDER[band] <= BAND_ORDER[previous]
        ):
            return
        active_alert = next((a for a in self.alerts.values()
                             if a.get("encounter_key") == p.encounter_key
                             and a["status"] in ACTIVE_ALERT_STATUSES), None)
        if active_alert and BAND_ORDER[active_alert["risk_band"]] >= BAND_ORDER[band]:
            pred["alert_id"] = active_alert["alert_id"]
            return
        if active_alert:
            active_alert["status"] = "superseded"
        alert_key = f"{self.model_version}|{p.encounter_key}|{pred.get('source_hour', pred['hour'])}|{band}"
        alert_id = f"alert-{hashlib.sha256(alert_key.encode()).hexdigest()[:12]}"
        existing = self.alerts.get(alert_id)
        if existing and existing["status"] != "retracted":
            pred["alert_id"] = alert_id
            return
        threshold = self.thresholds[band]
        interruptive = self._alert_is_interruptive(p)
        self.alerts[alert_id] = {
            "alert_id": alert_id,
            "patient_id": p.patient_id,
            "encounter_id": p.encounter_id,
            "encounter_key": p.encounter_key,
            "display_name": p.display_name,
            "unit_id": p.unit_id,
            "risk_band": band,
            "probability": pred["probability"],
            "uncertainty": pred["uncertainty"],
            "threshold": threshold,
            "hour": pred["hour"],
            "created_at": pred["timestamp"],
            "raised_at": utc_now(),
            "reason": (
                f"High-risk early-warning score {pred['probability']:.0%} crossed "
                f"the validation-selected {threshold:.0%} threshold"
            ),
            "factors": pred["factors"],
            "data_quality": pred["data_quality"],
            "trustgate": pred["trustgate"],
            "model_version": self.model_version,
            "model_hash": self.model_hash,
            "input_revision": pred["input_revision"],
            "status": "open" if interruptive else "silent",
            "disposition": "interruptive" if interruptive else "shadow",
            "context_policy": clinical_context.alert_policy(p.context)[1],
            "actions": [],
        }
        pred["alert_id"] = alert_id
        self._log("alert_created" if interruptive else "alert_shadow_recorded", {
            "alert_id": alert_id,
            "patient_id": p.patient_id,
            "encounter_id": p.encounter_id,
            "encounter_key": p.encounter_key,
            "risk_band": band,
            "source_time": pred["timestamp"],
            "input_revision": pred["input_revision"],
            "site_mode": self.site.state.effective_mode,
        })

    def _reconcile_alerts(self, patient: Patient) -> None:
        for prediction in patient.predictions:
            prediction["alert_id"] = None
        desired: tuple[dict, str] | None = None
        previous = "insufficient_data"
        for prediction in patient.predictions:
            trusted_alert = (
                prediction["risk_band"] == "high_risk"
                and prediction.get("trustgate", {}).get("state") == TrustState.alert.value
            )
            if trusted_alert and previous != "high_risk":
                desired = (prediction, previous)
            previous = (
                "high_risk"
                if trusted_alert
                else ("watch" if prediction["risk_band"] == "high_risk" else prediction["risk_band"])
            )
        desired_id = None
        if (
            desired
            and patient.predictions[-1].get("trustgate", {}).get("state") == TrustState.alert.value
        ):
            prediction, prior_band = desired
            self._maybe_alert(patient, prediction, prior_band)
            desired_id = prediction["alert_id"]
        for alert in self.alerts.values():
            if (
                alert.get("encounter_key") == patient.encounter_key
                and alert["status"] in ACTIVE_ALERT_STATUSES
                and alert["alert_id"] != desired_id
            ):
                alert["status"] = "retracted"
                self._log(
                    "alert_retracted_after_recompute",
                    {
                        "alert_id": alert["alert_id"],
                        "patient_id": patient.patient_id,
                        "encounter_id": patient.encounter_id,
                        "encounter_key": patient.encounter_key,
                        "input_revision": patient.revision,
                    },
                )

    # ---------- alert workflow ----------
    def act_on_alert(
        self,
        alert_id: str,
        user_id: str,
        action: str,
        reason: str | None,
        ts: datetime,
        role: str = "clinician",
        *,
        quiet_minutes: int | None = None,
    ) -> str:
        with self.lock:
            self._require_writable()
            alert = self.alerts[alert_id]
            alert["status"] = action
            if action == "snoozed":
                minutes = int(quiet_minutes or 60)
                alert["snoozed_until"] = (ts + timedelta(minutes=minutes)).isoformat()
            else:
                alert.pop("snoozed_until", None)
            alert["actions"].append({
                "user_id": user_id,
                "role": role,
                "action": action,
                "reason": reason,
                "at": ts.isoformat(),
                "quiet_minutes": quiet_minutes if action == "snoozed" else None,
            })
            audit_id = self._log("alert_" + action, {
                "alert_id": alert_id,
                "patient_id": alert["patient_id"],
                "encounter_id": alert.get("encounter_id"),
                "encounter_key": alert.get("encounter_key"),
                "user_id": user_id,
                "actor": user_id,
                "actor_role": role,
                "reason": reason,
                "quiet_minutes": quiet_minutes if action == "snoozed" else None,
                "source_time": ts.isoformat(),
            })
            self._persist_state()
            return audit_id

    def open_alert_count(self, patient_identifier: str | None = None) -> int:
        now = datetime.now(timezone.utc)
        count = 0
        for alert in self.alerts.values():
            if patient_identifier is not None and patient_identifier not in {
                alert["patient_id"], alert.get("encounter_key")
            }:
                continue
            if alert["status"] == "open":
                count += 1
            elif alert["status"] == "snoozed":
                until = alert.get("snoozed_until")
                if until and datetime.fromisoformat(until) <= now:
                    alert["status"] = "open"
                    alert.pop("snoozed_until", None)
                    count += 1
        return count

    def resolve_patient(self, identifier: str) -> Patient | None:
        direct = self.patients.get(identifier)
        if direct is not None:
            return direct
        matches = [patient for patient in self.patients.values() if patient.patient_id == identifier]
        return matches[0] if len(matches) == 1 else None

    # ---------- shift ownership and handoff ----------
    def claim_ownership(self, patient: Patient, actor: Any, shift_label: str | None) -> dict:
        with self.lock:
            self._require_writable()
            row = {
                "encounter_key": patient.encounter_key,
                "owner": actor.user_id,
                "role": actor.role,
                "shift_label": shift_label,
                "claimed_at": utc_now(),
            }
            self.records.upsert(bed_ownership, "encounter_key", row)
            self.ownership[patient.encounter_key] = row
            self._log("bed_ownership_claimed", {
                "patient_id": patient.patient_id,
                "encounter_key": patient.encounter_key,
                "actor": actor.user_id,
                "actor_role": actor.role,
                "shift_label": shift_label,
            })
            return row

    def release_ownership(self, patient: Patient, actor: Any) -> None:
        with self.lock:
            self._require_writable()
            self.records.delete(bed_ownership, bed_ownership.c.encounter_key == patient.encounter_key)
            previous = self.ownership.pop(patient.encounter_key, None)
            self._log("bed_ownership_released", {
                "patient_id": patient.patient_id,
                "encounter_key": patient.encounter_key,
                "actor": actor.user_id,
                "actor_role": actor.role,
                "previous_owner": previous["owner"] if previous else None,
            })

    def add_handoff_note(self, patient: Patient, actor: Any, note: str) -> dict:
        with self.lock:
            self._require_writable()
            recorded_at = utc_now()
            row = {
                "note_id": hashlib.sha256(f"{patient.encounter_key}|{actor.user_id}|{recorded_at}|{note}".encode()).hexdigest()[:32],
                "encounter_key": patient.encounter_key,
                "user_id": actor.user_id,
                "note": note,
                "recorded_at": recorded_at,
            }
            self.records.insert(handoff_notes, row)
            self._log("handoff_note_added", {
                "patient_id": patient.patient_id,
                "encounter_key": patient.encounter_key,
                "actor": actor.user_id,
                "actor_role": actor.role,
                "note_id": row["note_id"],
            })
            return row

    def handoff_notes_for(self, encounter_key: str, limit: int = 5) -> list[dict]:
        return self.records.select(
            handoff_notes,
            handoff_notes.c.encounter_key == encounter_key,
            order_by=handoff_notes.c.recorded_at.desc(),
            limit=limit,
        )

    # ---------- provenance ----------
    def patient_frame(self, patient: Patient) -> pd.DataFrame:
        """Hourly observed (not forward-filled) frame with an ``_hour`` key for either source."""
        if patient.source_mode == "api":
            if patient.raw.empty:
                return pd.DataFrame({"_hour": []})
            return self._materialize_api_timeline(patient)
        frame = patient.raw.copy()
        frame["_hour"] = np.arange(len(frame))
        return frame

    def provenance(self, patient: Patient) -> list[dict]:
        frame = self.patient_frame(patient)
        rows: list[dict] = []
        for code in VITAL_COLS + LAB_COLS:
            if code not in frame or frame[code].notna().sum() == 0:
                continue
            observed = frame[frame[code].notna()]
            last = observed.iloc[-1]
            hour = int(last["_hour"])
            meta = patient.observation_meta.get((hour, code), {})
            if patient.source_mode == "api":
                source_time = meta.get("source_time") or datetime.fromtimestamp(hour * 3600, tz=timezone.utc).isoformat()
                source = meta.get("source", "api")
            else:
                source_time = (REPLAY_EPOCH + timedelta(hours=hour)).isoformat()
                source = "physionet-2019-held-out-replay"
            rows.append({
                "code": code,
                "value": float(last[code]),
                "unit": meta.get("unit") or _canonical_unit(code),
                "source": source,
                "connector": meta.get("connector", "replay" if patient.source_mode == "replay" else "native_json"),
                "source_time": source_time,
                "received_at": meta.get("received_at"),
                "validation_warning": meta.get("warning"),
                "observations_total": int(observed.shape[0]),
                "required": code in REQUIRED_SIGNALS,
            })
        return rows

    def signal_matrix(self, patient: Patient, hours: int = 24) -> dict:
        frame = self.patient_frame(patient).tail(hours)
        hour_labels = [
            int(value) for value in (frame["ICULOS"] if "ICULOS" in frame else frame["_hour"]).fillna(0)
        ]
        signals = []
        for code in MATRIX_SIGNALS:
            observed = [bool(flag) for flag in frame[code].notna()] if code in frame else [False] * len(frame)
            signals.append({
                "code": code,
                "required": code in REQUIRED_SIGNALS,
                "observed": observed,
                "observed_hours": int(sum(observed)),
            })
        return {"hours": hour_labels, "signals": signals, "window_hours": len(frame)}

    # ---------- persistence ----------
    @staticmethod
    def _snapshot_key(encounter_key: str) -> str:
        return "patient:" + hashlib.sha256(encounter_key.encode()).hexdigest()[:40]

    def _restore_state(self) -> None:
        entries = self.store.load_state_entries()
        self._snapshot_keys = set(entries)
        patient_payloads: list[dict] = []
        alerts_payload: dict = {}
        if any(key.startswith("patient:") or key == "alerts" for key in entries):
            for key, payload in entries.items():
                if key.startswith("patient:"):
                    patient_payloads.append(payload)
                    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
                    self._snapshot_hashes[key] = hashlib.sha256(blob.encode()).hexdigest()
                elif key == "alerts":
                    alerts_payload = payload or {}
                    blob = json.dumps(alerts_payload, sort_keys=True, separators=(",", ":"), default=str)
                    self._snapshot_hashes[key] = hashlib.sha256(blob.encode()).hexdigest()
        else:
            legacy = entries.get("engine-v1") or self.store.load_state()
            if not legacy:
                return
            patient_payloads = legacy.get("patients", [])
            alerts_payload = legacy.get("alerts", {})
        for stored in patient_payloads:
            raw = pd.DataFrame(stored.get("raw", []))
            observation_meta = {}
            for key, value in stored.get("observation_meta", {}).items():
                hour, code = key.split("|", 1)
                observation_meta[(int(hour), code)] = value
            patient = Patient(
                encounter_key=stored["encounter_key"],
                patient_id=stored["patient_id"],
                encounter_id=stored["encounter_id"],
                display_name=stored["display_name"],
                unit_id=stored["unit_id"],
                source_mode="api",
                age=stored.get("age"),
                sex=stored.get("sex"),
                raw=raw,
                predictions=stored.get("predictions", []),
                static_values=stored.get("static_values", {}),
                observation_meta=observation_meta,
                icu_start_hour=stored.get("icu_start_hour"),
                segment_start_hour=stored.get("segment_start_hour"),
                revision=stored.get("revision", 0),
                bed_id=stored.get("bed_id"),
                kind=stored.get("kind", "icu"),
                status=stored.get("status", "admitted"),
                hypercapnic_scale2=bool(stored.get("hypercapnic_scale2", False)),
                admitted_at=stored.get("admitted_at"),
                discharged_at=stored.get("discharged_at"),
                news2=stored.get("news2", []),
                context=stored.get("context"),
            )
            self.patients[patient.encounter_key] = patient
        self.alerts.update(alerts_payload)

    def _write_snapshot_entry(self, key: str, payload: dict) -> None:
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        digest = hashlib.sha256(blob.encode()).hexdigest()
        if self._snapshot_hashes.get(key) == digest:
            return
        self.store.save_state_entry(key, payload)
        self._snapshot_hashes[key] = digest
        self.snapshot_writes_total += 1
        self.snapshot_bytes_written_total += len(blob)

    def _persist_state(self) -> None:
        """Persist restart state incrementally: one row per encounter plus one alerts row.

        Only entries whose content changed are rewritten, so an ingest batch for
        one bed no longer rewrites every bed's snapshot. Durability is unchanged:
        writes are synchronous and prediction/audit rows flush first.
        """
        if settings.writer_lease_enabled and not self.records.renew_lease(LEASE_KEY, self.writer_id):
            self.read_only_reason = "writer_lease_lost"
            raise ReadOnlyError(self.read_only_reason)
        started = time.perf_counter()
        if self._pending_records:
            self.records.insert_many_ignore(prediction_records, _json_safe(self._pending_records))
            self._pending_records = []
        api_keys = set()
        seen_keys: set[str] = set()
        for patient in self.patients.values():
            if patient.source_mode != "api":
                continue
            api_keys.add(patient.encounter_key)
            key = self._snapshot_key(patient.encounter_key)
            seen_keys.add(key)
            raw_records = json.loads(patient.raw.to_json(orient="records"))
            self._write_snapshot_entry(
                key,
                _json_safe(
                    {
                        "encounter_key": patient.encounter_key,
                        "patient_id": patient.patient_id,
                        "encounter_id": patient.encounter_id,
                        "display_name": patient.display_name,
                        "unit_id": patient.unit_id,
                        "age": patient.age,
                        "sex": patient.sex,
                        "raw": raw_records,
                        "predictions": patient.predictions,
                        "static_values": patient.static_values,
                        "observation_meta": {
                            f"{hour}|{code}": metadata
                            for (hour, code), metadata in patient.observation_meta.items()
                        },
                        "icu_start_hour": patient.icu_start_hour,
                        "segment_start_hour": patient.segment_start_hour,
                        "revision": patient.revision,
                        "bed_id": patient.bed_id,
                        "kind": patient.kind,
                        "status": patient.status,
                        "hypercapnic_scale2": patient.hypercapnic_scale2,
                        "admitted_at": patient.admitted_at,
                        "discharged_at": patient.discharged_at,
                        "news2": patient.news2,
                        "context": patient.context,
                    }
                ),
            )
        alerts = {
            alert_id: alert
            for alert_id, alert in self.alerts.items()
            if alert.get("encounter_key") in api_keys
        }
        self._write_snapshot_entry("alerts", _json_safe(alerts))
        seen_keys.add("alerts")
        for stale_key in self._snapshot_keys - seen_keys:
            self.store.delete_state_entry(stale_key)
            self._snapshot_hashes.pop(stale_key, None)
        self._snapshot_keys = seen_keys
        self.snapshot_last_persist_ms = round((time.perf_counter() - started) * 1000, 2)

    def _log(self, event: str, detail: dict) -> str:
        recorded_at = datetime.now(timezone.utc).isoformat()
        previous_hash = self.audit[-1]["event_hash"] if self.audit else "0" * 64
        canonical = {
            "event": event,
            "recorded_at": recorded_at,
            "model_version": self.model_version,
            "model_hash": self.model_hash,
            "previous_hash": previous_hash,
            **detail,
        }
        event_hash = hashlib.sha256(
            json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()
        audit_id = f"audit-{event_hash[:12]}"
        self.audit.append({
            "audit_id": audit_id,
            "event": event,
            "at": recorded_at,
            "recorded_at": recorded_at,
            "model_version": self.model_version,
            "model_hash": self.model_hash,
            "previous_hash": previous_hash,
            "event_hash": event_hash,
            **detail,
        })
        self.store.append_audit(_json_safe(self.audit[-1]))
        return audit_id


def _canonical_unit(code: str) -> str | None:
    from app.services.clinical_contract import SPECS

    spec = SPECS.get(code)
    return spec.canonical_unit if spec else None


def _clean(v: Any) -> float | None:
    return None if v is None or pd.isna(v) else float(v)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
        return None
    return value


def _active_model_path() -> Path:
    configured = Path(settings.model_path)
    registry_path = Path(settings.model_registry_path)
    if not settings.use_model_registry or not registry_path.exists():
        return configured
    record = json.loads(registry_path.read_text())
    selected = Path(record["model_path"])
    if not selected.is_absolute():
        selected = registry_path.parent / selected
    actual_hash = hashlib.sha256(selected.read_bytes()).hexdigest()
    if actual_hash != record["model_sha256"]:
        raise RuntimeError("Active model registry hash mismatch.")
    return selected


_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = Engine()
    return _engine


def shutdown_engine() -> None:
    global _engine
    if _engine is not None:
        _engine.close()
        _engine = None
