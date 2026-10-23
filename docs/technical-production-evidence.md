# Technical execution — production evidence dossier

One page that maps the Technical Execution judging criterion to measured
artefacts. Nothing here is aspirational: every claim has a file, a command or
a public URL behind it.

## Rubric → evidence

| What judges look for | Where it is proven |
|---|---|
| Clarity of architecture (input → processing → output) | `docs/architecture.md`; live `/docs` and `/api-reference`; six connectors → one observation contract → frozen model → TrustGate → role-scoped UI |
| Model selection logic | `docs/model-card.md`: LightGBM Run 4 kept; tabular/graph/residual challengers rejected under preregistered gates with paired CIs |
| AI integration depth (ML + retrieval + optional LLM) | Frozen LightGBM scoring; deterministic mapping registry + optional on-prem/OpenAI-compatible mapping copilot (field names/units only, rate-capped); MCP read-only server — no multimodal claims invented |
| Explainability of the intelligence core | Per-prediction drivers; TrustGate state + reasons; clinical-context policy that never edits the probability; model card with failures |
| Code / workflow reliability | **147 backend tests** (full suite); frontend 14; public E2E **50/50** (`docs/evidence/judge-e2e-check.public.json`); failure injection **11/11** (`docs/evidence/failure-injection.md`) |
| Production maturity — security | Role matrix (operator 403 on patient routes); hash-chained audit; SBOM + vuln disposition with rescan-to-zero on shipped image (`docs/evidence/vulnerability-disposition.md`); rate limits; public demo lockdown |
| Production maturity — failure behaviour | Recovery drill with measured RTO (`docs/evidence/recovery-drill.md`); DB unavailable/corrupt boot refuses loudly; stale feed → Verify data; unknown unit / implausible value quarantined |
| Production maturity — release integrity | Release manifest: source commit + frozen model SHA + key-file hashes + rollback procedure (`docs/evidence/release-manifest.md`) |
| Connector robustness | Connector conformance across native JSON, FHIR R4, HL7 v2 ORU, CSV lab (`docs/evidence/connector-conformance.md`); synthetic only, tagged |
| Load behaviour | Scale check 9,600 obs / 1,440 predictions (`docs/scalability.md`); soak check live-rate ticks (`docs/evidence/soak-check.md`) |

## Input → processing → output (one paragraph a judge can check live)

**In:** FHIR R4 Bundle / NDJSON, HL7 v2 ORU, CSV lab, native JSON, bedside
charting, edge MLLP relay. **Process:** mapping registry (human-signed) →
unit/plausibility quarantine → observation contract → past-only feature window
→ frozen LightGBM (SHA-256 verified at start-up) → TrustGate
(Alert/Watch/Verify/Abstain) → readiness gates. **Out:** role-scoped ICU board,
bedside chart, alert queue with ownership, silent-pilot cockpit, hash-chained
audit, patient-free fleet heartbeat. Live: `/integration`, `/`, `/alerts`,
`/pilot`, `/operations`, `/fleet`, `/evidence`.

## Why this is not "features for the sake of AI depth"

- An LLM is used only as an optional mapping copilot behind a deterministic
  fallback — refused for diagnosis/treatment, capped, and refused on external
  endpoints outside demo unless the hospital opts in.
- Multimodal imaging/audio is **not** claimed; the clinical problem is tabular
  ICU time series, and inventing modalities would weaken the score.
- Microservices are **not** required for top band: a well-tested modular
  monolith with a single-writer lease is the deliberate production shape for
  one hospital's data plane.

## Reproduce the evidence pack

```bash
.venv/Scripts/python.exe infra/release_manifest.py --verify
cd backend && ../.venv/Scripts/python.exe ../infra/recovery_drill.py
.venv/Scripts/python.exe infra/failure_injection.py
.venv/Scripts/python.exe infra/connector_conformance.py
cd backend && ../.venv/Scripts/python.exe ../infra/soak_check.py --beds 20 --ticks 30
.venv/Scripts/python.exe infra/judge_e2e_check.py --api https://predictrx-sentinel-demo.onrender.com/api --fleet https://predictrx-sentinel-demo.onrender.com/fleet
```
