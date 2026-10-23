# Scalability and production hardening

How PredictRx Sentinel grows from one ICU to many hospitals without changing
its safety model. Two different scaling axes must not be confused:

| Axis | Unit of scale | How it scales today | Hard limit today |
|---|---|---|---|
| Inside one hospital | Beds, observations/hour, staff | One API writer per site on PostgreSQL; see measured capacity below | Live encounter state is held in memory and snapshotted per encounter; scoring is CPU-bound in-process |
| Across hospitals | Hospital sites | Every hospital is an isolated deployment (own database, own users, own audit chain). The vendor fleet console receives only signed, patient-free heartbeats, so adding hospital #1000 adds one heartbeat row per interval — no patient data ever centralises | Fleet console storage is single-file SQLite; rollout/billing tooling is founder-operated (see product gaps) |

This isolation is deliberate: a crash, breach or subscription dispute at one
site cannot expose or stop another hospital, and the vendor never holds a
central PHI database.

## What changed: incremental snapshot persistence

Previously every mutation rewrote one whole-engine JSON snapshot (all
encounters, every time). Now restart state is stored as **one row per
encounter plus one alerts row** (`engine_state` entries keyed
`patient:<sha256(encounter_key)>`), and only entries whose content hash changed
are rewritten. Durability is unchanged — prediction records and audit events
still flush synchronously before the snapshot — but an ingest batch for one bed
no longer rewrites every bed. `GET /v1/ops/status` reports
`scale.snapshot_last_persist_ms`, `snapshot_writes_total` and
`snapshot_kb_written_total` so a site can watch this directly. Databases with
the legacy single-blob snapshot migrate automatically on first persist.

## Measured single-site capacity

Run (synthetic load only, never clinical evidence):

```bash
cd backend && ../.venv/Scripts/python.exe ../infra/scale_check.py --beds 30 --hours 48
```

Measured 23 Oct 2026 on the development laptop (SQLite throwaway file, silent
mode, 30 beds × 48 hourly observations with 6-hourly labs — 9,600 observations
ingested as one 48-hour backfill batch per bed, the worst case because every
hour is rescored with its explanation):

| Metric | Result |
|---|---|
| Boot (model load + demo replay scoring) | 23.9 s |
| Ingest throughput (backfill, incl. rescoring) | 9,600 observations in 238 s ≈ 40 observations/s; median 7.6 s per 48-hour bed |
| Predictions scored | 1,440 (30 beds × 48 hours) |
| Snapshot persistence (whole run) | 44 entries written, 4.7 MB total; last persist 206 ms for 43 encounters |
| Database size after run | 19.8 MB (11,309 hash-chained audit events dominate) |
| Restart recovery | 0.22 s boot; all 43 encounters restored (silent mode, no replay rescore) |

Real-time load is far smaller than this backfill stress: a live feed adds one
new hour per bed, i.e. 30 scores/hour for a 30-bed ICU. The design point is
one hospital server (4 vCPU / 16 GB), not a data centre.

## Crash, backup and writer failover (per site)

| Event | Behaviour today |
|---|---|
| API crash/restart | Lease re-acquired; encounters, alerts, ownership and the hash-chained audit log reload from the database |
| Writer host dies | A standby instance started read-only; after the lease expires (`WRITER_LEASE_SECONDS`, default 300 s) an operator restarts the standby, which then acquires the lease and becomes writer. No split-brain: the database lease admits exactly one writer |
| Database unavailable | `/ready` returns 503; writes fail loudly; nothing is silently dropped |
| Feed outage | Connector circuit opens, payloads spool to disk-backed queue, readiness gate `feeds_healthy` fails |
| Backup/restore | `ops_cli backup` (checksummed logical backup) / `restore` refuses corrupt files, broken audit chains and a live writer; restore drills are part of onboarding |
| Bad release at one site | Only that site is affected; the fleet console flags version/model-hash drift per site (`model_matches_release`) |

## Thousands of hospitals: what scales, what is still founder-operated

Scales by design:

- **Compute/data**: per-site isolation — capacity grows by adding hospital
  servers, not by enlarging one central system.
- **Vendor visibility**: heartbeats are ~1 KB allowlisted metadata, HMAC-signed,
  replay-protected; the console needs no patient-data access.
- **Releases**: the frozen model is verified by SHA-256 at every site startup;
  the console compares each site's hash with the expected release hash.
- **Users**: accounts are per-site (hospital admin or hospital OIDC/SSO). There
  is intentionally no global user database.

## Enrolment and release rings (documented)

Repeatable site enrolment, canary → cohort → fleet rings, and halt conditions
are in `docs/fleet-enrolment-and-release-rings.md`. Global builder / NRB join
paths: `CONTRIBUTING.md`, `docs/nrb-global-builder-pack.md`. Published
alignment with worldwide clinical-AI practice:
`docs/global-corroboration.md`. Standards mapping:
`docs/standards-alignment.md`. Live-rate soak evidence:
`docs/evidence/soak-check.md`.

Still genuine gaps (not built; do not claim otherwise):

- Fleet console still uses SQLite and manual `sites.json`; a multi-hundred-site
  fleet will move to PostgreSQL storage with the same metadata-only contract.
- No central billing/subscription/entitlement system (founder research in
  progress). Subscription state must never be able to interrupt bedside
  workflows at a hospital.
- Within-site horizontal API scaling stays disabled until observations and
  scoring move fully to row-level records and a queue-backed scoring worker;
  the single-writer lease is the safety mechanism that prevents conflicting
  state until then.
- Backups are site-managed; encrypted off-site backup verification is an
  onboarding checklist item, not yet automated fleet-wide.

## Roadmap order (post-pilot)

1. Row-level observation storage + scoring worker (removes in-memory ceiling,
   enables read replicas behind the writer).
2. Fleet console on PostgreSQL with site onboarding, release rings and
   per-site entitlement records (metadata only, as today).
3. Automated backup verification reporting into the fleet heartbeat
   (last-backup age + checksum status — counts, never data).
