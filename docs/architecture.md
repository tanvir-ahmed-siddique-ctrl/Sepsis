# Architecture — PredictRx Sentinel

## High-level flow

```
EHR / LIS / monitors
  │  FHIR R4 Bundle · FHIR NDJSON · HL7 v2 ORU · native JSON
  ▼
Connector layer ── idempotency · mapping registry · unit conversion · retry spool · circuit breaker
  │                      │
  │                      └─► quarantine + connector events (feed health, lag)
  ▼
Observation engine (single active writer) ─► causal features ─► frozen Run 4 LightGBM
  │                                                                  │
  │                                                              TrustGate
  │                                                                  │
  │                                        Alert / Watch / Verify / Abstain
  ▼                                                                  │
Site mode gate: demo · silent · live-disabled · live ◄──────────────┘
  │   silent / live-disabled: shadow alerts, bedside blinded
  ▼
PostgreSQL (or SQLite): prediction records · outcomes · feedback · ownership ·
handoff notes · exports · site config · hash-chained audit
  │
  ├─► Next.js cockpit: command centre, alerts, patient, handoff, pilot, integration, readiness
  ├─► Prometheus /metrics
  └─► ops CLI: backup · restore · audit verify · key generation · config check
```

Ward and ICU care segments are isolated. Crossing between them clears the
current scoring view and starts a new segment at the first observation in the
new setting, so ward observations cannot become Run 4 ICU features. Historical
prediction/NEWS2 records and audit events remain append-only.

## Demo / Congress mode

```
Held-out PhysioNet replay  ──►  same observation engine  ──►  dashboard
Synthetic FHIR / HL7 samples ──►  connector layer        ──►  integration tests only
```

No live hospital data during the hackathon. Synthetic payloads are refused
outside demo mode and are never model evidence.

## Site modes

| Mode | Bedside view of API patients | Alerts |
|---|---|---|
| `demo` | Visible | Interruptive (replay only) |
| `silent` | Blinded for clinicians | Shadow, admin-only |
| `live-disabled` | Blinded | Shadow; live requested but readiness gates failed |
| `live` | Visible | Interruptive, TrustGate `alert` only |

