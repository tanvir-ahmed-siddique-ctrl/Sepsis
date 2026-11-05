# PredictRx fleet console (vendor control plane)

Each hospital runs its own PredictRx installation (the data plane). The vendor
runs this small console somewhere else to see, for every site, whether it is
online, which release and model hash it runs, whether its audit chain verifies,
how many readiness gates pass and whether any connector circuit is open.

Patient data cannot reach the console:

1. The site builds the heartbeat from an allowlist (`backend/app/fleet.py`); it
   carries counts and statuses only, never patient, encounter, bed, user or
   free-text values.
2. The site signs it with HMAC-SHA256 (`FLEET_SIGNING_KEY`).
3. The console rejects unknown sites, bad signatures, stale or replayed
   heartbeats and any field outside the allowlist.
4. The hospital opens no inbound port: `push_heartbeat.py` sends outbound only.

```bash
# vendor side
cp sites.example.json sites.json   # one entry per hospital, with its key
FLEET_SITES_FILE=sites.json FLEET_CONSOLE_TOKEN=change-me uvicorn fleet_console:app --port 8100

# hospital side, every 5 minutes (cron / Task Scheduler)
PREDICTRX_API_URL=http://127.0.0.1:8000 PREDICTRX_API_TOKEN=<operator token> \
FLEET_URL=https://fleet.example.com python push_heartbeat.py
```

Tests: `backend/tests/test_fleet.py`.

The console validates every nested heartbeat field before storage. `GET /v1/sites`
includes `attention` findings for overdue heartbeats, database or writer failures,
audit-chain failure, expected-model hash mismatch, and open connector circuits.
These are operational signals. The fleet cannot infer local clinical sensitivity,
calibration or outcome improvement from its patient-free heartbeat.
