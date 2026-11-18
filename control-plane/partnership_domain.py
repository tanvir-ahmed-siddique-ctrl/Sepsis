"""Hospital partnership, consultation, FDE delivery and education workflows.

Vendor/customer metadata only. No clinical patient records. Pricing figures are
never baked in; quotations remain configurable commercial records.
"""

from __future__ import annotations

import json
import secrets
from datetime import date, datetime, timezone
from typing import Callable

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from permissions import has_permission, require_permission


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


READINESS_TIERS = {"foundation", "connected", "advanced", "unspecified"}
ORG_SIZES = {"clinic", "small", "medium", "large", "tertiary", "academic", "specialist", "group", "unspecified"}
RELATIONSHIP_STATUSES = {
    "prospect", "discovery", "assessment", "technical_feasibility", "proposal", "contracted",
    "implementing", "evaluating", "governed_production", "managed_services", "suspended", "closed",
}
OPPORTUNITY_STAGES = {
    "new_inquiry", "qualification", "discovery_scheduled", "discovery_completed", "site_readiness",
    "technical_feasibility", "proposal_preparation", "proposal_sent", "commercial_legal_review",
    "agreement_pending", "implementation", "retrospective_evaluation", "silent_evaluation",
    "governance_signoff", "governed_production", "renewal_or_expansion", "on_hold", "not_qualified", "closed_lost",
}
CONSULTATION_PURPOSES = {
    "clinical_workflow", "hospital_it", "infrastructure", "equipment_connectivity",
    "site_readiness", "deployment_planning", "managed_it", "commercial", "education",
}
CONSULTATION_STATUSES = {"pending", "assigned", "confirmed", "declined", "rescheduled", "completed", "cancelled"}
CHECK_STATES = {"not_started", "in_progress", "requires_evidence", "blocked", "submitted", "approved", "rejected"}
FDE_CATEGORIES = {
    "site_readiness", "infrastructure_improvement", "equipment_connectivity",
    "hospital_it_implementation", "clinical_platform_integration",
    "clinical_intelligence_evaluation", "managed_technology_services",
}
FDE_STATUSES = {"planned", "active", "blocked", "awaiting_hospital", "completed", "cancelled"}
EVENT_TYPES = {
    "internal_training", "hospital_hosted_training", "free_educational_seminar",
    "professional_workshop", "technical_workshop", "university_collaboration", "conference_participation",
}
PROPOSAL_STATUSES = {"draft", "internal_review", "issued", "accepted", "rejected", "expired", "superseded"}
OWNERSHIP_MODELS = {"hospital_owned", "supplier_provided", "partner_managed", "unspecified"}


class ConsultationCreate(Strict):
    organization: str = Field(min_length=2, max_length=160)
    contact_name: str = Field(min_length=2, max_length=120)
    work_email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    job_title: str = Field(min_length=2, max_length=120)
    department: str | None = Field(default=None, max_length=120)
    country: str = Field(min_length=2, max_length=80)
    location: str = Field(min_length=2, max_length=160)
    hospital_type: str = Field(min_length=2, max_length=80)
    organization_size: str = "unspecified"
    readiness_self_report: str = "unspecified"
    purpose: str
    preferred_dates: str = Field(min_length=3, max_length=500)
    modality: str = Field(pattern="^(online|in_person|either)$")
    message: str | None = Field(default=None, max_length=2000)
    consent: bool
    website: str = Field(default="", max_length=0)


class ConsultationUpdate(Strict):
    status: str
    assigned_to: str | None = Field(default=None, max_length=120)
    organization_id: str | None = None
    site_id: str | None = None
    opportunity_id: str | None = None
    agenda: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=4000)
    next_action: str | None = Field(default=None, max_length=500)
    follow_up_date: date | None = None
    confirmed_at: str | None = None
    reason: str = Field(min_length=3, max_length=240)


class OpportunityCreate(Strict):
    name: str = Field(min_length=2, max_length=160)
    organization_id: str | None = None
    site_id: str | None = None
    primary_contact: str = Field(min_length=2, max_length=160)
    owner: str = Field(min_length=2, max_length=120)
    organization_size: str = "unspecified"
    readiness_tier: str = "unspecified"
    next_action: str = Field(min_length=2, max_length=500)
    due_on: date | None = None
    consultation_id: str | None = None
    lead_id: str | None = None


class OpportunityUpdate(Strict):
    stage: str
    next_action: str = Field(min_length=2, max_length=500)
    due_on: date | None = None
    owner: str | None = Field(default=None, max_length=120)
    organization_id: str | None = None
    site_id: str | None = None
    readiness_tier: str | None = None
    organization_size: str | None = None
    notes: str | None = Field(default=None, max_length=4000)
    reason: str = Field(min_length=3, max_length=240)


class OrgProfileUpdate(Strict):
    display_name: str | None = Field(default=None, min_length=2, max_length=160)
    organization_type: str | None = Field(default=None, max_length=80)
    organization_size: str | None = None
    readiness_tier: str | None = None
    relationship_status: str | None = None
    country: str | None = Field(default=None, max_length=80)
    primary_contact: str | None = Field(default=None, max_length=160)
    clinical_owner: str | None = Field(default=None, max_length=160)
    it_owner: str | None = Field(default=None, max_length=160)
    procurement_owner: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=4000)
    reason: str = Field(min_length=3, max_length=240)


class SiteProfileUpdate(Strict):
    address: str | None = Field(default=None, max_length=300)
    country: str | None = Field(default=None, max_length=80)
    timezone: str | None = Field(default=None, max_length=80)
    units_summary: str | None = Field(default=None, max_length=500)
    bed_scope: int | None = Field(default=None, ge=0, le=100000)
    site_owner: str | None = Field(default=None, max_length=160)
    deployment_lead: str | None = Field(default=None, max_length=160)
    environment_status: str | None = Field(default=None, max_length=80)
    governance_state: str | None = Field(default=None, max_length=80)
    service_plan: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=4000)
    reason: str = Field(min_length=3, max_length=240)


