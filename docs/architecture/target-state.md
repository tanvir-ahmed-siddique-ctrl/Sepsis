# Product information architecture: incremental target

This is a routing and boundary target, not a claim that every surface or entitlement service is implemented.

## Implementation checkpoint · 2026-11-15

- Phase 0 audit: completed in `current-state-audit.md`.
- Current API role boundaries: documented in `role-permission-matrix.md`; organization and workspace membership are still absent.
- Phase 1 foundation: palette and semantic alert tokens are in place; `/app/*`, `/platform/*`, `/portal`, `/signin`, and `/system-check` entry routes exist. Existing clinical page implementations remain the source of truth behind route aliases.
- Phase 2 public/sign-in: public site and focused sign-in have been updated. The visible role chooser and persistent role-switch HUD are removed. The sign-in destination is returned by the API; canonical hospital and operator entry routes now check the server-held session and authorized site workspace.
- Current sign-in reads `/v1/auth/workspaces`; the backend resolves supported site workspaces and their default path, and the header lists only those returned destinations. The response has no organization membership because the organization domain is not implemented. The browser now uses a Next session proxy with an HttpOnly, SameSite cookie; FastAPI still verifies every forwarded bearer request. The legacy browser sessionStorage token is removed on load.
- Public-demo lockdown now rejects the legacy demo-token endpoint and demo identity headers; this protects that service but requires a separately configured judge sign-in path before evaluation use.
- Evaluation: disabled unless a separate HTTPS evaluation URL is configured. The public demo API still has its legacy `DEMO_MODE` token endpoint; it is not an isolated evaluation deployment and must not be treated as one.
- Customer and vendor commercial records: not implemented. The portal and operator screens expose explicit configuration gaps; there are no fabricated accounts, contracts, invoices, licences, or support cases.
- Not yet completed: responsive/accessibility visual review, organization membership resolution, clinical page visual refactor, customer and vendor APIs/data, isolated evaluation tenant, and offline boundary verification. Instrument Serif, IBM Plex Sans, IBM Plex Mono and Noto Sans Bengali now bundle as local assets.

## Public

- `/` editorial public homepage.
- `/product`, `/how-it-works`, `/clinical-evidence`, `/deployment`, `/security`, `/licensing`, `/resources/*`, `/contact` public content.
- `/signin` single visual sign-in; `/login` remains an alias during migration.
- `/system-check` isolated synthetic environment entry; `/evaluator` is an alias only after isolation is actually configured. Until then this entry must not mint a production role token.

## Hospital Clinical System

- `/app/icu`, `/app/patients/[id]`, `/app/chart`, `/app/ward`, `/app/alerts`, `/app/handoff`, `/app/staff`, `/app/profile`.
- `/app/admin/*`: users, setup, shift roster, integrations, connections, pilot, readiness, current-site operations and audit.
- Preserve current top-level routes as compatibility aliases until links, service workers, API consumers and deployment are migrated.
- Keep inference, thresholds, TrustGate, validation, clinical workflows, audit and API contracts unchanged.

## Customer Portal (not implemented yet)

- `/portal/overview`, `organization`, `sites`, `licenses`, `contracts`, `documents`, `invoices`, `support`, `downloads`, `members`, `profile`.
- Back these routes only with customer-scoped persisted records and server-side membership/entitlement checks. Empty state means no record exists; it must not fabricate a customer, payment, contract, invoice or renewal.

## Vendor Control Plane (partial)

- `/platform/overview`, `organizations`, `sites`, `deployments`, `licenses`, `contracts`, `documents`, `billing`, `support`, `users`, `team`, `releases`, `models`, `security`, `audit`, `compliance`, `settings`.
- Separate vendor store and identity from hospital clinical records. Site heartbeats remain patient-free and strictly allowlisted.
- Current-site hospital operations remain under `/app/admin/operations`; fleet operations stay under `/platform/deployments`.

## Identity routing and environment boundaries

- A server-authenticated actor resolves role, organization/site memberships, permissions, entitlements and default workspace. The browser only displays workspaces returned for that actor.
- Until organization/workspace data and authorization APIs exist, do not imply that frontend navigation provides multi-tenant security.
- Evaluation uses a separate deployment/credentials/database/network where possible, seeded only with synthetic data and no production secrets. Payments, emails, licence issuance and releases in that environment must use non-delivering adapters.
- Hospital site authentication/inference/database/assets stay local. Vendor telemetry is opt-in, patient-free and bounded by both heartbeat allowlists.

## Route migration order

1. Keep existing top-level routes working and define new route groups without deleting APIs.
2. Move shared navigation and layouts to surface-specific shells; direct old routes to the canonical path using server redirects or re-exports.
3. Introduce server-side workspace resolution only with persisted membership and permission checks.
4. Activate customer/vendor mutation screens only after the corresponding storage, audit, authorization, migration and continuity rules exist.
5. Activate `/system-check` only in an isolated evaluation runtime; never silently use the public clinical demo DB as the evaluation tenant.
