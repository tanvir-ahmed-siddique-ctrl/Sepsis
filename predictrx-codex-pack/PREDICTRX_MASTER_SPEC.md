# PredictRx Sentinel — Product, Architecture, UX and Implementation Master Specification

**Document purpose:** Single source of truth for the redesign and productization of the existing PredictRx Sentinel repository. This specification is written for Codex or another coding agent working inside the actual repository.

**Product status:** Research prototype with retrospective public-data evaluation and simulated product workflows. This specification describes a target product architecture and experience; it does not assert that every target capability already exists or that the product is currently authorized for clinical production.

---

## 0. How to use this specification

1. Read this file and the repository `AGENTS.md` before editing.
2. Audit the current repository. Do not assume the route inventory below reflects the current implementation exactly; verify it against source code.
3. Preserve the existing clinical product and backend behavior. Refactor progressively instead of replacing the application wholesale.
4. Build the real visual system and functional routes. Do not stop after producing a design proposal.
5. Where a production integration, legal interpretation, commercial term, or clinical threshold is not defined, build a safe configurable boundary and document the missing decision. Do not invent business or clinical facts.

## 1. Product definition and positioning

PredictRx Sentinel is a hospital-local ICU clinical decision-support platform centred on an ML model that estimates sepsis risk from time-based ICU vital-sign and laboratory observations. The intended workflow is to surface a risk signal for clinician review, with a target prediction horizon of approximately six hours where supported by the frozen model and its evaluation design.

The product experience must make the following visible and understandable:
- The estimated risk output and its timestamp.
- The model/version/provenance used for the score.
- The observations and data-quality state contributing to the score.
- Missing, stale, invalid, or insufficient inputs.
- Whether the system scored, withheld/abstained, or could not score.
- Risk history/trend and relevant observed clinical context.
- Alert ownership, acknowledgement, review, handoff, and audit trail.

### 1.1 Non-negotiable evidence boundaries

The current evidence is retrospective and based on public datasets. No Bangladesh hospital validation, prospective clinical study, demonstrated workflow safety, clinical benefit, mortality reduction, regulatory authorization, or live hospital EHR connection is established by the supplied product description.

The interface and website must not claim or imply otherwise. Do not:
- State that PredictRx diagnoses sepsis.
- Recommend treatment or autonomous intervention.
- Claim mortality reduction, improved outcomes, proven clinical benefit, or proven six-hour warning in a live hospital population.
- Claim Bangladesh validation, prospective validation, regulatory approval, DGDA authorization, ISO certification, HIPAA compliance, or other compliance unless verified evidence is present in the repository and explicitly approved for publication.
- Invent AUC, sensitivity, specificity, calibration, sample sizes, subgroup results, hospital/customer names, or other metrics.

The public evidence page must show the true evaluation scope, dataset split/evaluation approach where documented, limitations, model version/provenance, and pending validation steps. If evidence values are not available from verified repository material, omit them and report the gap.

## 2. Product surfaces: one brand, distinct security and operational boundaries

PredictRx must feel like one coherent product under one root domain, but it is not one shared application/database with universal permissions. Implement or progressively prepare five surfaces:

1. **Public Website** — marketing, product explanation, evidence, architecture, security/privacy overview, deployment, contact, resources, legal notices.
2. **Customer Portal** — hospital/customer account, organization/site information, entitlements/licences, contracts, documents, invoices/receipts, renewals, support, downloads.
3. **Hospital Clinical System** — hospital-local clinical workflows, patient/encounter data, ICU, ward/NEWS2, alerting, charting, handoff, integrations, hospital administration, local audit and operations.
4. **Vendor Control Plane / Super Admin** — PredictRx company-wide organization/site/deployment/licence/contract/document/billing/support/release/security/compliance operations. No blanket patient-record access.
5. **Evaluation Environment** — isolated evaluation deployment/tenant using the same application interfaces and workflows, synthetic data, pre-provisioned evaluation access, and simulated side effects. It is not a separate fake-looking product and is not connected to production tenants or real hospital data.

These surfaces may share the same visual system and a unified root domain, but must retain their own authorization, data stores/tenants, runtime configuration, session boundaries, and API permissions.

## 3. Domain and route architecture

Use one submitted root domain for the public entry experience, with paths and/or subdomains under the same root domain for the other surfaces. Do not assume that one URL means one process or one database.

Suggested public routes:

```text
/                         Public homepage
/platform                 Product overview (public route; do not conflict with authenticated platform app)
/product                  Product capabilities
/how-it-works             Acquire → Qualify → Score → Respond
/clinical-evidence        Evidence and limitations
/deployment               Hospital-local/on-prem architecture
/security                 Security and privacy overview
/licensing                Commercial/licensing overview
/resources                Resources landing
/resources/docs            Product/technical docs
/resources/api             API documentation
/resources/workflows       Workflow guides
/about                    Company/mission (only verified facts)
/contact                  Contact
/request-demo             Demo request
/signin                   Unified sign-in
/system-check             Evaluation entry (the only judge-specific public label)
/portal                   Customer Portal entry
/app                      Hospital application entry (reachable through appropriate hospital deployment)
/platform                 Vendor control plane (authenticated; use unambiguous route layout if public /platform exists)
```

Resolve route namespace collisions carefully. A safer final structure may be `/company/platform` for the public product page and `/platform/overview` for the authenticated vendor control plane. Choose a consistent route map after auditing existing routes; document it.

For hospital-local deployments, use a configurable site hostname under the same root domain with split-horizon/internal DNS where appropriate, or a hospital-configured internal hostname. Example only: `site-001.predictrx.com` resolves inside the hospital network to its local gateway. Do not expose the local clinical server publicly merely to make the demo convenient.

### 3.1 Suggested authenticated route groups

