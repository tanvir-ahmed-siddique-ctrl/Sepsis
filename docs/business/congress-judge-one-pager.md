# PredictRx Sentinel — Congress judge brief

## One sentence

PredictRx Sentinel is a hospital-local ICU workflow and data-quality command
centre that lets a hospital evaluate a frozen sepsis model silently and earn
the right to alert through explicit evidence and governance gates.

## Input → intelligence → output

`FHIR / HL7 / monitor / CSV / bedside chart`
→ identity, code, unit and timestamp validation
→ quarantine unknown data
→ past-only 24-hour features
→ frozen Run 4
→ TrustGate: Alert / Watch / Verify data / Abstain
→ silent evidence first; no live alert until nine gates pass.

## Evidence judges can verify offline

- Frozen model SHA-256:
  `a7dcf5f4b2f00927c17d2468cba144b3db4642ccb5a9c946b484958a0413532d`
- Dataset B one-time held-out retrospective AUROC: **0.808**
  (95% CI 0.797–0.820).
- Dataset B AUPRC: **0.079**; calibration slope: **0.80**.
- The live presentation replays a separately identified **Dataset A internal
  test** case selected by a fixed median-warning-time rule.
- Six ingest paths plus the durable on-site edge relay.
- 220 ML, backend, frontend and edge tests in the current tree.
- `infra/congress_demo.py check` verifies model integrity, API readiness and
  the offline judge route.

## Innovation

The innovation claim is not “a new sepsis algorithm.” It is an operational
safety architecture around hospital AI:

- missingness and freshness are first-class model inputs and visible evidence;
- unknown source codes and units are quarantined rather than guessed;
- the model can abstain;
- ward NEWS2 and ICU ML are isolated;
- late data triggers revisioned re-scoring and audit;
- live mode is software-gated by local evidence, feeds, security and governance.

## Business

Initial offer:

1. paid hospital readiness and source assessment;
2. one-ICU installation, mapping and synthetic commissioning;
3. recurring workflow/research operations and support;
4. clinical alert module only after local evidence and authorization.

The immediate ask is one Bangladesh hospital partner for a paid, bounded
workflow/research deployment with silent scoring and explicit stop rules.

## Responsible-AI boundary

This is a retrospective research prototype. It is not approved for clinical
use and is not validated in Bangladesh. It does not diagnose, prescribe,
contact patients, change treatment, retrain itself or silently change
thresholds. No mortality, cost-saving, TrustGate false-alert reduction or
clinical-outcome claim is made.

## Current limitation and scale path

No hospital LOI, local validation, named NRB collaborator or regulatory
determination is claimed today. The deployed architecture is one hospital per
data plane. Repeatable site enrolment and a future metadata-only control plane
can scale operations without centralising identifiable patient records.

## Offline routes

- Judge page: `http://127.0.0.1:3000/presentation`
- Model evidence: `http://127.0.0.1:3000/model`
- Readiness passport: `http://127.0.0.1:3000/readiness`
- Integration proof: `http://127.0.0.1:3000/integration`

