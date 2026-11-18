"""SLA clocks, CAPA/QMS records, and shared entitlement helpers.

These are vendor/customer metadata workflows only. They never touch hospital
clinical databases or patient records.
"""

from __future__ import annotations

import json
import secrets
from datetime import date, datetime, timedelta, timezone
from typing import Callable

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from permissions import has_permission, require_permission


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


SEVERITY_SLA_CAPS = {"urgent": 60, "degraded": 240, "routine": 1440}
CAPA_STATES = {"open", "investigation", "action_planned", "in_progress", "verification", "closed", "cancelled"}
FINDING_STATES = {"open", "accepted", "linked_capa", "closed", "rejected"}
FINDING_TYPES = {"audit_finding", "incident", "complaint", "near_miss", "process_gap", "other"}


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CapaCreate(Strict):
    site_id: str
    title: str = Field(min_length=3, max_length=160)
    severity: str = Field(pattern="^(low|moderate|high|critical)$")
    owner: str = Field(min_length=2, max_length=120)
    due_on: date
    source_type: str = Field(default="manual", pattern="^(manual|compliance_task|ticket|qms_finding|other)$")
    source_id: str | None = Field(default=None, max_length=64)
    description: str = Field(min_length=3, max_length=1000)


class CapaUpdate(Strict):
    status: str
    root_cause: str | None = Field(default=None, max_length=1000)
    corrective_action: str | None = Field(default=None, max_length=1000)
    preventive_action: str | None = Field(default=None, max_length=1000)
    evidence_ref: str | None = Field(default=None, max_length=160)
    reason: str = Field(min_length=3, max_length=240)


class FindingCreate(Strict):
    site_id: str
    finding_type: str
    description: str = Field(min_length=3, max_length=1000)
    severity: str = Field(pattern="^(low|moderate|high|critical)$")
    owner: str = Field(min_length=2, max_length=120)
    due_on: date


class FindingUpdate(Strict):
    status: str
    capa_id: str | None = None
    evidence_ref: str | None = Field(default=None, max_length=160)
    reason: str = Field(min_length=3, max_length=240)


def sla_target_minutes(severity: str, plan_minutes: int | None) -> int:
    cap = SEVERITY_SLA_CAPS.get(severity, 1440)
    if plan_minutes is None:
        return cap
    return max(1, min(int(plan_minutes), cap))


def sla_due_iso(opened_at: str, minutes: int) -> str:
    opened = datetime.fromisoformat(opened_at)
    return (opened + timedelta(minutes=minutes)).isoformat()