```text
/app
  /icu                         ICU command centre
  /patients                    Patient/encounter list
  /patients/[id]               Patient detail
  /chart                       Bedside charting
  /ward                        Ward observations / NEWS2
  /alerts                      Alert centre
  /handoff                     Shift handoff
  /staff                       Staff/on-shift workflow
  /profile                     Current user profile
  /admin
    /overview                  Hospital admin home
    /users                     Local users and roles
    /setup                     Site setup
    /shift-roster              Shift roster
    /integrations              Connectors, feeds and integration mapping
    /connections               Connection architecture/status
    /pilot                     Silent-pilot governance/configuration
    /readiness                 Site readiness
    /operations                Current site's local operations
    /audit                     Site audit and integrity
    /units                     Units/beds, only if backed by real feature/data
  /model                       Authenticated model transparency, if needed

/portal
  /overview                    Customer account overview
  /organization                Organization profile and contacts
  /sites                       Customer sites and deployments (metadata only)
  /licenses                    Licences and entitlements
  /contracts                   Contracts and agreements
  /documents                   Customer document library
  /invoices                    Quotations/invoices/receipts
  /support                     Support cases
  /downloads                   Approved installation/docs/release downloads
  /members                     Customer account members
  /profile                     Customer user profile

/platform/overview              Vendor control-plane overview
/platform/organizations         Organizations and hospitals
/platform/sites                Site registry
/platform/deployments          Deployment fleet and health metadata
/platform/licenses             License issuance and entitlements
/platform/contracts            Contracts and agreements
/platform/documents            Internal/customer documents
/platform/billing              Finance and billing operations
/platform/support              Support and SLA operations
/platform/users                Customer and internal user administration
/platform/team                 Internal staff and role administration
/platform/releases             Application releases and deployment packages
/platform/models               Model registry/provenance/release metadata
/platform/security             Security events, incidents and vulnerabilities
/platform/audit                 Vendor control-plane audit
/platform/compliance            Compliance and quality-management document library
/platform/settings              Platform configuration
```

### 3.2 Preserve and migrate existing routes

The supplied current route inventory is a starting map, not a statement of verified source code. Inspect every route and preserve all working capabilities. Suggested migration:

| Existing route | Suggested destination |
|---|---|
| `/` | `/` public homepage |
| `/login` | `/signin` (redirect old route) |
| `/evaluator` | `/system-check` (redirect or preserve as alias) |
| `/icu` | `/app/icu` |
| `/dashboard` | redirect to `/app/icu` |
| `/patient/[id]` | `/app/patients/[id]` |
| `/chart` | `/app/chart` |
| `/ward` | `/app/ward` |
| `/alerts` | `/app/alerts` |
| `/handoff` | `/app/handoff` |
| `/staff` | `/app/staff` |
| `/profile` | `/app/profile` |
| `/hospital-admin` | `/app/admin/overview` |
| `/admin/users` | `/app/admin/users` |
| `/admin/setup` | `/app/admin/setup` |
| `/admin/shift-roster` | `/app/admin/shift-roster` |
| `/integration` | `/app/admin/integrations` |
| `/connection` | `/app/admin/connections` |
| `/pilot` | `/app/admin/pilot` |
| `/readiness` | `/app/admin/readiness` |
| `/operations` | `/app/admin/operations` for the current hospital site only |
| `/super-admin` | `/platform/overview` |
| `/model` | public evidence summary or authorized `/app/model`, depending on current content and sensitivity |
| `/evidence` | `/clinical-evidence` |
| `/business` | `/licensing` |
| `/docs` | `/resources/docs` |
| `/api-reference` | `/resources/api` |
| `/workflows` | `/resources/workflows` |
| `/judge` | `/system-check` or a non-public internal alias; do not expose evaluator branding throughout the product |
| `/judge-guide` | `/system-check/guide` (optional; evaluator-only context) |
| `/presentation` | `/system-check/presentation` (optional; evaluator-only context) |

Keep backward-compatible redirects. Do not mix current-site operations with vendor fleet operations: local site operations belong under `/app/admin/operations`; vendor deployment fleet belongs under `/platform/deployments`.

## 4. Sign-in and identity experience

### 4.1 One unified sign-in experience

The public website has one refined `/signin` experience. It should not ask the user to select a role such as Super Admin, Doctor, Nurse, or Hospital Admin. The server authenticates the identity and resolves:
- User identity.
- Organization/customer membership.
- Hospital site membership (if any).
- Role(s) and scoped permissions.
- Workspace entitlements.
- Deployment/environment context.

After successful authentication, the server chooses the appropriate default destination. If the user has multiple authorized workspaces, show a workspace switcher containing only workspaces actually authorized for that identity. The switcher is navigation, not an authorization mechanism; every API operation must re-check permissions.

### 4.2 Separate auth authorities where required

A unified visual entry does not require one shared auth dependency. The public cloud control plane and hospital-local system may use separate identity stores/providers. A hospital installation must support local accounts and/or a hospital identity provider reachable inside its network. Do not make cloud authentication a dependency for local clinical access.

When running inside a hospital local deployment, `/signin` authenticates against that deployment's local identity configuration. When running on the public domain, it authenticates against the cloud/customer identity provider. Determine the authority through deployment/host configuration, not a user-controlled role selector.

### 4.3 Authentication requirements

- Secure password hashing using an appropriate modern password-hashing scheme.
- Secure HttpOnly cookies; SameSite and Secure attributes; CSRF defenses for cookie-based mutations.
- Session expiration, logout, revocation, device/session visibility where appropriate.
- Password reset and account recovery with secure token handling.
- Rate limiting and generic error messages to reduce account enumeration.
- MFA required for production vendor privileged accounts; support hospital MFA/SSO according to configuration.
- Audit login, logout, failed authentication, privilege changes, role changes, sensitive export/download and administrative operations.
- No secrets or passwords in client bundles, source code, logs, or committed configuration.

## 5. Evaluation access: full product experience, not a fake judge product

The evaluator should navigate the same product, visual design, routes, navigation, and workflows that a customer/user would see. There must not be a separate judge-only UI theme or recurring labels such as “Judge Dashboard”, “Judge Mode”, or “For Judges” across application screens.

