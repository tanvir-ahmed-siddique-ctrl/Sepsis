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

ACCOUNT_DB=/tmp/accounts.db EVALUATION_RUNTIME=false \
  python - <<'PY' &
import os, uvicorn
from account_service import create_app
app = create_app(os.environ.get("ACCOUNT_DB", "/tmp/accounts.db"))
try:
    app.state.store.create_vendor("vendor@auralis.demo", "Auralis Demo Vendor", "auralis-demo-2026")
except ValueError:
    pass
with app.state.store.lock:
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    app.state.store.db.execute("INSERT OR IGNORE INTO organizations VALUES(?,?,?)", ("demo-hospital", "Dhaka Central ICU (Demo)", now))
    app.state.store.db.execute("INSERT OR IGNORE INTO sites VALUES(?,?,?,?)", ("demo-hospital-icu", "demo-hospital", "Adult ICU Unit A", now))
    app.state.store.db.commit()
uvicorn.run(app, host="127.0.0.1", port=8101, log_level="warning")
PY
accounts=$!

PREDICTRX_DEMO_OPERATOR=true FLEET_URL=http://127.0.0.1:8100 python push_heartbeat.py --every 60 &
relay=$!

cd /app/web
ACCOUNT_API_INTERNAL_URL=http://127.0.0.1:8101 HOSTNAME=0.0.0.0 node server.js &
web=$!

trap 'kill "$api" "$fleet" "$accounts" "$relay" "$web" 2>/dev/null' TERM INT
wait -n "$api" "$fleet" "$accounts" "$web"
status=$?
kill "$api" "$fleet" "$accounts" "$relay" "$web" 2>/dev/null
exit "$status"
