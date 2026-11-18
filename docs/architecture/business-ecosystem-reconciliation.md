# Auralis business & FDE ecosystem — reconciliation

Status date: 2026-11-18. Working tree audit against implementation. Brand: **Auralis** (product), **Aurie AI** (intelligence component). Prohibited visible marketing term from prior design instructions remains banned in UI.

## Confirmed existing functionality (pre-this slice)

- Vendor Control Plane + Customer Portal account service (orgs, sites, memberships, sessions).
- Commercial lifecycle: leads, inquiries, contacts, assessments → quotes → contracts → licences → invoices → payments → renewals.
- Operations: tickets/SLA, assets/lifecycle, compliance, training records, offboarding.
- Documents with encryption + scanner hook; enterprise CAPA/QMS.
- Hospital clinical surfaces: ICU, chart, alerts, handoff, ward/NEWS2, admin, integration/readiness/pilot routes.
- Public marketing redesign shells, for-hospitals/services/deployment/security/contact pages.
- Permission registry in `control-plane/permissions.py`.

## Partially implemented (extended here)

- CRM: legacy lead stages remain; **opportunity pipeline** with hospital-oriented stages added (`partnership_domain`).
- Contact: simple inquiry form remains at API; **consultation request** workflow added (preferred windows, pending confirmation).
- Assessments: commercial maturity assessments remain; **FDE readiness checklist passport** added (explicit states, no invented score).
- Training: operations training records remain; **education event programme** records added.
- Pricing: quote line items remain configurable; **internal unvalidated pricing assumption versions** stored privately (never public).

## Missing / future (not claimed operational)

- Live calendar provider with authorized availability slots.
- Supplier/OEM partnerships, equipment stock, leasing finance.
- Cross-hospital federated learning / pooled patient training.
- Automatic online learning.
- CME accreditation unless independently granted.
- Nationwide 24/7 managed IT unless staffed and contracted.
- Real hospital customers, paid contracts, clinical outcomes.

## Superseded / duplicate routes

| Historical | Canonical surface |
|---|---|
| `/dashboard` | Hospital workspace `/app` / `/icu` |
| `/super-admin` | Vendor `/platform/*` |
| `/business` | Public commercial approach (no prices) |
| `/evaluator` | Evaluation Environment |
| Competition `/judge*` `/presentation` | Restricted / non-primary nav |

Legacy paths preserved where still wired; do not delete working clinical features solely for age.

## Existing but incomplete business workflows

- Opportunity ↔ quote/contract linkage is associative (IDs), not forced state machine.
- Site profiles cover core fields; full 28-section passport UI is summarized in vendor partnership workspace (not every subsection has a dedicated page).
- Calendar confirmation is manual vendor status change, not Google/Outlook sync.

## Blocked by external hospital access

- Live HIS feeds, local validation evidence, biomedical OEM authorization, ethics/IRB, counsel-approved contracts, production IdP bind. See `REAL_WORLD_ACTION_PLAN.md`.

## Founder-provided strategic assumptions

- 7–8 year partnership horizon (planning framework, not contract length).
- Historical BDT package figures (site readiness 3L, silent pilot 5L, implementation 6L, annual licence 12L) — **unvalidated**, internal only.
- Hardware via suppliers vs owned stock — see founder decision register.

## Approved business policies (product constraints)

- No per-alert / per-patient / lives-saved pricing.
- No public price list from hypotheses.
- Clinical AI only after readiness + governance gates.
- Patient data under hospital-approved control; partnership ≠ unrestricted reuse.
- Education without purchase pressure or gift-for-adoption.

## Financial assumptions not validated

- All historical BDT figures above; margins; bed-band commercial bands pending cost analysis and discovery.

## Must not be represented as currently operational

- Paying hospital customers, supplier deals under negotiation, federated learning, continuous model improvement from live hospitals, universal equipment supply, CME unless granted.