The only prominent evaluator-specific entry label should be a small **“Judge System Check”** link beneath the normal sign-in form, leading to `/system-check`.

### 5.1 Evaluation access behaviour

- Provision one dedicated evaluation account in an isolated evaluation tenant/environment.
- The account can explore Hospital Clinical, Hospital Administration, Customer Portal, and Vendor Control Plane experiences using the same UI components and workflows.
- It must not become a production Super Admin account and must not access real production organizations, real hospital installations, real patient records, production credentials, production documents, or production infrastructure.
- Seed the account through a server-side seed/migration/bootstrap command or secure deployment configuration. Never commit its password or signing secret.
- For competition convenience, `/system-check` may display the isolated evaluation username/password from server-side evaluation configuration, or provide a one-click short-lived evaluation session. This public credential convenience is permitted only because the account is restricted to the synthetic sandbox. Rate-limit it, log access, and make it impossible to use against production.
- Evaluation access must be disabled by default outside the intended evaluation deployment (`EVALUATION_ACCESS_ENABLED=false` by default). Require an explicit deployment setting to enable it.
- Do not send real emails, SMS, payments, invoices to a gateway, real license activation/suspension, customer notifications, or production release commands from the evaluation environment. Use simulated adapters and clearly indicate when an action is simulated.
- Provide a deterministic seed/reset mechanism so the environment can be returned to a known state between evaluations. Do not reset while a session is actively using it without an explicit operator action.

### 5.2 Evaluation data provenance

Use the same clinical UI, but make the data source clear and truthful in a modest environment/site indicator, e.g. “Evaluation Hospital · Synthetic data” or “Data source: Generated simulation”. Do not repeatedly call it a judge dashboard. Never make synthetic patient records look like real patient data without provenance labels.

The current 10-bed ICU simulation and 5 staff-style personas may be preserved if they exist in the repository. Confirm actual seed values and current behavior before stating them in UI. Do not invent additional monitored patients, model metrics, hospital names, or system uptime.

### 5.3 Evaluation platform-operator persona

If the evaluator can inspect the vendor console, implement a separate `EvaluationOperator`/equivalent scope with access only to the evaluation organization's records. It must not inherit or impersonate real `RootAdmin` permissions. Production root-admin routes and secrets must remain unavailable.

## 6. Security domains, tenancy, and authorization

Use server-enforced roles, permissions, tenant/site scoping, and resource ownership. Frontend menu visibility is supplementary only.

Suggested roles (adapt to existing auth implementation):

### 6.1 Hospital roles
- `HospitalAdmin`: manages only their hospital's users, roles, units/beds, configuration, integrations, readiness, pilot governance, and site operations.
- `ICUConsultant`/`Clinician`: authorized clinical review, patient/encounter views, risk history, alerts, and handoff as configured.
- `Nurse`: authorized bedside charting, observations, alerts, handoff, and assigned patient/unit workflows.
- `ClinicalIT`: integration configuration, mapping, connector health and data-quality/quarantine workflows; patient access only when explicitly granted.
- `ClinicalViewer`: read-only view within an assigned site/unit scope.

### 6.2 Customer Portal roles
- `CustomerOwner`/`Director`: organization-level account, sites, licence, contracts and member administration.
- `ProcurementFinance`: quotations, invoices, payment/receipt records and contract documents.
- `TechnicalContact`: deployments metadata, installation docs, release notes and support tickets.
- `CustomerViewer`: explicitly permitted read-only account information.

### 6.3 Vendor roles
- `RootAdmin`: tightly restricted break-glass/global configuration; MFA, reason, strong audit, and optional dual approval for high-risk actions.
- `PlatformAdmin`: organizations, customer accounts, site registry and entitlement administration.
- `DeploymentEngineer`: installation, versions, rollout, deployment health and operational metadata.
- `SupportEngineer`: support cases and approved redacted diagnostics; no default patient-record access.
- `FinanceLegal`: contracts, quotes, invoices, receipts and customer commercial documents.
- `SecurityCompliance`: security/audit/compliance and incident workflows.

### 6.4 Evaluation role
- `EvaluationOperator` is a sandbox-only composite role scoped to the evaluation tenants/data and simulated actions. It must never be accepted by production authorization.

### 6.5 Authorization requirements
- Enforce tenant isolation at API and database/query layers.
- Enforce site/unit/resource ownership.
- Check object-level authorization on patient, document, invoice, license, support-ticket and deployment IDs to prevent IDOR.
- Separate vendor control-plane data from hospital clinical data.
- Deny by default; explicit least-privilege grants.
- Audit role changes, privilege elevation, exports, document downloads, licence changes, deployment changes, support access, and security configuration.
- No “impersonate customer” feature unless separately designed with approval, purpose, duration, visible session indicator, and immutable audit.

## 7. Data-plane and control-plane architecture

### 7.1 Hospital Clinical Data Plane (local)
Must host, within the hospital-approved environment:
- Clinical web application/assets.
- Local API/backend (preserve existing FastAPI services).
- Patient/encounter database and observations.
- Frozen ML inference service/artifacts.
- Input validation, freshness, missingness and TrustGate/data-quality logic.
- Clinical alerts, acknowledgement, handoff and audit records.
- Hospital-local auth/session service or locally reachable hospital IdP.
- Integration adapters/queues/quarantine for hospital sources.
- Local logs, encrypted backups, recovery/restore tooling.

### 7.2 Vendor Control Plane (cloud or company-operated environment)
May host:
- Customer organizations and account contacts.
- Site/deployment registry and deployment metadata.
- License/entitlement issuance and verification metadata.
- Contracts and commercial document records.
- Quotations, invoices and payment status entered/verified through configured business processes.
- Support tickets and non-PHI case metadata.
- Release package metadata and signed artifact distribution.
- Model registry metadata/provenance (not patient inference inputs/results).
- Platform security and administrative audit.
- Public website and documentation.

