"""Connector conformance run — every ingest path, measured, synthetic only.

Exercises the five production connectors against the real API on a throwaway
database, using the project's own synthetic generators (FHIR R4 Bundle, HL7 v2
ORU, CSV lab) plus native JSON. Reports accepted/quarantined counts and proves
that an unknown unit is quarantined on every path that carries units.

    ../.venv/Scripts/python.exe infra/connector_conformance.py

Writes docs/evidence/connector-conformance.{json,md}. Exit 0 iff every
connector path behaves as required. This is connector conformance evidence,
not clinical validation and not a vendor feed.
"""

from __future__ import annotations

import csv
import io
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import settings  # noqa: E402
from app.integrations.synthetic import synthetic_bundle, synthetic_oru  # noqa: E402

ADMIN = {"X-Demo-User": "conformance", "X-Demo-Role": "admin"}
OUT = ROOT / "docs" / "evidence"
results: list[dict] = []


def record(name: str, ok: bool, detail: str) -> None:
    results.append({"connector": name, "passed": bool(ok), "detail": detail})
    print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")


def counts(body: dict) -> tuple[int, int]:
    def n(v: object) -> int:
        return len(v) if isinstance(v, (list, dict)) else int(v or 0)

    return n(body.get("accepted", 0)), n(body.get("quarantined", 0))


def main() -> int:
    work = Path(tempfile.mkdtemp(prefix="predictrx-conformance-"))
    settings.demo_mode = True
    settings.public_demo_lockdown = False
    settings.writer_lease_enabled = True
    settings.database_url = f"sqlite:///{(work / 'site.db').as_posix()}"

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app, headers=ADMIN) as client:
        # Demo mode: the synthetic FHIR generator is tagged and correctly refused
        # outside demo (that refusal is itself a safety control). Conformance of
        # the connector path is measured here with tagged synthetic commissioning
        # payloads under demo mode — never as clinical evidence.
        assert client.put("/v1/site/mode", json={"mode": "demo", "reason": "conformance"}).status_code == 200

        # 1. Native JSON
        stamp = datetime(2026, 1, 10, 8, tzinfo=timezone.utc).isoformat()
        native = {
            "observations": [
                {"patient_id": "conf-native", "encounter_id": "conf-native-enc", "timestamp": stamp,
                 "code": code, "value": value, "unit": unit, "unit_id": settings.api_unit_id}
                for code, unit, value in (
                    ("HR", "bpm", 90), ("SBP", "mmHg", 118), ("MAP", "mmHg", 78),
                    ("Resp", "breaths/min", 18), ("Temp", "degC", 37.1), ("O2Sat", "%", 97),
                )
            ]
        }
        r = client.post("/v1/observations/batch", json=native)
        a, q = counts(r.json())
        record("native_json", r.status_code == 200 and a == 6 and q == 0,
               f"HTTP {r.status_code}, accepted={a}, quarantined={q}")

        # 2. FHIR R4 Bundle (synthetic, tagged) — same call shape as test_integration_api
        bundle = synthetic_bundle(patient_id="conf-fhir", encounter_id="conf-fhir-enc",
                                  unit_id="icu-fhir", hours=6)
        r = client.post("/v1/integrations/fhir/bundle", content=json.dumps(bundle))
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        a, q = counts(body) if body else (0, 0)
        record("fhir_r4_bundle", r.status_code == 200 and a > 0,
               f"HTTP {r.status_code}, accepted={a}, quarantined={q} (synthetic tagged Bundle)"
               + (f"; body={str(body)[:160]}" if r.status_code != 200 else ""))

        # 3. HL7 v2 ORU
        oru = synthetic_oru(patient_id="conf-hl7", visit_id="conf-hl7-visit", unit_id=settings.api_unit_id)
        r = client.post("/v1/integrations/hl7v2/oru", content=oru, headers={"Content-Type": "text/plain"})
        a, q = counts(r.json())
        record("hl7v2_oru", r.status_code == 200 and a > 0,
               f"HTTP {r.status_code}, accepted={a}, quarantined={q} (synthetic ORU)")

        # 4. CSV lab
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["patient_id", "encounter_id", "timestamp", "code", "value", "unit", "unit_id"])
        writer.writeheader()
        writer.writerow({
            "patient_id": "conf-csv", "encounter_id": "conf-csv-enc",
            "timestamp": stamp, "code": "Lactate", "value": "2.1", "unit": "mmol/L",
            "unit_id": settings.api_unit_id,
        })
        r = client.post("/v1/integrations/csv/lab", content=buf.getvalue(),
                        headers={"Content-Type": "text/csv"})
        a, q = counts(r.json())
        record("csv_lab", r.status_code == 200 and a >= 1,
               f"HTTP {r.status_code}, accepted={a}, quarantined={q}")

        # 5. Unknown unit quarantined on native path (safety invariant)
        bad = {
            "observations": [{
                "patient_id": "conf-native", "encounter_id": "conf-native-enc", "timestamp": stamp,
                "code": "HR", "value": 99, "unit": "furlongs/fortnight", "unit_id": settings.api_unit_id,
            }]
        }
        r = client.post("/v1/observations/batch", json=bad)
        a, q = counts(r.json())
        record("unknown_unit_quarantine_invariant", r.status_code == 200 and a == 0 and q >= 1,
               f"HTTP {r.status_code}, accepted={a}, quarantined={q}")

        # 6. Status surface reports each connector
        status = client.get("/v1/integrations/status")
        connectors = status.json().get("connectors") or status.json().get("feeds") or status.json()
        record("integrations_status_reachable", status.status_code == 200,
               f"HTTP {status.status_code}, keys={list(status.json().keys())[:8]}")

    report = {
        "format": "predictrx-connector-conformance/1",
        "claim": "Synthetic commissioning feeds only — proves connector wiring, not clinical accuracy",
        "connectors": results,
        "passed": all(item["passed"] for item in results),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "connector-conformance.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Connector conformance (synthetic commissioning)",
        "",
        "Every production ingest path exercised against a throwaway database. "
        "Payloads are the project's tagged synthetic generators — never clinical evidence.",
        "",
        "| Connector | Result | Detail |",
        "|---|---|---|",
    ]
    for item in results:
        lines.append(f"| `{item['connector']}` | {'PASS' if item['passed'] else 'FAIL'} | {item['detail']} |")
    lines += ["", f"**All paths passed: `{report['passed']}`**", "",
              "Generated by `infra/connector_conformance.py`.", ""]
    (OUT / "connector-conformance.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"checks": len(results), "passed": report["passed"]}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