def sla_fields(row: dict, now: datetime | None = None) -> dict:
    current = now or datetime.now(timezone.utc)
    due = row.get("sla_due_at")
    status = row.get("status")
    first = row.get("first_response_at") or row.get("acknowledged_at")
    breached = bool(row.get("sla_breached"))
    if due and status in {"open", "acknowledged", "in_progress", "waiting_for_hospital", "waiting_for_vendor"}:
        due_at = datetime.fromisoformat(due)
        if first:
            breached = datetime.fromisoformat(first) > due_at
        else:
            breached = current > due_at
    minutes_remaining = None
    if due and not first and status == "open":
        minutes_remaining = int((datetime.fromisoformat(due) - current).total_seconds() // 60)
    return {
        **row,
        "sla_breached": breached,
        "sla_minutes_remaining": minutes_remaining,
        "sla_response_met": bool(first) and due and datetime.fromisoformat(first) <= datetime.fromisoformat(due),
    }


def ensure_ticket_sla_columns(store) -> None:
    columns = {row[1] for row in store.db.execute("PRAGMA table_info(tickets)")}
    for name, definition in (
        ("assigned_to", "TEXT"),
        ("first_response_at", "TEXT"),
        ("acknowledged_at", "TEXT"),
        ("sla_due_at", "TEXT"),
        ("sla_breached", "INTEGER NOT NULL DEFAULT 0"),
        ("escalation_level", "INTEGER NOT NULL DEFAULT 0"),
        ("support_plan_id", "TEXT"),
        ("sla_target_minutes", "INTEGER"),
    ):
        if name not in columns:
            store.db.execute(f"ALTER TABLE tickets ADD COLUMN {name} {definition}")


def ensure_asset_lifecycle_columns(store) -> None:
    columns = {row[1] for row in store.db.execute("PRAGMA table_info(assets)")}
    for name, definition in (
        ("serial_number", "TEXT"),
        ("warranty_until", "TEXT"),
        ("lifecycle_state", "TEXT NOT NULL DEFAULT 'commissioned'"),
        ("retired_at", "TEXT"),
        ("disposition_ref", "TEXT"),
        ("updated_at", "TEXT"),
    ):
        if name not in columns:
            store.db.execute(f"ALTER TABLE assets ADD COLUMN {name} {definition}")
    store.db.execute("UPDATE assets SET lifecycle_state='commissioned' WHERE lifecycle_state IS NULL OR lifecycle_state=''")
    store.db.execute("UPDATE assets SET updated_at=registered_at WHERE updated_at IS NULL")


def resolve_support_plan(store, site_id: str) -> dict | None:
    return store.db.execute(
        "SELECT * FROM support_plans WHERE site_id=? ORDER BY created_at DESC LIMIT 1",
        (site_id,),
    ).fetchone()


def install_governance_routes(app: FastAPI, store, require_user: Callable, require_vendor: Callable) -> None:
    with store.lock:
        store.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS capa_records (
              id TEXT PRIMARY KEY,
              organization_id TEXT NOT NULL REFERENCES organizations(id),
              site_id TEXT NOT NULL REFERENCES sites(id),
              title TEXT NOT NULL,
              description TEXT NOT NULL,
              severity TEXT NOT NULL,
              status TEXT NOT NULL,
              owner TEXT NOT NULL,
              due_on TEXT NOT NULL,
              source_type TEXT NOT NULL,
              source_id TEXT,
              root_cause TEXT,
              corrective_action TEXT,
              preventive_action TEXT,
              evidence_ref TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              closed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS qms_findings (
              id TEXT PRIMARY KEY,
              organization_id TEXT NOT NULL REFERENCES organizations(id),
              site_id TEXT NOT NULL REFERENCES sites(id),
              finding_type TEXT NOT NULL,
              description TEXT NOT NULL,
              severity TEXT NOT NULL,
              status TEXT NOT NULL,
              owner TEXT NOT NULL,
              due_on TEXT NOT NULL,
              capa_id TEXT REFERENCES capa_records(id),
              evidence_ref TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            """
        )
        store.db.commit()

    def site_org(site_id: str, user: dict) -> str:
        row = store.db.execute("SELECT organization_id FROM sites WHERE id=?", (site_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Site not found")
        org_id = row["organization_id"]
        if user["evaluation"] and org_id != "evaluation-hospital":
            raise HTTPException(status_code=404, detail="Site not found")
        if not user["vendor"] and org_id not in user["organization_ids"]:
            raise HTTPException(status_code=404, detail="Site not found")
        return org_id

    def listed_capa(user: dict) -> list[dict]:
        with store.lock:
            if user["evaluation"]:
                rows = store.db.execute(
                    "SELECT * FROM capa_records WHERE organization_id=? ORDER BY updated_at DESC LIMIT 500",
                    ("evaluation-hospital",),
                ).fetchall()
            elif user["vendor"]:
                rows = store.db.execute("SELECT * FROM capa_records ORDER BY updated_at DESC LIMIT 500").fetchall()
            else:
                rows = store.db.execute(
                    "SELECT c.* FROM capa_records c JOIN memberships m ON m.organization_id=c.organization_id WHERE m.user_id=? ORDER BY c.updated_at DESC LIMIT 500",
                    (user["user_id"],),
                ).fetchall()
        today = date.today().isoformat()
        result = []
        for row in rows:
            item = dict(row)
            if not user["vendor"] and not user["evaluation"] and not has_permission(user, "customer.compliance.read", organization_id=item["organization_id"]):
                continue
            item["overdue"] = item["status"] not in {"closed", "cancelled"} and item["due_on"] < today
            result.append(item)
        return result

    def listed_findings(user: dict) -> list[dict]:
        with store.lock:
            if user["evaluation"]:
                rows = store.db.execute(
                    "SELECT * FROM qms_findings WHERE organization_id=? ORDER BY updated_at DESC LIMIT 500",
                    ("evaluation-hospital",),
                ).fetchall()
            elif user["vendor"]:
                rows = store.db.execute("SELECT * FROM qms_findings ORDER BY updated_at DESC LIMIT 500").fetchall()
            else:
                rows = store.db.execute(
                    "SELECT f.* FROM qms_findings f JOIN memberships m ON m.organization_id=f.organization_id WHERE m.user_id=? ORDER BY f.updated_at DESC LIMIT 500",
                    (user["user_id"],),
                ).fetchall()
        today = date.today().isoformat()
        result = []
        for row in rows:
            item = dict(row)
            if not user["vendor"] and not user["evaluation"] and not has_permission(user, "customer.compliance.read", organization_id=item["organization_id"]):
                continue
            item["overdue"] = item["status"] not in {"closed", "rejected"} and item["due_on"] < today
            result.append(item)
        return result

    @app.post("/v1/vendor/capa")
    def create_capa(body: CapaCreate, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.compliance.write")
        with store.lock:
            org_id = site_org(body.site_id, user)
            capa_id, at = secrets.token_hex(16), stamp()
            store.db.execute(
                "INSERT INTO capa_records VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    capa_id, org_id, body.site_id, body.title, body.description, body.severity, "open",
                    body.owner, str(body.due_on), body.source_type, body.source_id, None, None, None, None, at, at, None,
                ),
            )
            store.audit(user["user_id"], "created", "capa", capa_id)
            store.db.commit()
        return {"id": capa_id, "status": "open", "organization_id": org_id}

    @app.get("/v1/capa")
    def list_capa(user: dict = Depends(require_user)):
        if user["vendor"]:
            require_permission(user, "vendor.compliance.read")
        return {"records": listed_capa(user)}

    @app.patch("/v1/vendor/capa/{capa_id}")
    def update_capa(capa_id: str, body: CapaUpdate, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.compliance.write")
        if body.status not in CAPA_STATES:
            raise HTTPException(status_code=422, detail="Unknown CAPA status")
        with store.lock:
            row = store.db.execute("SELECT * FROM capa_records WHERE id=?", (capa_id,)).fetchone()
            if not row or (user["evaluation"] and row["organization_id"] != "evaluation-hospital"):
                raise HTTPException(status_code=404, detail="CAPA not found")
            if body.status == "closed" and not (body.evidence_ref or row["evidence_ref"]):
                raise HTTPException(status_code=422, detail="Evidence reference required before closure")
            if body.status == "closed" and not ((body.corrective_action or row["corrective_action"]) and (body.root_cause or row["root_cause"])):
                raise HTTPException(status_code=422, detail="Root cause and corrective action required before closure")
            closed_at = stamp() if body.status == "closed" else row["closed_at"]
            store.db.execute(
                """UPDATE capa_records SET status=?, root_cause=COALESCE(?,root_cause), corrective_action=COALESCE(?,corrective_action),
                   preventive_action=COALESCE(?,preventive_action), evidence_ref=COALESCE(?,evidence_ref), updated_at=?, closed_at=? WHERE id=?""",
                (body.status, body.root_cause, body.corrective_action, body.preventive_action, body.evidence_ref, stamp(), closed_at, capa_id),
            )
            store.audit(user["user_id"], f"capa_{body.status}:{body.reason}", "capa", capa_id)
            store.db.commit()
        return {"id": capa_id, "status": body.status}

    @app.post("/v1/vendor/qms-findings")
    def create_finding(body: FindingCreate, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.compliance.write")
        if body.finding_type not in FINDING_TYPES:
            raise HTTPException(status_code=422, detail="Unknown finding type")
        with store.lock:
            org_id = site_org(body.site_id, user)
            finding_id, at = secrets.token_hex(16), stamp()
            store.db.execute(
                "INSERT INTO qms_findings VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (finding_id, org_id, body.site_id, body.finding_type, body.description, body.severity, "open", body.owner, str(body.due_on), None, None, at, at),
            )
            store.audit(user["user_id"], "created", "qms_finding", finding_id)
            store.db.commit()
        return {"id": finding_id, "status": "open", "organization_id": org_id}

    @app.get("/v1/qms-findings")
    def list_findings(user: dict = Depends(require_user)):
        if user["vendor"]:
            require_permission(user, "vendor.compliance.read")
        return {"findings": listed_findings(user)}

    @app.patch("/v1/vendor/qms-findings/{finding_id}")
    def update_finding(finding_id: str, body: FindingUpdate, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.compliance.write")
        if body.status not in FINDING_STATES:
            raise HTTPException(status_code=422, detail="Unknown finding status")
        with store.lock:
            row = store.db.execute("SELECT * FROM qms_findings WHERE id=?", (finding_id,)).fetchone()
            if not row or (user["evaluation"] and row["organization_id"] != "evaluation-hospital"):
                raise HTTPException(status_code=404, detail="Finding not found")
            capa_id = body.capa_id
            if body.status == "linked_capa":
                if not capa_id:
                    raise HTTPException(status_code=422, detail="capa_id required to link finding")
                capa = store.db.execute("SELECT organization_id FROM capa_records WHERE id=?", (capa_id,)).fetchone()
                if not capa or capa["organization_id"] != row["organization_id"]:
                    raise HTTPException(status_code=404, detail="CAPA not found for organization")
            store.db.execute(
                "UPDATE qms_findings SET status=?, capa_id=COALESCE(?,capa_id), evidence_ref=COALESCE(?,evidence_ref), updated_at=? WHERE id=?",
                (body.status, capa_id, body.evidence_ref, stamp(), finding_id),
            )
            store.audit(user["user_id"], f"finding_{body.status}:{body.reason}", "qms_finding", finding_id)
            store.db.commit()
        return {"id": finding_id, "status": body.status, "capa_id": capa_id or row["capa_id"]}
