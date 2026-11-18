# Codex Start Prompt — PredictRx Sentinel

You are working inside the existing PredictRx Sentinel repository.

Read these files fully before editing:
1. `AGENTS.md`
2. `PREDICTRX_MASTER_SPEC.md`
3. `.agents/skills/predictrx-product/SKILL.md`

## Your mission
Turn the existing PredictRx Sentinel research prototype into a coherent product experience with:
- A distinctive editorial/institutional public website.
- One unified sign-in experience with server-side identity/organization/permission routing and no role dropdown.
- A separate Customer Portal for organization accounts, licences, contracts, documents, invoices, renewals and support.
- The existing Hospital Clinical System reorganized as a clear clinical workstation while preserving current ICU, patient, charting, ward/NEWS2, alerts, handoff, integration, readiness, pilot, local operations and audit features.
- A serious Vendor Control Plane / Super Admin for organization, site, deployment, licence, contract, document, billing, user, support, release, model-provenance, security and compliance operations.
- A small `Judge System Check` entry beneath normal sign-in. It must open an isolated synthetic evaluation environment using the same real product UI and workflows, not a separate fake judge dashboard.
- Hospital-local/offline operation with local authentication and clinical services independent of public cloud availability.

## First action — audit the actual repository
Do not start by replacing the UI. Inspect current routes, layouts, components, API calls, FastAPI services, database schema, auth/roles, model artifacts/hash, TrustGate/data quality, simulation, evaluator personas, tests, environment configuration and deployment. Do not reveal secret values. Write `docs/architecture/current-state-audit.md` with what exists, what works, what is partial/mocked, what is missing, the current route map and risks.

After the audit, continue with a phased implementation. Do not stop after presenting a plan. Make safe, reversible progress without waiting for approval for normal implementation work. Ask only if an essential decision cannot be resolved safely from the repository.

## Required design direction
- Public website: editorial/institutional medical technology, asymmetric grid, distinctive typography, warm paper/ink/forest palette, actual product screenshots, careful evidence statements.
- Hospital: calm clinical workstation, information-first, readable tables, patient timelines, source/freshness, model/version/provenance and alert workflows.
- Customer: professional account/document/contract/licence experience.
- Vendor: serious enterprise operations console, less card-based and more structured around tables/registers/audit.
- Fonts: Instrument Serif for selected large public display headings; IBM Plex Sans for application UI/body; IBM Plex Mono for hashes/IDs/logs. Optional Noto Sans Bengali. Self-host fonts/assets for local installs.
- Palette starting point: Paper `#F3F0E9`, Warm White `#FCFBF8`, Ink `#202B2C`, Forest `#28564E`, Muted Olive `#8B9279`, Copper `#B66E50`, Cool Grey `#E9ECEA`, Slate `#667471`.
- Clinical alert colours must be separate semantic tokens: critical red, high orange, moderate amber, low green, unavailable grey.
- Avoid generic AI-SaaS aesthetics, excessive rounded cards, gradients, glassmorphism, fake stats, glowing AI illustrations, stock-doctor hero imagery and decorative charts.

## Required security behaviour
- One sign-in visual experience; no user-selectable role dropdown.
- Server determines identity, organization, site, role, permissions and default workspace.
- Workspace switcher lists only authorized workspaces; every API rechecks authorization.
- Hospital local auth must function without internet/cloud dependency.
- Patient data, observations, patient-specific risk scores and patient-linked logs remain in the approved local hospital boundary by default.
- Vendor control plane receives only allowlisted operational metadata; no patient payload or patient-linked identifier.
- Vendor Super Admin has no blanket access to patient records.
- Evaluation account is pre-seeded in a physically/logically isolated synthetic evaluation tenant. It may explore all workspaces only in that evaluation environment. It cannot access production tenants, real hospital data, production secrets or real Root Admin privileges.
- Store evaluation username/password via secure deployment configuration/secret store, not source code or browser bundle. A publicly displayed credential is permitted only for the synthetic sandbox; otherwise offer one-click short-lived evaluation access. Rate-limit and audit access.
- Evaluation-side billing, emails, invoices, notifications, licence issuance and release operations use simulated adapters and have no real-world side effects.
- Only the small sign-in entry should say `Judge System Check`. Do not label normal application pages as judge mode. The hospital UI may show the truthful site/data provenance, such as `Evaluation Hospital · Synthetic data`.

## Preserve existing clinical work
Do not change the frozen ML model/artifacts, model hash, inference logic, risk thresholds, TrustGate, data validation, backend API contracts, audit behavior or clinical workflow semantics. Do not replace functioning APIs with mock data. Preserve old routes with redirects/aliases. Keep current-site operations separate from vendor fleet operations.

## Execution order
1. Repository audit and current-state report.
2. Target IA/route map and design tokens/font setup.
3. Shared layout primitives and navigation shells.
4. Public site and unified sign-in.
5. Hospital Clinical System refactor.
6. Customer Portal.
7. Vendor Control Plane.
8. Evaluation System Check and isolated seeded account.
9. Local/offline hardening, tests, documentation and visual QA.

Use the actual package scripts and installed versions. Do not upgrade major dependencies without justification. Test at each phase. At the end, report actual changed files/routes, migrations, env vars, tests/results, limitations and the clinical/legal/regulatory work still required before real clinical production.

**Do the audit first, then build. Do not turn the prototype into a fictional production clinical service through UI copy.**
