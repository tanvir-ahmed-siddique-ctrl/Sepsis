#!/bin/bash
# Public demo: hospital API + web app + vendor fleet console in one container.
# The site and the console talk only through the signed, patient-free heartbeat,
# exactly as they would across two networks.
set -u

FLEET_SIGNING_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export FLEET_SIGNING_KEY
python - <<'EOF'
import json, os
sha = json.load(open("/app/ml/artifacts/models/ACTIVE.json")).get("model_sha256")
sites = {os.environ["SITE_ID"]: {"name": "Public demo site (simulated hospital)",
                                 "key": os.environ["FLEET_SIGNING_KEY"], "expected_model_sha256": sha}}
json.dump(sites, open("/tmp/fleet-sites.json", "w"))
EOF

cd /app/backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --proxy-headers &
api=$!

cd /app/control-plane
env -u FLEET_SIGNING_KEY FLEET_SITES_FILE=/tmp/fleet-sites.json FLEET_DB=/tmp/fleet.db FLEET_PUBLIC_READ=true \
  uvicorn fleet_console:app --host 127.0.0.1 --port 8100 --workers 1 &
fleet=$!
PREDICTRX_DEMO_OPERATOR=true FLEET_URL=http://127.0.0.1:8100 python push_heartbeat.py --every 60 &
relay=$!

cd /app/web
HOSTNAME=0.0.0.0 node server.js &
web=$!

trap 'kill "$api" "$fleet" "$relay" "$web" 2>/dev/null' TERM INT
wait -n "$api" "$fleet" "$web"
status=$?
kill "$api" "$fleet" "$relay" "$web" 2>/dev/null
exit "$status"
