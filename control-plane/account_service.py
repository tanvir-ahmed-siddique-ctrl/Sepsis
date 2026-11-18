"""Auralis account boundary: vendor and customer metadata, separate from site clinical data.

This service never imports the hospital engine or its database. It stores only
organization/site registration and coded support requests. Run separately from
hospital-local services with ACCOUNT_DB on approved infrastructure.
"""

from __future__ import annotations

import getpass
import hashlib
import hmac
import json
import os
import base64
import struct
import time
import secrets
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from cryptography.fernet import Fernet
from commercial_domain import install_commercial_routes
from operations_domain import install_operations_routes
from document_domain import install_document_routes
from partnership_domain import install_partnership_routes
from enterprise_governance import (
    ensure_asset_lifecycle_columns,
    ensure_ticket_sla_columns,
    install_governance_routes,
    resolve_support_plan,
    sla_fields,
    sla_due_iso,
    sla_target_minutes,
)
from permissions import (
    CUSTOMER_ROLES,
    CUSTOMER_TABLE_PERMISSION,
    VENDOR_ROLES,
    has_permission,
    matrix_snapshot,
    require_permission,
)

SESSION_HOURS = 8
ISSUE_CODES = {"feed_unavailable", "mapping_review", "edge_unavailable", "backup_check", "account_access", "training_request", "other_operational"}
STATUSES = {"open", "acknowledged", "in_progress", "waiting_for_hospital", "waiting_for_vendor", "resolved", "closed"}
ASSET_KINDS = {"edge_appliance", "network_gateway", "storage", "ups", "bedside_interface", "other"}
ASSET_LIFECYCLE = {"ordered", "received", "commissioned", "in_service", "maintenance", "retired", "disposed"}
ASSET_TRANSITIONS = {
    "ordered": {"received"},
    "received": {"commissioned"},
    "commissioned": {"in_service", "maintenance", "retired"},
    "in_service": {"maintenance", "retired"},
    "maintenance": {"in_service", "retired"},
    "retired": {"disposed"},
    "disposed": set(),
}
COMPLIANCE_STATES = {"not_started", "in_progress", "awaiting_hospital", "awaiting_counsel", "submitted", "approved", "rejected", "expired", "needs_renewal"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def password_digest(password: str, salt: bytes | None = None) -> str:
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters")
    salt = salt or secrets.token_bytes(16)
    value = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return salt.hex() + ":" + value.hex()


def verify_password(password: str, digest: str) -> bool:
    try:
        salt_hex, expected = digest.split(":", 1)
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
        return hmac.compare_digest(actual, bytes.fromhex(expected))
    except (ValueError, TypeError):
        return False


def _cipher() -> Fernet:
    key = os.environ.get("ACCOUNT_MFA_KEY", "")
    if not key:
        raise RuntimeError("ACCOUNT_MFA_KEY is required for vendor MFA")
    return Fernet(key.encode())


def totp_code(secret: str, at: int | None = None) -> str:
    counter = int(time.time() if at is None else at) // 30
    digest = hmac.new(base64.b32decode(secret), struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % 1_000_000
    return f"{number:06d}"


def verify_totp(secret: str, code: str) -> bool:
    return len(code) == 6 and code.isdigit() and any(hmac.compare_digest(totp_code(secret, int(time.time()) + delta * 30), code) for delta in (-1, 0, 1))


def provisioning_uri(email: str, secret: str) -> str:
    from urllib.parse import quote
    return f"otpauth://totp/Auralis:{quote(email)}?secret={secret}&issuer=Auralis&algorithm=SHA1&digits=6&period=30"


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=1, max_length=512)
    totp_code: str | None = Field(default=None, pattern=r"^[0-9]{6}$")


class PasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(min_length=1, max_length=512)
    new_password: str = Field(min_length=12, max_length=512)


class OrganizationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    organization_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,62}$")
    name: str = Field(min_length=2, max_length=120)


class SiteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    site_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,62}$")
    organization_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,62}$")
    name: str = Field(min_length=2, max_length=120)


class CustomerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    display_name: str = Field(min_length=2, max_length=120)
    organization_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,62}$")
    password: str = Field(min_length=12, max_length=512)
    role: str = Field(default="customer_owner", pattern="^(customer_owner|procurement_finance|technical_contact|customer_viewer)$")


class CustomerInvite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    display_name: str = Field(min_length=2, max_length=120)
    organization_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,62}$")
    role: str = Field(pattern="^(customer_owner|procurement_finance|technical_contact|customer_viewer)$")
    reason: str = Field(min_length=3, max_length=240)


class AcceptInvite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=32, max_length=256)
    password: str = Field(min_length=12, max_length=512)


class VendorUserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    display_name: str = Field(min_length=2, max_length=120)
    role: str = Field(pattern="^(platform_admin|deployment_engineer|support_engineer|finance_legal|security_compliance)$")
    password: str = Field(min_length=12, max_length=512)


class MembershipChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    organization_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,62}$")
    role: str = Field(pattern="^(customer_owner|procurement_finance|technical_contact|customer_viewer)$")
    reason: str = Field(min_length=3, max_length=240)


class AccountStateChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    disabled: bool
    reason: str = Field(min_length=3, max_length=240)


class CustomerMemberInvite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    organization_id: str
    email: str = Field(min_length=3, max_length=254)
    display_name: str = Field(min_length=2, max_length=120)
    role: str
    reason: str = Field(min_length=3, max_length=240)


class ApprovalDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str = Field(pattern="^(approved|rejected)$")
    reason: str = Field(min_length=3, max_length=240)


class ApprovalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str = Field(pattern="^(vendor_role_change|customer_role_change|offboarding|licence_issue)$")
    payload: dict
    reason: str = Field(min_length=3, max_length=240)


class TicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    site_id: str
    issue_code: str
    severity: str = Field(pattern=r"^(routine|degraded|urgent)$")


class TicketUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    assigned_to: str | None = Field(default=None, max_length=120)
    escalate: bool = False
    reason: str | None = Field(default=None, max_length=240)


class AssetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    site_id: str
    asset_tag: str = Field(min_length=3, max_length=80)
    kind: str
    model: str = Field(min_length=2, max_length=120)
    firmware: str | None = Field(default=None, max_length=80)
    serial_number: str | None = Field(default=None, max_length=120)
    warranty_until: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    lifecycle_state: str = "commissioned"


class AssetLifecycleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lifecycle_state: str
    disposition_ref: str | None = Field(default=None, max_length=160)
    warranty_until: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    reason: str = Field(min_length=3, max_length=240)


class ComplianceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    site_id: str
    task_type: str = Field(min_length=3, max_length=100)
    owner: str = Field(min_length=2, max_length=120)


class ComplianceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    evidence_ref: str | None = Field(default=None, max_length=200)