### 7.3 Metadata exchange
The local installation may communicate with the vendor control plane for approved operational metadata only, e.g. deployment ID, software version, licence status, service heartbeat, CPU/memory/disk health, connector up/down status and release-update status.

Implement a strict allowlist/schema for telemetry. Do not transmit patient names, MRNs, encounter identifiers, vitals, labs, patient-specific risk scores, notes, timelines, raw connector payloads, or patient-linkable logs. Redact identifiers and review whether timestamps/metrics could indirectly identify a patient. Telemetry must be configurable, documented, minimized, and disabled or limited until hospital approval.

Cloud disconnection must not stop local authentication, patient access, inference, core alerts, charting, or local audit. Local-to-cloud metadata sync may queue and resume later only for approved metadata.

## 8. Hospital-local/offline deployment requirements

The hospital installation must be designed to work in an isolated network:
- Self-host Next.js assets, fonts, icons, required libraries and application resources.
- No required runtime call to Google Fonts, external CDNs, analytics, advertising, maps, remote image APIs, or external telemetry for core clinical workflows.
- Local auth/session and authorization must function without public internet.
- Local API, DB, inference, alert, charting and audit workflows must function without public internet.
- Support configurable local DNS/hostname and TLS/certificate operations.
- Support hospital-controlled backups, restore testing, encrypted storage, key management, and documented disaster recovery.
- Provide health checks for frontend, API, DB, ML service, connector, queue and audit store. Show `unknown`, `degraded`, or `not configured` honestly; never default to green.
- Use versioned migrations, preflight validation, maintenance windows, rollback/restore plans, and signed software/model artifacts.
- No automatic public-cloud failover that copies patient data outside the approved hospital boundary.
- Document installation prerequisites, supported OS/container runtime, ports, DNS, TLS, storage, CPU/RAM, backup, restore, updates and network isolation. Derive actual supported values from code/tests; do not invent them.

License expiry or loss of vendor connectivity must not delete patient records or silently disable access to historical records. Define a clinically safe continuity policy with legal/clinical owner review. Commercial enforcement must not create an unsafe clinical outage.

## 9. Hospital Clinical Workspace — product structure

Use a serious clinical workstation layout: stable left navigation, compact top header with hospital/site/unit/environment, clear patient/encounter context, dense readable tables, properly labelled charts, meaningful status indicators, and predictable actions.

### 9.1 Core clinical pages
- ICU Command Centre: unit overview, monitored encounters, risk categories, latest scoring, trends, alert queue, data freshness, feed/source state.
- Patient/Encounter List: filter/search/sort by authorized unit, encounter state, risk band, freshness, alert state.
- Patient Detail: patient/encounter context; risk estimate and prediction horizon where valid; score timestamp; trend/history; relevant vital/lab observations; data completeness/freshness; TrustGate state; missing/stale/invalid signals; model version/hash; explanation/contributing features with limitations; alert history; clinician review/acknowledgement; audit trail.
- Bedside Charting: observations and encounter/bed workflow as implemented by existing backend.
- Ward / NEWS2: preserve current NEWS2 workflows and their actual evidence/logic; do not invent scoring thresholds.
- Alerts: open/resolved alerts, ownership, acknowledgement, review, escalation and audit.
- Handoff: shift handoff, assigned care team and communication status.
- Staff / Shift Roster: staff and on-shift workflows according to current authorization.
- Profile: current user preferences and security/session options.

### 9.2 Hospital administration pages
- Users & Roles: local accounts, memberships, permissions, disable/reset flows.
- Site Setup: site identity, units, bed configuration, operational prerequisites.
- Shift Roster: assigned roles/shifts.
- Integration Hub: connectors, feeds, last successful exchange, schema/version, mapping, validation, quarantine and replay/reprocess status.
- Connection page: architecture and connection path; separate documentation from actual live connector status.
- Silent Pilot: governance settings and approved evaluation workflow; never imply it is a clinical deployment authorization.
- Readiness: explicit gates, evidence, owner, timestamp and blockers.
- Site Operations: current hospital deployment's DB/writer/read-only/connector/model/audit/service metadata. Do not show vendor fleet data here.
- Audit Integrity: local audit verification and integrity status.

### 9.3 Clinical visual rules
- Risk is not diagnosis. Use wording such as “model-estimated risk” or “risk estimate”.
- Show score time, input window, prediction horizon, model version, source and freshness near the score.
- Show stale/missing/insufficient data and abstention clearly. Do not colour a missing score as low risk.
- Distinguish patient observation values from model outputs and clinician-entered values.
- Charts need axis labels, units, timestamps, sensible ranges, readable tooltips, empty states and accessibility alternatives.
- Do not use colour alone to communicate severity; include text/icon/labels.
- Do not invent thresholds or risk band definitions. Fetch documented thresholds/configuration from the current model/backend; if absent, display the existing verified output without inventing bands.
- No autonomous clinical action or treatment recommendation.
- Make critical/high attention visible without alarmist animation or flashing.

## 10. Customer Portal

A customer/procurement/business user should not have to enter the ICU clinical application to manage the commercial relationship.

Include:
- Organization profile, authorized contacts, customer members.
- Registered customer sites and deployment metadata (not patient data).
- Product edition, licensed modules, user-seat/bed/unit entitlements where contractually configured.
- Licence certificate, issue/effective/expiry dates, renewal request and current status.
- Contract and agreement list with version/status/effective dates/signature status.
- Private customer document download area.
- Quotations, invoices, receipt/payment status, downloadable commercial documents.
- Installation guides, release notes and approved software/document downloads.
- Support ticket creation, status, attachments subject to strict no-PHI guidance, SLA/status and resolution history.
- Renewal and change requests.

Do not invent a payment gateway or automatically charge a customer. Until a verified payment integration exists, implement manual invoice/payment-record workflows and clearly label unconfigured integrations. Do not expose hospital patient records in this portal.

## 11. Vendor Control Plane / Super Admin

