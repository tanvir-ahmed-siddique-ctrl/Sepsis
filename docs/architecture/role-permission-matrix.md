# Role and permission matrix (five surfaces)

Authoritative **machine-readable** vendor/customer grants live in `control-plane/permissions.py` and are exposed at `GET /v1/permissions/matrix` for vendor operators. Hospital clinical enforcement remains in `backend/app/auth.py`.

This document is the human-readable summary. Frontend menus are not authorization.

## Surfaces

| Surface | Authority | Store |
|---|---|---|
| Public website | None (editorial) | Static / marketing |
| Hospital clinical + hospital admin | Hospital API JWT / OIDC / local accounts | Hospital DB |
| Customer portal | Account service memberships | `ACCOUNT_DB` |
| Vendor control plane | Account service vendor roles | `ACCOUNT_DB` |
| Evaluation | Separate runtime + DB + keys | Evaluation compose only |

## Hospital roles (`backend/app/auth.py`)

| Role | Intent | Notes |
|---|---|---|
| `admin` | HospitalAdmin | Users, units, integrations, roster, readiness, licence import |
| `clinician` | ICU consultant / physician | Clinical review, physician-only actions |
| `nurse` | Bedside nursing | Clinical workflows except physician-only |
| `clinical_viewer` | Read-only clinical | Reads only; no ack / ownership / context write |
| `clinical_it` | Clinical IT | Integration, mapping, quarantine, site ops; no default chart write |
| `operator` | Platform operator metadata | No patient chart routes |
| `integration` | Machine credential | Scoped ingest only |

## Customer portal roles

| Role | Representative permissions |
|---|---|
| `customer_owner` | Members invite, commercial reads, tickets, assets, compliance, offboarding request |
| `procurement_finance` | Quotes, contracts, invoices, payments, renewals |
| `technical_contact` | Licence/docs/training/tickets/assets/assessments |
| `customer_viewer` | Org/site/member/contact/document/training reads |

## Vendor roles

| Role | Representative permissions |
|---|---|
| `root_admin` | All vendor permissions; account disable; staff provision |
| `platform_admin` | Orgs, sites, directory, CRM, memberships, broad reads |
| `deployment_engineer` | Sites, assets, deployments, operational reads |
| `support_engineer` | Tickets, limited operational reads |
| `finance_legal` | Quotes, contracts, licences, invoices, payment verify, documents |
| `security_compliance` | Audit, compliance tasks, approvals, offboarding |
| `evaluation_operator` | Sandbox composite only when `EVALUATION_RUNTIME=true` |

## Enforcement rules

1. Deny by default; check permission (+ organization_id for customer).
2. Object-level org checks on every ID (ticket, invoice, document, licence).
3. Vendor permissions never create a hospital clinical session.
4. Evaluation blocks production side-effects (org create, real invitations, licence issue outside sandbox rules).
5. Invitation tokens are shown once, stored hashed, 48h expiry.
6. Approval decisions for customer role changes revoke sessions.

## Remaining software gaps

- Consolidate remaining commercial `role(user, …)` call sites to named permissions only.
- HttpOnly hospital web sessions.
- Hospital route guards fully switched to `CLINICAL_READ_ROLES` / `CLINICAL_IT_ROLES` (in progress).
- Dual-approver enforcement for every high-risk vendor action (offboarding partially covered).
