"""Configurable Role–Permission Matrix for Auralis account surfaces.

Hospital clinical authorization remains in the hospital API (`backend/app/auth.py`).
This registry governs the Vendor Control Plane and Customer Portal only. Evaluation
operators receive a sandbox composite grant scoped by EVALUATION_RUNTIME checks in
route handlers — never by widening production permissions.
"""

from __future__ import annotations

from typing import Iterable

# Canonical permission identifiers. Routes must check these rather than hard-coding
# role name lists so the matrix can evolve without scattering allow-lists.
PERMISSIONS: frozenset[str] = frozenset(
    {
        # Vendor — directory & tenancy
        "vendor.org.create",
        "vendor.org.read",
        "vendor.site.create",
        "vendor.site.read",
        "vendor.account.directory",
        "vendor.account.invite",
        "vendor.account.membership.write",
        "vendor.account.state.write",
        "vendor.staff.provision",
        "vendor.staff.read",
        "vendor.audit.read",
        # Vendor — commercial
        "vendor.crm.write",
        "vendor.crm.read",
        "vendor.quote.write",
        "vendor.quote.read",
        "vendor.contract.write",
        "vendor.contract.read",
        "vendor.licence.write",
        "vendor.licence.read",
        "vendor.invoice.write",
        "vendor.invoice.read",
        "vendor.payment.verify",
        "vendor.payment.read",
        "vendor.renewal.write",
        "vendor.renewal.read",
        # Vendor — operations / documents / compliance
        "vendor.asset.write",
        "vendor.asset.read",
        "vendor.compliance.write",
        "vendor.compliance.read",
        "vendor.ticket.write",
        "vendor.ticket.read",
        "vendor.document.write",
        "vendor.document.read",
        "vendor.training.write",
        "vendor.training.read",
        "vendor.deployment.write",
        "vendor.deployment.read",
        "vendor.offboarding.write",
        "vendor.offboarding.read",
        "vendor.approval.decide",
        # Customer portal (organization-scoped)
        "customer.org.read",
        "customer.site.read",
        "customer.member.invite",
        "customer.member.read",
        "customer.quote.read",
        "customer.contract.read",
        "customer.licence.read",
        "customer.invoice.read",
        "customer.payment.submit",
        "customer.payment.read",
        "customer.renewal.read",
        "customer.renewal.request",
        "customer.ticket.open",
        "customer.ticket.read",
        "customer.asset.read",
        "customer.compliance.read",
        "customer.document.read",
        "customer.training.read",
        "customer.contact.read",
        "customer.assessment.read",
        "customer.offboarding.request",
    }
)

VENDOR_ROLES = frozenset(
    {
        "root_admin",
        "platform_admin",
        "deployment_engineer",
        "support_engineer",
        "finance_legal",
        "security_compliance",
        "evaluation_operator",
    }
)

CUSTOMER_ROLES = frozenset(
    {
        "customer_owner",
        "procurement_finance",
        "technical_contact",
        "customer_viewer",
        "evaluation_operator",
    }
)

# Hospital clinical roles live in the hospital API. Documented here for the
# five-surface matrix and frontend profile mapping only.
HOSPITAL_ROLES = frozenset(
    {
        "admin",  # HospitalAdmin
        "clinician",  # ICUConsultant / Clinician
        "nurse",
        "clinical_it",
        "clinical_viewer",
        "operator",  # platform operator metadata — hospital API only
        "integration",
    }
)