The Vendor Control Plane is an internal enterprise operations console. It must support company-wide operations while avoiding default access to hospital patient records.

### 11.1 Modules
1. Platform Overview: real counts/statuses derived from registered records; empty states when no records; no fake fleet metrics.
2. Organizations & Hospitals: customer org profiles, contacts, status, contract references, sites.
3. Site Registry: site IDs, ownership, deployment target/mode, modules, support contacts.
4. Deployments & Fleet: software version, last heartbeat, local services health metadata, update channel, installation status, rollback/maintenance status.
5. Licences & Entitlements: create/issue/revoke/renew signed licence, site/deployment binding, product edition, modules, limits, effective/expiry dates, support/update entitlement, offline verification/grace policy.
6. Contracts & Agreements: MSA, DPA, pilot agreement/SOW, amendments, signatures, renewal/termination status.
7. Document Centre: private file repository, document IDs, version, owner, customer scope, effective/review/expiry date, approval/signature status, access/download audit.
8. Billing & Finance: quotations, invoices, receipts, payment reconciliation/status, credit notes/refunds only if supported by real process; no unconfigured automatic payment actions.
9. Customer Account Management: portal users, organization memberships, invitation/reset/deactivation.
10. Internal Team & Roles: least-privilege staff access and MFA.
11. Support & Service: tickets, severity, SLA, assignment, escalation, resolution, approved diagnostics.
12. Release Management: application versions, signed installation packages, changelogs, compatibility, rollout channels and rollback status.
13. Model Registry: model name/version/hash, artifact provenance, frozen status, approved release record, compatibility; never mutate the frozen model through casual UI edits.
14. Security & Audit: administrative events, access reviews, incidents, vulnerabilities, exceptions and remediation.
15. Compliance & Quality Library: policies, SOPs, risk management, verification/validation reports, CAPA, training and assessment artifacts.
16. Platform Settings: environment-level settings with safe change review and audit.

### 11.2 Root/admin safeguards
- MFA and re-authentication for sensitive actions.
- Reason/ticket reference for break-glass access.
- Time-limited and approved support access.
- Immutable/tamper-evident admin audit where technically feasible.
- Dual approval for high-risk production operations where appropriate.
- No blanket patient-data browsing/export feature.
- Separate production and evaluation credentials/configuration.

## 12. Document & Governance Centre

Maintain distinct repositories/scopes:

### Commercial/customer documents
- Master Service Agreement (MSA).
- Data Processing Agreement (DPA), when applicable.
- Pilot agreement / Statement of Work.
- Quotations, purchase orders, invoices and receipts.
- Licence certificates and renewal/termination records.
- Customer correspondence and support documents.

### Product/technical documents
- Product architecture and deployment guide.
- Installation/hardening guide and system requirements.
- Network/port/DNS/TLS guide.
- API and FHIR/HL7 mapping documents.
- Model card, intended use, provenance, evaluation and limitations.
- Test, verification and validation reports.
- SBOM, release notes, migration and rollback guides.
- Backup/restore and disaster-recovery guides.

### Security/legal/quality documents
- Privacy notice, terms, acceptable use and data retention/deletion policy.
- Security policy, incident response, vulnerability disclosure.
- Risk management and clinical safety documentation.
- Software lifecycle, requirements traceability, verification and release evidence.
- Quality management procedures, training records, audit and CAPA records.
- Applicable regulatory correspondence and approval evidence only when real.

Every document needs metadata: immutable ID, title/type, version, owner, organization/site scope, classification, effective date, review/expiry date, approval/signature state, access/download audit, retention rule. Use private object storage, encryption, malware scanning, content-type/size validation, versioning, access-controlled short-lived download URLs, and retention policies. Never put patient records or raw clinical exports in the general vendor Document Centre.

These are product capabilities and document categories, not legal templates guaranteed valid in Bangladesh. Legal documents must be drafted/reviewed by qualified counsel for the actual jurisdictions, intended use and contracts.

## 13. Public Website and trust centre

### 13.1 Visual concept
Public site style: **Editorial / Institutional Medical Technology**.
- Asymmetric editorial grid, expressive typography, restrained photography and actual product imagery.
- Warm paper/warm white background, dark ink, forest accent, muted olive and occasional copper.
- Avoid generic AI startup templates, glowing gradients, floating cards and fake doctor/brain imagery.
- Use actual screenshots from the application for product proof. If the screenshots show synthetic data, label the source accurately.
- Do not use generated clinical imagery as evidence or imply it is a real hospital.

### 13.2 Public pages
- Home: concise positioning, actual product preview, product workflow, deployment choice, evidence boundary, CTA.
- Product: capabilities and intended users.
- How it works: Acquire → Qualify → Score → Respond, without overstating automation.
- Clinical Evidence: retrospective scope, metrics only if verified, methodology, limitations, pending validation.
- Deployment: local/on-prem architecture, data boundary, connectivity and integration prerequisites.
- Security & Privacy: controls actually implemented vs planned; data flow and telemetry policy.
- Licensing: editions/modules and contact for commercial terms; do not fabricate price or offer.
- Resources: docs, technical/API reference, workflows, release notes where public.
- About: only verified company/team information.
- Contact / Request Demo: validated lead form, consent/notice, spam protection, secure handling.

### 13.3 Legal/trust pages
Prepare structured routes/content for:
- Privacy Policy / Privacy Notice.
- Terms of Service.
- Acceptable Use Policy.
- Cookie notice only if cookies/tracking require it; explain essential authentication cookies.
- AI Transparency / Model Limitations.
- Intended Use and Intended Users.
- Clinical Safety and Limitations.
- Security Overview and Vulnerability Reporting.
- Data Retention and Deletion.
- Data rights/contact/complaints.
- Incident reporting.
- Regulatory status.
- Subprocessor/data-flow disclosure where relevant.