class AccountStore:
    def __init__(self, db_path: str):
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        with self.lock:
            self.db.executescript("""
                PRAGMA foreign_keys = ON;
                CREATE TABLE IF NOT EXISTS organizations (
                  id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS sites (
                  id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
                  name TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS users (
                  id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL,
                  password_hash TEXT NOT NULL, vendor INTEGER NOT NULL DEFAULT 0,
                  must_change_password INTEGER NOT NULL DEFAULT 0,
                  failed_attempts INTEGER NOT NULL DEFAULT 0, locked_until TEXT,
                  mfa_secret TEXT);
                CREATE TABLE IF NOT EXISTS memberships (
                  user_id TEXT NOT NULL REFERENCES users(id), organization_id TEXT NOT NULL REFERENCES organizations(id),
                  PRIMARY KEY(user_id, organization_id));
                CREATE TABLE IF NOT EXISTS sessions (
                  token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), expires_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS customer_invitations (
                  id TEXT PRIMARY KEY, token_hash TEXT NOT NULL UNIQUE, email TEXT NOT NULL,
                  display_name TEXT NOT NULL, organization_id TEXT NOT NULL REFERENCES organizations(id),
                  role TEXT NOT NULL, expires_at TEXT NOT NULL, accepted_at TEXT,
                  invited_by TEXT NOT NULL REFERENCES users(id), created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS tickets (
                  id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
                  site_id TEXT NOT NULL REFERENCES sites(id), issue_code TEXT NOT NULL,
                  severity TEXT NOT NULL, status TEXT NOT NULL, opened_by TEXT NOT NULL REFERENCES users(id),
                  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                  assigned_to TEXT, first_response_at TEXT, acknowledged_at TEXT, sla_due_at TEXT,
                  sla_breached INTEGER NOT NULL DEFAULT 0, escalation_level INTEGER NOT NULL DEFAULT 0,
                  support_plan_id TEXT, sla_target_minutes INTEGER);
                CREATE TABLE IF NOT EXISTS assets (
                  id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
                  site_id TEXT NOT NULL REFERENCES sites(id), asset_tag TEXT NOT NULL UNIQUE,
                  kind TEXT NOT NULL, model TEXT NOT NULL, firmware TEXT, registered_at TEXT NOT NULL,
                  serial_number TEXT, warranty_until TEXT,
                  lifecycle_state TEXT NOT NULL DEFAULT 'commissioned',
                  retired_at TEXT, disposition_ref TEXT, updated_at TEXT);
                CREATE TABLE IF NOT EXISTS compliance_tasks (
                  id TEXT PRIMARY KEY, organization_id TEXT NOT NULL REFERENCES organizations(id),
                  site_id TEXT NOT NULL REFERENCES sites(id), task_type TEXT NOT NULL,
                  owner TEXT NOT NULL, status TEXT NOT NULL, evidence_ref TEXT,
                  created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS audit_events (
                  id INTEGER PRIMARY KEY AUTOINCREMENT, actor_id TEXT NOT NULL, action TEXT NOT NULL,
                  object_type TEXT NOT NULL, object_id TEXT NOT NULL, at TEXT NOT NULL,
                  prev_hash TEXT, event_hash TEXT);
                CREATE TABLE IF NOT EXISTS approval_requests (
                  id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload_json TEXT NOT NULL,
                  status TEXT NOT NULL, requested_by TEXT NOT NULL REFERENCES users(id),
                  decided_by TEXT REFERENCES users(id), reason TEXT NOT NULL,
                  decision_reason TEXT, created_at TEXT NOT NULL, decided_at TEXT);
            """)
            columns = {row[1] for row in self.db.execute("PRAGMA table_info(users)")}
            if "role" not in columns:
                self.db.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'customer_owner'")
                self.db.execute("UPDATE users SET role='root_admin' WHERE vendor=1")
            if "mfa_secret" not in columns:
                self.db.execute("ALTER TABLE users ADD COLUMN mfa_secret TEXT")
            if "disabled" not in columns:
                self.db.execute("ALTER TABLE users ADD COLUMN disabled INTEGER NOT NULL DEFAULT 0")
            if "role" not in {row[1] for row in self.db.execute("PRAGMA table_info(memberships)")}:
                self.db.execute("ALTER TABLE memberships ADD COLUMN role TEXT")
                self.db.execute("UPDATE memberships SET role=(SELECT role FROM users WHERE users.id=memberships.user_id)")
            ensure_ticket_sla_columns(self)
            ensure_asset_lifecycle_columns(self)
            audit_columns = {row[1] for row in self.db.execute("PRAGMA table_info(audit_events)")}
            if "prev_hash" not in audit_columns:
                self.db.execute("ALTER TABLE audit_events ADD COLUMN prev_hash TEXT")
                self.db.execute("ALTER TABLE audit_events ADD COLUMN event_hash TEXT")
                previous = "0" * 64
                for row in self.db.execute("SELECT id,actor_id,action,object_type,object_id,at FROM audit_events ORDER BY id").fetchall():
                    digest = self._event_hash(previous, row["actor_id"], row["action"], row["object_type"], row["object_id"], row["at"])
                    self.db.execute("UPDATE audit_events SET prev_hash=?,event_hash=? WHERE id=?", (previous, digest, row["id"]))
                    previous = digest
            self.db.commit()

    @staticmethod
    def _event_hash(previous: str, actor: str, action: str, kind: str, object_id: str, at: str) -> str:
        encoded = json.dumps([previous, actor, action, kind, object_id, at], separators=(",", ":"), ensure_ascii=False).encode()
        return hashlib.sha256(encoded).hexdigest()

    def audit(self, actor: str, action: str, kind: str, object_id: str) -> None:
        previous_row = self.db.execute("SELECT event_hash FROM audit_events ORDER BY id DESC LIMIT 1").fetchone()
        previous = previous_row[0] if previous_row else "0" * 64
        at = now()
        digest = self._event_hash(previous, actor, action, kind, object_id, at)
        self.db.execute("INSERT INTO audit_events(actor_id,action,object_type,object_id,at,prev_hash,event_hash) VALUES(?,?,?,?,?,?,?)", (actor, action, kind, object_id, at, previous, digest))

    def audit_integrity(self) -> bool:
        previous = "0" * 64
        with self.lock:
            for row in self.db.execute("SELECT actor_id,action,object_type,object_id,at,prev_hash,event_hash FROM audit_events ORDER BY id"):
                expected = self._event_hash(previous, row["actor_id"], row["action"], row["object_type"], row["object_id"], row["at"])
                if row["prev_hash"] != previous or row["event_hash"] != expected:
                    return False
                previous = expected
        return True

    def create_vendor(self, email: str, display_name: str, password: str) -> str | None:
        with self.lock:
            existing = self.db.execute("SELECT 1 FROM users WHERE vendor = 1").fetchone()
            if existing:
                raise ValueError("Vendor administrator already exists")
            user_id = secrets.token_hex(16)
            secret = base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=") if os.environ.get("ACCOUNT_REQUIRE_MFA") == "true" else None
            encrypted = _cipher().encrypt(secret.encode()).decode() if secret else None
            self.db.execute("INSERT INTO users(id,email,display_name,password_hash,vendor,role,mfa_secret) VALUES(?,?,?,?,1,'root_admin',?)",
                            (user_id, email.strip().lower(), display_name, password_digest(password), encrypted))
            self.audit(user_id, "vendor_bootstrapped", "user", user_id)
            self.db.commit()
            return provisioning_uri(email.strip().lower(), secret) if secret else None

    def identity(self, token: str) -> dict | None:
        digest = hashlib.sha256(token.encode()).hexdigest()
        with self.lock:
            row = self.db.execute("SELECT u.id,u.email,u.display_name,u.vendor,u.role,u.must_change_password,u.disabled,s.expires_at FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=?", (digest,)).fetchone()
            if not row or row["disabled"] or datetime.fromisoformat(row["expires_at"]) <= datetime.now(timezone.utc):
                return None
            member_rows = self.db.execute("SELECT organization_id,role FROM memberships WHERE user_id=?", (row["id"],)).fetchall()
            orgs = [item["organization_id"] for item in member_rows]
            organization_roles = {item["organization_id"]: item["role"] for item in member_rows}
            evaluation = os.environ.get("EVALUATION_RUNTIME") == "true" and row["email"] == "evaluator@auralis.invalid"
            return {"user_id": row["id"], "email": row["email"], "display_name": row["display_name"], "vendor": bool(row["vendor"]), "role": "evaluation_operator" if evaluation else row["role"], "evaluation": evaluation, "must_change_password": bool(row["must_change_password"]), "organization_ids": orgs, "organization_roles": organization_roles}


