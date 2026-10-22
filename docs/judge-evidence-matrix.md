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
| Innovation | Alerting authority is earned: the system can verify data or abstain, and live alerts are software-gated | `/presentation`, `/`, `/evidence` | Missed-detection and false-alert replay cases ship in the demo; complex challengers were rejected under preregistered gates (`docs/model-card.md`) | Built | Independent clinical-safety reviewer statement |
| Technical execution | One audited pipeline from FHIR/HL7/CSV/MLLP/charting to an explainable frozen score | `/integration`, `/operations`, `/api-reference` | 147 backend tests pass; E2E role check 47/47 locally (`docs/evidence/judge-e2e-check.local.json`); recovery drill passed (`docs/evidence/recovery-drill.md`); failure injection 11/11 (`docs/evidence/failure-injection.md`); shipped-image dependency scan: 0 known vulnerabilities after fixing the base image's pip, SBOM published (`docs/evidence/vulnerability-disposition.md`) | Measured | Real vendor conformance feed; independent penetration test |
| Business & global readiness | Staged adoption: readiness → integration → silent evaluation → governed alerts | `/readiness`, `/admin/setup`, `/docs` | No customer, LOI or revenue claimed anywhere in the product | External proof pending | Buyer/budget owner, procurement route, pricing test, written interest (founder research) |
| Impact & ethical AI | High-burden problem handled without over-claiming; privacy and subgroup transparency by design | `/pilot`, `/model`, `/evidence` | Sourced burden dossier with 16 references (BD severe-sepsis mortality 49.2%, zero bundle compliance; 1.8 ICU beds/100k; Kumar hour-gradient; Epic failure vs TREWS benefit) in `docs/impact-evidence.md`; Dataset B AUROC 0.808 / AUPRC 0.079, calibration slope 0.80, subgroup gaps >10 pp disclosed; KPI contract with pilot targets labelled unachieved; WHO-2021 principle mapping; safety case in `docs/safety-case.md` | Measured (retrospective + sourced) | Bangladesh validation; locally measured workflow KPIs; named clinical reviewer |
| Scalability & NRB | Hospitals scale as isolated data planes; vendor sees signed metadata only | `/fleet`, `/operations` | Scale check: 9,600 observations, 1,440 predictions, ≈40 obs/s backfill; 44 snapshot entries; restart restored 43 encounters (`infra/scale_check.py`, `docs/scalability.md`) | Measured | Named NRB/global collaborator; staged fleet rollout tooling |
| Presentation | A three-minute causal story from broken data to governed alerting | `/judge`, `/judge-guide`, `/presentation` | Judge pages and timed replay exist; public demo mode is locked so visitors cannot break the shared replay | Built | Final ≤181-second recorded video and portal submission (founder) |

## Artefacts in this folder

| File | What it proves | Regenerate |
|---|---|---|
| `release-manifest.json/.md` | Source commit, frozen-model SHA match, key-file hashes, rollback procedure | `infra/release_manifest.py` |
| `recovery-drill.json/.md` | Backup → restore → audit verification → restart with measured RTO on synthetic load | `infra/recovery_drill.py` |
| `judge-e2e-check.local.json` | 47 role/surface expectations held against a locally run locked demo API | `infra/judge_e2e_check.py` |
| `failure-injection.json/.md` | 11 injected failures (duplicates, bad unit, implausible value, stale feed, malformed payload, unauthorised writer, unavailable/corrupt DB) all behaved as required | `infra/failure_injection.py` |
| `pip-audit.json`, `npm-audit.json`, `sbom-*.cdx.json`, `vulnerability-disposition.md` | Dependency vulnerabilities of the exact shipped image, each finding fixed or dispositioned with evidence; CycloneDX SBOMs (52 Python + 487 web components) | see disposition doc |