Do not invent legal wording or claim that a draft is legally sufficient. Mark draft pages clearly as requiring qualified legal/regulatory review before commercial publication. Do not claim HIPAA, DGDA, ISO or other compliance/approval without evidence and appropriate review. Verify current Bangladesh and any target-market requirements with qualified counsel/regulatory specialists before making claims.

## 14. Visual design system

### 14.1 Brand direction
Brand concept: **Editorial Clinical Technology**.
Suggested brand line (not mandatory; verify with user/brand owner before changing existing approved copy): “A clearer view of critical care.”

Public website = editorial/institutional. Hospital = clinical workstation. Customer = institutional account portal. Vendor = enterprise operations console. Same identity, distinct density and navigation.

### 14.2 Typography
Preferred stack:
- **Instrument Serif**: selective public-site display headlines and editorial moments only. Do not use for clinical tables, labels, long body text, alerts or dense UI.
- **IBM Plex Sans**: primary application UI, public body, labels, tables, forms, clinical content.
- **IBM Plex Mono**: model hash, IDs, version strings, log/event codes, technical values.
- **Noto Sans Bengali**: optional future Bengali localization.

Self-host fonts and check font licences. Avoid remote font/CDN dependencies in hospital-local deployments. If Instrument Serif harms readability in small display sizes, use it only for large public display headings.

Suggested type scale (adjust after implementation and responsive testing):
- Public hero display: 64–76px desktop, responsively scaled down; Instrument Serif.
- Public section display: 40–48px; Instrument Serif or IBM Plex Sans depending on composition.
- Public body: 17–18px IBM Plex Sans.
- Application page title: 28–32px IBM Plex Sans semibold.
- Application section title: 18–22px.
- Clinical body: 14–16px with comfortable line height.
- Dense data table: 13–14px only where legible; never make key clinical values tiny.
- IDs/hashes: 12–13px IBM Plex Mono.

### 14.3 Brand palette
Initial proposed tokens:

| Token | Hex | Usage |
|---|---|---|
| Paper | `#F3F0E9` | Public site background/sections |
| Warm White | `#FCFBF8` | Public surface |
| Ink | `#202B2C` | Main text |
| Forest | `#28564E` | Brand/primary action |
| Muted Olive | `#8B9279` | Restrained secondary accent |
| Copper | `#B66E50` | Occasional editorial accent only |
| Cool Grey | `#E9ECEA` | Neutral UI surface/border |
| Slate | `#667471` | Secondary text |

These are starting tokens. Verify accessible contrast, focus visibility, dark text legibility, disabled states, and status semantics before finalization. Hospital interface may use a cooler neutral surface than the public marketing site while remaining within the same brand identity.

### 14.4 Clinical semantic tokens
Use separate tokens, not the brand palette:
- Critical: red.
- High: orange.
- Moderate: amber.
- Low: green.
- Unavailable/stale/unknown: grey.

Use both textual labels and non-colour indicators. Never equate unavailable/missing with low risk. Use only verified backend risk bands/thresholds.

### 14.5 Layout and component behaviour
- Prefer clear grid, typographic hierarchy and whitespace over repeated card grids.
- Public website can use expressive asymmetric layouts and editorial rules.
- Clinical pages should prioritize compact navigation, patient context, dense readable tables, clear filters and charts.
- Vendor console should prioritize tables, searchable registers, filters, detail panels, audit timelines, document lists and operational status.
- Customer Portal should prioritize account hierarchy, contract/licence status and document/action clarity.
- Use restrained border radius (generally 4–8px for operational controls; larger radius only where visually justified). Do not round every container excessively.
- Avoid large drop shadows, gradients, glassmorphism and needless animation.
- Use Lucide icons consistently; no emoji as primary navigation icons.
- Use Motion only for subtle transitions that do not impede clinical work.
- Use shadcn/ui selectively as component primitives; do not let its default template dictate the whole brand.
- Use Recharts only where charts improve clinical/operational understanding; label units, timestamps and series. Do not add decorative charts.

### 14.6 Accessibility and responsive behaviour
- WCAG 2.2 AA target where applicable; keyboard navigation, focus indication, semantic labels, contrast and screen-reader names.
- Clinical alert status must not rely on colour alone.
- Respect reduced-motion preferences.
- Support standard desktop clinical workstation sizes and tablets. Define mobile behaviour based on workflows; do not force a dense ICU workstation into a tiny mobile layout without deliberate prioritization.
- Ensure tables have responsive strategy, not merely horizontal overflow for every page.

## 15. Technical implementation guidance

### 15.1 Frontend
Existing stack is reported as Next.js + Tailwind; inspect actual versions before changes. TypeScript is preferred if existing project uses it. Use current project conventions; do not upgrade major framework versions without a clear need.

Suggested libraries where compatible and useful:
- shadcn/ui + Radix primitives for accessible controls.
- IBM Plex fonts / Instrument Serif self-hosted assets.
- Lucide icons.
- Recharts for purposeful charts.
- Motion for restrained motion.
- React Hook Form + Zod if compatible with existing form architecture.

Do not add libraries merely for the sake of the stack. Audit current dependencies first.

### 15.2 Backend and APIs
The existing backend is reported to include FastAPI and existing clinical workflows. Inspect actual services, route definitions, schemas, data models and tests. Preserve contracts. Create an API/service adapter layer for the new surfaces rather than duplicating scoring logic.

Never put clinical inference logic in the frontend. The frontend consumes authorized backend APIs and accurately renders their state.

### 15.3 Suggested repository organization
Adapt to existing structure rather than forcing a rewrite:

```text
app/
  (marketing)/
  (auth)/
  (hospital)/app/
  (customer)/portal/
  (vendor)/platform/
  (evaluation)/system-check/
components/
  ui/
  marketing/
  clinical/
  customer/
  platform/
  shared/
  charts/
lib/
  auth/
  permissions/
  api/
  config/
  telemetry/
  formatting/
styles/
```

Use Next.js route groups/layouts where appropriate. Ensure server/client component boundaries are intentional. Do not expose secrets through `NEXT_PUBLIC_*` variables.