def create_app(db_path: str = ":memory:") -> FastAPI:
    if os.environ.get("ACCOUNT_REQUIRE_MFA") == "true":
        _cipher()
    app = FastAPI(title="Auralis account service", version="0.1.0")
    store = AccountStore(db_path)
    app.state.store = store
    if os.environ.get("EVALUATION_RUNTIME") == "true":
        password = os.environ.get("EVALUATION_ACCOUNT_PASSWORD", "")
        if len(password) < 12:
            raise RuntimeError("Evaluation account password must be supplied through deployment secrets")
        with store.lock:
            evaluator = store.db.execute("SELECT id FROM users WHERE email=?", ("evaluator@auralis.invalid",)).fetchone()
            if not evaluator:
                store.create_vendor("evaluator@auralis.invalid", "Synthetic evaluator", password)
                evaluator = store.db.execute("SELECT id FROM users WHERE email=?", ("evaluator@auralis.invalid",)).fetchone()
            store.db.execute("INSERT OR IGNORE INTO organizations VALUES(?,?,?)", ("evaluation-hospital", "Evaluation Hospital · Synthetic data", now()))
            store.db.execute("INSERT OR IGNORE INTO sites VALUES(?,?,?,?)", ("evaluation-icu", "evaluation-hospital", "Synthetic ICU", now()))
            store.db.execute("INSERT OR IGNORE INTO memberships(user_id,organization_id,role) VALUES(?,?,?)", (evaluator["id"], "evaluation-hospital", "evaluation_operator"))
            store.db.commit()

    def require_user(authorization: str | None = Header(default=None)) -> dict:
        scheme, _, token = (authorization or "").partition(" ")
        identity = store.identity(token) if scheme.lower() == "bearer" and token else None
        if not identity:
            raise HTTPException(status_code=401, detail="Account sign-in required")
        return identity

    def require_vendor(user: dict = Depends(require_user)) -> dict:
        if not user["vendor"]:
            raise HTTPException(status_code=403, detail="Vendor role required")
        return user

    def allow_roles(user: dict, *roles: str) -> None:
        """Legacy role-name check kept for transitional call sites; prefer require_permission."""
        if user["evaluation"]:
            return
        if user["role"] not in roles and user["role"] != "root_admin":
            raise HTTPException(status_code=403, detail="Account role does not permit this action")

    @app.get("/v1/permissions/matrix")
    def permission_matrix(user: dict = Depends(require_user)):
        if not user["vendor"] and not user["evaluation"]:
            raise HTTPException(status_code=403, detail="Permission matrix is vendor-visible")
        if not user["evaluation"] and not (
            has_permission(user, "vendor.audit.read") or has_permission(user, "vendor.account.directory")
        ):
            raise HTTPException(status_code=403, detail="Account role does not permit this action")
        snapshot = matrix_snapshot()
        snapshot["caller"] = {
            "role": user["role"],
            "permissions": sorted(p for p in snapshot["permissions"] if has_permission(user, p)),
        }
        return snapshot

    @app.post("/v1/auth/login")
    def login(body: Login):
        email = body.email.strip().lower()
        with store.lock:
            row = store.db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
            locked = row and row["locked_until"] and datetime.fromisoformat(row["locked_until"]) > datetime.now(timezone.utc)
            password_ok = bool(row) and not row["disabled"] and not locked and verify_password(body.password, row["password_hash"])
            mfa_required = bool(row) and bool(row["vendor"]) and os.environ.get("ACCOUNT_REQUIRE_MFA") == "true"
            mfa_ok = not mfa_required or (bool(row["mfa_secret"]) and verify_totp(_cipher().decrypt(row["mfa_secret"].encode()).decode(), body.totp_code or ""))
            valid = password_ok and mfa_ok
            if not valid:
                if row and not locked:
                    failures = row["failed_attempts"] + 1
                    until = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat() if failures >= 5 else None
                    store.db.execute("UPDATE users SET failed_attempts=?,locked_until=? WHERE id=?", (failures, until, row["id"]))
                    store.db.commit()
                raise HTTPException(status_code=401, detail="Invalid account credentials")
            store.db.execute("UPDATE users SET failed_attempts=0,locked_until=NULL WHERE id=?", (row["id"],))
            token = secrets.token_urlsafe(32)
            expiry = (datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)).isoformat()
            store.db.execute("INSERT INTO sessions VALUES(?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), row["id"], expiry))
            store.audit(row["id"], "signed_in", "user", row["id"])
            store.db.commit()
            return {"access_token": token, "expires_in_seconds": SESSION_HOURS * 3600, "must_change_password": bool(row["must_change_password"])}

    @app.post("/v1/auth/change-password")
    def change_password(body: PasswordChange, user: dict = Depends(require_user)):
        with store.lock:
            found = store.db.execute("SELECT password_hash FROM users WHERE id=?", (user["user_id"],)).fetchone()
            if not found or not verify_password(body.current_password, found["password_hash"]):
                raise HTTPException(status_code=403, detail="Current password invalid")
            store.db.execute("UPDATE users SET password_hash=?,must_change_password=0 WHERE id=?",
                             (password_digest(body.new_password), user["user_id"]))
            store.db.execute("DELETE FROM sessions WHERE user_id=?", (user["user_id"],))
            store.audit(user["user_id"], "password_changed", "user", user["user_id"])
            store.db.commit()
        return {"changed": True, "sign_in_again": True}

    @app.post("/v1/auth/logout")
    def logout(authorization: str | None = Header(default=None), user: dict = Depends(require_user)):
        token = (authorization or "").partition(" ")[2]
        with store.lock:
            store.db.execute("DELETE FROM sessions WHERE token_hash=?", (hashlib.sha256(token.encode()).hexdigest(),))
            store.audit(user["user_id"], "signed_out", "user", user["user_id"])
            store.db.commit()
        return {"logged_out": True}

    @app.get("/v1/auth/me")
    def me(user: dict = Depends(require_user)):
        workspaces = []
        if user["vendor"]:
            workspaces.append({"id": "vendor", "path": "/platform/accounts"})
        if user["organization_ids"] and (not user["vendor"] or user["evaluation"]):
            workspaces.append({"id": "customer", "path": "/portal"})
        return {**user, "workspaces": workspaces}

    @app.post("/v1/vendor/organizations")
    def create_organization(body: OrganizationCreate, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.org.create")
        if user["evaluation"]:
            raise HTTPException(status_code=403, detail="Organization creation unavailable in synthetic evaluation")
        with store.lock:
            try:
                store.db.execute("INSERT INTO organizations VALUES(?,?,?)", (body.organization_id, body.name, now()))
                store.audit(user["user_id"], "created", "organization", body.organization_id)
                store.db.commit()
            except sqlite3.IntegrityError:
                raise HTTPException(status_code=409, detail="Organization already exists") from None
        return body.model_dump()

    @app.post("/v1/vendor/sites")
    def create_site(body: SiteCreate, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.site.create")
        if user["evaluation"] and body.organization_id != "evaluation-hospital":
            raise HTTPException(status_code=404, detail="Organization not found")
        with store.lock:
            try:
                store.db.execute("INSERT INTO sites VALUES(?,?,?,?)", (body.site_id, body.organization_id, body.name, now()))
                store.audit(user["user_id"], "created", "site", body.site_id)
                store.db.commit()
            except sqlite3.IntegrityError:
                raise HTTPException(status_code=409, detail="Organization or site invalid") from None
        return body.model_dump()

    @app.post("/v1/vendor/customers")
    def create_customer(body: CustomerCreate, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.account.invite")
        if body.role not in CUSTOMER_ROLES - {"evaluation_operator"}:
            raise HTTPException(status_code=422, detail="Unknown customer role")
        if user["evaluation"] and body.organization_id != "evaluation-hospital":
            raise HTTPException(status_code=404, detail="Organization not found")
        with store.lock:
            if not store.db.execute("SELECT 1 FROM organizations WHERE id=?", (body.organization_id,)).fetchone():
                raise HTTPException(status_code=404, detail="Organization not found")
            user_id = secrets.token_hex(16)
            try:
                store.db.execute("INSERT INTO users(id,email,display_name,password_hash,vendor,must_change_password,role) VALUES(?,?,?,?,0,1,?)",
                                 (user_id, body.email.strip().lower(), body.display_name, password_digest(body.password), body.role))
                store.db.execute("INSERT INTO memberships(user_id,organization_id,role) VALUES(?,?,?)", (user_id, body.organization_id, body.role))
                store.audit(user["user_id"], "customer_provisioned", "user", user_id)
                store.db.commit()
            except sqlite3.IntegrityError:
                store.db.rollback()
                raise HTTPException(status_code=409, detail="Customer account already exists") from None
        return {"user_id": user_id, "organization_id": body.organization_id}

    @app.post("/v1/vendor/customer-invitations")
    def invite_customer(body: CustomerInvite, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.account.invite")
        if body.role not in CUSTOMER_ROLES - {"evaluation_operator"}:
            raise HTTPException(status_code=422, detail="Unknown customer role")
        if user["evaluation"]:
            raise HTTPException(status_code=403, detail="Invitations unavailable in synthetic evaluation")
        email = body.email.strip().lower()
        with store.lock:
            if not store.db.execute("SELECT 1 FROM organizations WHERE id=?", (body.organization_id,)).fetchone():
                raise HTTPException(status_code=404, detail="Organization not found")
            if store.db.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
                raise HTTPException(status_code=409, detail="Account already exists; use membership assignment")
            token = secrets.token_urlsafe(48)
            invitation_id = secrets.token_hex(16)
            expiry = (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()
            store.db.execute("INSERT INTO customer_invitations VALUES(?,?,?,?,?,?,?,?,?,?)", (
                invitation_id, hashlib.sha256(token.encode()).hexdigest(), email, body.display_name,
                body.organization_id, body.role, expiry, None, user["user_id"], now()))
            store.audit(user["user_id"], f"customer_invited:{body.reason}", "invitation", invitation_id)
            store.db.commit()
        return {"invitation_id": invitation_id, "token": token, "expires_at": expiry,
                "delivery": "Provide once through an institution-approved secure channel"}

    @app.post("/v1/auth/accept-invitation")
    def accept_invitation(body: AcceptInvite):
        token_hash = hashlib.sha256(body.token.encode()).hexdigest()
        with store.lock:
            invitation = store.db.execute("SELECT * FROM customer_invitations WHERE token_hash=?", (token_hash,)).fetchone()
            if not invitation or invitation["accepted_at"] or datetime.fromisoformat(invitation["expires_at"]) <= datetime.now(timezone.utc):
                raise HTTPException(status_code=400, detail="Invitation invalid or expired")
            if store.db.execute("SELECT 1 FROM users WHERE email=?", (invitation["email"],)).fetchone():
                raise HTTPException(status_code=409, detail="Account already exists; contact administrator")
            account_id = secrets.token_hex(16)
            try:
                store.db.execute("INSERT INTO users(id,email,display_name,password_hash,vendor,must_change_password,role) VALUES(?,?,?,?,0,0,?)", (
                    account_id, invitation["email"], invitation["display_name"], password_digest(body.password), invitation["role"]))
                store.db.execute("INSERT INTO memberships(user_id,organization_id,role) VALUES(?,?,?)", (
                    account_id, invitation["organization_id"], invitation["role"]))
                store.db.execute("UPDATE customer_invitations SET accepted_at=? WHERE id=? AND accepted_at IS NULL", (now(), invitation["id"]))
                store.audit(account_id, "customer_invitation_accepted", "invitation", invitation["id"])
                store.db.commit()
            except sqlite3.IntegrityError:
                store.db.rollback()
                raise HTTPException(status_code=409, detail="Invitation cannot be accepted") from None
        return {"activated": True, "sign_in_required": True}

    @app.post("/v1/vendor/staff")
    def create_vendor_staff(body: VendorUserCreate, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.staff.provision")
        if body.role not in VENDOR_ROLES - {"evaluation_operator", "root_admin"}:
            raise HTTPException(status_code=422, detail="Unknown vendor staff role")
        if user["evaluation"]:
            raise HTTPException(status_code=403, detail="Staff provisioning disabled in evaluation")
        with store.lock:
            staff_id = secrets.token_hex(16)
            secret = base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=") if os.environ.get("ACCOUNT_REQUIRE_MFA") == "true" else None
            encrypted = _cipher().encrypt(secret.encode()).decode() if secret else None
            try:
                store.db.execute("INSERT INTO users(id,email,display_name,password_hash,vendor,must_change_password,role,mfa_secret) VALUES(?,?,?,?,1,1,?,?)", (staff_id, body.email.strip().lower(), body.display_name, password_digest(body.password), body.role, encrypted))
                store.audit(user["user_id"], "staff_provisioned", "user", staff_id)
                store.db.commit()
            except sqlite3.IntegrityError:
                store.db.rollback()
                raise HTTPException(status_code=409, detail="Account already exists") from None
        return {"user_id": staff_id, "role": body.role, "mfa_provisioning_uri": provisioning_uri(body.email.strip().lower(), secret) if secret else None}

    @app.get("/v1/vendor/staff")
    def vendor_staff(user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.staff.read")
        with store.lock:
            rows = store.db.execute("SELECT id,email,display_name,role,must_change_password FROM users WHERE vendor=1 ORDER BY display_name").fetchall()
        return {"staff": [dict(row) for row in rows]}

    @app.get("/v1/vendor/accounts")
    def account_directory(user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.account.directory")
        if user["evaluation"]:
            raise HTTPException(status_code=403, detail="Production directory unavailable in evaluation")
        with store.lock:
            rows = store.db.execute("SELECT id,email,display_name,vendor,role,disabled,must_change_password FROM users ORDER BY display_name LIMIT 1000").fetchall()
            memberships = store.db.execute("SELECT user_id,organization_id,role FROM memberships").fetchall()
        by_user: dict[str, dict[str, str]] = {}
        for item in memberships:
            by_user.setdefault(item["user_id"], {})[item["organization_id"]] = item["role"]
        return {"accounts": [{**dict(row), "organization_ids": sorted(by_user.get(row["id"], {})), "organization_roles": by_user.get(row["id"], {})} for row in rows]}

    @app.post("/v1/vendor/accounts/{account_id}/memberships")
    def add_membership(account_id: str, body: MembershipChange, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.account.membership.write")
        if body.role not in CUSTOMER_ROLES - {"evaluation_operator"}:
            raise HTTPException(status_code=422, detail="Unknown customer role")
        if user["evaluation"]:
            raise HTTPException(status_code=403, detail="Membership changes unavailable in evaluation")
        with store.lock:
            account = store.db.execute("SELECT vendor,role FROM users WHERE id=?", (account_id,)).fetchone()
            if not account or account["vendor"]:
                raise HTTPException(status_code=404, detail="Customer account not found")
            if not store.db.execute("SELECT 1 FROM organizations WHERE id=?", (body.organization_id,)).fetchone():
                raise HTTPException(status_code=404, detail="Organization not found")
            store.db.execute("INSERT OR IGNORE INTO memberships(user_id,organization_id,role) VALUES(?,?,?)", (account_id, body.organization_id, body.role))
            store.db.execute("UPDATE memberships SET role=? WHERE user_id=? AND organization_id=?", (body.role, account_id, body.organization_id))
            store.db.execute("DELETE FROM sessions WHERE user_id=?", (account_id,))
            store.audit(user["user_id"], f"membership_added:{body.reason}", "user", account_id)
            store.db.commit()
        return {"user_id": account_id, "organization_id": body.organization_id, "role": body.role, "sign_in_again": True}

    @app.delete("/v1/vendor/accounts/{account_id}/memberships/{organization_id}")
    def remove_membership(account_id: str, organization_id: str, reason: str, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.account.membership.write")
        if user["evaluation"]:
            raise HTTPException(status_code=403, detail="Membership changes unavailable in evaluation")
        if len(reason.strip()) < 3:
            raise HTTPException(status_code=422, detail="Reason required")
        with store.lock:
            result = store.db.execute("DELETE FROM memberships WHERE user_id=? AND organization_id=?", (account_id, organization_id))
            if not result.rowcount:
                raise HTTPException(status_code=404, detail="Membership not found")
            store.db.execute("DELETE FROM sessions WHERE user_id=?", (account_id,))
            store.audit(user["user_id"], f"membership_removed:{reason}", "user", account_id)
            store.db.commit()
        return {"removed": True, "sign_in_again": True}

    @app.patch("/v1/vendor/accounts/{account_id}/memberships/{organization_id}")
    def assign_membership_role(account_id: str, organization_id: str, body: MembershipChange, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.account.membership.write")
        if body.role not in CUSTOMER_ROLES - {"evaluation_operator"}:
            raise HTTPException(status_code=422, detail="Unknown customer role")
        if user["evaluation"] or body.organization_id != organization_id:
            raise HTTPException(status_code=403, detail="Membership role change unavailable")
        with store.lock:
            result = store.db.execute("UPDATE memberships SET role=? WHERE user_id=? AND organization_id=? AND EXISTS (SELECT 1 FROM users WHERE id=? AND vendor=0)", (body.role, account_id, organization_id, account_id))
            if not result.rowcount:
                raise HTTPException(status_code=404, detail="Membership not found")
            store.db.execute("DELETE FROM sessions WHERE user_id=?", (account_id,))
            store.audit(user["user_id"], f"membership_role_{body.role}:{body.reason}", "user", account_id)
            store.db.commit()
        return {"user_id": account_id, "organization_id": organization_id, "role": body.role, "sign_in_again": True}

    @app.patch("/v1/vendor/accounts/{account_id}/state")
    def account_state(account_id: str, body: AccountStateChange, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.account.state.write")
        if user["evaluation"] or account_id == user["user_id"]:
            raise HTTPException(status_code=403, detail="Account state change unavailable")
        with store.lock:
            target = store.db.execute("SELECT vendor,role FROM users WHERE id=?", (account_id,)).fetchone()
            if not target or target["role"] == "root_admin":
                raise HTTPException(status_code=404, detail="Account not found")
            store.db.execute("UPDATE users SET disabled=? WHERE id=?", (int(body.disabled), account_id))
            store.db.execute("DELETE FROM sessions WHERE user_id=?", (account_id,))
            store.audit(user["user_id"], f"{'disabled' if body.disabled else 'enabled'}:{body.reason}", "user", account_id)
            store.db.commit()
        return {"user_id": account_id, "disabled": body.disabled, "sessions_revoked": True}

    @app.get("/v1/organizations")
    def organizations(user: dict = Depends(require_user)):
        with store.lock:
            if user["evaluation"]:
                rows = store.db.execute("SELECT id,name,created_at FROM organizations WHERE id='evaluation-hospital'").fetchall()
            elif user["vendor"]:
                rows = store.db.execute("SELECT id,name,created_at FROM organizations ORDER BY name").fetchall()
            else:
                rows = store.db.execute("SELECT o.id,o.name,o.created_at FROM organizations o JOIN memberships m ON m.organization_id=o.id WHERE m.user_id=? ORDER BY o.name", (user["user_id"],)).fetchall()
        return {"organizations": [dict(row) for row in rows]}

    @app.get("/v1/sites")
    def sites(user: dict = Depends(require_user)):
        with store.lock:
            if user["evaluation"]:
                rows = store.db.execute("SELECT id,organization_id,name,created_at FROM sites WHERE organization_id='evaluation-hospital' ORDER BY name").fetchall()
            elif user["vendor"]:
                rows = store.db.execute("SELECT id,organization_id,name,created_at FROM sites ORDER BY name").fetchall()
            else:
                rows = store.db.execute("SELECT s.id,s.organization_id,s.name,s.created_at FROM sites s JOIN memberships m ON m.organization_id=s.organization_id WHERE m.user_id=? ORDER BY s.name", (user["user_id"],)).fetchall()
        return {"sites": [dict(row) for row in rows]}

    @app.post("/v1/vendor/assets")
    def register_asset(body: AssetCreate, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.asset.write")
        if body.kind not in ASSET_KINDS:
            raise HTTPException(status_code=422, detail="Unknown asset kind")
        if body.lifecycle_state not in ASSET_LIFECYCLE:
            raise HTTPException(status_code=422, detail="Unknown asset lifecycle state")
        with store.lock:
            site = store.db.execute("SELECT organization_id FROM sites WHERE id=?", (body.site_id,)).fetchone()
            if not site or (user["evaluation"] and site["organization_id"] != "evaluation-hospital"):
                raise HTTPException(status_code=404, detail="Site not found")
            asset_id, stamp = secrets.token_hex(16), now()
            try:
                store.db.execute(
                    """INSERT INTO assets(id,organization_id,site_id,asset_tag,kind,model,firmware,registered_at,serial_number,warranty_until,lifecycle_state,retired_at,disposition_ref,updated_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (asset_id, site["organization_id"], body.site_id, body.asset_tag, body.kind, body.model, body.firmware, stamp, body.serial_number, body.warranty_until, body.lifecycle_state, None, None, stamp),
                )
                store.audit(user["user_id"], "registered", "asset", asset_id)
                store.db.commit()
            except sqlite3.IntegrityError:
                raise HTTPException(status_code=409, detail="Asset tag already registered") from None
        return {"id": asset_id, "organization_id": site["organization_id"], **body.model_dump(), "lifecycle_state": body.lifecycle_state}

    @app.get("/v1/assets")
    def assets(user: dict = Depends(require_user)):
        if user["vendor"]:
            require_permission(user, "vendor.asset.read")
        with store.lock:
            if user["evaluation"]:
                rows = store.db.execute("SELECT * FROM assets WHERE organization_id='evaluation-hospital' ORDER BY registered_at DESC LIMIT 500").fetchall()
            elif user["vendor"]:
                rows = store.db.execute("SELECT * FROM assets ORDER BY registered_at DESC LIMIT 500").fetchall()
            else:
                rows = store.db.execute("SELECT a.* FROM assets a JOIN memberships m ON m.organization_id=a.organization_id WHERE m.user_id=? ORDER BY a.registered_at DESC LIMIT 500", (user["user_id"],)).fetchall()
        today = datetime.now(timezone.utc).date().isoformat()
        result = []
        for row in rows:
            item = dict(row)
            if not (user["vendor"] or user["evaluation"] or has_permission(user, CUSTOMER_TABLE_PERMISSION["assets"], organization_id=item["organization_id"])):
                continue
            item["warranty_expired"] = bool(item.get("warranty_until") and item["warranty_until"] < today)
            result.append(item)
        return {"assets": result}

    @app.patch("/v1/vendor/assets/{asset_id}")
    def update_asset_lifecycle(asset_id: str, body: AssetLifecycleUpdate, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.asset.write")
        if body.lifecycle_state not in ASSET_LIFECYCLE:
            raise HTTPException(status_code=422, detail="Unknown asset lifecycle state")
        with store.lock:
            row = store.db.execute("SELECT * FROM assets WHERE id=?", (asset_id,)).fetchone()
            if not row or (user["evaluation"] and row["organization_id"] != "evaluation-hospital"):
                raise HTTPException(status_code=404, detail="Asset not found")
            current = row["lifecycle_state"] or "commissioned"
            allowed = ASSET_TRANSITIONS.get(current, set())
            if body.lifecycle_state != current and body.lifecycle_state not in allowed:
                raise HTTPException(status_code=409, detail=f"Cannot move asset from {current} to {body.lifecycle_state}")
            if body.lifecycle_state in {"retired", "disposed"} and not (body.disposition_ref or row["disposition_ref"]):
                raise HTTPException(status_code=422, detail="Disposition reference required for retirement or disposal")
            retired_at = now() if body.lifecycle_state in {"retired", "disposed"} and not row["retired_at"] else row["retired_at"]
            disposition = body.disposition_ref or row["disposition_ref"]
            warranty = body.warranty_until if body.warranty_until is not None else row["warranty_until"]
            store.db.execute(
                "UPDATE assets SET lifecycle_state=?, disposition_ref=?, warranty_until=?, retired_at=?, updated_at=? WHERE id=?",
                (body.lifecycle_state, disposition, warranty, retired_at, now(), asset_id),
            )
            store.audit(user["user_id"], f"lifecycle_{body.lifecycle_state}:{body.reason}", "asset", asset_id)
            store.db.commit()
        return {"id": asset_id, "lifecycle_state": body.lifecycle_state, "disposition_ref": disposition, "retired_at": retired_at}

    @app.post("/v1/vendor/compliance-tasks")
    def create_compliance_task(body: ComplianceCreate, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.compliance.write")
        with store.lock:
            site = store.db.execute("SELECT organization_id FROM sites WHERE id=?", (body.site_id,)).fetchone()
            if not site or (user["evaluation"] and site["organization_id"] != "evaluation-hospital"):
                raise HTTPException(status_code=404, detail="Site not found")
            task_id, stamp = secrets.token_hex(16), now()
            store.db.execute("INSERT INTO compliance_tasks VALUES(?,?,?,?,?,?,?,?,?)", (task_id, site["organization_id"], body.site_id, body.task_type, body.owner, "not_started", None, stamp, stamp))
            store.audit(user["user_id"], "created", "compliance_task", task_id)
            store.db.commit()
        return {"id": task_id, "organization_id": site["organization_id"], **body.model_dump(), "status": "not_started", "evidence_ref": None}

    @app.get("/v1/compliance-tasks")
    def compliance_tasks(user: dict = Depends(require_user)):
        if user["vendor"]:
            require_permission(user, "vendor.compliance.read")
        with store.lock:
            if user["evaluation"]:
                rows = store.db.execute("SELECT * FROM compliance_tasks WHERE organization_id='evaluation-hospital' ORDER BY updated_at DESC LIMIT 500").fetchall()
            elif user["vendor"]:
                rows = store.db.execute("SELECT * FROM compliance_tasks ORDER BY updated_at DESC LIMIT 500").fetchall()
            else:
                rows = store.db.execute("SELECT c.* FROM compliance_tasks c JOIN memberships m ON m.organization_id=c.organization_id WHERE m.user_id=? ORDER BY c.updated_at DESC LIMIT 500", (user["user_id"],)).fetchall()
        return {"tasks": [dict(row) for row in rows if user["vendor"] or user["evaluation"] or has_permission(user, CUSTOMER_TABLE_PERMISSION["compliance_tasks"], organization_id=row["organization_id"])]}

    @app.patch("/v1/vendor/compliance-tasks/{task_id}")
    def update_compliance_task(task_id: str, body: ComplianceUpdate, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.compliance.write")
        if body.status not in COMPLIANCE_STATES:
            raise HTTPException(status_code=422, detail="Unknown compliance status")
        with store.lock:
            row = store.db.execute("SELECT evidence_ref,organization_id FROM compliance_tasks WHERE id=?", (task_id,)).fetchone()
            if not row or (user["evaluation"] and row["organization_id"] != "evaluation-hospital"):
                raise HTTPException(status_code=404, detail="Task not found")
            evidence = body.evidence_ref or row["evidence_ref"]
            if body.status == "approved" and not evidence:
                raise HTTPException(status_code=422, detail="Document evidence reference required before approval")
            store.db.execute("UPDATE compliance_tasks SET status=?,evidence_ref=?,updated_at=? WHERE id=?", (body.status, evidence, now(), task_id))
            store.audit(user["user_id"], "status_changed", "compliance_task", task_id)
            store.db.commit()
        return {"id": task_id, "status": body.status, "evidence_ref": evidence}

    @app.post("/v1/tickets")
    def open_ticket(body: TicketCreate, user: dict = Depends(require_user)):
        if user["must_change_password"]:
            raise HTTPException(status_code=403, detail="Change temporary password first")
        if body.issue_code not in ISSUE_CODES:
            raise HTTPException(status_code=422, detail="Unknown operational issue code")
        with store.lock:
            site = store.db.execute("SELECT organization_id FROM sites WHERE id=?", (body.site_id,)).fetchone()
            if not site or (user["evaluation"] and site["organization_id"] != "evaluation-hospital") or (not user["vendor"] and site["organization_id"] not in user["organization_ids"]):
                raise HTTPException(status_code=404, detail="Site not found")
            if not user["vendor"] and not has_permission(user, "customer.ticket.open", organization_id=site["organization_id"]):
                raise HTTPException(status_code=403, detail="Organization role cannot open support tickets")
            ticket_id, stamp = secrets.token_hex(16), now()
            plan = resolve_support_plan(store, body.site_id)
            target = sla_target_minutes(body.severity, plan["response_target_minutes"] if plan else None)
            due = sla_due_iso(stamp, target)
            store.db.execute(
                """INSERT INTO tickets(id,organization_id,site_id,issue_code,severity,status,opened_by,created_at,updated_at,assigned_to,first_response_at,acknowledged_at,sla_due_at,sla_breached,escalation_level,support_plan_id,sla_target_minutes)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (ticket_id, site["organization_id"], body.site_id, body.issue_code, body.severity, "open", user["user_id"], stamp, stamp, None, None, None, due, 0, 0, plan["id"] if plan else None, target),
            )
            store.audit(user["user_id"], "opened", "ticket", ticket_id)
            store.db.commit()
        return {"id": ticket_id, "organization_id": site["organization_id"], "site_id": body.site_id, "issue_code": body.issue_code, "severity": body.severity, "status": "open", "sla_due_at": due, "sla_target_minutes": target, "support_plan_id": plan["id"] if plan else None}

    @app.get("/v1/tickets")
    def tickets(user: dict = Depends(require_user)):
        if user["vendor"]:
            require_permission(user, "vendor.ticket.read")
        with store.lock:
            if user["evaluation"]:
                rows = store.db.execute("SELECT * FROM tickets WHERE organization_id='evaluation-hospital' ORDER BY updated_at DESC LIMIT 500").fetchall()
            elif user["vendor"]:
                rows = store.db.execute("SELECT * FROM tickets ORDER BY updated_at DESC LIMIT 500").fetchall()
            else:
                rows = store.db.execute("SELECT t.* FROM tickets t JOIN memberships m ON m.organization_id=t.organization_id WHERE m.user_id=? ORDER BY t.updated_at DESC LIMIT 500", (user["user_id"],)).fetchall()
            enriched = []
            for row in rows:
                item = sla_fields(dict(row))
                if not (user["vendor"] or user["evaluation"] or has_permission(user, CUSTOMER_TABLE_PERMISSION["tickets"], organization_id=item["organization_id"])):
                    continue
                if item["sla_breached"] and not row["sla_breached"]:
                    store.db.execute("UPDATE tickets SET sla_breached=1 WHERE id=?", (item["id"],))
                enriched.append(item)
            store.db.commit()
        return {"tickets": enriched}

    @app.patch("/v1/tickets/{ticket_id}")
    def update_ticket(ticket_id: str, body: TicketUpdate, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.ticket.write")
        if body.status not in STATUSES:
            raise HTTPException(status_code=422, detail="Unknown ticket status")
        with store.lock:
            found = store.db.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
            if not found or (user["evaluation"] and found["organization_id"] != "evaluation-hospital"):
                raise HTTPException(status_code=404, detail="Ticket not found")
            stamp = now()
            first_response = found["first_response_at"]
            acknowledged = found["acknowledged_at"]
            if body.status in {"acknowledged", "in_progress", "waiting_for_hospital", "waiting_for_vendor", "resolved", "closed"} and not first_response:
                first_response = stamp
            if body.status == "acknowledged" and not acknowledged:
                acknowledged = stamp
            escalation = found["escalation_level"] or 0
            if body.escalate:
                escalation = escalation + 1
            breached = found["sla_breached"]
            if found["sla_due_at"] and first_response:
                breached = int(datetime.fromisoformat(first_response) > datetime.fromisoformat(found["sla_due_at"]))
            store.db.execute(
                """UPDATE tickets SET status=?, updated_at=?, assigned_to=COALESCE(?,assigned_to), first_response_at=?, acknowledged_at=?,
                   escalation_level=?, sla_breached=? WHERE id=?""",
                (body.status, stamp, body.assigned_to, first_response, acknowledged, escalation, breached, ticket_id),
            )
            action = "escalated" if body.escalate else "status_changed"
            note = f"{action}:{body.reason}" if body.reason else action
            store.audit(user["user_id"], note, "ticket", ticket_id)
            store.db.commit()
            updated = dict(store.db.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone())
        return sla_fields(updated)

    @app.get("/v1/tickets/sla-breaches")
    def ticket_sla_breaches(user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.ticket.read")
        with store.lock:
            rows = store.db.execute("SELECT * FROM tickets ORDER BY updated_at DESC LIMIT 500").fetchall()
        return {"tickets": [sla_fields(dict(row)) for row in rows if sla_fields(dict(row))["sla_breached"]]}

    @app.get("/v1/vendor/audit")
    def audit_events(user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.audit.read")
        with store.lock:
            rows = store.db.execute("SELECT id,actor_id,action,object_type,object_id,at,event_hash FROM audit_events ORDER BY id DESC LIMIT 500").fetchall()
        return {"integrity_ok": store.audit_integrity(), "events": [dict(row) for row in rows]}

    @app.post("/v1/portal/organizations/{organization_id}/invitations")
    def customer_invite_member(organization_id: str, body: CustomerMemberInvite, user: dict = Depends(require_user)):
        if body.organization_id != organization_id:
            raise HTTPException(status_code=422, detail="Organization mismatch")
        if user["vendor"] and not user["evaluation"]:
            raise HTTPException(status_code=403, detail="Use vendor invitation endpoints")
        require_permission(user, "customer.member.invite", organization_id=organization_id)
        if body.role not in CUSTOMER_ROLES - {"evaluation_operator", "customer_owner"}:
            raise HTTPException(status_code=422, detail="Customer owners may invite non-owner roles only")
        if user["evaluation"]:
            raise HTTPException(status_code=403, detail="Invitations unavailable in synthetic evaluation")
        email = body.email.strip().lower()
        with store.lock:
            if organization_id not in user["organization_ids"]:
                raise HTTPException(status_code=404, detail="Organization not found")
            if store.db.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
                raise HTTPException(status_code=409, detail="Account already exists; request vendor membership assignment")
            token = secrets.token_urlsafe(48)
            invitation_id = secrets.token_hex(16)
            expiry = (datetime.now(timezone.utc) + timedelta(hours=48)).isoformat()
            store.db.execute("INSERT INTO customer_invitations VALUES(?,?,?,?,?,?,?,?,?,?)", (
                invitation_id, hashlib.sha256(token.encode()).hexdigest(), email, body.display_name,
                organization_id, body.role, expiry, None, user["user_id"], now()))
            store.audit(user["user_id"], f"customer_member_invited:{body.reason}", "invitation", invitation_id)
            store.db.commit()
        return {"invitation_id": invitation_id, "token": token, "expires_at": expiry,
                "delivery": "Provide once through an institution-approved secure channel"}

    @app.get("/v1/portal/organizations/{organization_id}/members")
    def customer_members(organization_id: str, user: dict = Depends(require_user)):
        require_permission(user, "customer.member.read", organization_id=organization_id)
        with store.lock:
            if not user["evaluation"] and organization_id not in user["organization_ids"] and not user["vendor"]:
                raise HTTPException(status_code=404, detail="Organization not found")
            rows = store.db.execute(
                "SELECT u.id,u.email,u.display_name,m.role,u.disabled FROM memberships m JOIN users u ON u.id=m.user_id WHERE m.organization_id=? ORDER BY u.display_name",
                (organization_id,),
            ).fetchall()
        return {"members": [dict(row) for row in rows]}

    @app.post("/v1/vendor/approvals")
    def create_approval(body: ApprovalCreate, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.account.membership.write")
        if user["evaluation"]:
            raise HTTPException(status_code=403, detail="Approvals unavailable in evaluation")
        approval_id = secrets.token_hex(16)
        with store.lock:
            store.db.execute(
                "INSERT INTO approval_requests VALUES(?,?,?,?,?,?,?,?,?,?)",
                (approval_id, body.kind, json.dumps(body.payload, separators=(",", ":")), "pending", user["user_id"], None, body.reason, None, now(), None),
            )
            store.audit(user["user_id"], f"approval_requested:{body.kind}", "approval", approval_id)
            store.db.commit()
        return {"id": approval_id, "status": "pending", "kind": body.kind}

    @app.get("/v1/vendor/approvals")
    def list_approvals(user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.approval.decide")
        with store.lock:
            rows = store.db.execute("SELECT id,kind,payload_json,status,requested_by,decided_by,reason,decision_reason,created_at,decided_at FROM approval_requests ORDER BY created_at DESC LIMIT 200").fetchall()
        return {"approvals": [{**dict(row), "payload": json.loads(row["payload_json"])} for row in rows]}

    @app.patch("/v1/vendor/approvals/{approval_id}")
    def decide_approval(approval_id: str, body: ApprovalDecision, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.approval.decide")
        if user["evaluation"]:
            raise HTTPException(status_code=403, detail="Approvals unavailable in evaluation")
        with store.lock:
            row = store.db.execute("SELECT * FROM approval_requests WHERE id=?", (approval_id,)).fetchone()
            if not row or row["status"] != "pending":
                raise HTTPException(status_code=404, detail="Approval not found")
            if row["requested_by"] == user["user_id"] and user["role"] != "root_admin":
                raise HTTPException(status_code=403, detail="Requester cannot decide their own approval")
            payload = json.loads(row["payload_json"])
            if body.status == "approved" and row["kind"] == "customer_role_change":
                account_id = payload.get("account_id")
                organization_id = payload.get("organization_id")
                new_role = payload.get("role")
                if not account_id or not organization_id or new_role not in CUSTOMER_ROLES - {"evaluation_operator"}:
                    raise HTTPException(status_code=422, detail="Invalid approval payload")
                result = store.db.execute(
                    "UPDATE memberships SET role=? WHERE user_id=? AND organization_id=?",
                    (new_role, account_id, organization_id),
                )
                if not result.rowcount:
                    raise HTTPException(status_code=404, detail="Membership not found")
                store.db.execute("DELETE FROM sessions WHERE user_id=?", (account_id,))
            store.db.execute(
                "UPDATE approval_requests SET status=?,decided_by=?,decision_reason=?,decided_at=? WHERE id=?",
                (body.status, user["user_id"], body.reason, now(), approval_id),
            )
            store.audit(user["user_id"], f"approval_{body.status}:{row['kind']}", "approval", approval_id)
            store.db.commit()
        return {"id": approval_id, "status": body.status}

    install_commercial_routes(app, store, require_user, require_vendor)
    install_operations_routes(app, store, require_user, require_vendor)
    install_document_routes(app, store, require_user, require_vendor)
    install_governance_routes(app, store, require_user, require_vendor)
    install_partnership_routes(app, store, require_user, require_vendor)

    @app.get("/health")
    def health():
        return {"status": "ok", "patient_data": "none"}

    return app


app = create_app(os.environ.get("ACCOUNT_DB", ":memory:"))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["bootstrap-vendor", "enroll-mfa"])
    parser.add_argument("--email", required=True)
    parser.add_argument("--name")
    args = parser.parse_args()
    db = os.environ.get("ACCOUNT_DB")
    if not db or db == ":memory:":
        raise SystemExit("Set ACCOUNT_DB to a persistent account database path")
    accounts = AccountStore(db)
    if args.command == "bootstrap-vendor":
        if not args.name:
            raise SystemExit("--name is required for bootstrap-vendor")
        password = getpass.getpass("Initial vendor password: ")
        uri = accounts.create_vendor(args.email, args.name, password)
        print("Vendor administrator created")
    else:
        secret = base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")
        encrypted = _cipher().encrypt(secret.encode()).decode()
        with accounts.lock:
            row = accounts.db.execute("SELECT id FROM users WHERE email=? AND vendor=1", (args.email.strip().lower(),)).fetchone()
            if not row:
                raise SystemExit("Vendor account not found")
            accounts.db.execute("UPDATE users SET mfa_secret=? WHERE id=?", (encrypted, row["id"]))
            accounts.audit("local_operator", "mfa_enrolled", "user", row["id"])
            accounts.db.execute("DELETE FROM sessions WHERE user_id=?", (row["id"],))
            accounts.db.commit()
        uri = provisioning_uri(args.email.strip().lower(), secret)
        print("Vendor MFA enrolled; existing sessions revoked")
    if uri:
        print("Store this provisioning URI in an authenticator now; it will not be shown again:")
        print(uri)
