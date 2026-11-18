"""Patient-free deployment, service and controlled offboarding records."""

from __future__ import annotations

import json
import secrets
from datetime import date, datetime, timezone
from typing import Callable

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DeploymentCreate(Strict):
    site_id: str
    environment: str = Field(pattern="^(hospital_local|evaluation|staging)$")
    release_version: str = Field(min_length=2, max_length=80)
    installation_ref: str = Field(min_length=3, max_length=160)
    status: str = Field(pattern="^(planned|commissioning|silent_evaluation|approved_operation|maintenance|retired)$")


class SupportPlanCreate(Strict):
    site_id: str
    scope: str = Field(min_length=3, max_length=500)
    support_hours: str = Field(min_length=3, max_length=160)
    response_target_minutes: int | None = Field(default=None, ge=1, le=10080)
    onsite_visits_included: int = Field(default=0, ge=0, le=1000)
    escalation_contact_role: str = Field(min_length=2, max_length=100)
    exclusions: str = Field(min_length=3, max_length=500)
    contract_id: str | None = None


class ServiceVisitCreate(Strict):
    site_id: str
    asset_id: str | None = None
    visit_on: date
    work_code: str = Field(pattern="^(installation|maintenance|repair|training|inspection|backup_test)$")
    engineer_role: str = Field(min_length=2, max_length=100)
    work_summary: str = Field(min_length=3, max_length=500)
    acknowledgement_ref: str | None = Field(default=None, max_length=160)
    next_action: str | None = Field(default=None, max_length=240)


class TrainingCreate(Strict):
    site_id: str
    role_group: str = Field(pattern="^(clinician|nurse|hospital_admin|clinical_it|other)$")
    session_on: date
    completion_ref: str = Field(min_length=3, max_length=160)
    trainer_role: str = Field(min_length=2, max_length=100)


class OffboardingCreate(Strict):
    site_id: str
    reason: str = Field(min_length=3, max_length=500)
    authorization_ref: str = Field(min_length=3, max_length=160)


class OffboardingCheck(Strict):
    check: str
    evidence_ref: str = Field(min_length=3, max_length=160)


class OffboardingApproval(Strict):
    reason: str = Field(min_length=3, max_length=240)


CHECKS = (
    "contract_scope", "retention_and_hold", "export_return", "backup_archive",
    "credential_revocation", "connector_shutdown", "hardware_disposition", "hospital_decommission_plan",
)


