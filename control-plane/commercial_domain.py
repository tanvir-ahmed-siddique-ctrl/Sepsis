"""Contract-based commercial records in the account authority, never the clinical DB.

Amounts are integer minor currency units. No payment gateway or clinical licence
activation is implied by these records. Every query is scoped to the identity's
organization memberships, including the synthetic evaluation operator.
"""

from __future__ import annotations

import json
import base64
import binascii
import os
import secrets
import sqlite3
from datetime import date, datetime, timezone
from typing import Callable

from fastapi import Depends, FastAPI, HTTPException, Response
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import BaseModel, ConfigDict, Field

from permissions import CUSTOMER_TABLE_PERMISSION, has_permission, require_permission


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LeadCreate(Strict):
    name: str = Field(min_length=2, max_length=120)
    contact_role: str = Field(min_length=2, max_length=80)
    contact_channel: str = Field(pattern="^(email|phone|meeting|referral)$")
    next_action: str = Field(min_length=2, max_length=240)
    follow_up_date: date | None = None


class PublicInquiry(Strict):
    organization: str = Field(min_length=2, max_length=120)
    work_email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    contact_role: str = Field(min_length=2, max_length=80)
    interest: str = Field(pattern="^(site_assessment|integration|managed_edge|evaluation|consultation)$")
    consent: bool
    website: str = Field(default="", max_length=0)


class LeadUpdate(Strict):
    stage: str
    next_action: str = Field(min_length=2, max_length=240)
    follow_up_date: date | None = None
    reason: str = Field(min_length=3, max_length=240)


class LeadOrganizationLink(Strict):
    organization_id: str
    reason: str = Field(min_length=3, max_length=240)


class ContactCreate(Strict):
    organization_id: str
    channel: str = Field(pattern="^(call|email|meeting|site_visit|training|support|renewal)$")
    contact_role: str = Field(min_length=2, max_length=80)
    summary: str = Field(min_length=3, max_length=500)
    next_action: str | None = Field(default=None, max_length=240)
    customer_visible: bool = False


class AssessmentCreate(Strict):
    site_id: str
    lead_id: str | None = None
    maturity: str = Field(pattern="^M[0-4]$")
    source_inventory_ref: str | None = Field(default=None, max_length=120)
    findings: str = Field(min_length=3, max_length=500)
    decision: str = Field(pattern="^(pending|go|no_go)$")


class QuoteLine(Strict):
    category: str = Field(pattern="^(assessment|integration|installation|hardware|training|licence|managed_edge|support|validation|other)$")
    description: str = Field(min_length=2, max_length=160)
    quantity: int = Field(ge=1, le=100000)
    unit_minor: int = Field(ge=0, le=10**12)
    discount_minor: int = Field(default=0, ge=0, le=10**12)
    tax_basis_points: int = Field(default=0, ge=0, le=10000)


class QuoteCreate(Strict):
    site_id: str
    assessment_id: str | None = None
    currency: str = Field(default="BDT", pattern="^[A-Z]{3}$")
    valid_until: date
    assumptions: str = Field(min_length=3, max_length=1000)
    exclusions: str = Field(min_length=3, max_length=1000)
    lines: list[QuoteLine] = Field(min_length=1, max_length=100)


class QuoteRevision(Strict):
    valid_until: date
    assumptions: str = Field(min_length=3, max_length=1000)
    exclusions: str = Field(min_length=3, max_length=1000)
    lines: list[QuoteLine] = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=3, max_length=240)


class StatusDecision(Strict):
    status: str
    reason: str = Field(min_length=3, max_length=240)


class ContractCreate(Strict):
    site_id: str
    quote_id: str | None = None
    starts_on: date
    ends_on: date
    notice_days: int = Field(ge=0, le=3650)
    document_ref: str = Field(min_length=3, max_length=160)
    scope: str = Field(min_length=3, max_length=1000)


class LicenceCreate(Strict):
    contract_id: str
    modules: list[str] = Field(min_length=1, max_length=30)
    unit_limit: int = Field(ge=1, le=10000)
    bed_limit: int = Field(ge=1, le=100000)
    support_tier: str = Field(pattern="^(setup_only|standard|enhanced)$")
    effective_on: date
    expires_on: date


class LicenceStateUpdate(Strict):
    entitlement_status: str = Field(pattern="^(revoked|suspended|active)$")
    reason: str = Field(min_length=3, max_length=240)


class InvoiceCreate(Strict):
    contract_id: str
    quote_id: str | None = None
    invoice_number: str = Field(min_length=3, max_length=80)
    due_on: date
    currency: str = Field(default="BDT", pattern="^[A-Z]{3}$")
    lines: list[QuoteLine] = Field(min_length=1, max_length=100)


class PaymentCreate(Strict):
    invoice_id: str
    amount_minor: int = Field(gt=0, le=10**12)
    paid_on: date
    channel: str = Field(pattern="^(bank_transfer|cheque|other_approved)$")
    reference: str = Field(min_length=3, max_length=120)
    evidence_ref: str = Field(min_length=3, max_length=160)


class PaymentDecision(Strict):
    status: str = Field(pattern="^(verified|rejected|needs_clarification)$")
    reason: str = Field(min_length=3, max_length=240)


class RenewalCreate(Strict):
    contract_id: str
    request_type: str = Field(pattern="^(renew|expand|downgrade|cancel)$")
    note: str = Field(min_length=3, max_length=500)


class CreditCreate(Strict):
    invoice_id: str
    amount_minor: int = Field(gt=0, le=10**12)
    reason: str = Field(min_length=3, max_length=240)
    document_ref: str = Field(min_length=3, max_length=160)


LEAD_STAGES = {
    "received", "initial_contact", "discovery", "assessment_scheduled",
    "assessment_complete", "solution_scoped", "proposal_issued",
    "negotiation", "procurement_review", "contract_signed",
    "deployment_scheduled", "commissioning", "active", "renewal",
    "closed_lost", "cancelled",
}


def totals(lines: list[QuoteLine]) -> dict[str, int]:
    subtotal = tax = discount = 0
    for line in lines:
        gross = line.quantity * line.unit_minor
        if line.discount_minor > gross:
            raise HTTPException(status_code=422, detail="Line discount exceeds gross amount")
        taxable = gross - line.discount_minor
        subtotal += gross
        discount += line.discount_minor
        tax += (taxable * line.tax_basis_points + 5000) // 10000
    if subtotal > 10**15:
        raise HTTPException(status_code=422, detail="Quote total exceeds allowed range")
    return {"subtotal_minor": subtotal, "discount_minor": discount, "tax_minor": tax, "total_minor": subtotal - discount + tax}


