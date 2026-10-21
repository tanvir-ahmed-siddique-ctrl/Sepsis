# Site operations — PredictRx Sentinel

How a hospital runs PredictRx on its own infrastructure during a silent pilot.
The design target is one ICU site, on-premises, reachable only inside the
hospital network. Nothing here is a regulatory or clinical approval.

## Deployment

```bash
cp .env.example .env.site            # fill in every secret
docker compose -f docker-compose.yml -f docker-compose.site.yml --env-file .env.site up -d --build
docker compose -f docker-compose.yml -f docker-compose.site.yml --env-file .env.site exec api python -m app.ops_cli check-config
```

`docker-compose.site.yml` turns the demo stack into a site stack:

- `DEMO_MODE=false`: no demo headers, no demo tokens, no replay, synthetic
  payloads refused.
- `SITE_MODE=silent` at first start. After that the persisted, audited site
  configuration is authoritative.
- Compose refuses to start unless `POSTGRES_PASSWORD`, `SITE_ID`, `JWT_SECRET`,
  `EXPORT_SALT`, `METRICS_TOKEN`, `INTEGRATION_API_KEYS`, `CORS_ORIGINS` and
  `PUBLIC_API_URL` are set.
- API and web bind to `127.0.0.1` only. Publish them through the hospital
  reverse proxy, which terminates TLS. TLS and secret storage are the site's
  responsibility and are not implemented here.
- Replay cases are not mounted; the image never contains patient data.

Both containers run as non-root users, restart `unless-stopped`, and have
health checks (`/health` for the API, `/` for the web app).

### Single active writer

The engine keeps live encounter state in memory and persists it row by row.
To keep that consistent, exactly one API process may write:

- Each process takes the `engine-writer` lease in the database and renews it.
- A second process, or one that loses the lease, starts **read-only**: writes
  return `503`, reads keep working, and the UI shows a read-only banner.
- The API runs with `--workers 1`. Horizontal scaling is disabled until all
  state is fully row-level. `GET /v1/ops/status` reports the lease holder.

## Authentication