class FdeProjectCreate(Strict):
    organization_id: str
    site_id: str
    title: str = Field(min_length=3, max_length=160)
    category: str
    deployment_lead: str = Field(min_length=2, max_length=120)
    scope: str = Field(min_length=3, max_length=2000)
    start_on: date | None = None
    target_on: date | None = None
    opportunity_id: str | None = None


class FdeProjectUpdate(Strict):
    status: str
    deployment_lead: str | None = Field(default=None, max_length=120)
    next_action: str | None = Field(default=None, max_length=500)
    blockers: str | None = Field(default=None, max_length=2000)
    milestones_json: str | None = Field(default=None, max_length=8000)
    reason: str = Field(min_length=3, max_length=240)


class ReadinessItemUpdate(Strict):
    state: str
    evidence_ref: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=1000)
    reason: str = Field(min_length=3, max_length=240)


class EquipmentCreate(Strict):
    organization_id: str
    site_id: str
    category: str = Field(min_length=2, max_length=80)
    manufacturer: str | None = Field(default=None, max_length=120)
    model: str = Field(min_length=2, max_length=120)
    quantity: int = Field(ge=1, le=100000)
    ownership_model: str = "unspecified"
    procurement_status: str = Field(default="identified", max_length=80)
    supplier_ref: str | None = Field(default=None, max_length=160)
    warranty_until: date | None = None
    notes: str | None = Field(default=None, max_length=1000)


class EducationEventCreate(Strict):
    title: str = Field(min_length=3, max_length=160)
    event_type: str
    objectives: str = Field(min_length=3, max_length=2000)
    host_institution: str | None = Field(default=None, max_length=160)
    event_on: date
    location: str | None = Field(default=None, max_length=200)
    format: str = Field(pattern="^(online|in_person|hybrid)$")
    speaker: str | None = Field(default=None, max_length=160)
    audience: str = Field(min_length=2, max_length=200)
    organization_id: str | None = None
    included_complimentary: bool = False


class PartnershipPlanCreate(Strict):
    organization_id: str
    horizon_years: int = Field(ge=1, le=12, default=8)
    year_1_focus: str = Field(min_length=3, max_length=1000)
    years_2_3_focus: str = Field(min_length=3, max_length=1000)
    years_4_5_focus: str = Field(min_length=3, max_length=1000)
    years_6_8_focus: str = Field(min_length=3, max_length=1000)
    notes: str | None = Field(default=None, max_length=4000)


class ProposalCreate(Strict):
    organization_id: str
    site_id: str
    opportunity_id: str | None = None
    title: str = Field(min_length=3, max_length=160)
    executive_summary: str = Field(min_length=3, max_length=4000)
    scope_json: str = Field(min_length=2, max_length=20000)
    assumptions: str = Field(min_length=3, max_length=4000)
    exclusions: str = Field(min_length=3, max_length=4000)
    timeline_notes: str = Field(min_length=3, max_length=4000)
    valid_until: date


class ProposalUpdate(Strict):
    status: str
    reason: str = Field(min_length=3, max_length=240)


DEFAULT_READINESS_ITEMS = [
    ("network_availability", "Network availability"),
    ("server_workstation_inventory", "Server and workstation inventory"),
    ("storage_backup", "Storage and backup readiness"),
    ("data_source_inventory", "Data-source inventory"),
    ("his_lis_ownership", "HIS/LIS/monitor ownership"),
    ("device_inventory", "Medical device and equipment inventory"),
    ("interface_types", "Available interface types"),
    ("timestamp_unit_consistency", "Timestamp and unit consistency"),
    ("sandbox_availability", "Test/sandbox availability"),
    ("security_requirements", "Network and security requirements"),
    ("local_compute", "Local server/VM readiness"),
    ("identity_access", "Identity and access requirements"),
    ("privacy_security_review", "Privacy/security review"),
    ("clinical_governance_owners", "Clinical governance owners"),
    ("procurement_permissions", "Procurement and deployment permissions"),
    ("technical_staffing", "Technical staffing and support capacity"),
]


