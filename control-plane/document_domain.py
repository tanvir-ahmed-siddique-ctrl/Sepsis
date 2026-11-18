"""Small private PDF vault for commercial documents, with fail-closed scanning.

Production uploads require an approved ClamAV-compatible INSTREAM scanner and
an encryption key. Clinical records are explicitly outside this repository.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import os
import secrets
import sqlite3
import socket
import struct
from datetime import date, datetime, timedelta, timezone
from typing import Callable

from cryptography.fernet import Fernet
from fastapi import Depends, FastAPI, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

MAX_DOCUMENT_BYTES = 1_000_000
DOCUMENT_TYPES = {"agreement", "proposal", "invoice_support", "licence_record", "training", "deployment", "compliance", "other_commercial"}
RETENTION_POLICIES = {"contractual", "regulatory", "operational", "training", "legal_hold"}
LIFECYCLE_STATES = {"draft", "active", "under_review", "archived", "destroyed"}
LIFECYCLE_TRANSITIONS = {
    "draft": {"active"},
    "active": {"under_review", "archived", "destroyed"},
    "under_review": {"active", "archived"},
    "archived": {"destroyed", "active"},
    "destroyed": set(),
}
DEFAULT_RETENTION_YEARS = {
    "agreement": 7,
    "proposal": 3,
    "invoice_support": 7,
    "licence_record": 7,
    "training": 5,
    "deployment": 5,
    "compliance": 7,
    "other_commercial": 3,
}


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def scanner_clean(content: bytes) -> bool:
    if os.environ.get("EVALUATION_RUNTIME") == "true":
        return True  # isolated synthetic documents only; no external side effect
    endpoint = os.environ.get("ACCOUNT_CLAMD_HOST", "")
    if not endpoint:
        raise HTTPException(status_code=503, detail="Document scanner is not configured")
    port = int(os.environ.get("ACCOUNT_CLAMD_PORT", "3310"))
    try:
        with socket.create_connection((endpoint, port), timeout=4) as connection:
            connection.settimeout(8)
            connection.sendall(b"zINSTREAM\0" + struct.pack(">I", len(content)) + content + struct.pack(">I", 0))
            reply = connection.recv(512)
    except (OSError, ValueError) as error:
        raise HTTPException(status_code=503, detail="Document scanner unavailable") from error
    if b"FOUND" in reply:
        return False
    if not reply.startswith(b"stream: OK"):
        raise HTTPException(status_code=503, detail="Document scanner result indeterminate")
    return True


class DocumentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    organization_id: str
    site_id: str | None = None
    document_key: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,79}$")
    version: int = Field(ge=1, le=10000)
    title: str = Field(min_length=3, max_length=160)
    document_type: str
    access: str = Field(pattern="^(vendor_only|customer_visible)$")
    owner_role: str = Field(min_length=2, max_length=80)
    expires_on: date | None = None
    effective_on: date | None = None
    review_on: date | None = None
    retention_policy: str = "contractual"
    retention_years: int | None = Field(default=None, ge=1, le=50)
    content_b64: str = Field(min_length=8, max_length=1_500_000)


class DocumentApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=3, max_length=240)


class DocumentLifecycleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lifecycle_status: str
    retention_policy: str | None = None
    review_on: date | None = None
    retention_until: date | None = None
    reason: str = Field(min_length=3, max_length=240)


def ensure_document_lifecycle_columns(store) -> None:
    columns = {row[1] for row in store.db.execute("PRAGMA table_info(documents)")}
    for name, definition in (
        ("effective_on", "TEXT"),
        ("review_on", "TEXT"),
        ("retention_until", "TEXT"),
        ("retention_policy", "TEXT NOT NULL DEFAULT 'contractual'"),
        ("lifecycle_status", "TEXT NOT NULL DEFAULT 'draft'"),
        ("destroyed_at", "TEXT"),
    ):
        if name not in columns:
            store.db.execute(f"ALTER TABLE documents ADD COLUMN {name} {definition}")
    store.db.execute("UPDATE documents SET lifecycle_status='draft' WHERE lifecycle_status IS NULL OR lifecycle_status=''")
    store.db.execute("UPDATE documents SET lifecycle_status='active' WHERE approval_status='approved' AND (lifecycle_status='draft' OR lifecycle_status IS NULL OR lifecycle_status='')")
    store.db.execute("UPDATE documents SET retention_policy='contractual' WHERE retention_policy IS NULL OR retention_policy=''")


def install_document_routes(app: FastAPI, store, require_user: Callable, require_vendor: Callable) -> None:
    with store.lock:
        store.db.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
              id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
              site_id TEXT REFERENCES sites(id), document_key TEXT NOT NULL, version INTEGER NOT NULL,
              title TEXT NOT NULL, document_type TEXT NOT NULL, access TEXT NOT NULL,
              owner_role TEXT NOT NULL, expires_on TEXT, sha256 TEXT NOT NULL,
              scan_status TEXT NOT NULL, approval_status TEXT NOT NULL,
              encrypted_pdf BLOB NOT NULL, created_at TEXT NOT NULL, approved_at TEXT,
              effective_on TEXT, review_on TEXT, retention_until TEXT,
              retention_policy TEXT NOT NULL DEFAULT 'contractual',
              lifecycle_status TEXT NOT NULL DEFAULT 'draft', destroyed_at TEXT,
              UNIQUE(document_key,version));
        """)
        ensure_document_lifecycle_columns(store)
        store.db.commit()

    def role(user: dict, *allowed: str) -> None:
        if user["evaluation"]:
            return
        if user["role"] not in allowed and user["role"] != "root_admin":
            raise HTTPException(status_code=403, detail="Account role does not permit this action")

    def key() -> Fernet:
        raw = os.environ.get("ACCOUNT_DOCUMENT_KEY", "")
        if not raw:
            raise HTTPException(status_code=503, detail="Document encryption is not configured")
        try:
            return Fernet(raw.encode())
        except (ValueError, binascii.Error) as error:
            raise HTTPException(status_code=503, detail="Document encryption configuration invalid") from error

    def accessible(row: dict, user: dict) -> bool:
        from permissions import has_permission

        if row.get("lifecycle_status") == "destroyed":
            return user["vendor"]  # metadata only for vendor audit
        if user["evaluation"] and row["organization_id"] != "evaluation-hospital":
            return False
        if not user["vendor"]:
            document_permissions = {
                "agreement": "customer.contract.read",
                "proposal": "customer.quote.read",
                "invoice_support": "customer.invoice.read",
                "licence_record": "customer.licence.read",
                "training": "customer.training.read",
                "deployment": "customer.document.read",
                "compliance": "customer.compliance.read",
                "other_commercial": "customer.document.read",
            }
            permission = document_permissions.get(row["document_type"], "customer.document.read")
            return (
                row["organization_id"] in user["organization_ids"]
                and has_permission(user, permission, organization_id=row["organization_id"])
                and row["access"] == "customer_visible"
                and row["approval_status"] == "approved"
                and row.get("lifecycle_status") in {None, "active", "under_review"}
            )
        return True

    def public_row(row: dict) -> dict:
        item = {key_name: value for key_name, value in dict(row).items() if key_name != "encrypted_pdf"}
        today = date.today().isoformat()
        item["review_due"] = bool(item.get("review_on") and item["review_on"] <= today and item.get("lifecycle_status") in {"active", "under_review"})
        item["retention_due"] = bool(item.get("retention_until") and item["retention_until"] <= today and item.get("lifecycle_status") not in {"destroyed"})
        item["content_destroyed"] = item.get("lifecycle_status") == "destroyed" or not row["encrypted_pdf"]
        return item

    @app.post("/v1/vendor/documents")
    def upload_document(body: DocumentCreate, user: dict = Depends(require_vendor)):
        from permissions import require_permission

        require_permission(user, "vendor.document.write")
        if body.document_type not in DOCUMENT_TYPES:
            raise HTTPException(status_code=422, detail="Unknown document type")
        if body.retention_policy not in RETENTION_POLICIES:
            raise HTTPException(status_code=422, detail="Unknown retention policy")
        try:
            content = base64.b64decode(body.content_b64, validate=True)
        except (ValueError, binascii.Error) as error:
            raise HTTPException(status_code=422, detail="Invalid PDF encoding") from error
        if len(content) > MAX_DOCUMENT_BYTES or not content.startswith(b"%PDF-") or b"%%EOF" not in content[-64:]:
            raise HTTPException(status_code=422, detail="PDF must be validly framed and below 1 MB")
        cipher = key()
        clean = scanner_clean(content)
        if not clean:
            raise HTTPException(status_code=422, detail="Document rejected by scanner")
        years = body.retention_years or DEFAULT_RETENTION_YEARS[body.document_type]
        effective = body.effective_on or date.today()
        review = body.review_on or (effective + timedelta(days=365))
        retention_until = effective + timedelta(days=365 * years)
        if body.expires_on and str(body.expires_on) < str(retention_until):
            # expires_on is commercial visibility; retention may outlive commercial expiry
            pass
        with store.lock:
            if user["evaluation"] and body.organization_id != "evaluation-hospital":
                raise HTTPException(status_code=404, detail="Organization not found")
            if not store.db.execute("SELECT 1 FROM organizations WHERE id=?", (body.organization_id,)).fetchone():
                raise HTTPException(status_code=404, detail="Organization not found")
            if body.site_id:
                site = store.db.execute("SELECT organization_id FROM sites WHERE id=?", (body.site_id,)).fetchone()
                if not site or site["organization_id"] != body.organization_id:
                    raise HTTPException(status_code=404, detail="Site not found")
            document_id = secrets.token_hex(16)
            try:
                store.db.execute(
                    """INSERT INTO documents(id,organization_id,site_id,document_key,version,title,document_type,access,owner_role,expires_on,sha256,scan_status,approval_status,encrypted_pdf,created_at,approved_at,effective_on,review_on,retention_until,retention_policy,lifecycle_status,destroyed_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        document_id, body.organization_id, body.site_id, body.document_key, body.version, body.title,
                        body.document_type, body.access, body.owner_role, str(body.expires_on) if body.expires_on else None,
                        hashlib.sha256(content).hexdigest(), "synthetic_clean" if user["evaluation"] else "scanner_clean",
                        "draft", cipher.encrypt(content), stamp(), None, str(effective), str(review), str(retention_until),
                        body.retention_policy, "draft", None,
                    ),
                )
                store.audit(user["user_id"], "uploaded", "document", document_id)
                store.db.commit()
            except sqlite3.IntegrityError as error:
                store.db.rollback()
                raise HTTPException(status_code=409, detail="Document version already exists") from error
            except Exception:
                store.db.rollback()
                raise
        return {
            "id": document_id,
            "approval_status": "draft",
            "lifecycle_status": "draft",
            "retention_policy": body.retention_policy,
            "retention_until": str(retention_until),
            "review_on": str(review),
            "sha256": hashlib.sha256(content).hexdigest(),
        }

    @app.patch("/v1/vendor/documents/{document_id}")
    def approve_document(document_id: str, body: DocumentApproval, user: dict = Depends(require_vendor)):
        from permissions import require_permission

        require_permission(user, "vendor.document.write")
        with store.lock:
            row = store.db.execute("SELECT organization_id,approval_status,lifecycle_status FROM documents WHERE id=?", (document_id,)).fetchone()
            if not row or (user["evaluation"] and row["organization_id"] != "evaluation-hospital"):
                raise HTTPException(status_code=404, detail="Document not found")
            if row["approval_status"] != "draft":
                raise HTTPException(status_code=409, detail="Document approval is final")
            if row["lifecycle_status"] == "destroyed":
                raise HTTPException(status_code=409, detail="Destroyed documents cannot be approved")
            store.db.execute(
                "UPDATE documents SET approval_status='approved', approved_at=?, lifecycle_status='active' WHERE id=?",
                (stamp(), document_id),
            )
            store.audit(user["user_id"], f"approved:{body.reason}", "document", document_id)
            store.db.commit()
        return {"id": document_id, "approval_status": "approved", "lifecycle_status": "active"}

    @app.patch("/v1/vendor/documents/{document_id}/lifecycle")
    def update_document_lifecycle(document_id: str, body: DocumentLifecycleUpdate, user: dict = Depends(require_vendor)):
        from permissions import require_permission

        require_permission(user, "vendor.document.write")
        if body.lifecycle_status not in LIFECYCLE_STATES:
            raise HTTPException(status_code=422, detail="Unknown lifecycle status")
        if body.retention_policy is not None and body.retention_policy not in RETENTION_POLICIES:
            raise HTTPException(status_code=422, detail="Unknown retention policy")
        with store.lock:
            row = store.db.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
            if not row or (user["evaluation"] and row["organization_id"] != "evaluation-hospital"):
                raise HTTPException(status_code=404, detail="Document not found")
            current = row["lifecycle_status"] or ("active" if row["approval_status"] == "approved" else "draft")
            if body.lifecycle_status != current and body.lifecycle_status not in LIFECYCLE_TRANSITIONS.get(current, set()):
                raise HTTPException(status_code=409, detail=f"Cannot move document from {current} to {body.lifecycle_status}")
            if body.lifecycle_status == "destroyed":
                if (body.retention_policy or row["retention_policy"]) == "legal_hold":
                    raise HTTPException(status_code=409, detail="Documents on legal hold cannot be destroyed")
                if row["retention_until"] and row["retention_until"] > date.today().isoformat() and (body.retention_policy or row["retention_policy"]) != "operational":
                    raise HTTPException(status_code=409, detail="Retention period has not elapsed")
            destroyed_at = stamp() if body.lifecycle_status == "destroyed" else row["destroyed_at"]
            encrypted = b"" if body.lifecycle_status == "destroyed" else row["encrypted_pdf"]
            store.db.execute(
                """UPDATE documents SET lifecycle_status=?, retention_policy=COALESCE(?,retention_policy), review_on=COALESCE(?,review_on),
                   retention_until=COALESCE(?,retention_until), destroyed_at=?, encrypted_pdf=? WHERE id=?""",
                (
                    body.lifecycle_status,
                    body.retention_policy,
                    str(body.review_on) if body.review_on else None,
                    str(body.retention_until) if body.retention_until else None,
                    destroyed_at,
                    encrypted,
                    document_id,
                ),
            )
            store.audit(user["user_id"], f"lifecycle_{body.lifecycle_status}:{body.reason}", "document", document_id)
            store.db.commit()
        return {"id": document_id, "lifecycle_status": body.lifecycle_status, "content_destroyed": body.lifecycle_status == "destroyed"}

    @app.get("/v1/documents")
    def documents(user: dict = Depends(require_user)):
        with store.lock:
            if user["evaluation"]:
                rows = store.db.execute("SELECT * FROM documents WHERE organization_id='evaluation-hospital' ORDER BY created_at DESC LIMIT 500").fetchall()
            elif user["vendor"]:
                rows = store.db.execute("SELECT * FROM documents ORDER BY created_at DESC LIMIT 500").fetchall()
            else:
                rows = store.db.execute(
                    "SELECT * FROM documents WHERE organization_id IN (SELECT organization_id FROM memberships WHERE user_id=?) AND access='customer_visible' AND approval_status='approved' AND lifecycle_status IN ('active','under_review') ORDER BY created_at DESC LIMIT 500",
                    (user["user_id"],),
                ).fetchall()
        return {"documents": [public_row(row) for row in rows if accessible(dict(row), user)]}

    @app.get("/v1/documents/lifecycle-due")
    def documents_lifecycle_due(user: dict = Depends(require_vendor)):
        from permissions import require_permission

        require_permission(user, "vendor.document.read")
        today = date.today().isoformat()
        with store.lock:
            rows = store.db.execute("SELECT * FROM documents ORDER BY created_at DESC LIMIT 1000").fetchall()
        due = []
        for row in rows:
            item = public_row(row)
            if item["review_due"] or item["retention_due"]:
                due.append(item)
            elif item.get("expires_on") and item["expires_on"] <= today and item.get("lifecycle_status") == "active":
                due.append(item)
        return {"documents": due, "as_of": today}

    @app.get("/v1/documents/{document_id}/download")
    def download_document(document_id: str, user: dict = Depends(require_user)):
        with store.lock:
            row = store.db.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
            if not row or not accessible(dict(row), user):
                raise HTTPException(status_code=404, detail="Document not found")
            if row["approval_status"] != "approved":
                raise HTTPException(status_code=404, detail="Document not approved")
            if row["lifecycle_status"] in {"archived", "destroyed"} and not user["vendor"]:
                raise HTTPException(status_code=409, detail="Document is not available for customer download")
            if row["lifecycle_status"] == "destroyed" or not row["encrypted_pdf"]:
                raise HTTPException(status_code=410, detail="Document content destroyed under retention policy")
            if row["lifecycle_status"] == "archived" and user["vendor"]:
                pass
            content = key().decrypt(row["encrypted_pdf"])
            store.audit(user["user_id"], "downloaded", "document", document_id)
            store.db.commit()
        return Response(content, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=auralis-document-{document_id[:12]}.pdf", "Cache-Control": "no-store"})
