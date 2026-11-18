---
name: predictrx-product
description: Design, implement, audit, and maintain the PredictRx Sentinel public website, customer portal, hospital-local clinical workspace, vendor control plane, and isolated evaluation environment.
---

# PredictRx Product Engineering Skill

Use this skill whenever changing PredictRx product UX, architecture, authentication, routing, local deployment, clinical workflows, customer account features, vendor administration, licensing, documents, or evaluation access.

## Required reading
- Read repository `AGENTS.md`.
- Read `PREDICTRX_MASTER_SPEC.md` at the repository root.
- Inspect the current code and tests before deciding what to change.

## Workflow
1. Audit existing implementation, routes, APIs, backend contracts, auth, database, frozen model, simulation and deployment.
2. Separate verified existing behavior from partial, mocked, proposed or missing features.
3. Preserve existing clinical behavior and evidence boundaries.
4. Plan the smallest safe implementation sequence.
5. Implement incrementally, testing each affected layer.
6. Verify server-side authorization and environment isolation, not just UI visibility.
7. Report changed files, routes, configuration, tests, failures and remaining production gates.

## Product surfaces
Maintain five distinct surfaces under one coherent brand:
- Public Website.
- Customer Portal.
- Hospital Clinical System.
- Vendor Control Plane.
- Evaluation Environment.

They may share components and root-domain routing, but never assume they share identity authority, database, secrets or permissions.

## Identity and evaluation rules
- No role dropdown for selecting privileges.
- Resolve user, organization, site, roles, and destination server-side.
- Workspace switcher shows only authorized destinations.
- Hospital-local auth must not require public cloud connectivity.
- The isolated evaluation account can access all evaluation workspaces only in the synthetic evaluation tenant.
- Never permit evaluation credentials to reach production tenants or production Super Admin capabilities.
- A small `Judge System Check` entry may appear on the sign-in page. Do not put judge-specific language throughout the normal product UI.
- Evaluation uses the same product UI as production, while data provenance remains honest and visible.

## Security and clinical truth
- Enforce tenant and object-level permissions at APIs.
- Vendor staff have no blanket access to patient records.
- Keep patient data local by default; telemetry must be allowlisted and free of patient payloads.
- Do not invent clinical thresholds, metrics, outcomes, customers, regulatory status or certifications.
- Preserve frozen ML artifacts, inference logic, data-quality gates and backend contracts.
- Show missing/stale inputs and abstention distinctly from low risk.
- Risk estimates are not diagnoses or treatment recommendations.

## Visual direction
- Public: editorial/institutional medical technology, asymmetry, expressive display typography, warm paper palette and authentic screenshots.
- Hospital: clinical workstation with clear hierarchy, compact but readable data tables, patient context, labelled trends and purposeful alerts.
- Customer: institutional account, licence, contract, invoice, document and support experience.
- Vendor: serious operations console with tables, filters, document registers, deployments, licences, audit and security.
- Avoid generic AI-SaaS cards, gradients, glassmorphism, glowing illustrations, fake metrics and excessive rounding.
- Type: Instrument Serif for selected public display headings; IBM Plex Sans for UI/body; IBM Plex Mono for technical values; optional Noto Sans Bengali. Self-host local assets.
- Brand palette: `#F3F0E9`, `#FCFBF8`, `#202B2C`, `#28564E`, `#8B9279`, `#B66E50`, `#E9ECEA`, `#667471`. Verify accessibility.
- Clinical status colours are separate semantic tokens: red/critical, orange/high, amber/moderate, green/low, grey/unavailable.

## Implementation safety
- Do not replace backend behavior with mock data.
- Do not make destructive migrations or production changes without authorization.
- Do not expose credentials in source, client bundles, logs or committed env files.
- Use evaluation-only adapters for email, billing, licence issuance, customer notification and release actions.
- Run the repository's actual lint, typecheck, test and build commands; report real results.
- If information is missing, make a conservative reversible assumption and document it. Ask only for a genuine blocker.

## Done means
The affected feature works end-to-end, retains existing workflows, has server-side access controls, has honest loading/empty/error/source states, is responsive and accessible, is tested, and has documented configuration and known gaps.