def simple_pdf(lines: list[str]) -> bytes:
    """A single-page, text-only PDF for server-generated commercial records."""
    def safe(value: str) -> str:
        ascii_text = value.encode("ascii", "replace").decode("ascii")[:105]
        return ascii_text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    commands = ["BT /F1 10 Tf 48 790 Td 14 TL"]
    for index, line in enumerate(lines[:48]):
        commands.append(("" if index == 0 else "T* ") + f"({safe(line)}) Tj")
    commands.append("ET")
    stream = "\n".join(commands).encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    result = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(result))
        result.extend(f"{index} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = len(result)
    result.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        result.extend(f"{offset:010d} 00000 n \n".encode())
    result.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return bytes(result)


def install_commercial_routes(app: FastAPI, store, require_user: Callable, require_vendor: Callable) -> None:
    with store.lock:
        store.db.executescript("""
            CREATE TABLE IF NOT EXISTS leads (id TEXT PRIMARY KEY,name TEXT NOT NULL,stage TEXT NOT NULL,contact_role TEXT NOT NULL,contact_channel TEXT NOT NULL,next_action TEXT NOT NULL,follow_up_date TEXT,reason TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS public_inquiries (id TEXT PRIMARY KEY,organization TEXT NOT NULL,email TEXT NOT NULL,contact_role TEXT NOT NULL,interest TEXT NOT NULL,consent_at TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS contacts (id TEXT PRIMARY KEY,organization_id TEXT NOT NULL REFERENCES organizations(id),channel TEXT NOT NULL,contact_role TEXT NOT NULL,summary TEXT NOT NULL,next_action TEXT,customer_visible INTEGER NOT NULL,created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS assessments (id TEXT PRIMARY KEY,organization_id TEXT NOT NULL REFERENCES organizations(id),site_id TEXT NOT NULL REFERENCES sites(id),maturity TEXT NOT NULL,source_inventory_ref TEXT,findings TEXT NOT NULL,decision TEXT NOT NULL,created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS quotes (id TEXT PRIMARY KEY,organization_id TEXT NOT NULL REFERENCES organizations(id),site_id TEXT NOT NULL REFERENCES sites(id),currency TEXT NOT NULL,status TEXT NOT NULL,current_version INTEGER NOT NULL,created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS quote_versions (quote_id TEXT NOT NULL REFERENCES quotes(id),version INTEGER NOT NULL,valid_until TEXT NOT NULL,assumptions TEXT NOT NULL,exclusions TEXT NOT NULL,lines_json TEXT NOT NULL,subtotal_minor INTEGER NOT NULL,discount_minor INTEGER NOT NULL,tax_minor INTEGER NOT NULL,total_minor INTEGER NOT NULL,reason TEXT NOT NULL,created_at TEXT NOT NULL,issued_at TEXT,PRIMARY KEY(quote_id,version));
            CREATE TABLE IF NOT EXISTS contracts (id TEXT PRIMARY KEY,organization_id TEXT NOT NULL REFERENCES organizations(id),site_id TEXT NOT NULL REFERENCES sites(id),quote_id TEXT REFERENCES quotes(id),starts_on TEXT NOT NULL,ends_on TEXT NOT NULL,notice_days INTEGER NOT NULL,document_ref TEXT NOT NULL,scope TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS licences (id TEXT PRIMARY KEY,organization_id TEXT NOT NULL REFERENCES organizations(id),site_id TEXT NOT NULL REFERENCES sites(id),contract_id TEXT NOT NULL REFERENCES contracts(id),modules_json TEXT NOT NULL,unit_limit INTEGER NOT NULL,bed_limit INTEGER NOT NULL,support_tier TEXT NOT NULL,effective_on TEXT NOT NULL,expires_on TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS licence_packages (licence_id TEXT PRIMARY KEY REFERENCES licences(id),package_json TEXT NOT NULL,key_id TEXT NOT NULL,issued_at TEXT NOT NULL,issued_by TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS invoices (id TEXT PRIMARY KEY,organization_id TEXT NOT NULL REFERENCES organizations(id),site_id TEXT NOT NULL REFERENCES sites(id),contract_id TEXT NOT NULL REFERENCES contracts(id),quote_id TEXT REFERENCES quotes(id),invoice_number TEXT NOT NULL UNIQUE,due_on TEXT NOT NULL,currency TEXT NOT NULL,status TEXT NOT NULL,lines_json TEXT NOT NULL,subtotal_minor INTEGER NOT NULL,discount_minor INTEGER NOT NULL,tax_minor INTEGER NOT NULL,total_minor INTEGER NOT NULL,created_at TEXT NOT NULL,issued_at TEXT);
            CREATE TABLE IF NOT EXISTS payments (id TEXT PRIMARY KEY,organization_id TEXT NOT NULL REFERENCES organizations(id),invoice_id TEXT NOT NULL REFERENCES invoices(id),amount_minor INTEGER NOT NULL,paid_on TEXT NOT NULL,channel TEXT NOT NULL,reference TEXT NOT NULL,evidence_ref TEXT NOT NULL,status TEXT NOT NULL,reviewed_by TEXT,review_reason TEXT,created_at TEXT NOT NULL,reviewed_at TEXT);
            CREATE TABLE IF NOT EXISTS credit_notes (id TEXT PRIMARY KEY,organization_id TEXT NOT NULL REFERENCES organizations(id),invoice_id TEXT NOT NULL REFERENCES invoices(id),amount_minor INTEGER NOT NULL,reason TEXT NOT NULL,document_ref TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL,issued_at TEXT);
            CREATE TABLE IF NOT EXISTS renewals (id TEXT PRIMARY KEY,organization_id TEXT NOT NULL REFERENCES organizations(id),contract_id TEXT NOT NULL REFERENCES contracts(id),request_type TEXT NOT NULL,note TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL);
        """)
        version_columns = {row[1] for row in store.db.execute("PRAGMA table_info(quote_versions)")}
        if "issued_at" not in version_columns:
            store.db.execute("ALTER TABLE quote_versions ADD COLUMN issued_at TEXT")
        for table, column, definition in (("leads", "organization_id", "TEXT"), ("assessments", "lead_id", "TEXT"), ("quotes", "assessment_id", "TEXT")):
            if column not in {row[1] for row in store.db.execute(f"PRAGMA table_info({table})")}:
                store.db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        if "submitted_by" not in {row[1] for row in store.db.execute("PRAGMA table_info(payments)")}:
            store.db.execute("ALTER TABLE payments ADD COLUMN submitted_by TEXT")
        licence_columns = {row[1] for row in store.db.execute("PRAGMA table_info(licences)")}
        for name, definition in (
            ("entitlement_status", "TEXT NOT NULL DEFAULT 'active'"),
            ("state_changed_at", "TEXT"),
            ("state_reason", "TEXT"),
        ):
            if name not in licence_columns:
                store.db.execute(f"ALTER TABLE licences ADD COLUMN {name} {definition}")
        store.db.execute("UPDATE licences SET entitlement_status='active' WHERE entitlement_status IS NULL OR entitlement_status=''")
        store.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS entitlement_invalidations (
              id TEXT PRIMARY KEY,
              licence_id TEXT NOT NULL REFERENCES licences(id),
              organization_id TEXT NOT NULL REFERENCES organizations(id),
              site_id TEXT NOT NULL REFERENCES sites(id),
              previous_status TEXT NOT NULL,
              new_status TEXT NOT NULL,
              reason TEXT NOT NULL,
              package_json TEXT,
              created_at TEXT NOT NULL,
              created_by TEXT NOT NULL
            );
            """
        )
        store.db.commit()

    def role(user: dict, *allowed: str, permission: str | None = None) -> None:
        """Transitional helper: prefer explicit permission= when available."""
        if permission:
            if user["vendor"] or user["evaluation"]:
                require_permission(user, permission)
            else:
                # Customer callers must hold the permission in at least one org;
                # object-level checks still use organization_id below.
                if not any(has_permission(user, permission, organization_id=org) for org in user.get("organization_ids", [])):
                    raise HTTPException(status_code=403, detail="Account role does not permit this action")
                user["_required_permission"] = permission
            return
        if user["evaluation"]:
            return
        if not user["vendor"]:
            if not any(value in allowed for value in user["organization_roles"].values()):
                raise HTTPException(status_code=403, detail="Account role does not permit this action")
            user["_required_customer_roles"] = allowed
            return
        if user["role"] not in allowed and user["role"] != "root_admin":
            raise HTTPException(status_code=403, detail="Account role does not permit this action")

    def check_org(user: dict, org_id: str) -> None:
        if user["evaluation"] and org_id != "evaluation-hospital":
            raise HTTPException(status_code=404, detail="Record not found")
        if not user["vendor"] and org_id not in user["organization_ids"]:
            raise HTTPException(status_code=404, detail="Record not found")
        if not user["vendor"] and user.get("_required_permission") and not has_permission(user, user["_required_permission"], organization_id=org_id):
            raise HTTPException(status_code=403, detail="Organization role does not permit this action")
        if not user["vendor"] and user.get("_required_customer_roles") and user["organization_roles"].get(org_id) not in user["_required_customer_roles"]:
            raise HTTPException(status_code=403, detail="Organization role does not permit this action")

    def site_org(site_id: str, user: dict) -> str:
        row = store.db.execute("SELECT organization_id FROM sites WHERE id=?", (site_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Site not found")
        check_org(user, row["organization_id"])
        return row["organization_id"]

    def can_read(user: dict, table: str, org_id: str) -> bool:
        if user["vendor"] or user["evaluation"]:
            return True
        permission = CUSTOMER_TABLE_PERMISSION.get(table)
        return bool(permission) and has_permission(user, permission, organization_id=org_id)

    def listed(table: str, user: dict, extra: str = "") -> list[dict]:
        with store.lock:
            if user["evaluation"]:
                rows = store.db.execute(f"SELECT * FROM {table} WHERE organization_id=? {extra}", ("evaluation-hospital",)).fetchall()
            elif user["vendor"]:
                rows = store.db.execute(f"SELECT * FROM {table} {extra}").fetchall()
            else:
                rows = store.db.execute(f"SELECT * FROM {table} WHERE organization_id IN (SELECT organization_id FROM memberships WHERE user_id=?) {extra}", (user["user_id"],)).fetchall()
        return [dict(row) for row in rows if can_read(user, table, row["organization_id"])]

    def record(table: str, record_id: str, user: dict) -> dict:
        with store.lock:
            row = store.db.execute(f"SELECT * FROM {table} WHERE id=?", (record_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Record not found")
        result = dict(row)
        check_org(user, result["organization_id"])
        if not can_read(user, table, result["organization_id"]):
            raise HTTPException(status_code=404, detail="Record not found")
        return result

    @app.post("/v1/public/inquiries")
    def public_inquiry(body: PublicInquiry):
        if not body.consent:
            raise HTTPException(status_code=422, detail="Contact consent is required")
        if os.environ.get("EVALUATION_RUNTIME") == "true":
            raise HTTPException(status_code=403, detail="Public inquiries are disabled in synthetic evaluation")
        email = body.work_email.strip().lower()
        with store.lock:
            recent = store.db.execute("SELECT 1 FROM public_inquiries WHERE email=? AND datetime(created_at)>=datetime('now','-1 hour')", (email,)).fetchone()
            if recent:
                return {"recorded": True}
            inquiry_id, at = secrets.token_hex(16), stamp()
            store.db.execute("INSERT INTO public_inquiries VALUES(?,?,?,?,?,?,?,?)", (inquiry_id, body.organization, email, body.contact_role, body.interest, at, "received", at))
            store.audit("public", "received", "inquiry", inquiry_id)
            store.db.commit()
        return {"recorded": True}

    @app.get("/v1/vendor/inquiries")
    def inquiries(user: dict = Depends(require_vendor)):
        role(user, "platform_admin")
        if user["evaluation"]:
            return {"inquiries": []}
        with store.lock:
            rows = store.db.execute("SELECT * FROM public_inquiries ORDER BY created_at DESC LIMIT 500").fetchall()
        return {"inquiries": [dict(row) for row in rows]}

    @app.post("/v1/vendor/leads")
    def create_lead(body: LeadCreate, user: dict = Depends(require_vendor)):
        role(user, "platform_admin")
        if user["evaluation"]:
            raise HTTPException(status_code=403, detail="Lead capture disabled in synthetic evaluation")
        with store.lock:
            lead_id, at = secrets.token_hex(16), stamp()
            store.db.execute("INSERT INTO leads(id,name,stage,contact_role,contact_channel,next_action,follow_up_date,reason,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (lead_id, body.name, "received", body.contact_role, body.contact_channel, body.next_action, str(body.follow_up_date) if body.follow_up_date else None, None, at, at))
            store.audit(user["user_id"], "created", "lead", lead_id)
            store.db.commit()
        return {"id": lead_id, "stage": "received"}

    @app.get("/v1/vendor/leads")
    def leads(user: dict = Depends(require_vendor)):
        role(user, "platform_admin")
        if user["evaluation"]:
            return {"leads": []}
        with store.lock:
            rows = store.db.execute("SELECT * FROM leads ORDER BY updated_at DESC LIMIT 500").fetchall()
        return {"leads": [dict(row) for row in rows]}

    @app.patch("/v1/vendor/leads/{lead_id}")
    def advance_lead(lead_id: str, body: LeadUpdate, user: dict = Depends(require_vendor)):
        role(user, "platform_admin")
        if user["evaluation"]:
            raise HTTPException(status_code=403, detail="Lead updates disabled in synthetic evaluation")
        if body.stage not in LEAD_STAGES:
            raise HTTPException(status_code=422, detail="Unknown pipeline stage")
        with store.lock:
            if not store.db.execute("SELECT 1 FROM leads WHERE id=?", (lead_id,)).fetchone():
                raise HTTPException(status_code=404, detail="Lead not found")
            store.db.execute("UPDATE leads SET stage=?,next_action=?,follow_up_date=?,reason=?,updated_at=? WHERE id=?", (body.stage, body.next_action, str(body.follow_up_date) if body.follow_up_date else None, body.reason, stamp(), lead_id))
            store.audit(user["user_id"], "stage_changed", "lead", lead_id)
            store.db.commit()
        return {"id": lead_id, "stage": body.stage}

    @app.post("/v1/vendor/leads/{lead_id}/organization")
    def link_lead(lead_id: str, body: LeadOrganizationLink, user: dict = Depends(require_vendor)):
        role(user, "platform_admin")
        if user["evaluation"]:
            raise HTTPException(status_code=403, detail="Lead linking disabled in evaluation")
        with store.lock:
            lead = store.db.execute("SELECT organization_id FROM leads WHERE id=?", (lead_id,)).fetchone()
            if not lead:
                raise HTTPException(status_code=404, detail="Lead not found")
            if lead["organization_id"] and lead["organization_id"] != body.organization_id:
                raise HTTPException(status_code=409, detail="Lead is already linked to an organization")
            if not store.db.execute("SELECT 1 FROM organizations WHERE id=?", (body.organization_id,)).fetchone():
                raise HTTPException(status_code=404, detail="Organization not found")
            store.db.execute("UPDATE leads SET organization_id=?,updated_at=? WHERE id=?", (body.organization_id, stamp(), lead_id))
            store.audit(user["user_id"], f"linked_organization:{body.reason}", "lead", lead_id)
            store.db.commit()
        return {"id": lead_id, "organization_id": body.organization_id}

    @app.post("/v1/vendor/contacts")
    def add_contact(body: ContactCreate, user: dict = Depends(require_vendor)):
        role(user, "platform_admin", "support_engineer")
        with store.lock:
            check_org(user, body.organization_id)
            if not store.db.execute("SELECT 1 FROM organizations WHERE id=?", (body.organization_id,)).fetchone():
                raise HTTPException(status_code=404, detail="Organization not found")
            contact_id = secrets.token_hex(16)
            store.db.execute("INSERT INTO contacts VALUES(?,?,?,?,?,?,?,?)", (contact_id, body.organization_id, body.channel, body.contact_role, body.summary, body.next_action, int(body.customer_visible), stamp()))
            store.audit(user["user_id"], "created", "contact", contact_id)
            store.db.commit()
        return {"id": contact_id}

    @app.get("/v1/contacts")
    def contacts(user: dict = Depends(require_user)):
        if user["vendor"]:
            role(user, "platform_admin", "support_engineer", "finance_legal")
        rows = listed("contacts", user, "ORDER BY created_at DESC LIMIT 500")
        return {"contacts": rows if user["vendor"] else [row for row in rows if row["customer_visible"]]}

    @app.post("/v1/vendor/assessments")
    def add_assessment(body: AssessmentCreate, user: dict = Depends(require_vendor)):
        role(user, "platform_admin", "deployment_engineer")
        with store.lock:
            org_id = site_org(body.site_id, user)
            if body.lead_id:
                lead = store.db.execute("SELECT organization_id FROM leads WHERE id=?", (body.lead_id,)).fetchone()
                if not lead or lead["organization_id"] != org_id:
                    raise HTTPException(status_code=409, detail="Assessment lead must belong to the site organization")
            assessment_id = secrets.token_hex(16)
            store.db.execute("INSERT INTO assessments(id,organization_id,site_id,maturity,source_inventory_ref,findings,decision,created_at,lead_id) VALUES(?,?,?,?,?,?,?,?,?)", (assessment_id, org_id, body.site_id, body.maturity, body.source_inventory_ref, body.findings, body.decision, stamp(), body.lead_id))
            store.audit(user["user_id"], "created", "assessment", assessment_id)
            store.db.commit()
        return {"id": assessment_id}

    @app.get("/v1/assessments")
    def assessments(user: dict = Depends(require_user)):
        if user["vendor"]:
            role(user, "platform_admin", "deployment_engineer")
        return {"assessments": listed("assessments", user, "ORDER BY created_at DESC LIMIT 500")}

    @app.post("/v1/vendor/quotes")
    def create_quote(body: QuoteCreate, user: dict = Depends(require_vendor)):
        role(user, "finance_legal")
        amounts = totals(body.lines)
        with store.lock:
            org_id = site_org(body.site_id, user)
            if body.assessment_id:
                assessment = store.db.execute("SELECT site_id,decision FROM assessments WHERE id=? AND organization_id=?", (body.assessment_id, org_id)).fetchone()
                if not assessment or assessment["site_id"] != body.site_id or assessment["decision"] != "go":
                    raise HTTPException(status_code=409, detail="Quotation needs a go assessment for the same site")
            quote_id, at = secrets.token_hex(16), stamp()
            store.db.execute("INSERT INTO quotes(id,organization_id,site_id,currency,status,current_version,created_at,assessment_id) VALUES(?,?,?,?,?,?,?,?)", (quote_id, org_id, body.site_id, body.currency, "draft", 1, at, body.assessment_id))
            store.db.execute("INSERT INTO quote_versions(quote_id,version,valid_until,assumptions,exclusions,lines_json,subtotal_minor,discount_minor,tax_minor,total_minor,reason,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (quote_id, 1, str(body.valid_until), body.assumptions, body.exclusions, json.dumps([line.model_dump() for line in body.lines]), amounts["subtotal_minor"], amounts["discount_minor"], amounts["tax_minor"], amounts["total_minor"], "initial", at))
            store.audit(user["user_id"], "created", "quote", quote_id)
            store.db.commit()
        return {"id": quote_id, "version": 1, "status": "draft", **amounts}

    @app.post("/v1/vendor/quotes/{quote_id}/revisions")
    def revise_quote(quote_id: str, body: QuoteRevision, user: dict = Depends(require_vendor)):
        role(user, "finance_legal")
        amounts = totals(body.lines)
        with store.lock:
            quote = record("quotes", quote_id, user)
            if quote["status"] in {"accepted", "rejected", "expired"}:
                raise HTTPException(status_code=409, detail="Final quote cannot be revised")
            version = quote["current_version"] + 1
            store.db.execute("INSERT INTO quote_versions(quote_id,version,valid_until,assumptions,exclusions,lines_json,subtotal_minor,discount_minor,tax_minor,total_minor,reason,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (quote_id, version, str(body.valid_until), body.assumptions, body.exclusions, json.dumps([line.model_dump() for line in body.lines]), amounts["subtotal_minor"], amounts["discount_minor"], amounts["tax_minor"], amounts["total_minor"], body.reason, stamp()))
            store.db.execute("UPDATE quotes SET current_version=?,status='draft' WHERE id=?", (version, quote_id))
            store.audit(user["user_id"], "revised", "quote", quote_id)
            store.db.commit()
        return {"id": quote_id, "version": version, **amounts}

    @app.get("/v1/quotes")
    def quotes(user: dict = Depends(require_user)):
        if user["vendor"]:
            role(user, "finance_legal", "platform_admin")
        rows = listed("quotes", user, "ORDER BY created_at DESC LIMIT 500")
        if not user["vendor"]:
            rows = [row for row in rows if row["status"] in {"issued", "acknowledged", "accepted", "rejected", "expired"}]
        with store.lock:
            for row in rows:
                version = store.db.execute("SELECT * FROM quote_versions WHERE quote_id=? AND version=?", (row["id"], row["current_version"])).fetchone()
                row["current"] = dict(version)
                row["current"]["lines"] = json.loads(row["current"].pop("lines_json"))
        return {"quotes": rows}

    @app.get("/v1/quotes/{quote_id}/versions")
    def quote_history(quote_id: str, user: dict = Depends(require_user)):
        if user["vendor"]:
            role(user, "finance_legal", "platform_admin")
        quote = record("quotes", quote_id, user)
        if not user["vendor"] and quote["status"] not in {"issued", "acknowledged", "accepted", "rejected", "expired"}:
            raise HTTPException(status_code=404, detail="Record not found")
        with store.lock:
            rows = store.db.execute("SELECT * FROM quote_versions WHERE quote_id=? ORDER BY version", (quote_id,)).fetchall() if user["vendor"] else store.db.execute("SELECT * FROM quote_versions WHERE quote_id=? AND issued_at IS NOT NULL ORDER BY version", (quote_id,)).fetchall()
        return {"versions": [{**dict(row), "lines": json.loads(row["lines_json"])} for row in rows]}

    @app.get("/v1/quotes/{quote_id}/versions/{version}/pdf")
    def quote_pdf(quote_id: str, version: int, user: dict = Depends(require_user)):
        if user["vendor"]:
            role(user, "finance_legal", "platform_admin")
        quote = record("quotes", quote_id, user)
        with store.lock:
            row = store.db.execute("SELECT * FROM quote_versions WHERE quote_id=? AND version=?", (quote_id, version)).fetchone()
        if not row or (not user["vendor"] and row["issued_at"] is None):
            raise HTTPException(status_code=404, detail="Quote version not found")
        lines = json.loads(row["lines_json"])
        document = simple_pdf([
            "Auralis | Site-specific quotation",
            f"Quote {quote_id} | Version {version} | {quote['currency']}",
            f"Organization {quote['organization_id']} | Site {quote['site_id']}",
            f"Valid until {row['valid_until']}",
            "Items (amounts in minor currency units):",
            *[f"{item['description']}: {item['quantity']} x {item['unit_minor']} | discount {item['discount_minor']} | tax {item['tax_basis_points']} bps" for item in lines[:32]],
            f"Subtotal {row['subtotal_minor']} | discount {row['discount_minor']} | tax {row['tax_minor']}",
            f"Total {row['total_minor']}",
            f"Assumptions: {row['assumptions']}",
            f"Exclusions: {row['exclusions']}",
        ])
        return Response(document, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=auralis-quote-{quote_id[:12]}-v{version}.pdf", "Cache-Control": "no-store"})

    @app.post("/v1/vendor/contracts")
    def create_contract(body: ContractCreate, user: dict = Depends(require_vendor)):
        role(user, "finance_legal")
        if body.ends_on <= body.starts_on:
            raise HTTPException(status_code=422, detail="Contract end must follow start")
        with store.lock:
            org_id = site_org(body.site_id, user)
            if body.quote_id:
                quote = record("quotes", body.quote_id, user)
                if quote["site_id"] != body.site_id or quote["status"] != "accepted":
                    raise HTTPException(status_code=409, detail="Contract requires an accepted quote for the same site")
            contract_id = secrets.token_hex(16)
            store.db.execute("INSERT INTO contracts VALUES(?,?,?,?,?,?,?,?,?,?,?)", (contract_id, org_id, body.site_id, body.quote_id, str(body.starts_on), str(body.ends_on), body.notice_days, body.document_ref, body.scope, "draft", stamp()))
            store.audit(user["user_id"], "created", "contract", contract_id)
            store.db.commit()
        return {"id": contract_id, "status": "draft"}

    @app.get("/v1/contracts")
    def contracts(user: dict = Depends(require_user)):
        if user["vendor"]:
            role(user, "finance_legal", "platform_admin")
        rows = listed("contracts", user, "ORDER BY created_at DESC LIMIT 500")
        return {"contracts": rows if user["vendor"] else [row for row in rows if row["status"] in {"signed", "expired", "terminated"}]}

    @app.post("/v1/vendor/licences")
    def create_licence(body: LicenceCreate, user: dict = Depends(require_vendor)):
        role(user, "platform_admin")
        if body.expires_on <= body.effective_on:
            raise HTTPException(status_code=422, detail="Expiry must follow effective date")
        with store.lock:
            contract = record("contracts", body.contract_id, user)
            if contract["status"] != "signed":
                raise HTTPException(status_code=409, detail="Signed contract required")
            licence_id = secrets.token_hex(16)
            store.db.execute(
                "INSERT INTO licences(id,organization_id,site_id,contract_id,modules_json,unit_limit,bed_limit,support_tier,effective_on,expires_on,status,created_at,entitlement_status,state_changed_at,state_reason) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (licence_id, contract["organization_id"], contract["site_id"], body.contract_id, json.dumps(body.modules), body.unit_limit, body.bed_limit, body.support_tier, str(body.effective_on), str(body.expires_on), "pending_governance", stamp(), "active", None, None),
            )
            store.audit(user["user_id"], "recorded", "licence", licence_id)
            store.db.commit()
        return {"id": licence_id, "status": "pending_governance", "entitlement_status": "active"}

    @app.get("/v1/licences")
    def licences(user: dict = Depends(require_user)):
        if user["vendor"]:
            role(user, "platform_admin", "finance_legal")
        rows = listed("licences", user, "ORDER BY created_at DESC LIMIT 500")
        for row in rows:
            row["modules"] = json.loads(row.pop("modules_json"))
            row["entitlement_status"] = row.get("entitlement_status") or "active"
        return {"licences": rows}

    def _licence_signer():
        key_id = os.environ.get("ACCOUNT_LICENCE_KEY_ID", "")
        encoded = os.environ.get("ACCOUNT_LICENCE_PRIVATE_KEY", "")
        if not key_id or not encoded:
            raise HTTPException(status_code=503, detail="Licence signer not configured")
        try:
            signer = Ed25519PrivateKey.from_private_bytes(base64.b64decode(encoded, validate=True))
        except (ValueError, binascii.Error) as error:
            raise HTTPException(status_code=503, detail="Licence signer configuration invalid") from error
        return key_id, signer

    def _sign_claims(claims: dict, key_id: str, signer: Ed25519PrivateKey) -> dict:
        payload = json.dumps(claims, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        return {"claims": claims, "key_id": key_id, "signature": base64.b64encode(signer.sign(payload)).decode("ascii")}

    @app.post("/v1/vendor/licences/{licence_id}/issue")
    def issue_licence(licence_id: str, user: dict = Depends(require_vendor)):
        role(user, "platform_admin")
        if user["evaluation"]:
            raise HTTPException(status_code=403, detail="Real licence issuance disabled in evaluation")
        key_id, signer = _licence_signer()
        with store.lock:
            licence = record("licences", licence_id, user)
            contract = record("contracts", licence["contract_id"], user)
            if contract["status"] != "signed" or licence["status"] != "pending_governance":
                raise HTTPException(status_code=409, detail="Signed contract and unissued licence required")
            if (licence.get("entitlement_status") or "active") != "active":
                raise HTTPException(status_code=409, detail="Revoked or suspended licences cannot be issued")
            claims = {
                "licence_id": licence_id,
                "organization_id": licence["organization_id"],
                "site_id": licence["site_id"],
                "contract_id": licence["contract_id"],
                "modules": json.loads(licence["modules_json"]),
                "unit_limit": licence["unit_limit"],
                "bed_limit": licence["bed_limit"],
                "effective_on": licence["effective_on"],
                "expires_on": licence["expires_on"],
                "issued_at": stamp(),
                "entitlement_status": "active",
            }
            package = _sign_claims(claims, key_id, signer)
            store.db.execute("INSERT INTO licence_packages VALUES(?,?,?,?,?)", (licence_id, json.dumps(package), key_id, stamp(), user["user_id"]))
            store.db.execute("UPDATE licences SET status='issued_for_site_review', entitlement_status='active' WHERE id=?", (licence_id,))
            store.audit(user["user_id"], "issued_offline_package", "licence", licence_id)
            store.db.commit()
        return {"id": licence_id, "status": "issued_for_site_review", "entitlement_status": "active", "clinical_approval_separate": True}

    @app.patch("/v1/vendor/licences/{licence_id}/entitlement")
    def update_licence_entitlement(licence_id: str, body: LicenceStateUpdate, user: dict = Depends(require_vendor)):
        role(user, "platform_admin")
        if user["evaluation"]:
            raise HTTPException(status_code=403, detail="Licence entitlement changes disabled in evaluation")
        key_id, signer = _licence_signer()
        with store.lock:
            licence = record("licences", licence_id, user)
            previous = licence.get("entitlement_status") or "active"
            if body.entitlement_status == previous:
                raise HTTPException(status_code=409, detail="Entitlement already in requested state")
            if body.entitlement_status == "active" and previous == "revoked":
                raise HTTPException(status_code=409, detail="Revoked licences cannot be reactivated; create a new licence")
            if licence["status"] == "pending_governance" and body.entitlement_status != "revoked":
                raise HTTPException(status_code=409, detail="Issue the licence before suspending or reactivating")
            at = stamp()
            status_map = {"revoked": "revoked", "suspended": "suspended", "active": "issued_for_site_review"}
            claims = {
                "licence_id": licence_id,
                "organization_id": licence["organization_id"],
                "site_id": licence["site_id"],
                "contract_id": licence["contract_id"],
                "modules": json.loads(licence["modules_json"]),
                "unit_limit": licence["unit_limit"],
                "bed_limit": licence["bed_limit"],
                "effective_on": licence["effective_on"],
                "expires_on": licence["expires_on"],
                "issued_at": at,
                "entitlement_status": body.entitlement_status,
            }
            package = _sign_claims(claims, key_id, signer)
            invalidation_id = secrets.token_hex(16)
            store.db.execute(
                "INSERT INTO entitlement_invalidations VALUES(?,?,?,?,?,?,?,?,?,?)",
                (invalidation_id, licence_id, licence["organization_id"], licence["site_id"], previous, body.entitlement_status, body.reason, json.dumps(package), at, user["user_id"]),
            )
            existing = store.db.execute("SELECT 1 FROM licence_packages WHERE licence_id=?", (licence_id,)).fetchone()
            if existing:
                store.db.execute("UPDATE licence_packages SET package_json=?, key_id=?, issued_at=?, issued_by=? WHERE licence_id=?", (json.dumps(package), key_id, at, user["user_id"], licence_id))
            else:
                store.db.execute("INSERT INTO licence_packages VALUES(?,?,?,?,?)", (licence_id, json.dumps(package), key_id, at, user["user_id"]))
            store.db.execute(
                "UPDATE licences SET status=?, entitlement_status=?, state_changed_at=?, state_reason=? WHERE id=?",
                (status_map[body.entitlement_status], body.entitlement_status, at, body.reason, licence_id),
            )
            store.audit(user["user_id"], f"entitlement_{body.entitlement_status}:{body.reason}", "licence", licence_id)
            store.db.commit()
        return {
            "id": licence_id,
            "entitlement_status": body.entitlement_status,
            "status": status_map[body.entitlement_status],
            "invalidation_id": invalidation_id,
            "package": package,
            "clinical_approval_separate": True,
            "note": "Hospital must import the returned package for local entitlement invalidation; running bedside sessions are never interrupted by this API.",
        }

    @app.get("/v1/licences/{licence_id}/package")
    def licence_package(licence_id: str, user: dict = Depends(require_user)):
        if user["vendor"]:
            role(user, "platform_admin", "finance_legal")
        licence = record("licences", licence_id, user)
        entitlement = licence.get("entitlement_status") or "active"
        with store.lock:
            row = store.db.execute("SELECT package_json FROM licence_packages WHERE licence_id=?", (licence_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Licence package not issued")
            if entitlement in {"revoked", "suspended"} and not user["vendor"]:
                raise HTTPException(status_code=409, detail=f"Licence entitlement is {entitlement}; request vendor invalidation package")
            store.audit(user["user_id"], "downloaded_offline_package", "licence", licence_id)
            store.db.commit()
        return {
            "package": json.loads(row["package_json"]),
            "site_id": licence["site_id"],
            "entitlement_status": entitlement,
            "clinical_approval_separate": True,
        }

    @app.get("/v1/licences/{licence_id}/invalidations")
    def licence_invalidations(licence_id: str, user: dict = Depends(require_user)):
        if user["vendor"]:
            role(user, "platform_admin", "finance_legal")
        licence = record("licences", licence_id, user)
        with store.lock:
            rows = store.db.execute(
                "SELECT id,licence_id,previous_status,new_status,reason,created_at,created_by FROM entitlement_invalidations WHERE licence_id=? ORDER BY created_at DESC",
                (licence_id,),
            ).fetchall()
        return {"licence_id": licence_id, "site_id": licence["site_id"], "invalidations": [dict(row) for row in rows]}
    @app.post("/v1/vendor/invoices")
    def create_invoice(body: InvoiceCreate, user: dict = Depends(require_vendor)):
        role(user, "finance_legal")
        amounts = totals(body.lines)
        with store.lock:
            contract = record("contracts", body.contract_id, user)
            if contract["status"] != "signed":
                raise HTTPException(status_code=409, detail="Signed contract required")
            if body.quote_id:
                quote = record("quotes", body.quote_id, user)
                if quote["site_id"] != contract["site_id"] or quote["currency"] != body.currency or quote["status"] != "accepted" or (contract["quote_id"] and contract["quote_id"] != body.quote_id):
                    raise HTTPException(status_code=409, detail="Invoice quote must match the signed contract, site and currency")
            invoice_id = secrets.token_hex(16)
            try:
                store.db.execute("INSERT INTO invoices VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (invoice_id, contract["organization_id"], contract["site_id"], body.contract_id, body.quote_id, body.invoice_number, str(body.due_on), body.currency, "draft", json.dumps([line.model_dump() for line in body.lines]), amounts["subtotal_minor"], amounts["discount_minor"], amounts["tax_minor"], amounts["total_minor"], stamp(), None))
                store.audit(user["user_id"], "created", "invoice", invoice_id)
                store.db.commit()
            except sqlite3.IntegrityError:
                store.db.rollback()
                raise HTTPException(status_code=409, detail="Invoice number already exists") from None
        return {"id": invoice_id, "status": "draft", **amounts}

    @app.get("/v1/invoices")
    def invoices(user: dict = Depends(require_user)):
        if user["vendor"]:
            role(user, "finance_legal")
        rows = listed("invoices", user, "ORDER BY created_at DESC LIMIT 500")
        if not user["vendor"]:
            rows = [row for row in rows if row["status"] not in {"draft", "void"}]
        with store.lock:
            for row in rows:
                verified = store.db.execute("SELECT COALESCE(SUM(amount_minor),0) FROM payments WHERE invoice_id=? AND status='verified'", (row["id"],)).fetchone()[0]
                credited = store.db.execute("SELECT COALESCE(SUM(amount_minor),0) FROM credit_notes WHERE invoice_id=? AND status='issued'", (row["id"],)).fetchone()[0]
                row["verified_minor"] = verified
                row["credited_minor"] = credited
                row["balance_minor"] = row["total_minor"] - verified - credited
                row["effective_status"] = "overdue" if row["status"] in {"issued", "partially_paid"} and row["due_on"] < date.today().isoformat() and row["balance_minor"] > 0 else row["status"]
                row["lines"] = json.loads(row.pop("lines_json"))
        return {"invoices": rows}

    @app.get("/v1/invoices/{invoice_id}/pdf")
    def invoice_pdf(invoice_id: str, user: dict = Depends(require_user)):
        with store.lock:
            invoice = record("invoices", invoice_id, user)
            if invoice["status"] in {"draft", "void"}:
                raise HTTPException(status_code=404, detail="Issued invoice not found")
            verified = store.db.execute("SELECT COALESCE(SUM(amount_minor),0) FROM payments WHERE invoice_id=? AND status='verified'", (invoice_id,)).fetchone()[0]
            credited = store.db.execute("SELECT COALESCE(SUM(amount_minor),0) FROM credit_notes WHERE invoice_id=? AND status='issued'", (invoice_id,)).fetchone()[0]
            store.audit(user["user_id"], "downloaded", "invoice", invoice_id)
            store.db.commit()
        lines = [f"Auralis invoice {invoice['invoice_number']}", f"Site: {invoice['site_id']}", f"Status: {invoice['status']}", f"Due: {invoice['due_on']}", f"Currency: {invoice['currency']}", "", "Items:"]
        for item in json.loads(invoice["lines_json"]):
            lines.append(f"{item['description']}  qty {item['quantity']}  unit {item['unit_minor']} minor")
        lines += ["", f"Subtotal (minor): {invoice['subtotal_minor']}", f"Discount (minor): {invoice['discount_minor']}", f"Configured tax (minor): {invoice['tax_minor']}", f"Total (minor): {invoice['total_minor']}", f"Verified receipts (minor): {verified}", f"Issued credits (minor): {credited}", f"Outstanding (minor): {invoice['total_minor'] - verified - credited}", "Payment status requires manual verification."]
        return Response(simple_pdf(lines), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=auralis-invoice-{invoice_id[:12]}.pdf", "Cache-Control": "no-store"})

    @app.post("/v1/payments")
    def submit_payment(body: PaymentCreate, user: dict = Depends(require_user)):
        if user["vendor"]:
            role(user, "finance_legal")
        else:
            role(user, "customer_owner", "procurement_finance")
        if user["must_change_password"]:
            raise HTTPException(status_code=403, detail="Change temporary password first")
        with store.lock:
            invoice = record("invoices", body.invoice_id, user)
            if invoice["status"] in {"draft", "void"}:
                raise HTTPException(status_code=409, detail="Invoice is not payable")
            verified = store.db.execute("SELECT COALESCE(SUM(amount_minor),0) FROM payments WHERE invoice_id=? AND status='verified'", (body.invoice_id,)).fetchone()[0]
            credited = store.db.execute("SELECT COALESCE(SUM(amount_minor),0) FROM credit_notes WHERE invoice_id=? AND status='issued'", (body.invoice_id,)).fetchone()[0]
            if body.amount_minor > invoice["total_minor"] - verified - credited:
                raise HTTPException(status_code=409, detail="Payment claim exceeds outstanding invoice balance")
            payment_id = secrets.token_hex(16)
            store.db.execute("INSERT INTO payments(id,organization_id,invoice_id,amount_minor,paid_on,channel,reference,evidence_ref,status,reviewed_by,review_reason,created_at,reviewed_at,submitted_by) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (payment_id, invoice["organization_id"], body.invoice_id, body.amount_minor, str(body.paid_on), body.channel, body.reference, body.evidence_ref, "pending_verification", None, None, stamp(), None, user["user_id"]))
            store.audit(user["user_id"], "submitted", "payment", payment_id)
            store.db.commit()
        return {"id": payment_id, "status": "pending_verification"}

    @app.get("/v1/payments")
    def payments(user: dict = Depends(require_user)):
        if user["vendor"]:
            role(user, "finance_legal")
        return {"payments": listed("payments", user, "ORDER BY created_at DESC LIMIT 500")}

    @app.get("/v1/payments/{payment_id}/receipt.pdf")
    def receipt_pdf(payment_id: str, user: dict = Depends(require_user)):
        with store.lock:
            payment = record("payments", payment_id, user)
            if payment["status"] != "verified":
                raise HTTPException(status_code=404, detail="Verified receipt not found")
            invoice = record("invoices", payment["invoice_id"], user)
            store.audit(user["user_id"], "downloaded", "receipt", payment_id)
            store.db.commit()
        lines = ["Auralis manually verified payment receipt", f"Invoice: {invoice['invoice_number']}", f"Site: {invoice['site_id']}", f"Amount (minor {invoice['currency']}): {payment['amount_minor']}", f"Paid on: {payment['paid_on']}", f"Channel: {payment['channel']}", f"Reference: {payment['reference']}", f"Evidence reference: {payment['evidence_ref']}", f"Verified at: {payment['reviewed_at']}", "This records manual reconciliation, not provider confirmation."]
        return Response(simple_pdf(lines), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=auralis-receipt-{payment_id[:12]}.pdf", "Cache-Control": "no-store"})

    @app.post("/v1/renewals")
    def request_renewal(body: RenewalCreate, user: dict = Depends(require_user)):
        if user["vendor"]:
            role(user, "platform_admin", "finance_legal")
        else:
            role(user, "customer_owner", "procurement_finance")
        if user["must_change_password"]:
            raise HTTPException(status_code=403, detail="Change temporary password first")
        with store.lock:
            contract = record("contracts", body.contract_id, user)
            renewal_id = secrets.token_hex(16)
            store.db.execute("INSERT INTO renewals VALUES(?,?,?,?,?,?,?)", (renewal_id, contract["organization_id"], body.contract_id, body.request_type, body.note, "requested", stamp()))
            store.audit(user["user_id"], "requested", "renewal", renewal_id)
            store.db.commit()
        return {"id": renewal_id, "status": "requested"}

    @app.get("/v1/renewals")
    def renewals(user: dict = Depends(require_user)):
        if user["vendor"]:
            role(user, "platform_admin", "finance_legal")
        return {"renewals": listed("renewals", user, "ORDER BY created_at DESC LIMIT 500")}

    @app.patch("/v1/vendor/renewals/{renewal_id}")
    def decide_renewal(renewal_id: str, body: StatusDecision, user: dict = Depends(require_vendor)):
        role(user, "platform_admin", "finance_legal")
        allowed = {"requested": {"under_review", "rejected"}, "under_review": {"quoted", "approved", "rejected"}, "quoted": {"approved", "rejected"}, "approved": {"closed"}}
        with store.lock:
            renewal = record("renewals", renewal_id, user)
            if body.status not in allowed.get(renewal["status"], set()):
                raise HTTPException(status_code=409, detail="Invalid renewal transition")
            store.db.execute("UPDATE renewals SET status=? WHERE id=?", (body.status, renewal_id))
            store.audit(user["user_id"], f"status_{body.status}:{body.reason}", "renewal", renewal_id)
            store.db.commit()
        return {"id": renewal_id, "status": body.status}

    @app.post("/v1/vendor/credits")
    def create_credit(body: CreditCreate, user: dict = Depends(require_vendor)):
        role(user, "finance_legal")
        with store.lock:
            invoice = record("invoices", body.invoice_id, user)
            if invoice["status"] in {"draft", "void"}:
                raise HTTPException(status_code=409, detail="Issued invoice required")
            credit_id = secrets.token_hex(16)
            store.db.execute("INSERT INTO credit_notes VALUES(?,?,?,?,?,?,?,?,?)", (credit_id, invoice["organization_id"], body.invoice_id, body.amount_minor, body.reason, body.document_ref, "draft", stamp(), None))
            store.audit(user["user_id"], "created", "credit_note", credit_id)
            store.db.commit()
        return {"id": credit_id, "status": "draft"}

    @app.get("/v1/credits")
    def credits(user: dict = Depends(require_user)):
        if user["vendor"]:
            role(user, "finance_legal")
        rows = listed("credit_notes", user, "ORDER BY created_at DESC LIMIT 500")
        return {"credits": rows if user["vendor"] else [row for row in rows if row["status"] == "issued"]}

    @app.patch("/v1/vendor/credits/{credit_id}")
    def issue_credit(credit_id: str, body: StatusDecision, user: dict = Depends(require_vendor)):
        role(user, "finance_legal")
        if body.status != "issued":
            raise HTTPException(status_code=422, detail="Only issue is supported")
        with store.lock:
            credit = record("credit_notes", credit_id, user)
            if credit["status"] != "draft":
                raise HTTPException(status_code=409, detail="Credit note already issued")
            invoice = record("invoices", credit["invoice_id"], user)
            verified = store.db.execute("SELECT COALESCE(SUM(amount_minor),0) FROM payments WHERE invoice_id=? AND status='verified'", (invoice["id"],)).fetchone()[0]
            credited = store.db.execute("SELECT COALESCE(SUM(amount_minor),0) FROM credit_notes WHERE invoice_id=? AND status='issued'", (invoice["id"],)).fetchone()[0]
            if credit["amount_minor"] > invoice["total_minor"] - verified - credited:
                raise HTTPException(status_code=409, detail="Credit exceeds outstanding balance")
            store.db.execute("UPDATE credit_notes SET status='issued',issued_at=? WHERE id=?", (stamp(), credit_id))
            remaining = invoice["total_minor"] - verified - credited - credit["amount_minor"]
            store.db.execute("UPDATE invoices SET status=? WHERE id=?", ("paid" if remaining == 0 else "partially_paid" if verified else "issued", invoice["id"]))
            store.audit(user["user_id"], f"issued:{body.reason}", "credit_note", credit_id)
            store.db.commit()
        return {"id": credit_id, "status": "issued"}

    @app.get("/v1/vendor/finance/summary")
    def finance_summary(user: dict = Depends(require_vendor)):
        role(user, "finance_legal")
        org = "evaluation-hospital" if user["evaluation"] else None
        with store.lock:
            invoice_rows = store.db.execute("SELECT currency,SUM(total_minor) AS amount FROM invoices WHERE status NOT IN ('draft','void') AND (? IS NULL OR organization_id=?) GROUP BY currency", (org, org)).fetchall()
            payment_rows = store.db.execute("SELECT i.currency,SUM(p.amount_minor) AS amount FROM payments p JOIN invoices i ON i.id=p.invoice_id WHERE p.status='verified' AND (? IS NULL OR p.organization_id=?) GROUP BY i.currency", (org, org)).fetchall()
            credit_rows = store.db.execute("SELECT i.currency,SUM(c.amount_minor) AS amount FROM credit_notes c JOIN invoices i ON i.id=c.invoice_id WHERE c.status='issued' AND (? IS NULL OR c.organization_id=?) GROUP BY i.currency", (org, org)).fetchall()
            pipeline_rows = store.db.execute("SELECT q.currency,SUM(v.total_minor) AS amount FROM quotes q JOIN quote_versions v ON v.quote_id=q.id AND v.version=q.current_version WHERE q.status IN ('draft','internal_review','issued','acknowledged') AND (? IS NULL OR q.organization_id=?) GROUP BY q.currency", (org, org)).fetchall()
        currencies: dict[str, dict[str, int]] = {}
        for key, rows in (("invoiced_minor", invoice_rows), ("verified_receipts_minor", payment_rows), ("issued_credits_minor", credit_rows), ("pipeline_quotes_minor", pipeline_rows)):
            for row in rows:
                currencies.setdefault(row["currency"], {"invoiced_minor": 0, "verified_receipts_minor": 0, "issued_credits_minor": 0, "pipeline_quotes_minor": 0})[key] = row["amount"]
        for amounts in currencies.values():
            amounts["outstanding_minor"] = amounts["invoiced_minor"] - amounts["verified_receipts_minor"] - amounts["issued_credits_minor"]
        return {"currencies": currencies}

    @app.patch("/v1/vendor/quotes/{quote_id}")
    def decide_quote(quote_id: str, body: StatusDecision, user: dict = Depends(require_vendor)):
        role(user, "finance_legal")
        allowed = {"draft": {"internal_review"}, "internal_review": {"issued", "draft"}, "issued": {"acknowledged", "accepted", "rejected", "expired"}, "acknowledged": {"accepted", "rejected", "expired"}}
        with store.lock:
            quote = record("quotes", quote_id, user)
            if body.status not in allowed.get(quote["status"], set()):
                raise HTTPException(status_code=409, detail="Invalid quote transition")
            store.db.execute("UPDATE quotes SET status=? WHERE id=?", (body.status, quote_id))
            if body.status == "issued":
                store.db.execute("UPDATE quote_versions SET issued_at=? WHERE quote_id=? AND version=?", (stamp(), quote_id, quote["current_version"]))
            store.audit(user["user_id"], f"status_{body.status}:{body.reason}", "quote", quote_id)
            store.db.commit()
        return {"id": quote_id, "status": body.status}

    @app.patch("/v1/vendor/contracts/{contract_id}")
    def decide_contract(contract_id: str, body: StatusDecision, user: dict = Depends(require_vendor)):
        role(user, "finance_legal")
        allowed = {"draft": {"under_review", "cancelled"}, "under_review": {"signed", "draft", "cancelled"}, "signed": {"expired", "terminated"}}
        with store.lock:
            contract = record("contracts", contract_id, user)
            if body.status not in allowed.get(contract["status"], set()):
                raise HTTPException(status_code=409, detail="Invalid contract transition")
            store.db.execute("UPDATE contracts SET status=? WHERE id=?", (body.status, contract_id))
            store.audit(user["user_id"], f"status_{body.status}:{body.reason}", "contract", contract_id)
            store.db.commit()
        return {"id": contract_id, "status": body.status}

    @app.patch("/v1/vendor/invoices/{invoice_id}")
    def issue_invoice(invoice_id: str, body: StatusDecision, user: dict = Depends(require_vendor)):
        role(user, "finance_legal")
        if body.status not in {"issued", "void"}:
            raise HTTPException(status_code=422, detail="Only issue or void is supported")
        with store.lock:
            invoice = record("invoices", invoice_id, user)
            if invoice["status"] != "draft":
                raise HTTPException(status_code=409, detail="Issued invoices are immutable")
            store.db.execute("UPDATE invoices SET status=?,issued_at=? WHERE id=?", (body.status, stamp() if body.status == "issued" else None, invoice_id))
            store.audit(user["user_id"], f"status_{body.status}:{body.reason}", "invoice", invoice_id)
            store.db.commit()
        return {"id": invoice_id, "status": body.status}

    @app.patch("/v1/vendor/payments/{payment_id}")
    def decide_payment(payment_id: str, body: PaymentDecision, user: dict = Depends(require_vendor)):
        role(user, "finance_legal")
        with store.lock:
            payment = record("payments", payment_id, user)
            if payment["status"] not in {"pending_verification", "needs_clarification"}:
                raise HTTPException(status_code=409, detail="Payment review is final")
            if payment["submitted_by"] == user["user_id"] and body.status == "verified":
                raise HTTPException(status_code=403, detail="A different finance reviewer must verify the submission")
            if body.status == "verified":
                invoice = record("invoices", payment["invoice_id"], user)
                verified = store.db.execute("SELECT COALESCE(SUM(amount_minor),0) FROM payments WHERE invoice_id=? AND status='verified'", (invoice["id"],)).fetchone()[0]
                credited = store.db.execute("SELECT COALESCE(SUM(amount_minor),0) FROM credit_notes WHERE invoice_id=? AND status='issued'", (invoice["id"],)).fetchone()[0]
                if payment["amount_minor"] > invoice["total_minor"] - verified - credited:
                    raise HTTPException(status_code=409, detail="Verified payment exceeds outstanding balance")
            store.db.execute("UPDATE payments SET status=?,reviewed_by=?,review_reason=?,reviewed_at=? WHERE id=?", (body.status, user["user_id"], body.reason, stamp(), payment_id))
            if body.status == "verified":
                balance = invoice["total_minor"] - verified - credited - payment["amount_minor"]
                store.db.execute("UPDATE invoices SET status=? WHERE id=?", ("paid" if balance == 0 else "partially_paid", invoice["id"]))
            store.audit(user["user_id"], f"review_{body.status}:{body.reason}", "payment", payment_id)
            store.db.commit()
        return {"id": payment_id, "status": body.status}