def install_partnership_routes(app: FastAPI, store, require_user: Callable, require_vendor: Callable) -> None:
    with store.lock:
        store.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS consultation_requests (
              id TEXT PRIMARY KEY,
              organization_name TEXT NOT NULL,
              contact_name TEXT NOT NULL,
              email TEXT NOT NULL,
              job_title TEXT NOT NULL,
              department TEXT,
              country TEXT NOT NULL,
              location TEXT NOT NULL,
              hospital_type TEXT NOT NULL,
              organization_size TEXT NOT NULL,
              readiness_self_report TEXT NOT NULL,
              purpose TEXT NOT NULL,
              preferred_dates TEXT NOT NULL,
              modality TEXT NOT NULL,
              message TEXT,
              status TEXT NOT NULL,
              assigned_to TEXT,
              organization_id TEXT REFERENCES organizations(id),
              site_id TEXT REFERENCES sites(id),
              opportunity_id TEXT,
              agenda TEXT,
              notes TEXT,
              next_action TEXT,
              follow_up_date TEXT,
              confirmed_at TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS opportunities (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              organization_id TEXT REFERENCES organizations(id),
              site_id TEXT REFERENCES sites(id),
              primary_contact TEXT NOT NULL,
              owner TEXT NOT NULL,
              stage TEXT NOT NULL,
              organization_size TEXT NOT NULL,
              readiness_tier TEXT NOT NULL,
              next_action TEXT NOT NULL,
              due_on TEXT,
              consultation_id TEXT,
              lead_id TEXT,
              notes TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS organization_profiles (
              organization_id TEXT PRIMARY KEY REFERENCES organizations(id),
              display_name TEXT,
              organization_type TEXT,
              organization_size TEXT NOT NULL DEFAULT 'unspecified',
              readiness_tier TEXT NOT NULL DEFAULT 'unspecified',
              relationship_status TEXT NOT NULL DEFAULT 'prospect',
              country TEXT,
              primary_contact TEXT,
              clinical_owner TEXT,
              it_owner TEXT,
              procurement_owner TEXT,
              notes TEXT,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS site_profiles (
              site_id TEXT PRIMARY KEY REFERENCES sites(id),
              organization_id TEXT NOT NULL REFERENCES organizations(id),
              address TEXT,
              country TEXT,
              timezone TEXT,
              units_summary TEXT,
              bed_scope INTEGER,
              site_owner TEXT,
              deployment_lead TEXT,
              environment_status TEXT,
              governance_state TEXT,
              service_plan TEXT,
              notes TEXT,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS fde_projects (
              id TEXT PRIMARY KEY,
              organization_id TEXT NOT NULL REFERENCES organizations(id),
              site_id TEXT NOT NULL REFERENCES sites(id),
              opportunity_id TEXT,
              title TEXT NOT NULL,
              category TEXT NOT NULL,
              status TEXT NOT NULL,
              deployment_lead TEXT NOT NULL,
              scope TEXT NOT NULL,
              start_on TEXT,
              target_on TEXT,
              next_action TEXT,
              blockers TEXT,
              milestones_json TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS readiness_checklist_items (
              id TEXT PRIMARY KEY,
              project_id TEXT NOT NULL REFERENCES fde_projects(id),
              item_key TEXT NOT NULL,
              label TEXT NOT NULL,
              state TEXT NOT NULL,
              evidence_ref TEXT,
              notes TEXT,
              updated_at TEXT NOT NULL,
              UNIQUE(project_id, item_key)
            );
            CREATE TABLE IF NOT EXISTS equipment_records (
              id TEXT PRIMARY KEY,
              organization_id TEXT NOT NULL REFERENCES organizations(id),
              site_id TEXT NOT NULL REFERENCES sites(id),
              category TEXT NOT NULL,
              manufacturer TEXT,
              model TEXT NOT NULL,
              quantity INTEGER NOT NULL,
              ownership_model TEXT NOT NULL,
              procurement_status TEXT NOT NULL,
              supplier_ref TEXT,
              warranty_until TEXT,
              notes TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS education_events (
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              event_type TEXT NOT NULL,
              objectives TEXT NOT NULL,
              host_institution TEXT,
              event_on TEXT NOT NULL,
              location TEXT,
              format TEXT NOT NULL,
              speaker TEXT,
              audience TEXT NOT NULL,
              organization_id TEXT REFERENCES organizations(id),
              included_complimentary INTEGER NOT NULL DEFAULT 0,
              status TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS partnership_plans (
              id TEXT PRIMARY KEY,
              organization_id TEXT NOT NULL REFERENCES organizations(id),
              horizon_years INTEGER NOT NULL,
              year_1_focus TEXT NOT NULL,
              years_2_3_focus TEXT NOT NULL,
              years_4_5_focus TEXT NOT NULL,
              years_6_8_focus TEXT NOT NULL,
              notes TEXT,
              status TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS proposals (
              id TEXT PRIMARY KEY,
              organization_id TEXT NOT NULL REFERENCES organizations(id),
              site_id TEXT NOT NULL REFERENCES sites(id),
              opportunity_id TEXT,
              title TEXT NOT NULL,
              version INTEGER NOT NULL,
              status TEXT NOT NULL,
              executive_summary TEXT NOT NULL,
              scope_json TEXT NOT NULL,
              assumptions TEXT NOT NULL,
              exclusions TEXT NOT NULL,
              timeline_notes TEXT NOT NULL,
              valid_until TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS pricing_assumption_versions (
              id TEXT PRIMARY KEY,
              label TEXT NOT NULL,
              currency TEXT NOT NULL,
              assumptions_json TEXT NOT NULL,
              status TEXT NOT NULL,
              valid_from TEXT NOT NULL,
              notes TEXT,
              created_at TEXT NOT NULL
            );
            """
        )
        # Seed internal unvalidated pricing assumptions once (never public).
        if not store.db.execute("SELECT 1 FROM pricing_assumption_versions LIMIT 1").fetchone():
            store.db.execute(
                "INSERT INTO pricing_assumption_versions VALUES(?,?,?,?,?,?,?,?)",
                (
                    secrets.token_hex(8),
                    "historical-hypothesis-qna",
                    "BDT",
                    json.dumps({
                        "site_readiness_minor": 30000000,
                        "silent_pilot_six_month_minor": 50000000,
                        "production_implementation_minor": 60000000,
                        "annual_site_licence_minor": 120000000,
                        "validated": False,
                        "public": False,
                        "note": "Unvalidated internal hypotheses from historical Q&A; not approved public rates.",
                    }),
                    "unvalidated_hypothesis",
                    date.today().isoformat(),
                    "Internal only. Never publish on public website.",
                    stamp(),
                ),
            )
        store.db.commit()

    def check_org(user: dict, organization_id: str | None) -> None:
        if not organization_id:
            return
        if user["evaluation"] and organization_id != "evaluation-hospital":
            raise HTTPException(status_code=404, detail="Organization not found")
        if not user["vendor"] and organization_id not in user.get("organization_ids", []):
            raise HTTPException(status_code=404, detail="Organization not found")

    def ensure_org(organization_id: str, user: dict) -> None:
        row = store.db.execute("SELECT id FROM organizations WHERE id=?", (organization_id,)).fetchone()
        if not row or (user["evaluation"] and organization_id != "evaluation-hospital"):
            raise HTTPException(status_code=404, detail="Organization not found")

    def ensure_site(site_id: str, organization_id: str | None, user: dict) -> dict:
        row = store.db.execute("SELECT * FROM sites WHERE id=?", (site_id,)).fetchone()
        if not row or (user["evaluation"] and row["organization_id"] != "evaluation-hospital"):
            raise HTTPException(status_code=404, detail="Site not found")
        if organization_id and row["organization_id"] != organization_id:
            raise HTTPException(status_code=422, detail="Site does not belong to organization")
        return dict(row)

    @app.post("/v1/public/consultations")
    def create_consultation(body: ConsultationCreate):
        if not body.consent:
            raise HTTPException(status_code=422, detail="Contact consent is required")
        import os

        if os.environ.get("EVALUATION_RUNTIME") == "true":
            raise HTTPException(status_code=403, detail="Consultations disabled in synthetic evaluation")
        if body.purpose not in CONSULTATION_PURPOSES:
            raise HTTPException(status_code=422, detail="Unknown consultation purpose")
        if body.organization_size not in ORG_SIZES or body.readiness_self_report not in READINESS_TIERS:
            raise HTTPException(status_code=422, detail="Unknown size or readiness value")
        email = body.work_email.strip().lower()
        with store.lock:
            recent = store.db.execute(
                "SELECT 1 FROM consultation_requests WHERE email=? AND datetime(created_at)>=datetime('now','-1 hour')",
                (email,),
            ).fetchone()
            if recent:
                return {"recorded": True, "status": "pending"}
            consultation_id, at = secrets.token_hex(16), stamp()
            store.db.execute(
                """INSERT INTO consultation_requests VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    consultation_id, body.organization, body.contact_name, email, body.job_title, body.department,
                    body.country, body.location, body.hospital_type, body.organization_size, body.readiness_self_report,
                    body.purpose, body.preferred_dates, body.modality, body.message, "pending", None, None, None, None,
                    None, None, None, None, None, at, at,
                ),
            )
            store.audit("public", "consultation_requested", "consultation", consultation_id)
            store.db.commit()
        return {"recorded": True, "id": consultation_id, "status": "pending", "note": "Preferred times are pending confirmation; this is not a booked meeting."}

    @app.get("/v1/vendor/consultations")
    def list_consultations(user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.crm.read")
        if user["evaluation"]:
            return {"consultations": []}
        with store.lock:
            rows = store.db.execute("SELECT * FROM consultation_requests ORDER BY created_at DESC LIMIT 500").fetchall()
        return {"consultations": [dict(row) for row in rows]}

    @app.patch("/v1/vendor/consultations/{consultation_id}")
    def update_consultation(consultation_id: str, body: ConsultationUpdate, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.crm.write")
        if body.status not in CONSULTATION_STATUSES:
            raise HTTPException(status_code=422, detail="Unknown consultation status")
        with store.lock:
            row = store.db.execute("SELECT * FROM consultation_requests WHERE id=?", (consultation_id,)).fetchone()
            if not row or user["evaluation"]:
                raise HTTPException(status_code=404, detail="Consultation not found")
            if body.organization_id:
                ensure_org(body.organization_id, user)
            if body.site_id:
                ensure_site(body.site_id, body.organization_id or row["organization_id"], user)
            store.db.execute(
                """UPDATE consultation_requests SET status=?, assigned_to=COALESCE(?,assigned_to), organization_id=COALESCE(?,organization_id),
                   site_id=COALESCE(?,site_id), opportunity_id=COALESCE(?,opportunity_id), agenda=COALESCE(?,agenda),
                   notes=COALESCE(?,notes), next_action=COALESCE(?,next_action), follow_up_date=COALESCE(?,follow_up_date),
                   confirmed_at=COALESCE(?,confirmed_at), updated_at=? WHERE id=?""",
                (
                    body.status, body.assigned_to, body.organization_id, body.site_id, body.opportunity_id, body.agenda,
                    body.notes, body.next_action, str(body.follow_up_date) if body.follow_up_date else None,
                    body.confirmed_at, stamp(), consultation_id,
                ),
            )
            store.audit(user["user_id"], f"consultation_{body.status}:{body.reason}", "consultation", consultation_id)
            store.db.commit()
        return {"id": consultation_id, "status": body.status}

    @app.post("/v1/vendor/opportunities")
    def create_opportunity(body: OpportunityCreate, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.crm.write")
        if body.organization_size not in ORG_SIZES or body.readiness_tier not in READINESS_TIERS:
            raise HTTPException(status_code=422, detail="Unknown size or readiness tier")
        with store.lock:
            if body.organization_id:
                ensure_org(body.organization_id, user)
            if body.site_id:
                ensure_site(body.site_id, body.organization_id, user)
            opportunity_id, at = secrets.token_hex(16), stamp()
            store.db.execute(
                "INSERT INTO opportunities VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    opportunity_id, body.name, body.organization_id, body.site_id, body.primary_contact, body.owner,
                    "new_inquiry", body.organization_size, body.readiness_tier, body.next_action,
                    str(body.due_on) if body.due_on else None, body.consultation_id, body.lead_id, None, at, at,
                ),
            )
            store.audit(user["user_id"], "created", "opportunity", opportunity_id)
            store.db.commit()
        return {"id": opportunity_id, "stage": "new_inquiry"}

    @app.get("/v1/vendor/opportunities")
    def list_opportunities(user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.crm.read")
        with store.lock:
            if user["evaluation"]:
                rows = store.db.execute(
                    "SELECT * FROM opportunities WHERE organization_id='evaluation-hospital' OR organization_id IS NULL ORDER BY updated_at DESC LIMIT 500"
                ).fetchall()
            else:
                rows = store.db.execute("SELECT * FROM opportunities ORDER BY updated_at DESC LIMIT 500").fetchall()
        return {"opportunities": [dict(row) for row in rows], "stages": sorted(OPPORTUNITY_STAGES)}

    @app.patch("/v1/vendor/opportunities/{opportunity_id}")
    def update_opportunity(opportunity_id: str, body: OpportunityUpdate, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.crm.write")
        if body.stage not in OPPORTUNITY_STAGES:
            raise HTTPException(status_code=422, detail="Unknown opportunity stage")
        with store.lock:
            row = store.db.execute("SELECT * FROM opportunities WHERE id=?", (opportunity_id,)).fetchone()
            if not row or (user["evaluation"] and row["organization_id"] not in {None, "evaluation-hospital"}):
                raise HTTPException(status_code=404, detail="Opportunity not found")
            store.db.execute(
                """UPDATE opportunities SET stage=?, next_action=?, due_on=?, owner=COALESCE(?,owner), organization_id=COALESCE(?,organization_id),
                   site_id=COALESCE(?,site_id), readiness_tier=COALESCE(?,readiness_tier), organization_size=COALESCE(?,organization_size),
                   notes=COALESCE(?,notes), updated_at=? WHERE id=?""",
                (
                    body.stage, body.next_action, str(body.due_on) if body.due_on else None, body.owner,
                    body.organization_id, body.site_id, body.readiness_tier, body.organization_size, body.notes, stamp(), opportunity_id,
                ),
            )
            store.audit(user["user_id"], f"opportunity_{body.stage}:{body.reason}", "opportunity", opportunity_id)
            store.db.commit()
        return {"id": opportunity_id, "stage": body.stage}

    @app.put("/v1/vendor/organizations/{organization_id}/profile")
    def upsert_org_profile(organization_id: str, body: OrgProfileUpdate, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.org.read")
        if body.organization_size and body.organization_size not in ORG_SIZES:
            raise HTTPException(status_code=422, detail="Unknown organization size")
        if body.readiness_tier and body.readiness_tier not in READINESS_TIERS:
            raise HTTPException(status_code=422, detail="Unknown readiness tier")
        if body.relationship_status and body.relationship_status not in RELATIONSHIP_STATUSES:
            raise HTTPException(status_code=422, detail="Unknown relationship status")
        with store.lock:
            ensure_org(organization_id, user)
            existing = store.db.execute("SELECT * FROM organization_profiles WHERE organization_id=?", (organization_id,)).fetchone()
            at = stamp()
            if not existing:
                store.db.execute(
                    "INSERT INTO organization_profiles VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        organization_id, body.display_name, body.organization_type,
                        body.organization_size or "unspecified", body.readiness_tier or "unspecified",
                        body.relationship_status or "prospect", body.country, body.primary_contact,
                        body.clinical_owner, body.it_owner, body.procurement_owner, body.notes, at,
                    ),
                )
            else:
                store.db.execute(
                    """UPDATE organization_profiles SET display_name=COALESCE(?,display_name), organization_type=COALESCE(?,organization_type),
                       organization_size=COALESCE(?,organization_size), readiness_tier=COALESCE(?,readiness_tier),
                       relationship_status=COALESCE(?,relationship_status), country=COALESCE(?,country),
                       primary_contact=COALESCE(?,primary_contact), clinical_owner=COALESCE(?,clinical_owner),
                       it_owner=COALESCE(?,it_owner), procurement_owner=COALESCE(?,procurement_owner),
                       notes=COALESCE(?,notes), updated_at=? WHERE organization_id=?""",
                    (
                        body.display_name, body.organization_type, body.organization_size, body.readiness_tier,
                        body.relationship_status, body.country, body.primary_contact, body.clinical_owner,
                        body.it_owner, body.procurement_owner, body.notes, at, organization_id,
                    ),
                )
            store.audit(user["user_id"], f"org_profile_updated:{body.reason}", "organization_profile", organization_id)
            store.db.commit()
            row = store.db.execute("SELECT * FROM organization_profiles WHERE organization_id=?", (organization_id,)).fetchone()
        return dict(row)

    @app.get("/v1/organizations/{organization_id}/profile")
    def get_org_profile(organization_id: str, user: dict = Depends(require_user)):
        if user["vendor"]:
            require_permission(user, "vendor.org.read")
        else:
            require_permission(user, "customer.org.read", organization_id=organization_id)
        check_org(user, organization_id)
        with store.lock:
            ensure_org(organization_id, user)
            org = store.db.execute("SELECT id,name,created_at FROM organizations WHERE id=?", (organization_id,)).fetchone()
            profile = store.db.execute("SELECT * FROM organization_profiles WHERE organization_id=?", (organization_id,)).fetchone()
            sites = store.db.execute("SELECT id,name,created_at FROM sites WHERE organization_id=? ORDER BY name", (organization_id,)).fetchall()
        result = {"organization": dict(org), "profile": dict(profile) if profile else None, "sites": [dict(s) for s in sites]}
        if not user["vendor"]:
            # Customers see relationship/readiness summaries, not internal notes.
            if result["profile"]:
                result["profile"] = {
                    k: result["profile"].get(k)
                    for k in ("organization_id", "display_name", "organization_type", "organization_size", "readiness_tier", "relationship_status", "country", "updated_at")
                }
        return result

    @app.put("/v1/vendor/sites/{site_id}/profile")
    def upsert_site_profile(site_id: str, body: SiteProfileUpdate, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.site.read")
        with store.lock:
            site = ensure_site(site_id, None, user)
            existing = store.db.execute("SELECT 1 FROM site_profiles WHERE site_id=?", (site_id,)).fetchone()
            at = stamp()
            if not existing:
                store.db.execute(
                    "INSERT INTO site_profiles VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        site_id, site["organization_id"], body.address, body.country, body.timezone, body.units_summary,
                        body.bed_scope, body.site_owner, body.deployment_lead, body.environment_status,
                        body.governance_state, body.service_plan, body.notes, at,
                    ),
                )
            else:
                store.db.execute(
                    """UPDATE site_profiles SET address=COALESCE(?,address), country=COALESCE(?,country), timezone=COALESCE(?,timezone),
                       units_summary=COALESCE(?,units_summary), bed_scope=COALESCE(?,bed_scope), site_owner=COALESCE(?,site_owner),
                       deployment_lead=COALESCE(?,deployment_lead), environment_status=COALESCE(?,environment_status),
                       governance_state=COALESCE(?,governance_state), service_plan=COALESCE(?,service_plan),
                       notes=COALESCE(?,notes), updated_at=? WHERE site_id=?""",
                    (
                        body.address, body.country, body.timezone, body.units_summary, body.bed_scope, body.site_owner,
                        body.deployment_lead, body.environment_status, body.governance_state, body.service_plan,
                        body.notes, at, site_id,
                    ),
                )
            store.audit(user["user_id"], f"site_profile_updated:{body.reason}", "site_profile", site_id)
            store.db.commit()
            row = store.db.execute("SELECT * FROM site_profiles WHERE site_id=?", (site_id,)).fetchone()
        return dict(row)

    @app.get("/v1/sites/{site_id}/profile")
    def get_site_profile(site_id: str, user: dict = Depends(require_user)):
        with store.lock:
            site = store.db.execute("SELECT * FROM sites WHERE id=?", (site_id,)).fetchone()
            if not site:
                raise HTTPException(status_code=404, detail="Site not found")
            check_org(user, site["organization_id"])
            if user["vendor"]:
                require_permission(user, "vendor.site.read")
            else:
                require_permission(user, "customer.site.read", organization_id=site["organization_id"])
            profile = store.db.execute("SELECT * FROM site_profiles WHERE site_id=?", (site_id,)).fetchone()
        return {"site": dict(site), "profile": dict(profile) if profile else None}

    @app.post("/v1/vendor/fde-projects")
    def create_fde_project(body: FdeProjectCreate, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.deployment.write")
        if body.category not in FDE_CATEGORIES:
            raise HTTPException(status_code=422, detail="Unknown FDE category")
        with store.lock:
            ensure_org(body.organization_id, user)
            ensure_site(body.site_id, body.organization_id, user)
            project_id, at = secrets.token_hex(16), stamp()
            store.db.execute(
                "INSERT INTO fde_projects VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    project_id, body.organization_id, body.site_id, body.opportunity_id, body.title, body.category,
                    "planned", body.deployment_lead, body.scope, str(body.start_on) if body.start_on else None,
                    str(body.target_on) if body.target_on else None, None, None, "[]", at, at,
                ),
            )
            for key, label in DEFAULT_READINESS_ITEMS:
                store.db.execute(
                    "INSERT INTO readiness_checklist_items VALUES(?,?,?,?,?,?,?,?)",
                    (secrets.token_hex(12), project_id, key, label, "not_started", None, None, at),
                )
            store.audit(user["user_id"], "created", "fde_project", project_id)
            store.db.commit()
        return {"id": project_id, "status": "planned", "readiness_items": len(DEFAULT_READINESS_ITEMS)}

    @app.get("/v1/fde-projects")
    def list_fde_projects(user: dict = Depends(require_user)):
        if user["vendor"]:
            require_permission(user, "vendor.deployment.read")
        with store.lock:
            if user["evaluation"]:
                rows = store.db.execute("SELECT * FROM fde_projects WHERE organization_id='evaluation-hospital' ORDER BY updated_at DESC LIMIT 500").fetchall()
            elif user["vendor"]:
                rows = store.db.execute("SELECT * FROM fde_projects ORDER BY updated_at DESC LIMIT 500").fetchall()
            else:
                rows = store.db.execute(
                    "SELECT p.* FROM fde_projects p JOIN memberships m ON m.organization_id=p.organization_id WHERE m.user_id=? ORDER BY p.updated_at DESC LIMIT 500",
                    (user["user_id"],),
                ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            if not user["vendor"] and not has_permission(user, "customer.assessment.read", organization_id=item["organization_id"]):
                continue
            result.append(item)
        return {"projects": result}

    @app.patch("/v1/vendor/fde-projects/{project_id}")
    def update_fde_project(project_id: str, body: FdeProjectUpdate, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.deployment.write")
        if body.status not in FDE_STATUSES:
            raise HTTPException(status_code=422, detail="Unknown FDE status")
        with store.lock:
            row = store.db.execute("SELECT * FROM fde_projects WHERE id=?", (project_id,)).fetchone()
            if not row or (user["evaluation"] and row["organization_id"] != "evaluation-hospital"):
                raise HTTPException(status_code=404, detail="Project not found")
            store.db.execute(
                """UPDATE fde_projects SET status=?, deployment_lead=COALESCE(?,deployment_lead), next_action=COALESCE(?,next_action),
                   blockers=COALESCE(?,blockers), milestones_json=COALESCE(?,milestones_json), updated_at=? WHERE id=?""",
                (body.status, body.deployment_lead, body.next_action, body.blockers, body.milestones_json, stamp(), project_id),
            )
            store.audit(user["user_id"], f"fde_{body.status}:{body.reason}", "fde_project", project_id)
            store.db.commit()
        return {"id": project_id, "status": body.status}

    @app.get("/v1/fde-projects/{project_id}/readiness")
    def get_readiness(project_id: str, user: dict = Depends(require_user)):
        with store.lock:
            project = store.db.execute("SELECT * FROM fde_projects WHERE id=?", (project_id,)).fetchone()
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
            check_org(user, project["organization_id"])
            if user["vendor"]:
                require_permission(user, "vendor.deployment.read")
            else:
                require_permission(user, "customer.assessment.read", organization_id=project["organization_id"])
            items = store.db.execute("SELECT * FROM readiness_checklist_items WHERE project_id=? ORDER BY label", (project_id,)).fetchall()
        return {"project_id": project_id, "items": [dict(i) for i in items]}

    @app.patch("/v1/vendor/fde-projects/{project_id}/readiness/{item_id}")
    def update_readiness_item(project_id: str, item_id: str, body: ReadinessItemUpdate, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.deployment.write")
        if body.state not in CHECK_STATES:
            raise HTTPException(status_code=422, detail="Unknown checklist state")
        with store.lock:
            item = store.db.execute("SELECT * FROM readiness_checklist_items WHERE id=? AND project_id=?", (item_id, project_id)).fetchone()
            if not item:
                raise HTTPException(status_code=404, detail="Checklist item not found")
            project = store.db.execute("SELECT organization_id FROM fde_projects WHERE id=?", (project_id,)).fetchone()
            if user["evaluation"] and project["organization_id"] != "evaluation-hospital":
                raise HTTPException(status_code=404, detail="Checklist item not found")
            store.db.execute(
                "UPDATE readiness_checklist_items SET state=?, evidence_ref=COALESCE(?,evidence_ref), notes=COALESCE(?,notes), updated_at=? WHERE id=?",
                (body.state, body.evidence_ref, body.notes, stamp(), item_id),
            )
            store.audit(user["user_id"], f"readiness_{body.state}:{body.reason}", "readiness_item", item_id)
            store.db.commit()
        return {"id": item_id, "state": body.state}

    @app.post("/v1/vendor/equipment")
    def create_equipment(body: EquipmentCreate, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.asset.write")
        if body.ownership_model not in OWNERSHIP_MODELS:
            raise HTTPException(status_code=422, detail="Unknown ownership model")
        with store.lock:
            ensure_org(body.organization_id, user)
            ensure_site(body.site_id, body.organization_id, user)
            equipment_id, at = secrets.token_hex(16), stamp()
            store.db.execute(
                "INSERT INTO equipment_records VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    equipment_id, body.organization_id, body.site_id, body.category, body.manufacturer, body.model,
                    body.quantity, body.ownership_model, body.procurement_status, body.supplier_ref,
                    str(body.warranty_until) if body.warranty_until else None, body.notes, at, at,
                ),
            )
            store.audit(user["user_id"], "created", "equipment", equipment_id)
            store.db.commit()
        return {"id": equipment_id, "procurement_status": body.procurement_status}

    @app.get("/v1/equipment")
    def list_equipment(user: dict = Depends(require_user)):
        if user["vendor"]:
            require_permission(user, "vendor.asset.read")
        with store.lock:
            if user["evaluation"]:
                rows = store.db.execute("SELECT * FROM equipment_records WHERE organization_id='evaluation-hospital' ORDER BY updated_at DESC LIMIT 500").fetchall()
            elif user["vendor"]:
                rows = store.db.execute("SELECT * FROM equipment_records ORDER BY updated_at DESC LIMIT 500").fetchall()
            else:
                rows = store.db.execute(
                    "SELECT e.* FROM equipment_records e JOIN memberships m ON m.organization_id=e.organization_id WHERE m.user_id=? ORDER BY e.updated_at DESC LIMIT 500",
                    (user["user_id"],),
                ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            if not user["vendor"] and not has_permission(user, "customer.asset.read", organization_id=item["organization_id"]):
                continue
            if not user["vendor"]:
                item.pop("supplier_ref", None)
                item.pop("notes", None)
            result.append(item)
        return {"equipment": result}

    @app.post("/v1/vendor/education-events")
    def create_education_event(body: EducationEventCreate, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.training.write")
        if body.event_type not in EVENT_TYPES:
            raise HTTPException(status_code=422, detail="Unknown event type")
        with store.lock:
            if body.organization_id:
                ensure_org(body.organization_id, user)
            event_id, at = secrets.token_hex(16), stamp()
            store.db.execute(
                "INSERT INTO education_events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    event_id, body.title, body.event_type, body.objectives, body.host_institution, str(body.event_on),
                    body.location, body.format, body.speaker, body.audience, body.organization_id,
                    int(body.included_complimentary), "planned", at, at,
                ),
            )
            store.audit(user["user_id"], "created", "education_event", event_id)
            store.db.commit()
        return {"id": event_id, "status": "planned"}

    @app.get("/v1/education-events")
    def list_education_events(user: dict = Depends(require_user)):
        if user["vendor"]:
            require_permission(user, "vendor.training.read")
        with store.lock:
            if user["evaluation"]:
                rows = store.db.execute(
                    "SELECT * FROM education_events WHERE organization_id='evaluation-hospital' OR organization_id IS NULL ORDER BY event_on DESC LIMIT 500"
                ).fetchall()
            elif user["vendor"]:
                rows = store.db.execute("SELECT * FROM education_events ORDER BY event_on DESC LIMIT 500").fetchall()
            else:
                rows = store.db.execute(
                    """SELECT e.* FROM education_events e LEFT JOIN memberships m ON m.organization_id=e.organization_id
                       WHERE e.organization_id IS NULL OR m.user_id=? ORDER BY e.event_on DESC LIMIT 500""",
                    (user["user_id"],),
                ).fetchall()
        events = []
        for row in rows:
            item = dict(row)
            if user["vendor"] or user["evaluation"]:
                events.append(item)
                continue
            org_id = item.get("organization_id")
            if org_id is None:
                continue
            if has_permission(user, "customer.training.read", organization_id=org_id):
                events.append(item)
        return {"events": events}

    @app.post("/v1/vendor/partnership-plans")
    def create_partnership_plan(body: PartnershipPlanCreate, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.crm.write")
        with store.lock:
            ensure_org(body.organization_id, user)
            plan_id, at = secrets.token_hex(16), stamp()
            store.db.execute(
                "INSERT INTO partnership_plans VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    plan_id, body.organization_id, body.horizon_years, body.year_1_focus, body.years_2_3_focus,
                    body.years_4_5_focus, body.years_6_8_focus, body.notes, "internal_planning", at, at,
                ),
            )
            store.audit(user["user_id"], "created", "partnership_plan", plan_id)
            store.db.commit()
        return {"id": plan_id, "status": "internal_planning", "note": "Internal strategic horizon only; not a binding contract duration."}

    @app.get("/v1/vendor/partnership-plans")
    def list_partnership_plans(user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.crm.read")
        with store.lock:
            rows = store.db.execute("SELECT * FROM partnership_plans ORDER BY updated_at DESC LIMIT 500").fetchall()
        return {"plans": [dict(row) for row in rows]}

    @app.post("/v1/vendor/proposals")
    def create_proposal(body: ProposalCreate, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.quote.write")
        with store.lock:
            ensure_org(body.organization_id, user)
            ensure_site(body.site_id, body.organization_id, user)
            try:
                json.loads(body.scope_json)
            except json.JSONDecodeError as error:
                raise HTTPException(status_code=422, detail="scope_json must be valid JSON") from error
            proposal_id, at = secrets.token_hex(16), stamp()
            store.db.execute(
                "INSERT INTO proposals VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    proposal_id, body.organization_id, body.site_id, body.opportunity_id, body.title, 1, "draft",
                    body.executive_summary, body.scope_json, body.assumptions, body.exclusions, body.timeline_notes,
                    str(body.valid_until), at, at,
                ),
            )
            store.audit(user["user_id"], "created", "proposal", proposal_id)
            store.db.commit()
        return {"id": proposal_id, "status": "draft", "version": 1}

    @app.get("/v1/proposals")
    def list_proposals(user: dict = Depends(require_user)):
        if user["vendor"]:
            require_permission(user, "vendor.quote.read")
        with store.lock:
            if user["evaluation"]:
                rows = store.db.execute("SELECT * FROM proposals WHERE organization_id='evaluation-hospital' ORDER BY updated_at DESC LIMIT 500").fetchall()
            elif user["vendor"]:
                rows = store.db.execute("SELECT * FROM proposals ORDER BY updated_at DESC LIMIT 500").fetchall()
            else:
                rows = store.db.execute(
                    "SELECT p.* FROM proposals p JOIN memberships m ON m.organization_id=p.organization_id WHERE m.user_id=? AND p.status IN ('issued','accepted') ORDER BY p.updated_at DESC LIMIT 500",
                    (user["user_id"],),
                ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            if not user["vendor"] and not has_permission(user, "customer.quote.read", organization_id=item["organization_id"]):
                continue
            item["scope"] = json.loads(item.pop("scope_json"))
            result.append(item)
        return {"proposals": result}

    @app.patch("/v1/vendor/proposals/{proposal_id}")
    def update_proposal(proposal_id: str, body: ProposalUpdate, user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.quote.write")
        if body.status not in PROPOSAL_STATUSES:
            raise HTTPException(status_code=422, detail="Unknown proposal status")
        with store.lock:
            row = store.db.execute("SELECT * FROM proposals WHERE id=?", (proposal_id,)).fetchone()
            if not row or (user["evaluation"] and row["organization_id"] != "evaluation-hospital"):
                raise HTTPException(status_code=404, detail="Proposal not found")
            store.db.execute("UPDATE proposals SET status=?, updated_at=? WHERE id=?", (body.status, stamp(), proposal_id))
            store.audit(user["user_id"], f"proposal_{body.status}:{body.reason}", "proposal", proposal_id)
            store.db.commit()
        return {"id": proposal_id, "status": body.status}

    @app.get("/v1/vendor/pricing-assumptions")
    def pricing_assumptions(user: dict = Depends(require_vendor)):
        require_permission(user, "vendor.quote.read")
        with store.lock:
            rows = store.db.execute("SELECT * FROM pricing_assumption_versions ORDER BY created_at DESC LIMIT 50").fetchall()
        return {
            "assumptions": [{**dict(row), "assumptions": json.loads(row["assumptions_json"]), "public": False} for row in rows],
            "warning": "Unvalidated internal hypotheses only. Never publish as market rates.",
        }

    @app.get("/v1/partnership/taxonomy")
    def partnership_taxonomy(user: dict = Depends(require_user)):
        return {
            "readiness_tiers": sorted(READINESS_TIERS),
            "organization_sizes": sorted(ORG_SIZES),
            "relationship_statuses": sorted(RELATIONSHIP_STATUSES),
            "opportunity_stages": sorted(OPPORTUNITY_STAGES),
            "consultation_purposes": sorted(CONSULTATION_PURPOSES),
            "fde_categories": sorted(FDE_CATEGORIES),
            "event_types": sorted(EVENT_TYPES),
            "ownership_models": sorted(OWNERSHIP_MODELS),
        }
