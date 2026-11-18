# PredictRx Repository Guardrails

These instructions apply to every coding task in this repository. Read `PREDICTRX_MASTER_SPEC.md` before making product-wide changes.

## Product truth
- PredictRx Sentinel is currently a research prototype for hospital-local ICU sepsis-risk decision support. Retrospective public-data evaluation and simulated workflows do not establish Bangladesh hospital validation, prospective clinical benefit, regulatory authorization, or production clinical readiness.
- Never invent hospitals, customers, partnerships, users, licences, deployment counts, clinical outcomes, model metrics, regulatory approvals, certifications, or uptime statistics.
- Clearly distinguish real operational state, seeded sample data, synthetic evaluation data, and unavailable/not-configured integrations.
- Never present generated/simulated data as real patient data or a live hospital EHR feed.
- Do not describe a model risk estimate as a diagnosis, treatment recommendation, or autonomous clinical decision.

## Preserve existing functionality
- Audit the existing repository, routes, APIs, authentication, data contracts, model artifacts, tests, and deployment configuration before changing them.
- Preserve existing FastAPI/backend behavior, frozen ML model and artifacts, model hash/version, inference logic, thresholds, TrustGate/data-quality behavior, clinical workflows, audit behavior, and API contracts unless the user explicitly authorizes a change.
- Do not replace working backend integrations with mock data. Use mocks only in an explicitly isolated evaluation/demo environment and label them accurately.
- Do not remove existing routes or features. Add redirects/compatibility aliases when reorganizing routes.
- Never perform destructive database migrations, delete records, rotate production secrets, change production infrastructure, or run external side-effecting actions without explicit authorization.

## Security boundaries
- Keep Public Website, Customer Portal, Hospital Clinical System, Vendor Control Plane, and Evaluation Environment logically and operationally separated.
- A unified sign-in experience is allowed; a user-selected role dropdown is not an authorization mechanism. Resolve identity, organization/site membership, role, entitlements, and destination server-side.
- Enforce permissions on the server/API as well as in navigation/UI. Hiding a button or route is not security.
- Never grant a hospital account vendor-wide Super Admin access. Never grant vendor staff blanket access to patient records.
- The evaluation account may access all evaluation workspaces only within an isolated synthetic-data evaluation tenant. It must never access production tenants, real hospital data, production secrets, or production Super Admin privileges.
- Never commit passwords, API keys, signing keys, database credentials, private certificates, or tokens. Use environment secrets/secret management. Public evaluation credentials, if intentionally shown to judges, must be limited to the isolated synthetic sandbox and must never be reused in production.
- Use secure, HttpOnly, SameSite cookies; CSRF protection where applicable; rate limits; secure password hashing; session expiry/revocation; MFA for privileged production users; and audit logs for privileged actions.

## Hospital-local privacy and continuity
- Patient-identifiable data, observations, patient-specific scores, clinical notes, timelines, and patient-linked logs must remain within the approved hospital data boundary by default.
- The hospital-local clinical application must not depend on public cloud availability for local authentication, core UI assets, database access, inference, or core clinical workflows.
- Self-host fonts and required frontend assets. Avoid third-party analytics, advertising pixels, remote fonts, and unnecessary external requests in the clinical app.
- Vendor telemetry must be disabled by default or strictly allowlisted, approved by the hospital, minimized, redacted, and limited to operational metadata. Do not send patient payloads or patient-linked identifiers to the vendor control plane.
- License expiry, cloud disconnection, or a commercial dispute must never silently delete patient data or unexpectedly interrupt access to existing clinical records. Preserve a documented safe-continuity policy.

## Visual design rules
- Public website: editorial/institutional medical technology, expressive but restrained typography, asymmetric layouts, warm paper tones, authentic product screenshots, clear evidence boundaries.
- Hospital workspace: calm clinical workstation, high information clarity, readable dense tables, patient timelines, precise statuses, restrained decoration.
- Vendor Control Plane: serious enterprise operations console focused on organizations, deployments, licences, contracts, documents, finance, support, releases, security, and audit.
- Customer Portal: institutional account/document experience focused on licences, contracts, invoices, downloads, renewals, and support.
- Avoid generic AI-SaaS aesthetics: no gratuitous gradients, glassmorphism, glowing brain/waveform illustrations, excessive rounded statistic cards, fake metrics, stock-doctor hero imagery, or needless animation.
- Preferred typography: Instrument Serif for selected public editorial display headings; IBM Plex Sans for application/public body and UI; IBM Plex Mono for IDs, hashes, logs, and technical values. Noto Sans Bengali may be added for future Bengali localization. Self-host all fonts required by hospital-local installations.
- Preferred brand palette: Paper `#F3F0E9`, Warm White `#FCFBF8`, Ink `#202B2C`, Forest `#28564E`, Muted Olive `#8B9279`, Copper `#B66E50`, Cool Grey `#E9ECEA`, Slate `#667471`. Treat these as design direction; verify contrast and accessibility.
- Clinical alert colours are separate semantic tokens: Critical/red, High/orange, Moderate/amber, Low/green, Unavailable/grey. Never use brand copper/olive as a substitute for risk severity.
- Avoid making every panel a rounded card. Use hierarchy, tables, section rules, whitespace, typography, and purposeful layouts. Prefer modest radii and clear focus states.

## Implementation process
1. Read `PREDICTRX_MASTER_SPEC.md` and inspect the repo before coding.
2. Report the existing architecture and the actual state of features. Identify what works, what is partial, what is mocked, and what is missing.
3. Write a phased implementation plan with risks and tests, then continue implementation without waiting for approval for ordinary reversible work.
4. Ask the user only when a genuinely blocking decision cannot be resolved safely from repository evidence. Otherwise state a conservative assumption and record it.
5. Work incrementally. Run relevant tests, type checks, lint, build, and security checks using commands discovered from the repository.
6. Do not claim tests passed unless they were actually run. Report failures and unresolved gaps honestly.
7. At completion, provide changed routes/components, migrations, configuration/env vars, tests run, known gaps, and deployment steps.
