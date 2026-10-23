# Judge evidence matrix

One row per judging claim: where a judge can verify it live, what has been
measured, and what is still missing. Statuses are honest — *External proof
pending* means no repository work can substitute for a real person or site.

Regenerate the machine-checked artefacts with:

```bash
.venv/Scripts/python.exe infra/release_manifest.py
cd backend && ../.venv/Scripts/python.exe ../infra/recovery_drill.py
.venv/Scripts/python.exe infra/judge_e2e_check.py --api <demo-api-url> [--fleet <fleet-url>]
cd backend && ../.venv/Scripts/python.exe ../infra/scale_check.py --beds 30 --hours 48
```

| Criterion | Claim a judge can test | Live proof | Measured evidence | Status | Still missing |
|---|---|---|---|---|---|
| Innovation | Unlock why sepsis ML is not everywhere: EHR lock-in + unsafe transfer | `/connection`, `/presentation`, `/`, `/integration` | Connection Ladder L0–U5 + U0–U2 shipped (Vendor Adapter, soft-landing, SMART sandbox, CDS Hooks); Transfer Shield S1–S8 incl. S6 habit gate; commercial/legal playbook — `docs/innovation-adoption-barriers.md`, `docs/business/ehr-partnership-and-commercial-strategy.md` | Built | Epic Showroom live listing remains commercial (not claimed) |
| Technical execution | One audited pipeline from FHIR/HL7/CSV/MLLP/charting to an explainable frozen score | `/integration`, `/operations`, `/api-reference`, `/evidence` | 147 backend tests; public E2E 50/50; connector conformance 6/6; failure injection 11/11; recovery drill; soak 3,600 obs/0 errors; scale 9,600 obs; vuln rescan 0; SBOM; release manifest — dossier `docs/technical-production-evidence.md` | Measured | Independent pen-test is hospital-stage, not a missing prototype control |
| Business & global readiness | Staged adoption: readiness → integration → silent evaluation → governed alerts | `/readiness`, `/admin/setup`, `/docs` | No customer, LOI or revenue claimed anywhere in the product | External proof pending | Buyer/budget owner, procurement route, pricing test, written interest (founder research) |
| Impact & ethical AI | High-burden problem handled without over-claiming; privacy and subgroup transparency by design | `/pilot`, `/model`, `/evidence` | Sourced burden dossier; measured KPI baseline; fairness audit; scenario model; DPIA; WHO mapping; safety case | Measured (retrospective + sourced) | Named-site pilot KPIs when a partner exists |
| Scalability & NRB | Hospitals scale as isolated data planes; vendor sees signed metadata only | `/fleet`, `/operations` | Scale + soak measured; enrolment + release rings `docs/fleet-enrolment-and-release-rings.md`; global corroboration `docs/global-corroboration.md`; CONTRIBUTING + NRB pack; standards alignment | Measured | Named NRB person optional; readiness shipped without fabricating one |
| Presentation | A three-minute causal story from broken data to governed alerting | `/judge`, `/judge-guide`, `/presentation` | Judge pages and timed replay exist; public demo mode is locked so visitors cannot break the shared replay | Built | Final ≤181-second recorded video and portal submission (founder) |

## Artefacts in this folder

| File | What it proves | Regenerate |
|---|---|---|
| `release-manifest.json/.md` | Source commit, frozen-model SHA match, key-file hashes, rollback procedure | `infra/release_manifest.py` |
| `recovery-drill.json/.md` | Backup → restore → audit verification → restart with measured RTO on synthetic load | `infra/recovery_drill.py` |
| `judge-e2e-check.local.json` | 47 role/surface expectations held against a locally run locked demo API | `infra/judge_e2e_check.py` |
| `failure-injection.json/.md` | 11 injected failures (duplicates, bad unit, implausible value, stale feed, malformed payload, unauthorised writer, unavailable/corrupt DB) all behaved as required | `infra/failure_injection.py` |
| `pip-audit.json`, `npm-audit.json`, `sbom-*.cdx.json`, `vulnerability-disposition.md` | Dependency vulnerabilities of the exact shipped image, each finding fixed or dispositioned with evidence; CycloneDX SBOMs (52 Python + 487 web components) | see disposition doc |
| `connector-conformance.json/.md` | Native JSON, FHIR R4, HL7 v2 ORU, CSV lab + unknown-unit quarantine invariant | `infra/connector_conformance.py` |
| `soak-check.json/.md` | Live-rate soak: 20 beds × 30 ticks, 3,600 observations, 0 errors | `infra/soak_check.py` |
