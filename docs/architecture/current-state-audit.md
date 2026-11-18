# PredictRx Sentinel: current-state audit

Audit date: 2026-11-15. Repository commit: 98b3973. This report contains no secret values or patient identifiers.

## Summary

PredictRx Sentinel is a hospital-local research prototype centered on a frozen, retrospective ICU sepsis-risk model. The codebase contains a Next.js App Router frontend, FastAPI clinical API, SQLite/PostgreSQL persistence, local account auth, OIDC JWT validation, role/unit authorization, FHIR/HL7v2/CSV/vendor adapters, clinical workflows, readiness governance and a separately implemented patient-free fleet heartbeat.

The current frontend is not yet the target product architecture. Routes are mostly top-level, one shared navigation shell is role-dependent, and login combines local account, PIN, OIDC token paste and demo role selection. There is no Customer Portal data model or comprehensive vendor operations domain. The evaluator launcher obtains a requested role from the demo-token API and uses the same service/data environment; it is not an isolated synthetic tenant.

The public demo is consolidated: one container runs Next.js, the FastAPI service and fleet console. This supports a hackathon deployment but does not establish separate hospital, vendor and evaluation security boundaries. Hospital-local operation is supported by the site deployment and local persistence options, but independent offline continuity still needs end-to-end verification.

The requested .agents/skills/predictrx-product/SKILL.md could not be found in the repository or available user skills directory. Root AGENTS.md and the supplied predictrx-codex-pack/AGENTS.md and PREDICTRX_MASTER_SPEC.md were read. User-provided research files and the pack are untracked; this audit does not stage or modify them.

## Runtime and repository map

- Frontend: frontend/. Package scripts: dev, build, start, lint, test. Installed versions: Next.js 16.4.2, React 19.3.1, Tailwind 3.4.13, TypeScript 5.6.3, Vitest 5.0.5. No major upgrade is indicated.
- Backend: backend/app/main.py; route modules under backend/app/api/routes; clinical engine under backend/app/services/engine.py.
- Persistence: backend/app/persistence.py and backend/app/records.py. StateStore supports SQLite and PostgreSQL, with engine state, relational operational records and append-only hash-chained audit events. Schema creation includes runtime CREATE TABLE IF NOT EXISTS. An Alembic chain exists under backend/migrations/versions for persistent state, pilot records and site accounts; new commercial schemas must use reviewed migrations.
- Edge service/tests: edge/.
- Vendor fleet console: control-plane/fleet_console.py and push_heartbeat.py. Site heartbeat is signed, schema-validated and allowlisted.
- Hospital/site deployment: docker-compose.site.yml. Public consolidated demo: docker-compose.public-demo.yml, infra/Dockerfile.demo and infra/demo-start.sh. The demo image includes the frozen model and de-identified public replay cases; it must not be given hospital patient data.
- Root .env exists but is ignored. This report inspected variable names from .env.example only; secret values were not read or printed.
- Frontend same-origin API/fleet rewrites are configured in frontend/next.config.js for the consolidated container.

## Existing route map

| Route | Current responsibility |
|---|---|
| / and /home | Public portal. Root exports the portal. Current homepage is a small overview with integration, evidence and adoption links. |
| /login | Local password/TOTP, PIN unlock, demo role form, OIDC token paste and evaluator gateway. |
| /evaluator | Five persona launcher. Calls the demo-token endpoint and navigates to existing workflows. |
| /icu and /dashboard | ICU overview; unit polling, risk/trust states, trends, alerts and ownership. Dashboard is an alias/export. |
| /patient/[id] | Patient/encounter risk, timeline, provenance, signal freshness, context and workflow components. |
| /chart and /ward | Bedside encounter charting and deterministic NEWS2 ward observations. NEWS2 is separate from the ICU sepsis model. |
| /alerts, /handoff, /staff, /profile | Alert review, handoff, roster/on-shift, account profile/avatar/preferences/device settings. |
| /hospital-admin, /admin/users, /admin/setup, /admin/shift-roster | Hospital admin landing, local users, setup/readiness and staff roster. |
| /integration, /connection | Feed/connector status, mappings, quarantine/spool, sample loading and connection ladder. |
| /pilot, /readiness, /operations | Silent pilot, site readiness/model passport and current-site operations. |
| /model, /evidence | Model evaluation/transparency and evidence/limitations. |
| /business, /docs, /api-reference, /workflows | Commercial hypothesis, documentation, API reference and workflow guide. |
| /super-admin | Operator landing with current-site diagnostics and vendor console links. |
| /judge, /judge-guide, /presentation | Existing judge/evaluator guide and presentation pages. |

