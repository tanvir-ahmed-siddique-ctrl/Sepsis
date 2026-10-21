# Hospital data integration — PredictRx Sentinel

PredictRx accepts observations through one validated pipeline. Every connector
below ends in the same engine call, so FHIR, HL7 v2 and native JSON data are
scored, quarantined, de-duplicated and audited identically.

> Synthetic data (Synthea-style FHIR bundles, sample HL7 messages) exercises
> the integration path only. It is never model evidence and is refused outside
> demo mode.

## Connectors

| Connector | Endpoint | Standard | Status |
|---|---|---|---|
| Native JSON | `POST /v1/observations/batch` | PredictRx observation schema | Implemented |
| FHIR R4 Bundle | `POST /v1/integrations/fhir/bundle` | FHIR R4 `Bundle` of `Patient`, `Encounter`, `Observation` | Implemented |
| FHIR NDJSON | `POST /v1/integrations/fhir/ndjson` | FHIR Bulk Data 3.0 file format (one resource per line) | Implemented as a file import; the `$export` client is not |
| HL7 v2 ORU^R01 | `POST /v1/integrations/hl7v2/oru` | HL7 v2.5.1 ORU^R01 (PID / PV1 / OBX) | Adapter contract; the hospital interface engine (e.g. Mirth) delivers messages |
| HL7 v2 ADT | `POST /v1/integrations/hl7v2/adt` | A01 admission, A02 transfer, A03 discharge (PID / PV1) | Generic idempotent contract implemented; partner PID/PV1 profile sign-off required |
| Lab CSV | `POST /v1/integrations/csv/lab` | Header aliases plus native codes or LOINC | Implemented; unknown rows are quarantined |

Connector health, the mapping registry, the quarantine list, connector events
and the retry spool are visible on the admin **Integration** page and through
`GET /v1/integrations/{status,mappings,quarantine,events,spool}`.

## Mapping registry

`knowledge/fhir_mapping.v1.json` is the versioned code and unit registry. It maps
LOINC codes (and local codes a site adds) to the PhysioNet 2019 signal names
the frozen model expects, with the allowed units and a linear conversion for
each. Its status is **draft**: the site interface analyst must verify every
code and unit before a silent pilot.

- An unknown code or an unsupported unit is quarantined with a reason, never
  silently dropped or coerced. Values outside the clinical contract's
  plausible range are quarantined the same way.
- Unit conversion happens before validation (for example °F to °C, lactate
  mg/dL to mmol/L, creatinine µmol/L to mg/dL).
- Every accepted observation keeps provenance: source system, connector,
  source time, receive time and validation warnings. The patient page shows it.

Changing the registry is a versioned code change, reviewed like any other.
An administrator can record a source-specific acceptance at
`POST /v1/integrations/mappings/signoff` after the hospital interface analyst
verifies at least ten representative examples. The sign-off is bound to the
registry SHA-256; any registry change returns the site to draft until it is
reviewed again.

## Bedside monitors and paper-first hospitals

The optional `edge` Compose profile accepts HL7 over MLLP on port 2575, the
transport commonly exposed by a bedside-monitor central station. It writes
every message to an fsync-backed append-only queue before acknowledging it,
returns HL7 `AA`/`AE` acknowledgements, and forwards to the API with a scoped
integration key. Network failures use bounded exponential retry; the queue
survives restart. Common symbolic IEEE 11073 MDC vital codes are explicitly
mapped to LOINC at the edge; unknown vendor codes remain unchanged and are
quarantined by the API. Every mapping must be checked against the site's
monitor-interface manual.

```bash
EDGE_INTEGRATION_KEY=monitor-feed.<secret> docker compose --profile edge up -d edge
curl http://localhost:8081/health
```

For paper-first units, `/chart` provides Bangla/English tablet charting,
admit/transfer/discharge, automatic MAP calculation, °F-to-°C conversion,
bed-label QR codes, missing/stale reminders and an IndexedDB store-and-forward
outbox. Ward records are scored only by deterministic NEWS2; they never enter
the frozen ICU sepsis model. The device must be hospital-managed because its
offline outbox temporarily contains clinical observations.

## Delivery guarantees

| Guarantee | Mechanism |
|---|---|
| Idempotency | `Idempotency-Key` header. A replay of the same body returns the stored result; reuse with a different body is `409`. |
| Duplicates | The same code, encounter and source time is ignored and audited as `observation_duplicate_ignored`. |
| Late data | Out-of-order observations are accepted, flagged as late, and the affected hours are re-scored. An alert that no longer holds is retracted with an audit event. |
| Retry spool | If ingestion fails, the payload is spooled and replayed from the Integration page or `POST /v1/integrations/spool/replay`. |
| Circuit breaker | After `CIRCUIT_FAILURE_THRESHOLD` consecutive failures the connector opens for `CIRCUIT_COOLDOWN_SECONDS`; payloads spool instead of failing repeatedly. |
| Stale feeds | A connector with no success for `FEED_STALE_MINUTES` is marked stale and fails the `feeds_healthy` readiness gate. |
| Read-only degraded mode | If this instance cannot hold the writer lease or the database fails, writes return `503` and the UI shows a read-only banner; reads keep working. |

## Credentials

Connectors authenticate with scoped integration keys, not user sessions:

```bash
python -m app.ops_cli new-integration-key --key-id lab-feed --units icu-a --scopes ingest:hl7v2
```

The command prints the secret once (`X-Integration-Key: lab-feed.<secret>`) for
the interface engine and a hashed entry for `INTEGRATION_API_KEYS`. Only the
SHA-256 is stored server-side. A key can be limited to scopes (`ingest:json`,
`ingest:fhir`, `ingest:hl7v2`) and units; anything else is `403`.

## Site modes and what each connector does

| Mode | Scoring | Bedside view | Alerts |
|---|---|---|---|
| `demo` | Replay and synthetic data | Visible | Interruptive (demo only) |
| `silent` | Real feeds scored and recorded | Clinicians blinded (`403`) on API patients | Shadow alerts, admin-only |
| `live-disabled` | As silent | Blinded | Shadow; live was requested but gates failed |
| `live` | Real feeds | Visible | Interruptive, only for TrustGate `alert` |

Live mode can only be reached when every readiness gate passes (see
[operations](operations.md#silent-pilot-readiness-gates)). Backfill imports
(`?backfill=true`, the default for NDJSON) only ever produce shadow alerts.

## Roadmap (not implemented)

- **SMART App Launch 2.2** — launch the patient view inside the EHR with the
  clinician's EHR context and OAuth2 scopes, replacing the separate login.
- **CDS Hooks 2.0.1** — return a `patient-view` card that links to the
  PredictRx patient page. Cards will show the TrustGate state and citations,
  never treatment suggestions.
- **FHIR Bulk Data `$export` client** — scheduled retrospective pulls for the
  local validation that the first readiness gate requires.
- **FHIR Subscriptions** — push delivery instead of interface-engine polling.

Each item needs a partner EHR test environment; none is claimed as working.