### 15.4 Environment configuration
Use explicit environment-specific config and validate required variables at startup. Examples (names can be adapted):

```text
APP_ENV=development|evaluation|staging|production|hospital-local
PUBLIC_BASE_URL=
AUTH_MODE=cloud|local|hospital-sso
EVALUATION_ACCESS_ENABLED=false
EVALUATION_DEMO_USERNAME=
EVALUATION_DEMO_PASSWORD=
EVALUATION_TENANT_ID=
EVALUATION_SESSION_SECRET=
CONTROL_PLANE_URL=
LOCAL_API_BASE_URL=
TELEMETRY_ENABLED=false
TELEMETRY_ALLOWLIST_VERSION=
LICENSE_PUBLIC_KEY=
LICENSE_SIGNING_KEY=       # vendor signing service only; never deployed to hospital frontend
```

Do not blindly implement all names if the repo already has an environment convention. Keep signing private keys in the control plane/secret store; local installations only need the public verification key or a secure equivalent. Never log secrets.

### 15.5 Data and storage boundaries
- Vendor DB: organizations, site/deployment metadata, accounts, licences, contracts, docs metadata, invoices, support and control-plane audit.
- Hospital DB: patients, encounters, observations, model inference records, alerts, charting, handoff, staff/site config, local audit and integration records.
- Evaluation DB: seeded synthetic evaluation tenant only; never share production DB credentials or tables without hard isolation.
- Document object storage: private, encrypted, scoped, versioned, scanned; no clinical payloads.

Physical separation is preferred for the evaluation environment and hospital data plane. If a shared infrastructure is temporarily used for the evaluation sandbox, enforce separate databases/credentials, network and secret boundaries, and prove no cross-environment data access. Do not treat a tenant ID filter alone as sufficient isolation for production-sensitive data.

## 16. Licensing design

Use per-hospital/per-site licensing with configurable entitlements, not a rigid hardcoded plan. A licence record may include:
- Licence ID and signed claims.
- Organization ID, site ID, deployment ID.
- Product edition and enabled modules.
- Maximum users/seats, beds/units if contractually defined.
- Effective/expiry dates.
- Support and update entitlement.
- Offline verification and grace/continuity policy.
- Issuer, signature algorithm/key ID, issue/revocation history.

Hospital local verifies signed license using a public key. Signing private key remains in controlled vendor infrastructure. Avoid online callback as a mandatory dependency for local inference or clinical workflows. Do not expose patient information in license checks. Expiry must not delete records or abruptly block safe access to existing clinical records. All issuance/renewal/revocation is audited.

Do not invent commercial prices, tax treatment, contract clauses or user limits. Admin UI may support configurable values and manual quotes until approved business policy exists.

## 17. Security, privacy, legal and regulatory workstream

This section is a checklist for engineering and review, not a claim of legal compliance.

- Create a data inventory and data-flow diagram for each environment.
- Document controller/processor roles and customer responsibilities with qualified counsel.
- Review the current applicable Bangladesh privacy, cybersecurity, health-sector, medical-device and procurement requirements; obtain legal/regulatory advice before market or clinical claims.
- Verify current DGDA medical-device/SaMD classification and applicable authorization pathway for the exact intended use and deployment model.
- Create privacy impact/data protection assessment as appropriate.
- Create threat model, security architecture, vulnerability disclosure and incident response.
- Implement least privilege, MFA, secret management, encryption in transit/at rest, audit, backup/restore and vulnerability management.
- Build requirements traceability, software verification/validation, risk management and release controls appropriate to applicable medical software obligations.
- Consider relevant standards/frameworks (e.g. ISO 13485, ISO 14971, IEC 62304, IEC 81001-5-1, OWASP ASVS, HL7 FHIR) only as applicable; do not claim conformity/certification without assessment/evidence.
- Clinical validation, Bangladesh-local evaluation, ethics requirements, hospital commissioning, training and clinical governance must be completed as applicable before clinical production use.
- Keep retrospective prototype, technical pilot, clinical validation and authorized production as separate readiness states.

## 18. Execution plan for Codex

Codex must proceed in the following phases. Do not make a large destructive rewrite in one pass.

### Phase 0 — Repository audit (first action)
Inspect:
- Repository tree and instructions (`AGENTS.md`, `README`, package manifests, lockfiles, deployment files).
- Next.js/Tailwind/React versions and current design system.
- All frontend routes, layouts, components and styles.
- API endpoints, FastAPI services, schemas, auth, role logic and tenant handling.
- Database schema/migrations/seed data.
- Frozen model artifact, version/hash, inference path, TrustGate/data validation and scoring logic.
- Existing evaluator personas, simulation feed and generated data.
- Existing tests, lint/typecheck/build scripts, CI and deployment setup.
- Existing secrets/environment variables by name only; never print secret values.

Produce `docs/architecture/current-state-audit.md` with:
- What exists and where.
- What currently works.
- What is partial/mocked/demo-only.
- Current route inventory.
- API/data dependency map.
- Current auth/role model and gaps.
- What must not change.
- Risks and phased implementation proposal.

Do not stop here: continue to Phase 1 after the audit unless a genuine blocker makes safe implementation impossible.

### Phase 1 — Information architecture and design foundation
- Implement design tokens and font strategy.
- Build navigation/layout shells for public, hospital, customer, vendor and evaluation surfaces.
- Establish route guards and server permission helpers based on actual backend/auth capabilities.
- Keep old routes redirecting to new routes.
- Build responsive primitives and accessibility states.
- Create visual QA screenshots for key viewports where project tooling permits.

### Phase 2 — Public Website and Sign-in
- Build public pages and trust/evidence/deployment content using only verified information.
- Implement unified `/signin` with server-side destination resolution.
- No role dropdown.
- Keep public `Judge System Check` link small and only in the sign-in context.
- Implement contact/demo form with server validation, spam protection and no fabricated success.

