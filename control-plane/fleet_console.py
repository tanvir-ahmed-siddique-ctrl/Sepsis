"""PredictRx fleet console — the vendor control plane.

Runs outside every hospital. Sites push signed, patient-free heartbeats
(``GET /v1/ops/heartbeat`` on the site, relayed by ``push_heartbeat.py``); the
console verifies the HMAC, rejects any field outside the heartbeat allowlist,
and shows fleet status. It has no route to request patient data from a site.

Run:  FLEET_SITES_FILE=sites.json FLEET_CONSOLE_TOKEN=... uvicorn fleet_console:app --port 8100
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import re
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

SCHEMA = "predictrx-heartbeat/v1"
ALLOWED_KEYS = frozenset({
    "schema", "site_id", "generated_at", "release_version", "site", "model", "runtime",
    "audit", "readiness", "connectors", "activity",
})
MAX_CLOCK_SKEW = timedelta(minutes=10)
NESTED_KEYS = {
    "site": {"effective_mode", "interruptive_alerts_enabled", "demo_auth_enabled"},
    "model": {"version", "sha256", "frozen"},
    "runtime": {"read_only", "database_healthy"},
    "audit": {"chain_valid", "events"},
    "readiness": {"passed", "total", "failed_gates"},
    "activity": {"active_live_encounters", "open_alerts", "shadow_alerts", "predictions_24h", "quarantined_24h"},
    "connector": {"connector", "circuit", "minutes_since_success", "quarantine_rate", "pending_spool"},
}
SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$")
GATE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
CONNECTOR_NAMES = {"native_json", "fhir_r4", "hl7v2_oru", "csv_lab", "vendor_adapter"}


def _valid_payload(payload: dict) -> bool:
    """Reject nested extras and unbounded/free-text values before storing a heartbeat."""
    if set(payload) != ALLOWED_KEYS or payload.get("schema") != SCHEMA:
        return False
    if not isinstance(payload.get("site_id"), str) or not SLUG.fullmatch(payload["site_id"]):
        return False
    if not isinstance(payload.get("release_version"), str) or not SLUG.fullmatch(payload["release_version"]):
        return False
    try:
        generated = datetime.fromisoformat(payload["generated_at"])
        if generated.utcoffset() is None:
            return False
    except (TypeError, ValueError):
        return False
    for section in ("site", "model", "runtime", "audit", "readiness", "activity"):
        if not isinstance(payload.get(section), dict) or set(payload[section]) != NESTED_KEYS[section]:
            return False
    if not isinstance(payload.get("connectors"), list) or len(payload["connectors"]) > 32:
        return False
    for item in payload["connectors"]:
        if not isinstance(item, dict) or set(item) != NESTED_KEYS["connector"]:
            return False
        if not isinstance(item["connector"], str) or item["connector"] not in CONNECTOR_NAMES:
            return False
        if item["circuit"] not in ("open", "closed", "half_open"):
            return False
        for key in ("minutes_since_success", "quarantine_rate"):
            value = item[key]
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= (1 if key == "quarantine_rate" else 1_000_000)):
                return False
        if type(item["pending_spool"]) is not int or not 0 <= item["pending_spool"] <= 1_000_000:
            return False
    for section, keys in (("site", ("interruptive_alerts_enabled", "demo_auth_enabled")),
                          ("model", ("frozen",)), ("runtime", ("read_only", "database_healthy")),
                          ("audit", ("chain_valid",))):
        if any(type(payload[section][key]) is not bool for key in keys):
            return False
    if not isinstance(payload["site"]["effective_mode"], str) or not SLUG.fullmatch(payload["site"]["effective_mode"]):
        return False
    if not isinstance(payload["model"]["version"], str) or not SLUG.fullmatch(payload["model"]["version"]):
        return False
    if not isinstance(payload["model"]["sha256"], str) or not re.fullmatch(r"[a-f0-9]{64}", payload["model"]["sha256"]):
        return False
    for section, keys in (("audit", ("events",)), ("readiness", ("passed", "total")),
                          ("activity", NESTED_KEYS["activity"])):
        if any(type(payload[section][key]) is not int or not 0 <= payload[section][key] <= 1_000_000_000 for key in keys):
            return False
    readiness = payload["readiness"]
    if readiness["passed"] > readiness["total"] or readiness["total"] > 64:
        return False
    if not isinstance(readiness["failed_gates"], list) or len(readiness["failed_gates"]) > 64:
        return False
    return all(isinstance(gate, str) and GATE.fullmatch(gate) for gate in readiness["failed_gates"])


def _attention(row: dict) -> list[dict[str, str]]:
    """Operational exceptions only; these are not claims about clinical model performance."""
    findings = []
    def add(code: str, severity: str, message: str) -> None:
        findings.append({"code": code, "severity": severity, "message": message})
    if row["status"] == "never_reported":
        add("no_heartbeat", "warning", "Site has never reported")
        return findings
    if row["status"] == "stale":
        add("stale_heartbeat", "critical", "Site heartbeat is overdue")
    if row["database_healthy"] is False:
        add("database_unhealthy", "critical", "Site database reports unhealthy")
    if row["read_only"] is True:
        add("read_only", "critical", "Site cannot accept writes")
    if row["audit_chain_valid"] is False:
        add("audit_chain_invalid", "critical", "Audit-chain verification failed")
    if row["model_matches_release"] is False:
        add("model_mismatch", "critical", "Model hash differs from site expectation")
    if row["connectors_open_circuit"]:
        add("connector_circuit_open", "warning", "One or more configured connectors have an open circuit")
    return findings


class Heartbeat(BaseModel):
    payload: dict
    signature: str | None = None
    signature_algorithm: str = "HMAC-SHA256"


def _canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()


def create_app(
    sites: dict[str, dict],
    db_path: str = ":memory:",
    console_token: str | None = None,
    stale_minutes: int = 15,
    public_read: bool = False,
) -> FastAPI:
    app = FastAPI(title="PredictRx fleet console", version="0.1.0")
    db = sqlite3.connect(db_path, check_same_thread=False)
    db.execute(
        "CREATE TABLE IF NOT EXISTS heartbeats ("
        "site_id TEXT NOT NULL, received_at TEXT NOT NULL, generated_at TEXT NOT NULL, payload TEXT NOT NULL)"
    )
    db.execute("CREATE INDEX IF NOT EXISTS heartbeats_site_time ON heartbeats (site_id, generated_at DESC)")
    lock = threading.Lock()

    def require_console(authorization: str | None = Header(default=None)) -> None:
        if public_read:
            return
        scheme, _, token = (authorization or "").partition(" ")
        if not console_token or scheme.lower() != "bearer" or not hmac.compare_digest(token, console_token):
            raise HTTPException(status_code=401, detail="Console token required")

    @app.post("/v1/heartbeats")
    def receive(body: Heartbeat):
        payload = body.payload
        site = sites.get(str(payload.get("site_id")))
        if site is None:
            raise HTTPException(status_code=403, detail="Unknown site")
        expected = hmac.new(site["key"].encode(), _canonical(payload), hashlib.sha256).hexdigest()
        if not body.signature or not hmac.compare_digest(body.signature, expected):
            raise HTTPException(status_code=401, detail="Invalid heartbeat signature")
        if not _valid_payload(payload):
            raise HTTPException(status_code=422, detail="Heartbeat outside metadata schema")
        generated = datetime.fromisoformat(payload["generated_at"])
        now = datetime.now(timezone.utc)
        if abs(now - generated) > MAX_CLOCK_SKEW:
            raise HTTPException(status_code=422, detail="Heartbeat timestamp outside the accepted window")
        with lock:
            last = db.execute(
                "SELECT MAX(generated_at) FROM heartbeats WHERE site_id = ?", (payload["site_id"],)
            ).fetchone()[0]
            if last and payload["generated_at"] <= last:
                raise HTTPException(status_code=409, detail="Replayed or out-of-order heartbeat")
            db.execute(
                "INSERT INTO heartbeats VALUES (?, ?, ?, ?)",
                (payload["site_id"], now.isoformat(), payload["generated_at"], json.dumps(payload)),
            )
            db.commit()
        return {"accepted": True, "site_id": payload["site_id"]}

    @app.get("/v1/sites", dependencies=[Depends(require_console)])
    def fleet():
        now = datetime.now(timezone.utc)
        rows = []
        with lock:
            for site_id, site in sorted(sites.items()):
                found = db.execute(
                    "SELECT payload, received_at FROM heartbeats WHERE site_id = ? ORDER BY generated_at DESC LIMIT 1",
                    (site_id,),
                ).fetchone()
                if found is None:
                    row = {"site_id": site_id, "name": site.get("name", site_id), "status": "never_reported"}
                    row["attention"] = _attention(row)
                    rows.append(row)
                    continue
                payload = json.loads(found[0])
                minutes = int((now - datetime.fromisoformat(found[1])).total_seconds() // 60)
                expected_hash = site.get("expected_model_sha256")
                row = {
                    "site_id": site_id,
                    "name": site.get("name", site_id),
                    "status": "online" if minutes <= stale_minutes else "stale",
                    "minutes_since_heartbeat": minutes,
                    "release_version": payload["release_version"],
                    "mode": payload["site"]["effective_mode"],
                    "model_version": payload["model"]["version"],
                    "model_matches_release": None if not expected_hash else payload["model"]["sha256"] == expected_hash,
                    "audit_chain_valid": payload["audit"]["chain_valid"],
                    "database_healthy": payload["runtime"]["database_healthy"],
                    "read_only": payload["runtime"]["read_only"],
                    "readiness": f"{payload['readiness']['passed']}/{payload['readiness']['total']}",
                    "connectors_open_circuit": [c["connector"] for c in payload["connectors"] if c.get("circuit") == "open"],
                    "activity": payload["activity"],
                }
                row["attention"] = _attention(row)
                rows.append(row)
        return {"sites": rows, "patient_data": "none — heartbeats are allowlisted metadata", "public_read": public_read}

    @app.get("/", response_class=HTMLResponse)
    def console_page():
        return CONSOLE_HTML

    return app


CONSOLE_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>PredictRx fleet console</title>
<style>body{font-family:system-ui;margin:2rem;color:#0f1c24}table{border-collapse:collapse;width:100%}
td,th{border-bottom:1px solid #ddd;padding:.4rem;text-align:left;font-size:.9rem}.online{color:#1f7a4d}.stale,.never_reported{color:#b42318}</style>
</head><body><h1>PredictRx fleet console</h1>
<p>Metadata only. No patient, encounter or user data is ever sent to this console.</p>
<p id="note"></p>
<table><thead><tr><th>Site</th><th>Status</th><th>Release</th><th>Mode</th><th>Model</th><th>Audit chain</th>
<th>Readiness</th><th>Open circuits</th><th>Predictions 24h</th><th>Attention</th></tr></thead><tbody id="rows"></tbody></table>
<script>
const base = location.pathname.replace(/\\/$/, "");
const esc = (v) => String(v ?? "—").replace(/[&<>"']/g, (c) => "&#" + c.charCodeAt(0) + ";");
async function fetchSites(){
  let token = sessionStorage.getItem("fleetToken");
  let r = await fetch(base + "/v1/sites", token ? {headers:{Authorization:"Bearer "+token}} : {});
  if (r.status === 401 && !token) {
    token = prompt("Console token");
    if (token) { sessionStorage.setItem("fleetToken", token); r = await fetch(base + "/v1/sites",{headers:{Authorization:"Bearer "+token}}); }
  }
  return r;
}
async function load(){
  const r = await fetchSites();
  if(!r.ok){document.getElementById("rows").innerHTML="<tr><td colspan=10>Unauthorised</td></tr>";return;}
  const {sites, public_read} = await r.json();
  document.getElementById("note").innerHTML = public_read
    ? 'Public demo console: read-only. Each hospital pushes a signed heartbeat every minute; nothing else leaves the hospital. <a href="/">Open the demo hospital app</a>.' : "";
  document.getElementById("rows").innerHTML = sites.map(s => `<tr><td>${esc(s.name)}</td>
  <td class="${esc(s.status)}">${esc(s.status)}${s.minutes_since_heartbeat!=null?` (${esc(s.minutes_since_heartbeat)} min)`:""}</td>
  <td>${esc(s.release_version)}</td><td>${esc(s.mode)}</td>
  <td>${esc(s.model_version)}${s.model_matches_release===false?" ⚠ hash mismatch":""}</td>
  <td>${s.audit_chain_valid==null?"—":s.audit_chain_valid?"valid":"BROKEN"}</td><td>${esc(s.readiness)}</td>
  <td>${esc((s.connectors_open_circuit||[]).join(", ")||"none")}</td><td>${esc(s.activity?.predictions_24h)}</td>
  <td>${(s.attention||[]).length ? s.attention.map(a => esc(a.message)).join("; ") : "Clear"}</td></tr>`).join("");
}
load(); setInterval(load, 30000);
</script></body></html>"""


def _from_env() -> FastAPI:
    sites_file = Path(os.environ.get("FLEET_SITES_FILE", "sites.json"))
    sites = json.loads(sites_file.read_text()) if sites_file.exists() else {}
    return create_app(
        sites,
        db_path=os.environ.get("FLEET_DB", "fleet.db"),
        console_token=os.environ.get("FLEET_CONSOLE_TOKEN"),
        stale_minutes=int(os.environ.get("FLEET_STALE_MINUTES", "15")),
        public_read=os.environ.get("FLEET_PUBLIC_READ", "").lower() == "true",
    )


app = _from_env()