No /app/*, /portal/*, /platform/* or /system-check route groups currently exist. Any migration must preserve aliases/redirects.

## API, data and identity

- FastAPI exposes health/ops plus versioned auth, patient, alert/audit, unit, care/NEWS2, observation, integration/EHR bridge, model/evidence, site/readiness/pilot and demo replay endpoints.
- Frontend calls APIs through frontend/lib/api.ts and polling hooks. Hospital data uses DATABASE_URL; SQLite is suitable for local setup, PostgreSQL is also supported.
- Clinical persistence includes observations, encounters, predictions, alerts, ownership, handoff, feedback/outcomes, connector events, quarantine/spool, profiles and audit. These records belong inside the hospital boundary.
- Roles include clinician, nurse, admin, operator and integration. FastAPI dependencies perform role/unit checks. Patient resolution enforces unit scope and silent-pilot blinding.
- Local password/PIN account management, password hashing, TOTP, disable/reset and session revocation exist. OIDC bearer JWT validation checks configured issuer/audience/JWKS and configured role/unit claims.
- Browser auth stores bearer tokens client-side; the target HttpOnly-cookie design is not implemented.
- Demo POST /v1/auth/demo-token is available only with DEMO_MODE=true, accepts caller-provided user ID and role, and is rate-limited. Evaluator UI uses it. This is unsafe as a production entry and is not equivalent to an isolated evaluation credential.
- /v1/auth/me returns role/unit/session metadata but no organization membership, entitlement, or workspace list. Sign-in does not resolve organization/site/workspace on the server.
- Operator is barred from most patient routes, but selected model/evidence and integration metadata endpoints include operator. Review individual dependencies before exposing any new vendor endpoint.
- Fleet payload allowlists are defined in backend/app/fleet.py and control-plane/fleet_console.py. Both must change together; no free text or patient/bed/user identifier may be added.
- No separate evaluation database, tenant/service credentials, isolated network, synthetic-only seeded identity, or side-effect adapters were found.

## Model invariants

- Artifact: ml/artifacts/models/latest/model.joblib.
- Version: v0.2.0-202609281906.
- FROZEN.json SHA-256: a7dcf5f4b2f00927c17d2468cba144b3db4642ccb5a9c946b484958a0413532d. Audit-time calculated artifact digest matched the manifest.
- Thresholds reside in the frozen manifest. Do not change the model, artifact, hash, thresholds, inference logic, TrustGate, clinical input validation, alert/readiness gating, audit semantics or API contracts as part of this product/frontend work.
- Inference is in backend/app/services/engine.py; TrustGate and clinical input contract are in backend/app/trustgate.py and backend/app/services/clinical_contract.py. Risk horizon is six hours where supported by the frozen model contract.
- NEWS2 is a separate deterministic ward score; it is not sent through the frozen ICU model.
- Evidence is retrospective public-data evaluation. No Bangladesh hospital validation, prospective benefit, mortality reduction, regulatory authorization or clinical-production readiness is established.

## Feature status

### Implemented and API-backed

- Local hospital API and SQLite/PostgreSQL persistence.
- Local accounts, OIDC validation, role/unit permissions, TOTP and session revocation primitives.
- ICU sepsis risk, trend, provenance, input-quality/freshness and TrustGate states.
- Encounter charting, admission/transfer/discharge, NEWS2, alert ownership/acknowledgement, handoff and audit.
- FHIR R4, HL7v2, CSV and vendor adapter ingestion; mapping, quarantine, spool and feed status.
- Site operating modes, readiness, silent-pilot workflows, model passport and signed metadata heartbeat.
- Basic fleet registration/status console separated from patient chart API.

### Partial or configuration-dependent

- Shared top-level frontend navigation is role-dependent but not a product-surface shell or authorized workspace switcher.
- Public site is not yet the requested editorial site; its data preview is explicitly illustrative and not an actual captured product screen.
- Login remains a multi-method page with a demo role selector and OIDC token paste.
- Evaluator is a launcher in the same runtime, not isolated evaluation.
- Super Admin page is a limited current-site view and link to fleet; fleet console is not full organization/licence/contract/billing/support operations.
- PWA/service worker and offline outbox code exist. This does not prove auth, inference, clinical UI and workflows remain available through public cloud loss.
- Telemetry schema is allowlisted, but hospital opt-in/configuration and no-PHI egress verification remain deployment tasks.

### Missing

- Customer Portal data/API for organization accounts, memberships, licences, contracts, documents, invoices, renewals, support and downloads.
- Vendor domain and APIs for organizations, sites, deployments, entitlements, contracts, billing, users/team, support, releases, model registry, security/compliance and audit operations.
- Server-resolved organization/site/workspace membership, entitlement enforcement, authorized workspace switcher and cookie-based unified sign-in.
- Separate synthetic evaluation runtime/tenant/account, reset process, side-effect sandbox adapters and isolation tests.
- Target route groups with backward-compatible redirects.
- Full public, hospital, customer and vendor visual systems; locally hosted typeface assets and visual/accessibility QA.
- Versioned migrations for new commercial/control-plane schema; the existing hospital Alembic chain does not cover those domains.
- Verified end-to-end hospital-local/offline deployment, backup/restore and update/rollback procedures.

## Risks and proposed phased plan

1. Keep demo role-token issuance disabled outside a fenced synthetic evaluation deployment. Current evaluator is not isolated.
2. Do not call browser role hiding an authorization boundary; enforce every new permission server-side.
3. Do not add invoice, licence, contract or hospital rows as fake operational data. Build clear empty/configuration states until backed by records.
4. Rework auth only with coordinated Next proxy/API cookie, CSRF, CORS and session design.
5. Keep site clinical DB, vendor metadata DB and evaluation DB separated. Do not make vendor operations access patient records.
6. Use a reviewed migration mechanism before adding durable customer/vendor objects; protect append-only audit semantics.
7. Phase order: (1) audit; (2) IA/tokens/shells; (3) public/sign-in; (4) clinical shell while preserving workflows; (5) customer data/API and portal; (6) vendor records/API and operations UI; (7) isolated evaluation deployment; (8) local/offline hardening, tests and documentation.
8. Any unsupported integration or legal/clinical decision remains explicitly unconfigured and documented; no clinical, commercial, customer, regulatory or performance claim is inferred.

## Audit verification

- Frontend installed versions and scripts, route source tree, FastAPI router declarations, auth dependencies, SQL schema definitions, deployment files, fleet allowlists, model manifest and artifact hash were inspected.
- No Dataset B evaluation was run; no secrets were printed; no patient records were read.
- Previous frontend build/typecheck/lint/tests had passed before this audit. The repo-local Python virtual environment was previously observed to point to a missing interpreter; backend and edge test results therefore remain unverified here.
- Continue implementation after this report. Run the relevant checks per phase and report unavailable/failing environments accurately.

## Work completed after the baseline audit

- Added docs/architecture/target-state.md and this audit report.
- Added a paper/ink/forest token set, separate clinical severity tokens, focus-visible treatment and reduced-motion support. Instrument Serif, IBM Plex Sans, IBM Plex Mono and Noto Sans Bengali now bundle locally through Fontsource packages; system fallbacks remain available.
- Restyled the public portal to use the institutional paper/forest palette and role-oriented navigation. Evidence statements remain retrospective and deployment claims remain qualified.
- Added /signin (the existing /login page implementation, with /login preserved), removed the visible demo role-selection form, and resolve the post-auth destination from the authenticated /v1/auth/workspaces response. This is site role routing, not yet organization/site entitlement routing. Browser bearer storage has since been replaced by an HttpOnly Next session cookie.
- Replaced the persona token launcher at /evaluator with a redirect to /system-check. The System Check page refuses to mint a production demo-role token and reports that the isolated evaluation environment is unavailable unless EVALUATION_SYSTEM_CHECK_URL points to a separate HTTPS (or local loopback) deployment. This is an honest disabled state, not a completed evaluation sandbox.
- Removed the frontend demo-token helper and persistent role-switch HUD. The backend /v1/auth/demo-token endpoint remains in unrestricted local DEMO_MODE for existing synthetic replay compatibility, but PUBLIC_DEMO_LOCKDOWN now disables that endpoint and demo identity headers on the public demo service. The public demo's Caddy front door also applies basic authentication to API paths. This is not a substitute for a physically or logically isolated evaluation deployment.
- Added /portal as a customer-portal entry with explicit unconfigured states; it has no customer record API and performs no billing/document/support operation.
- Added /app/* re-export routes for current clinical pages and /platform/overview alias to the existing operator page. Existing top-level URLs remain available.
- Added canonical clinical navigation and kept separate top-level site and platform entry points. Sign-in/System Check use a focused layout; the public site links to the Customer Portal. The operator view now distinguishes the existing heartbeat from unimplemented commercial controls. No backend schema, API, model, threshold, TrustGate or clinical workflow was changed.
- Added a Next server session path: local/PIN/IdP-token sign-in is validated by FastAPI, the browser receives an HttpOnly SameSite cookie, and the Next proxy attaches the bearer token to clinical requests. Mutations require a same-origin marker and origin check. The hospital web container now targets its local API at runtime; Caddy routes the session/proxy paths to Next. Organization membership and separate vendor/customer identity remain unimplemented.
- Canonical `/app/*` and `/platform/overview` routes now require a server-validated site workspace. The hospital API still enforces its own role and object permissions on every request. Legacy URLs remain compatibility routes and do not all have server layout guards.
- ICU polling now shows the last successful refresh and a refresh-failure state, and discards late responses after unit changes. Frontend verification: TypeScript, full ESLint, Vitest (4 files / 19 tests), and Next production build passed. Edge and standalone control-plane tests: 12 passed. The backend full suite returned 156 passed, 3 skipped and 1 failure: a round-trip test expected optional synthetic API encounters without enabling the simulation setting. The test now sets that option explicitly; its isolated rerun passed. No screenshots were captured.