| Mode | Use | Configuration |
|---|---|---|
| Demo headers | Local demo only | `DEMO_MODE=true` |
| Local JWT (HS256) | Small sites without an IdP | `AUTH_MODE=local`, `JWT_SECRET` (32+ random bytes) |
| Hospital OIDC / SSO | Recommended | `AUTH_MODE=oidc`, `OIDC_ISSUER`, `OIDC_AUDIENCE`, `OIDC_JWKS_URL`, claim names, `OIDC_ROLE_MAP` |
| Integration keys | Interface engines | `INTEGRATION_API_KEYS` (SHA-256 only), see [integration](integration.md#credentials) |

Roles are `nurse`, `clinician`, `admin`, `operator` (vendor metadata only, no
patient data) and `integration`. Tokens may carry an ICU unit scope; a
clinician cannot read another unit's patients.

Local accounts are database-backed and use scrypt password hashes, five-attempt
lockout, forced temporary-password change, optional TOTP, session revocation,
and unit scopes. TOTP seeds are encrypted at rest using the separate
`ACCOUNT_ENCRYPTION_KEY`. Create the first administrator while the API is
stopped:

```bash
docker compose run --rm --no-deps api python -m app.ops_cli bootstrap-admin \
  --user-id site.admin --display-name "Site Administrator" --password '<temporary-password>'
```

Ward-tablet PINs are personal, never shared, and issue 15-minute sessions.
Hospital SSO remains preferred where an OIDC identity provider exists.

The **Site users** admin page also manages unit scope, role, account state,
password reset and PIN/TOTP reset. Role, unit or state changes revoke existing
sessions. Removing a login profile deletes its credentials while immutable
audit events retain the stable user ID; the final active administrator cannot
be disabled, downgraded or removed. Create a second administrator before staff
turnover or planned maintenance.

The **Site setup** page aggregates service health, users, units, integrations
and silent-pilot gates. Follow the full [hospital onboarding runbook](hospital-onboarding.md)
before accepting patient data.

**Secret rotation.** Move the current secret into `JWT_PREVIOUS_SECRETS`
(JSON list), set a new `JWT_SECRET` and restart. New tokens use the new secret;
old tokens verify until they expire (`ACCESS_TOKEN_MINUTES`). Then remove the
old secret. Integration keys rotate by adding a new key, switching the
interface engine, and deleting the old entry.

## Abuse limits

The hospital reverse proxy is the first layer. The API adds its own budgets,
held in memory per one-minute window (single writer, so one process):

| Bucket | Keyed by | Default | Setting |
|---|---|---|---|
| Login, PIN login, demo token | Client address | 20/min | `RATE_LIMIT_LOGIN_PER_MINUTE` |
| Integration ingest | Integration key ID | 1,200/min | `RATE_LIMIT_INGEST_PER_MINUTE` |
| Everything else | Bearer token hash, else address | 600/min | `RATE_LIMIT_PER_MINUTE` |

Over budget returns `429` with `Retry-After`; a declared body over
`MAX_REQUEST_BYTES` (12 MB) returns `413` before parsing. `/health` and
`/ready` are exempt. Rejections are counted in
`predictrx_requests_rejected_total{bucket,reason}`. Set `FORWARDED_ALLOW_IPS`
to the reverse proxy address so addresses come from `X-Forwarded-For`;
otherwise every user shares the proxy's login budget.

## Monitoring

`GET /metrics` serves Prometheus text format. Scrape it with
`Authorization: Bearer $METRICS_TOKEN`; admins can also read it. Clinicians get
`403`.

| Metric | Watch for |
|---|---|
| `predictrx_http_requests_total`, `predictrx_http_request_seconds` (histogram) | Error rate, slow requests |
| `predictrx_inference_total`, `predictrx_inference_failures_total`, `predictrx_inference_seconds_sum` | Inference failures and latency |
| `predictrx_feed_minutes_since_success{connector}` | Feed silence (`-1` = never connected) |
| `predictrx_feed_median_source_lag_minutes{connector}` | Delayed charting or interface backlog |
| `predictrx_feed_quarantine_rate{connector}`, `predictrx_quarantined_last_24h` | Mapping or unit problems |
| `predictrx_feed_circuit_open{connector}`, `predictrx_spool_pending{connector}` | Connector outage |
| `predictrx_predictions_24h`, `predictrx_drift_*_24h` | Input drift proxies: mean score, availability shift, missing required vitals |
| `predictrx_alerts_open`, `predictrx_alerts_shadow_active` | Alert volume |
| `predictrx_audit_chain_valid` | Must stay `1`; `0` means the audit log was altered |
| `predictrx_read_only` | Must stay `0` on the active writer |
| `predictrx_site_interruptive_alerts_enabled` | `1` only in live mode |

The drift metrics are proxies, not validated out-of-distribution detectors.

## Backup and restore

Backups are logical (JSON rows per table, optionally gzipped), so they move
between SQLite and PostgreSQL. Each file records table counts, a SHA-256 of the
contents and the audit-chain head.

```bash
infra/backup.sh                                   # online; writes to the predictrx-backups volume
FORCE=1 infra/restore.sh predictrx-<stamp>.json.gz  # stops the API, restores, verifies, restarts
```

The CLI behind the scripts (`python -m app.ops_cli`):

| Command | Behaviour |
|---|---|
| `backup --out FILE` | Consistent snapshot in one transaction; safe while the API runs |
| `restore --input FILE [--force]` | Rejects a corrupt or edited file (checksum) and a broken audit chain; refuses while a writer holds the lease; refuses a non-empty database without `--force` |
| `verify-audit` | Recomputes the hash chain; exit code `2` if it is broken |
| `new-integration-key` | Generates a scoped connector credential |
| `check-config` | Lists unsafe settings; exit code `1` if any |
| `decommission --final-backup FILE --confirm-site-id ID --certificate OUT` | Offboarding: refuses unless the API is stopped, the site ID matches and the verified final backup equals the live database; then erases every table and writes a closeout certificate |

Backups contain identifiable clinical data. Store them encrypted, on site, with
access control, and test a restore before the pilot starts.

## Retention and export

- `RETENTION_DAYS` (default 365). An admin applies retention from the Pilot
  page; it deletes prediction records, connector events, idempotency records
  and finished spool entries older than the cut-off, and logs the run in the
  audit trail. Outcomes, feedback, the export log and the audit chain are kept.
  Pending spool entries are never deleted.
- Pilot exports pseudonymise encounter and alert IDs with
  `HMAC-SHA256(EXPORT_SALT, id)`, drop free-text notes, record the export's
  SHA-256 in the export log, and require a stated reason. Keep `EXPORT_SALT`
  secret and constant for the whole pilot, or exports stop linking.

## Bedside workflow and NEWS2

Admins define each care unit as `icu` or `ward`. The bedside chart supports
admit, transfer and discharge, unit-scoped census, an 8-hour completeness
report, offline queueing and QR bed labels. Missing values are shown and never
imputed merely to produce a score.

Ward observations use the published RCP NEWS2 2017 rule. A score is withheld
until all required fields are present. SpO2 Scale 2 is used only after a
clinician explicitly flags hypercapnic respiratory failure. NEWS2 output is not
a sepsis diagnosis and does not replace clinical judgment. Ward observations
do not enter frozen Run 4.

## Silent-pilot readiness gates

The site cannot leave silent mode until every gate passes. A request for live
mode while any gate fails is recorded as `live-disabled`, which behaves like
silent.

| Gate | Default target | Setting |
|---|---|---|
| Local retrospective validation recorded in the passport evidence | required | passport YAML |
| Silent-pilot duration | 28 days | `PILOT_MIN_DAYS` |
| Distinct encounters scored | 100 | `PILOT_MIN_ENCOUNTERS` |
| Chart-review adjudications | 30 | `PILOT_MIN_ADJUDICATED` |
| Shadow-alert sensitivity (≥10 adjudicated sepsis encounters) | 0.5 | `PILOT_MIN_SENSITIVITY` |
| Shadow alerts per 100 patient-hours | ≤ 2.0 | `PILOT_MAX_ALERTS_PER_100H` |
| Every connected feed healthy or degraded | required | — |
| Clinical governance / ethics sign-off recorded | required | Pilot page |
| Production security (no demo mode, non-default secrets or OIDC) | required | — |

These thresholds are starting points for the site's governance committee, not
validated cut-offs. The frozen Run 4 model and its thresholds never change
during a pilot; threshold simulation on the Pilot page is read-only analysis.

## Restart and failure behaviour

| Event | Behaviour |
|---|---|
| API restart | Encounter state, alerts, ownership and the audit chain reload from the database; the lease is re-acquired |
| Database unavailable | `/ready` returns `503`; writes fail; no silent data loss |
| Feed outage | Circuit opens, payloads spool, the feed shows stale, the `feeds_healthy` gate fails |
| Audit tampering | `predictrx_audit_chain_valid` drops to `0`; `verify-audit` names the first altered event |