_ALL_VENDOR = frozenset(p for p in PERMISSIONS if p.startswith("vendor."))
_ALL_CUSTOMER = frozenset(p for p in PERMISSIONS if p.startswith("customer."))

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "root_admin": _ALL_VENDOR,
    "platform_admin": frozenset(
        {
            "vendor.org.create",
            "vendor.org.read",
            "vendor.site.create",
            "vendor.site.read",
            "vendor.account.directory",
            "vendor.account.invite",
            "vendor.account.membership.write",
            "vendor.staff.read",
            "vendor.crm.write",
            "vendor.crm.read",
            "vendor.quote.read",
            "vendor.contract.read",
            "vendor.licence.read",
            "vendor.invoice.read",
            "vendor.payment.read",
            "vendor.renewal.read",
            "vendor.asset.read",
            "vendor.compliance.read",
            "vendor.ticket.read",
            "vendor.document.read",
            "vendor.training.read",
            "vendor.deployment.read",
            "vendor.offboarding.read",
            "vendor.approval.decide",
        }
    ),
    "deployment_engineer": frozenset(
        {
            "vendor.org.read",
            "vendor.site.create",
            "vendor.site.read",
            "vendor.asset.write",
            "vendor.asset.read",
            "vendor.deployment.write",
            "vendor.deployment.read",
            "vendor.licence.read",
            "vendor.document.read",
            "vendor.training.read",
            "vendor.ticket.read",
        }
    ),
    "support_engineer": frozenset(
        {
            "vendor.org.read",
            "vendor.site.read",
            "vendor.ticket.write",
            "vendor.ticket.read",
            "vendor.asset.read",
            "vendor.deployment.read",
            "vendor.document.read",
            "vendor.training.read",
        }
    ),
    "finance_legal": frozenset(
        {
            "vendor.org.read",
            "vendor.site.read",
            "vendor.crm.read",
            "vendor.quote.write",
            "vendor.quote.read",
            "vendor.contract.write",
            "vendor.contract.read",
            "vendor.licence.write",
            "vendor.licence.read",
            "vendor.invoice.write",
            "vendor.invoice.read",
            "vendor.payment.verify",
            "vendor.payment.read",
            "vendor.renewal.write",
            "vendor.renewal.read",
            "vendor.document.write",
            "vendor.document.read",
            "vendor.offboarding.read",
        }
    ),
    "security_compliance": frozenset(
        {
            "vendor.org.read",
            "vendor.site.read",
            "vendor.audit.read",
            "vendor.compliance.write",
            "vendor.compliance.read",
            "vendor.document.read",
            "vendor.offboarding.write",
            "vendor.offboarding.read",
            "vendor.approval.decide",
        }
    ),
    # Sandbox composite — route handlers still block production side-effects.
    "evaluation_operator": _ALL_VENDOR | _ALL_CUSTOMER,
    "customer_owner": frozenset(
        {
            "customer.org.read",
            "customer.site.read",
            "customer.member.invite",
            "customer.member.read",
            "customer.quote.read",
            "customer.contract.read",
            "customer.licence.read",
            "customer.invoice.read",
            "customer.payment.submit",
            "customer.payment.read",
            "customer.renewal.read",
            "customer.renewal.request",
            "customer.ticket.open",
            "customer.ticket.read",
            "customer.asset.read",
            "customer.compliance.read",
            "customer.document.read",
            "customer.training.read",
            "customer.contact.read",
            "customer.assessment.read",
            "customer.offboarding.request",
        }
    ),
    "procurement_finance": frozenset(
        {
            "customer.org.read",
            "customer.site.read",
            "customer.member.read",
            "customer.quote.read",
            "customer.contract.read",
            "customer.licence.read",
            "customer.invoice.read",
            "customer.payment.submit",
            "customer.payment.read",
            "customer.renewal.read",
            "customer.renewal.request",
            "customer.ticket.open",
            "customer.document.read",
            "customer.contact.read",
        }
    ),
    "technical_contact": frozenset(
        {
            "customer.org.read",
            "customer.site.read",
            "customer.member.read",
            "customer.licence.read",
            "customer.ticket.open",
            "customer.ticket.read",
            "customer.asset.read",
            "customer.document.read",
            "customer.training.read",
            "customer.contact.read",
            "customer.assessment.read",
        }
    ),
    "customer_viewer": frozenset(
        {
            "customer.org.read",
            "customer.site.read",
            "customer.member.read",
            "customer.contact.read",
            "customer.document.read",
            "customer.training.read",
        }
    ),
}

