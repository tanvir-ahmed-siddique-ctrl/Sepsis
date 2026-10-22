"""Judge-link end-to-end check: every role, every key surface, over HTTP.

Verifies the public demo (or any deployment) behaves as documented: clinical
roles reach clinical surfaces, the metadata-only operator is refused patient
data, admin surfaces work, fleet console is metadata-only, and the frozen
model hash is the registered one. Demo headers are used, so run this only
against a demo-mode instance.

    python infra/judge_e2e_check.py --api https://<host>/api --fleet https://<host>/fleet
    python infra/judge_e2e_check.py --api http://127.0.0.1:8000   # local compose API

Exit code 0 means every expectation held. A JSON report is printed.
"""

from __future__ import annotations

import argparse
import json
import sys

import httpx

EXPECTED_MODEL_SHA256 = "a7dcf5f4b2f00927c17d2468cba144b3db4642ccb5a9c946b484958a0413532d"

ROLES = ("nurse", "clinician", "admin", "operator")

# (path, roles expected to get 200, roles expected to get 403)
CHECKS: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("/v1/units", ("nurse", "clinician", "admin"), ("operator",)),
    ("/v1/units/icu-demo-1/overview", ("nurse", "clinician", "admin"), ("operator",)),
    ("/v1/alerts", ("nurse", "clinician", "admin"), ("operator",)),
    ("/v1/model", ROLES, ()),
    ("/v1/site/readiness", ("admin", "operator"), ("nurse", "clinician")),
    ("/v1/integrations/status", ("admin", "operator"), ("nurse", "clinician")),
    ("/v1/integrations/mappings/unmapped", ("admin", "operator"), ("nurse", "clinician")),
    ("/v1/ops/status", ("admin", "operator"), ("nurse", "clinician")),
    ("/v1/ops/heartbeat", ("admin", "operator"), ("nurse", "clinician")),
    ("/v1/auth/users", ("admin",), ("nurse", "clinician", "operator")),
)


def headers(role: str) -> dict[str, str]:
    return {"X-Demo-User": f"judge-check-{role}", "X-Demo-Role": role}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--api", required=True, help="API base URL, e.g. https://host/api or http://127.0.0.1:8000")
    parser.add_argument("--fleet", default=None, help="Fleet console base URL (optional)")
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()
    api = args.api.rstrip("/")

    failures: list[str] = []
    results: list[dict] = []

    def record(name: str, ok: bool, detail: str) -> None:
        results.append({"check": name, "ok": ok, "detail": detail})
        if not ok:
            failures.append(f"{name}: {detail}")

    with httpx.Client(timeout=args.timeout, follow_redirects=True) as client:
        health = client.get(f"{api}/health")
        record("health", health.status_code == 200, f"GET /health -> {health.status_code}")
        ready = client.get(f"{api}/ready")
        record("ready", ready.status_code == 200, f"GET /ready -> {ready.status_code}")

        for path, allowed, refused in CHECKS:
            for role in allowed:
                response = client.get(f"{api}{path}", headers=headers(role))
                record(f"{role} {path}", response.status_code == 200, f"expected 200, got {response.status_code}")
            for role in refused:
                response = client.get(f"{api}{path}", headers=headers(role))
                record(f"{role} refused {path}", response.status_code == 403, f"expected 403, got {response.status_code}")

        model = client.get(f"{api}/v1/model", headers=headers("clinician"))
        if model.status_code == 200:
            body = model.json()
            record("frozen model hash", body.get("model_hash") == EXPECTED_MODEL_SHA256,
                   f"model_hash={body.get('model_hash')}")
            record("model frozen flag", body.get("frozen") is True, f"frozen={body.get('frozen')}")
        else:
            record("frozen model hash", False, f"GET /v1/model -> {model.status_code}")

        heartbeat = client.get(f"{api}/v1/ops/heartbeat", headers=headers("operator"))
        if heartbeat.status_code == 200:
            text = heartbeat.text
            forbidden = [word for word in ("patient_id", "encounter_key", "display_name", "BED-") if word in text]
            record("heartbeat carries no patient fields", not forbidden, f"forbidden fields present: {forbidden}")
            record("heartbeat signed or explicitly unsigned",
                   heartbeat.json().get("signature_algorithm") in {"HMAC-SHA256", "unsigned"},
                   f"algorithm={heartbeat.json().get('signature_algorithm')}")
        else:
            record("heartbeat carries no patient fields", False, f"GET /v1/ops/heartbeat -> {heartbeat.status_code}")

        mode = client.put(f"{api}/v1/site/mode", headers=headers("admin"),
                          json={"mode": "silent", "reason": "judge e2e probe"})
        record("public demo mode locked (or audited change accepted)",
               mode.status_code in (200, 403), f"PUT /v1/site/mode -> {mode.status_code}")
        if mode.status_code == 200:  # a local, non-locked demo: restore immediately
            client.put(f"{api}/v1/site/mode", headers=headers("admin"),
                       json={"mode": "demo", "reason": "judge e2e restore"})

        if args.fleet:
            fleet = client.get(f"{args.fleet.rstrip('/')}/v1/sites")
            record("fleet console reachable", fleet.status_code == 200, f"GET fleet/v1/sites -> {fleet.status_code}")
            if fleet.status_code == 200:
                body = fleet.json()
                record("fleet declares no patient data", "none" in str(body.get("patient_data", "")),
                       f"patient_data={body.get('patient_data')!r}")
                record("fleet lists at least one site", len(body.get("sites", [])) >= 1,
                       f"sites={len(body.get('sites', []))}")

    report = {"api": api, "fleet": args.fleet, "checks": len(results), "failures": failures, "results": results}
    print(json.dumps(report, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
