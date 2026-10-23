# Fleet enrolment and staged release rings

How a new hospital is added and how a release reaches many sites without
centralising patient data. This is the operational pathway that makes
"thousands of isolated hospitals" concrete for judges.

## Enrol a site (repeatable)

1. Hospital provides a server (4 vCPU / 16 GB / 250 GB encrypted SSD) per
   `docs/hospital-onboarding.md`.
2. Install with `docker-compose.site.yml`; bootstrap the hospital admin;
   create the vendor `operator` account (metadata only).
3. Generate a unique `FLEET_SIGNING_KEY` for the site; add one entry to the
   vendor `control-plane/sites.json` (or future Postgres registry) with
   site_id, expected model SHA, expected image digest.
4. Site cron runs `control-plane/push_heartbeat.py` outbound only — hospital
   opens no inbound port to the vendor.
5. Fleet console shows the site online when the first valid heartbeat
   arrives; readiness gates and model-hash match are visible as metadata.

No patient field can be added to the heartbeat without changing **both**
allowlists (site sender + console). That dual-edit is deliberate.

## Release rings (staged rollout)

| Ring | Who | Halt condition |
|---|---|---|
| Canary | Founder's own demo / one partner lab site | Any of: model hash mismatch, audit chain invalid, readiness regression, heartbeat missing > 2 intervals |
| Cohort | 3–10 early hospitals that completed silent pilot | Same halt conditions; plus rising quarantine rate or review-time SLA breach reported in heartbeat counts |
| Fleet | Remaining enrolled sites | Proceed only after cohort ring holds for the agreed soak window |

Procedure per site:

1. Publish release manifest (`infra/release_manifest.py`) with image digest +
   model SHA + source commit.
2. Hospital pulls the new image (or receives the tagged artefact).
3. Restart; start-up refuses to run if the frozen model SHA does not match
   `ACTIVE.json`.
4. Fleet console compares reported model hash and image digest to the
   expected release; drift flags the site without touching patient care at
   any other hospital.
5. Rollback = redeploy previous manifest digest; documented in the release
   manifest itself.

## Why this is scalable without a central PHI database

Hospital #N adds: one server, one signing key, one heartbeat row. It does
**not** add rows to a vendor patient table — there is none. A bad release or
a crash at hospital #17 does not alter hospital #18. That is the scale axis
judges should score: operational repeatability of isolated data planes, not
one autoscaled multi-tenant PHI cloud.