# Maps commercial/ops table names to the customer permission required to read rows.
CUSTOMER_TABLE_PERMISSION: dict[str, str] = {
    "contacts": "customer.contact.read",
    "assessments": "customer.assessment.read",
    "quotes": "customer.quote.read",
    "contracts": "customer.contract.read",
    "licences": "customer.licence.read",
    "invoices": "customer.invoice.read",
    "payments": "customer.payment.read",
    "renewals": "customer.renewal.read",
    "credit_notes": "customer.invoice.read",
    "assets": "customer.asset.read",
    "compliance_tasks": "customer.compliance.read",
    "tickets": "customer.ticket.read",
    "documents": "customer.document.read",
    "training_sessions": "customer.training.read",
}

# Document-type → customer permission (finer than table-level when needed).
DOCUMENT_TYPE_PERMISSION: dict[str, str] = {
    "quote": "customer.quote.read",
    "contract": "customer.contract.read",
    "invoice": "customer.invoice.read",
    "licence": "customer.licence.read",
    "training": "customer.training.read",
    "installation": "customer.document.read",
    "release_notes": "customer.document.read",
    "compliance": "customer.compliance.read",
    "support": "customer.ticket.read",
    "other": "customer.document.read",
}


def permissions_for_role(role: str) -> frozenset[str]:
    return ROLE_PERMISSIONS.get(role, frozenset())


def vendor_has(user: dict, permission: str) -> bool:
    if permission not in PERMISSIONS:
        return False
    if user.get("evaluation"):
        return permission in ROLE_PERMISSIONS["evaluation_operator"]
    if not user.get("vendor"):
        return False
    role = user.get("role") or ""
    if role == "root_admin":
        return True
    return permission in permissions_for_role(role)


def customer_has(user: dict, permission: str, organization_id: str | None = None) -> bool:
    if permission not in PERMISSIONS:
        return False
    if user.get("evaluation"):
        return permission in ROLE_PERMISSIONS["evaluation_operator"]
    if user.get("vendor"):
        return False
    roles_by_org: dict = user.get("organization_roles") or {}
    if organization_id is not None:
        role = roles_by_org.get(organization_id)
        return bool(role) and permission in permissions_for_role(role)
    return any(permission in permissions_for_role(role) for role in roles_by_org.values())


def has_permission(user: dict, permission: str, *, organization_id: str | None = None) -> bool:
    if permission.startswith("vendor."):
        return vendor_has(user, permission)
    if permission.startswith("customer."):
        return customer_has(user, permission, organization_id)
    return False


def require_permission(user: dict, permission: str, *, organization_id: str | None = None) -> None:
    from fastapi import HTTPException

    if not has_permission(user, permission, organization_id=organization_id):
        raise HTTPException(status_code=403, detail="Account role does not permit this action")


def require_any_permission(user: dict, permissions: Iterable[str], *, organization_id: str | None = None) -> None:
    from fastapi import HTTPException

    if not any(has_permission(user, item, organization_id=organization_id) for item in permissions):
        raise HTTPException(status_code=403, detail="Account role does not permit this action")


def matrix_snapshot() -> dict:
    """API-readable matrix for vendor/admin documentation surfaces."""
    return {
        "permissions": sorted(PERMISSIONS),
        "vendor_roles": sorted(VENDOR_ROLES - {"evaluation_operator"}),
        "customer_roles": sorted(CUSTOMER_ROLES - {"evaluation_operator"}),
        "hospital_roles": sorted(HOSPITAL_ROLES),
        "role_permissions": {role: sorted(grants) for role, grants in sorted(ROLE_PERMISSIONS.items()) if role != "evaluation_operator"},
        "evaluation_note": "evaluation_operator is sandbox-only and rejected by production authorization paths",
    }
