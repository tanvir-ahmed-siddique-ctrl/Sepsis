# Auralis identity and permission implementation status

This inventory reflects the current APIs. It is not a claim that a configurable permission system is complete. The public website requires no account; account, hospital, and evaluation runtimes remain separate identity authorities.

| Surface / module | Current authorized actions and scope | Remaining governance or engineering decision |
|---|---|---|
| Hospital clinical | Clinician, nurse and hospital admin receive clinical access through local/OIDC identity and unit-scoped patient checks. Physician-only actions use narrower dependencies. Integration credentials have scoped ingest methods and units. Operator has metadata access only. | Hospital must approve precise clinical role assignments, unit ownership and emergency access. Per-record care-team assignment is not a universal policy. |
| Hospital administration | Local admin controls users, units, mappings, roster, readiness, pilot governance, site mode and signed site-licence import. All actions are locally audited. | Multi-role delegated administration and formal two-person sign-off for clinical activation need hospital policy. |
| Customer portal | Customer owner, procurement/finance, technical contact and viewer are assigned per organization membership and enforced via named permissions. Financial, technical, training and document reads filter by that organization's grants. Payment, renewal, support and offboarding mutations recheck the permission for the target organization. Vendor-approved membership additions/removals revoke sessions. Customer owners can invite non-owner members (`/v1/portal/organizations/{id}/invitations`). One-time 48-hour invitations activate after password set. | Institution identity verification and formal delegation policy still need work. Invitation tokens must be delivered through an approved secure channel; no email adapter is configured. |
| Vendor control plane | Root admin, platform admin, deployment engineer, support engineer, finance/legal and security/compliance are mapped through `control-plane/permissions.py`. Customer, contract, finance, deployment, document, audit and offboarding APIs check named permissions. Vendor accounts have no patient API. Root can disable/reactivate non-root accounts with immediate session revocation. `/v1/permissions/matrix` exposes the registry. Approval requests cover customer role changes. | Short-lived break-glass elevation with dual control for every high-risk action, and individual site assignments for vendor staff, remain. Root cannot be disabled through the state endpoint. |
| Evaluation | A separate runtime, database, keys and synthetic records seed an evaluation operator. Real licence issuance, production customer directory changes and external side effects are disabled. | Container isolation and network policy must be verified in the actual environment. A shared deployment must never be substituted for the isolated stack. |

## Current API safeguards

- Authentication and workspace resolution occur server-side. Browser navigation is supplementary; all protected API routes re-check identity and role.
- Customer records are organization-scoped at query/object lookup. Multiple memberships are additive and sessions are revoked on change.
- Hospital patient data remains in the hospital API/database. Vendor commercial permissions do not create a clinical session.
- Sensitive account, membership, payment, document, licence and offboarding actions are audited. Evaluation is denied production account management.
- Customer invitation tokens are returned once, stored only as SHA-256 hashes, expire after 48 hours and cannot be reused. Accounts have no membership until acceptance.
- Deny by default is the intended policy; existing module-specific role checks should be consolidated into an explicit permission registry before asserting a fully configurable RBAC/ABAC implementation.

## Competition evidence boundary

The supplied Congress document describes five 20-point team criteria: innovation/AI-native design, technical architecture, commercial viability, scale/impact, and responsible AI/data sovereignty/presentation. The preliminary submission also asks for a 180-second video, system flow, AI explanation, demo, and expected impact. The working code can demonstrate the synthetic evaluation and hospital-local architecture; it does not establish hospital validation, outcome improvement, customer adoption, regulatory authorization or production clinical readiness. Those must not be claimed for points.