def install_operations_routes(app: FastAPI, store, require_user: Callable, require_vendor: Callable) -> None:
    with store.lock:
        store.db.executescript("""
            CREATE TABLE IF NOT EXISTS deployments (id TEXT PRIMARY KEY,organization_id TEXT NOT NULL REFERENCES organizations(id),site_id TEXT NOT NULL REFERENCES sites(id),environment TEXT NOT NULL,release_version TEXT NOT NULL,installation_ref TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS support_plans (id TEXT PRIMARY KEY,organization_id TEXT NOT NULL REFERENCES organizations(id),site_id TEXT NOT NULL REFERENCES sites(id),contract_id TEXT REFERENCES contracts(id),scope TEXT NOT NULL,support_hours TEXT NOT NULL,response_target_minutes INTEGER,onsite_visits_included INTEGER NOT NULL,escalation_contact_role TEXT NOT NULL,exclusions TEXT NOT NULL,created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS service_visits (id TEXT PRIMARY KEY,organization_id TEXT NOT NULL REFERENCES organizations(id),site_id TEXT NOT NULL REFERENCES sites(id),asset_id TEXT REFERENCES assets(id),visit_on TEXT NOT NULL,work_code TEXT NOT NULL,engineer_role TEXT NOT NULL,work_summary TEXT NOT NULL,acknowledgement_ref TEXT,next_action TEXT,created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS training_records (id TEXT PRIMARY KEY,organization_id TEXT NOT NULL REFERENCES organizations(id),site_id TEXT NOT NULL REFERENCES sites(id),role_group TEXT NOT NULL,session_on TEXT NOT NULL,completion_ref TEXT NOT NULL,trainer_role TEXT NOT NULL,created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS offboarding_requests (id TEXT PRIMARY KEY,organization_id TEXT NOT NULL REFERENCES organizations(id),site_id TEXT NOT NULL REFERENCES sites(id),reason TEXT NOT NULL,authorization_ref TEXT NOT NULL,status TEXT NOT NULL,requested_by TEXT NOT NULL,checks_json TEXT NOT NULL,first_approver TEXT,second_approver TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
        """)
        store.db.commit()

    def role(user: dict, *allowed: str) -> None:
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
        if not user["vendor"] and user.get("_required_customer_roles") and user["organization_roles"].get(org_id) not in user["_required_customer_roles"]:
            raise HTTPException(status_code=403, detail="Organization role does not permit this action")

    def site_org(site_id: str, user: dict) -> str:
        row = store.db.execute("SELECT organization_id FROM sites WHERE id=?", (site_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Site not found")
        check_org(user, row["organization_id"])
        return row["organization_id"]

    def listed(table: str, user: dict) -> list[dict]:
        from permissions import has_permission

        with store.lock:
            if user["evaluation"]:
                rows = store.db.execute(f"SELECT * FROM {table} WHERE organization_id=? ORDER BY created_at DESC LIMIT 500", ("evaluation-hospital",)).fetchall()
            elif user["vendor"]:
                rows = store.db.execute(f"SELECT * FROM {table} ORDER BY created_at DESC LIMIT 500").fetchall()
            else:
                rows = store.db.execute(f"SELECT * FROM {table} WHERE organization_id IN (SELECT organization_id FROM memberships WHERE user_id=?) ORDER BY created_at DESC LIMIT 500", (user["user_id"],)).fetchall()
        customer_read_permissions = {
            "deployments": "customer.licence.read",
            "support_plans": "customer.ticket.read",
            "service_visits": "customer.asset.read",
            "training_records": "customer.training.read",
            "offboarding_requests": "customer.offboarding.request",
        }
        return [
            dict(row)
            for row in rows
            if user["vendor"]
            or user["evaluation"]
            or has_permission(user, customer_read_permissions.get(table, "customer.org.read"), organization_id=row["organization_id"])
        ]

    def get_offboarding(request_id: str, user: dict) -> dict:
        row = store.db.execute("SELECT * FROM offboarding_requests WHERE id=?", (request_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Request not found")
        result = dict(row)
        check_org(user, result["organization_id"])
        return result

    @app.post("/v1/vendor/deployments")
    def create_deployment(body: DeploymentCreate, user: dict = Depends(require_vendor)):
        role(user, "deployment_engineer", "platform_admin")
        with store.lock:
            org = site_org(body.site_id, user)
            record_id = secrets.token_hex(16)
            store.db.execute("INSERT INTO deployments VALUES(?,?,?,?,?,?,?,?)", (record_id, org, body.site_id, body.environment, body.release_version, body.installation_ref, body.status, stamp()))
            store.audit(user["user_id"], "registered", "deployment", record_id)
            store.db.commit()
        return {"id": record_id, "organization_id": org, **body.model_dump()}

    @app.get("/v1/deployments")
    def deployments(user: dict = Depends(require_user)):
        return {"deployments": listed("deployments", user)}

    @app.post("/v1/vendor/support-plans")
    def create_support_plan(body: SupportPlanCreate, user: dict = Depends(require_vendor)):
        role(user, "support_engineer", "platform_admin")
        with store.lock:
            org = site_org(body.site_id, user)
            if body.contract_id:
                contract = store.db.execute("SELECT organization_id,site_id,status FROM contracts WHERE id=?", (body.contract_id,)).fetchone()
                if not contract or contract["organization_id"] != org or contract["site_id"] != body.site_id or contract["status"] != "signed":
                    raise HTTPException(status_code=409, detail="Support plan requires a signed same-site contract")
            record_id = secrets.token_hex(16)
            store.db.execute("INSERT INTO support_plans VALUES(?,?,?,?,?,?,?,?,?,?,?)", (record_id, org, body.site_id, body.contract_id, body.scope, body.support_hours, body.response_target_minutes, body.onsite_visits_included, body.escalation_contact_role, body.exclusions, stamp()))
            store.audit(user["user_id"], "registered", "support_plan", record_id)
            store.db.commit()
        return {"id": record_id, "organization_id": org, **body.model_dump()}

    @app.get("/v1/support-plans")
    def support_plans(user: dict = Depends(require_user)):
        return {"support_plans": listed("support_plans", user)}

    @app.post("/v1/vendor/service-visits")
    def create_service_visit(body: ServiceVisitCreate, user: dict = Depends(require_vendor)):
        role(user, "support_engineer", "deployment_engineer")
        with store.lock:
            org = site_org(body.site_id, user)
            if body.asset_id:
                asset = store.db.execute("SELECT site_id FROM assets WHERE id=?", (body.asset_id,)).fetchone()
                if not asset or asset["site_id"] != body.site_id:
                    raise HTTPException(status_code=409, detail="Asset is not registered at this site")
            record_id = secrets.token_hex(16)
            store.db.execute("INSERT INTO service_visits VALUES(?,?,?,?,?,?,?,?,?,?,?)", (record_id, org, body.site_id, body.asset_id, str(body.visit_on), body.work_code, body.engineer_role, body.work_summary, body.acknowledgement_ref, body.next_action, stamp()))
            store.audit(user["user_id"], "recorded", "service_visit", record_id)
            store.db.commit()
        return {"id": record_id, "organization_id": org, **body.model_dump()}

    @app.get("/v1/service-visits")
    def service_visits(user: dict = Depends(require_user)):
        return {"service_visits": listed("service_visits", user)}

    @app.post("/v1/vendor/training")
    def create_training(body: TrainingCreate, user: dict = Depends(require_vendor)):
        role(user, "support_engineer", "deployment_engineer")
        with store.lock:
            org = site_org(body.site_id, user)
            record_id = secrets.token_hex(16)
            store.db.execute("INSERT INTO training_records VALUES(?,?,?,?,?,?,?,?)", (record_id, org, body.site_id, body.role_group, str(body.session_on), body.completion_ref, body.trainer_role, stamp()))
            store.audit(user["user_id"], "recorded", "training", record_id)
            store.db.commit()
        return {"id": record_id, "organization_id": org, **body.model_dump()}

    @app.get("/v1/training")
    def training(user: dict = Depends(require_user)):
        return {"training": listed("training_records", user)}

    @app.post("/v1/offboarding")
    def request_offboarding(body: OffboardingCreate, user: dict = Depends(require_user)):
        if user["must_change_password"]:
            raise HTTPException(status_code=403, detail="Change temporary password first")
        if not user["vendor"]:
            role(user, "customer_owner")
        else:
            role(user, "platform_admin")
        with store.lock:
            org = site_org(body.site_id, user)
            request_id, at = secrets.token_hex(16), stamp()
            store.db.execute("INSERT INTO offboarding_requests VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (request_id, org, body.site_id, body.reason, body.authorization_ref, "checks_pending", user["user_id"], json.dumps({}), None, None, at, at))
            store.audit(user["user_id"], "requested", "offboarding", request_id)
            store.db.commit()
        return {"id": request_id, "status": "checks_pending", "required_checks": CHECKS}

    @app.get("/v1/offboarding")
    def offboarding(user: dict = Depends(require_user)):
        rows = listed("offboarding_requests", user)
        for row in rows:
            row["checks"] = json.loads(row.pop("checks_json"))
        return {"requests": rows, "required_checks": CHECKS}

    @app.post("/v1/vendor/offboarding/{request_id}/checks")
    def record_check(request_id: str, body: OffboardingCheck, user: dict = Depends(require_vendor)):
        role(user, "security_compliance", "platform_admin")
        if body.check not in CHECKS:
            raise HTTPException(status_code=422, detail="Unknown offboarding check")
        with store.lock:
            request = get_offboarding(request_id, user)
            if request["first_approver"]:
                raise HTTPException(status_code=409, detail="Checks locked after approval begins")
            checks = json.loads(request["checks_json"])
            checks[body.check] = {"evidence_ref": body.evidence_ref, "actor": user["user_id"], "at": stamp()}
            store.db.execute("UPDATE offboarding_requests SET checks_json=?,updated_at=? WHERE id=?", (json.dumps(checks), stamp(), request_id))
            store.audit(user["user_id"], f"check_{body.check}", "offboarding", request_id)
            store.db.commit()
        return {"id": request_id, "completed_checks": sorted(checks)}

    @app.post("/v1/vendor/offboarding/{request_id}/approve")
    def approve_offboarding(request_id: str, body: OffboardingApproval, user: dict = Depends(require_vendor)):
        role(user, "root_admin", "security_compliance")
        if user["evaluation"]:
            raise HTTPException(status_code=403, detail="Destructive approvals disabled in synthetic evaluation")
        with store.lock:
            request = get_offboarding(request_id, user)
            if request["requested_by"] == user["user_id"]:
                raise HTTPException(status_code=403, detail="Requester cannot approve")
            checks = json.loads(request["checks_json"])
            if set(checks) != set(CHECKS):
                raise HTTPException(status_code=409, detail="All offboarding checks need evidence")
            if request["second_approver"]:
                raise HTTPException(status_code=409, detail="Already approved")
            if request["first_approver"] == user["user_id"]:
                raise HTTPException(status_code=409, detail="Second approval requires a different user")
            field = "second_approver" if request["first_approver"] else "first_approver"
            status = "ready_for_hospital_execution" if request["first_approver"] else "awaiting_second_approval"
            store.db.execute(f"UPDATE offboarding_requests SET {field}=?,status=?,updated_at=? WHERE id=?", (user["user_id"], status, stamp(), request_id))
            store.audit(user["user_id"], f"approved_{field}:{body.reason}", "offboarding", request_id)
            store.db.commit()
        return {"id": request_id, "status": status, "hospital_data_deleted": False}