### Phase 3 — Hospital Clinical Workspace
- Refactor current `/icu`, patient, chart, ward, alerts, handoff, staff, profile, hospital admin, integrations, pilot, readiness and operations screens into the new design.
- Preserve backend workflows and scoring behavior.
- Ensure data provenance, input freshness, model identity and abstention states are visible.
- Implement local/offline asset behavior and local auth integration where supported.

### Phase 4 — Customer Portal
- Build organization account, licence, documents, invoices, support and downloads.
- Use real backend records where they exist. If absent, build model/API contracts and clearly labelled evaluation-only simulated behavior; do not present it as a live payment/document/legal process.

### Phase 5 — Vendor Control Plane
- Build organizations, sites, deployments, licenses, contracts/docs, billing, users/team, support, releases/model registry, security/audit and compliance library.
- Enforce vendor role separation and no default patient record access.
- Keep site-level operations and vendor fleet separate.

### Phase 6 — Evaluation access
- Build `/system-check` with evaluation access configured from server-side secrets/seed process.
- Ensure one evaluation identity can explore all workspaces inside the evaluation environment only.
- Use same production UI and same route structures where possible.
- Disable real-world side effects; use sandbox adapters.
- Seed deterministic synthetic data and provide safe reset tooling.
- Add environment guard tests proving evaluation credentials cannot authenticate against production and production admin credentials cannot be loaded into evaluation.

### Phase 7 — Local deployment and hardening
- Verify hospital-local build uses only self-hosted assets/fonts.
- Verify no external call is required for core local workflows.
- Verify auth/inference/DB/clinical views work when control plane/internet is unreachable.
- Verify telemetry allowlist and no patient payload leakage.
- Verify backup/restore, migration, update, rollback, TLS, secrets and security headers.
- Document deployment and support operations using actual verified configuration.

### Phase 8 — QA and release evidence
- Run unit, integration, API authorization, tenant-isolation, UI, accessibility, build, lint, typecheck and security tests that exist or can be added safely.
- Add tests for no role-selector escalation, no cross-tenant access, evaluation isolation, local offline functionality, no PHI telemetry, licence continuity, and no accidental payment/email/release side effects in evaluation.
- Compare critical UI pages at desktop and tablet sizes.
- Report all passing and failing tests accurately.
- Produce `docs/architecture/target-state.md`, route map, data-flow map, role/permission matrix, environment variable reference, local deployment guide, evaluation guide, security checklist, and remaining production/clinical/regulatory gaps.

## 19. Acceptance criteria

The redesign is not complete until the following have been addressed or explicitly recorded as blocked/not implemented:

### Product and design
- [ ] Public website has distinctive editorial/institutional design and authentic product visuals.
- [ ] Hospital interface is a calm, dense, readable clinical workstation.
- [ ] Customer portal is separate from clinical workflows.
- [ ] Vendor control plane is a real operations console, not a generic stats dashboard.
- [ ] Typeface, palette, spacing, component and responsive behavior are consistent.
- [ ] No generic AI-SaaS visual clichés or invented claims.

### Routing and identity
- [ ] One root-domain user experience.
- [ ] Unified sign-in, no self-selected role dropdown.
- [ ] Server-side identity/membership/permission-based routing.
- [ ] Workspace switcher only lists authorized workspaces.
- [ ] Hospital local authentication works independently of cloud where configured.
- [ ] Existing routes have compatibility redirects.

### Evaluation
- [ ] One pre-provisioned evaluation account or short-lived entry flow.
- [ ] Evaluation can access the full product UI within isolated sandbox.
- [ ] Same product interface; no pervasive judge-specific branding.
- [ ] Only `/system-check` is explicitly evaluator-specific.
- [ ] Evaluation data is synthetic and visibly attributed.
- [ ] Evaluation cannot access real hospitals, production admin, production secrets or patient data.
- [ ] Evaluation side effects are sandboxed.

### Security and privacy
- [ ] Server/API authorization and object-level tenant checks.
- [ ] Vendor operator cannot freely browse patient records.
- [ ] Hospital data remains local by default.
- [ ] Telemetry allowlist prevents PHI/patient payload egress.
- [ ] Local app has no required external asset/font/service dependency.
- [ ] Privileged changes are audited.
- [ ] Secrets are not committed or exposed to browser.

### Clinical truth
- [ ] Score, time, model version, data quality and source are clear.
- [ ] Missing/stale/abstained outputs cannot appear as low risk.
- [ ] No fabricated metrics, thresholds, partnerships, regulatory claims or outcomes.
- [ ] Existing frozen model/inference logic and contracts are preserved.

### Operational completeness
- [ ] Customer documents/licences/billing/support have honest configured/unconfigured states.
- [ ] Document centre access, encryption, versioning and audit are implemented or scoped.
- [ ] Licence expiry does not delete data or create unsafe clinical interruption.
- [ ] Local deployment, backup/restore, update/rollback and support procedures are documented.
- [ ] Tests and remaining gaps are reported truthfully.

## 20. Required final deliverables from Codex

At the end of implementation provide:
1. Current-state audit and target-state architecture.
2. Updated route map and redirects.
3. Public website, sign-in, hospital, customer, vendor and evaluation UI.
4. Role/permission matrix and server-side authorization implementation or explicit gaps.
5. Data-flow/security boundary diagram.
6. Evaluation-account seeding and safe reset instructions.
7. Environment variable reference with no secrets.
8. Hospital-local/offline deployment guide.
9. Customer Portal and Vendor Control Plane operations guide.
10. Document/licence lifecycle specification.
11. Tests run with actual results.
12. Exact list of unimplemented features, external integrations, legal/regulatory reviews and clinical validation still required before real clinical production.

**Final instruction:** Build the most complete, coherent, truthful product experience the existing repository safely supports. Do not turn a research prototype into a fictional production hospital system through UI copy. Preserve the real clinical core, add the missing company/product operations around it, and make every environment boundary explicit and testable.