Mode changes need an admin, a reason, and an audit event. Live mode requires
every readiness gate in [operations](operations.md#silent-pilot-readiness-gates).

## Components

| Component | Tech | Responsibility |
|---|---|---|
| `ml/` | Python, Polars, sklearn, LightGBM, SHAP | Features, train, eval, export model |
| `backend/` | FastAPI, Pydantic, SQLAlchemy, SQLite/PostgreSQL, Alembic | Observations, predictions, TrustGate, alerts, persistence, audit |
| `backend/app/integrations/` | FHIR R4, HL7 v2, NDJSON adapters | Connectors, mapping registry, spool, circuit breaker, feed health |
| `backend/app/pilot.py` | Pure Python | Silent-pilot metrics, threshold simulation, readiness gates, exports |
| `backend/app/guidelines.py` | Versioned JSON registry | Cited guideline and local-protocol retrieval; refuses treatment queries |
| `backend/app/ops_cli.py` | CLI | Backup, restore, audit verification, integration keys, config check |
| `backend/app/accounts.py` | Python, SQL | Local users, scrypt passwords, TOTP encryption, PIN and token revocation |
| `backend/app/news2.py` | Pure Python | Deterministic RCP NEWS2 2017 for ward encounters only |
| `edge/` | Python stdlib, MLLP | Durable on-site monitor relay, ACK, retry, IEEE 11073 normalization |
| `frontend/` | Next.js, TypeScript, Tailwind, ECharts, Vitest | ICU cockpit + presentation mode |
| `knowledge/` | Versioned JSON | Evidence graph, guideline excerpts, FHIR mapping registry |
| `infra/` | Docker Compose, shell | Local demo stack, site override, backup/restore scripts |
| `.github/` | GitHub Actions | Tests, build, migration round-trip, frozen-hash checks, container smoke |

## Core entities

- Patient, Encounter, Observation (with provenance)
- PredictionRecord (append-only, revisioned), Alert, AlertAction
- OutcomeRecord (chart-review adjudication), FeedbackRecord
- BedOwnership, HandoffNote
- ConnectorEvent, ConnectorSpool, IngestRequest (idempotency)
- SiteConfig, LocalProtocol, ExportLog, WriterLease
- CareUnit, Encounter, News2Record, SiteUser, RevokedToken
- ModelVersion, AuditEvent, User, ICUUnit

## API (V1)

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/observations/batch` | Ingest native JSON observations |
| POST | `/v1/integrations/fhir/bundle`, `/fhir/ndjson`, `/hl7v2/oru` | Standards-based ingestion |
| POST | `/v1/integrations/hl7v2/adt` | Generic HL7 A01/A02/A03 census workflow |
| GET | `/v1/integrations/status`, `/mappings`, `/quarantine`, `/events`, `/spool` | Integration hub (admin) |
| GET | `/v1/patients/{id}/risk/current`, `/risk/timeline` | Latest risk and hourly scores |
| GET | `/v1/patients/{id}/provenance`, `/signals` | Observation provenance and missing-signal matrix |
| POST/DELETE | `/v1/patients/{id}/ownership` | Claim, release or take over a bed |
| GET/POST | `/v1/patients/{id}/handoff-notes` | Shift handoff notes |
| GET | `/v1/alerts`; POST `/v1/alerts/{id}/acknowledge` | Alert review with SLA clock |
| GET | `/v1/units`, `/v1/units/{id}/overview`, `/v1/units/{id}/handoff` | Command centre and printable handoff |
| GET/PUT/POST | `/v1/site/status`, `/readiness`, `/mode`, `/governance-signoff` | Site mode and readiness gates |
| GET/POST | `/v1/pilot/metrics`, `/outcomes`, `/feedback`, `/export`, `/exports`, `/retention/apply` | Silent-pilot evidence loop |
| GET | `/v1/evidence/features/{feature}`, `/guidance`, `/guidance/search` | Non-causal context and cited guidance |
| GET/POST | `/v1/evidence/guidelines`, `/local-protocols` | Guideline approval and two-person local protocols |
| GET | `/v1/model`, `/v1/model/passport` | Frozen metrics and readiness passport |
| GET | `/v1/auth/me`; POST `/v1/auth/demo-token` | Session (demo token only in demo mode) |
| GET | `/v1/ops/status`, `/v1/ops/audit/verify`, `/metrics` | Operations and Prometheus |
| GET | `/health`, `/ready` | Liveness; readiness (replay cases required only in demo mode) |
| POST | `/v1/auth/login`, `/pin-login`; GET/POST/PATCH `/v1/auth/users` | Local accounts and admin management |
| GET/POST | `/v1/care/units`, `/census`, `/completeness`, `/encounters/*/chart` | ADT, bedside flowsheet and data quality |
| GET | `/v1/care/wards/{unit}/news2` | Deterministic ward NEWS2 board |
| POST | `/v1/integrations/csv/lab` | Hospital lab CSV with aliases and LOINC mapping |

## Security and persistence

- Hospital OIDC (RS256/ES256 via JWKS) or local HS256 JWT with rotation
- Clinician / administrator / integration route guards and ICU unit scoping
- Scoped integration keys; only SHA-256 hashes are configured
- Demo headers are accepted only while `DEMO_MODE=true`
- Pseudonymous IDs only; exports use HMAC-SHA256 with a site salt
- No raw PhysioNet files in Git or in container images
- Row-level records for predictions, outcomes, feedback, ownership, connector
  events and site configuration; restart state is one snapshot row per
  encounter (only changed encounters are rewritten)
- One active writer per site, enforced by a database lease; others run
  read-only. Horizontal API scaling inside a site is disabled; hospitals
  scale out as isolated sites with a metadata-only vendor fleet console —
  see [scalability](scalability.md)
- Audit events form a SHA-256 previous-hash chain, verified on demand and
  exported as a Prometheus gauge
- Alembic owns the schema (`0001` restart state and audit, `0002` pilot,
  connector, governance and lease tables); SQLite remains the offline fallback

TLS termination and managed-secret storage are deployment-environment
responsibilities and are not claimed as implemented here. See
[operations](operations.md) and [integration](integration.md).

## Inference constraints

- CPU-oriented inference. The historical artifact records approximately 5 ms
  model-only latency; full API/TrustGate load evidence is limited to local smoke tests.
- Insufficient-data state when window incomplete
- Model version stamped on every prediction
- Event-time gaps are retained; late data trigger idempotent downstream recomputation
- Only High Risk that passes TrustGate can create an interruptive alert

## TrustGate V1

- **Alert:** high-risk score, fresh required vitals, and stable across three
  missing/delayed-data perturbations
- **Watch:** passive monitoring; never creates the High Risk interrupt
- **Verify data:** score exists but freshness, availability, or stability is weak
- **Abstain:** insufficient history or severe staleness/availability failure

`input_shift_score` is a transparent required-vital availability proxy, not a
validated out-of-distribution probability. The frozen primary model has one
member, so its zero ensemble spread is not treated as a confidence interval or
used by the gate.
