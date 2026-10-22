# Safety case — PredictRx Sentinel (research prototype)

A structured argument that the known hazards of an ICU risk-alerting system
are controlled by named mechanisms, each backed by a test or an operational
control. This is an engineering safety case for a research prototype; it is
not a regulatory clearance, clinical validation or approval for care.

## Top-level claim

**No interruptive clinical alert can be produced by untrusted data, an
unverified model, an unauthorised role, or a site that has not passed its
readiness gates — and every exception is visible in an audit trail.**

## Hazard → control → evidence

| # | Hazard | Control (mechanism) | Evidence |
|---|---|---|---|
| H1 | Model artefact swapped or corrupted before scoring | ACTIVE.json registry pins the frozen Run 4 SHA-256; start-up refuses a mismatch | `backend/app/services/engine.py` `_active_model_path`; `infra/release_manifest.py --verify`; model hash on `/evidence` |
| H2 | Score presented on stale or missing data | TrustGate states: Alert / Watch / Verify data / Abstain; insufficient history shows no score | TrustGate tests in `backend/tests/`; `/model` and patient pages show state + reasons |
| H3 | Unknown lab codes or wrong units silently guessed | Versioned LOINC/unit registry, range validation, quarantine with provenance; nothing unmapped reaches features | Integration tests; `/integration` quarantine view; mapping sign-off bound to registry SHA |
| H4 | Duplicate / late / out-of-order feed data corrupts the timeline | Idempotency keys, revisioned re-scoring, audit of every recompute | Integration API tests (duplicate, late-data cases) |
| H5 | Alert fatigue from a noisy threshold | Silent mode first; nine readiness gates incl. shadow alert-burden limits must pass before live mode | `docs/operations.md` gate table; `/pilot` shadow metrics |
| H6 | Automation bias — staff over-trust the number | Plain-language drivers labelled associative (TreeSHAP), data-quality shown beside every score, human acknowledge/dismiss/escalate with reason | Patient page; alert workflow tests |
| H7 | Wrong population (pregnancy, comfort care, chronic baselines) misread by a population model | Physician-documented context policy after scoring; shadow-only for out-of-scope groups; suppressions expire at a review deadline | `docs/safety-ethics.md` context table; clinical-context tests |
| H8 | Vendor (operator) account reaches patient data | Role guard: operator gets metadata routes only; patient routes return 403 | `backend/tests/test_roles.py`; `infra/judge_e2e_check.py` (47 checks, 0 failures locally) |
| H9 | Patient data centralised at the vendor | Hospital-local data plane; fleet heartbeat is an allowlist, HMAC-signed, replay-protected; console rejects non-allowlisted fields | `backend/app/fleet.py`, `control-plane/fleet_console.py`, fleet tests |
| H10 | LLM invents a terminology mapping or receives patient data | Copilot receives field names/units only, may only choose among retrieved candidates or "none", answers outside candidates are discarded, human signs the registry SHA | Copilot tests incl. PHI-pattern refusal; `/integration` copilot panel |
| H11 | Audit trail altered after the fact | Append-only hash-chained audit; `ops_cli verify-audit` recomputes the chain; Prometheus gauge `predictrx_audit_chain_valid` | Recovery drill restored 409 events with a valid chain (`docs/evidence/recovery-drill.md`) |
| H12 | Crash loses encounters or double-writes | Single-writer database lease (second instance is read-only), per-encounter incremental snapshots, logical backup/restore | `docs/scalability.md`; `infra/recovery_drill.py`; site-mode/snapshot regression tests |
| H13 | Ward score confused with ICU sepsis model | NEWS2 is a separate deterministic rule module; ward observations never enter the frozen ICU model | NEWS2 tests; `/ward` labelling |
| H14 | Treatment or dosing advice generated | Evidence retrieval refuses treatment/dosing questions; product has no treatment output surface | Guideline/evidence tests |

## Residual risks (open, owned)

| Risk | Status |
|---|---|
| Model transfer to Bangladeshi ICUs (care-process features are hospital-specific) | Open — requires local retrospective validation, then silent pilot; the readiness passport currently recommends *Retrospective validation* |
| Calibration slope 0.80 on Dataset B | Open — thresholds/calibration must be re-fitted locally under a prespecified protocol before any clinical use |
| TrustGate false-alert benefit not established (paired CI crosses zero) | Open — presented as a data-quality layer only; measured again in silent pilots |
| Single-writer availability (writer host failure needs operator restart after lease expiry) | Controlled — documented failover in `docs/operations.md`; automated promotion is roadmap |
| No independent penetration test yet | Open — required before a hospital pilot; not claimed as done |
| Subgroup sensitivity gaps >10 pp on retrospective cohorts | Disclosed in `docs/model-card.md`; subgroup metrics are mandatory pilot outputs |

## Rules that keep this safety case true

- The frozen model, its thresholds and this file's claims change only through
  a new version with its own evaluation.
- Any new route returning patient-level data must refuse the `operator` role
  and be added to `infra/judge_e2e_check.py`.
- Any new fleet-heartbeat field must be added to both allowlists and proven
  patient-free.
