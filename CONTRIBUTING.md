# Contributing to PredictRx Sentinel

For Non-Resident Bangladeshi (NRB) specialists, global builders and hospital
engineers who want to join without a special invitation. The product is a
hospital-local ICU intelligence layer; contributions must keep that safety
model intact.

## Before you write code

1. Read `AGENTS.md` (hard product rules: frozen model, no fabricated clinical
   claims, operator never sees patient data, no Dataset B re-scoring).
2. Read `docs/architecture.md`, `docs/safety-ethics.md` and
   `docs/global-corroboration.md` so you know why the design looks the way it
   does.
3. Run the stack locally (`docker compose up -d --build`) and
   `python infra/congress_demo.py check`.

## Good first contributions (bounded, reviewable)

| Area | Example | Must not |
|---|---|---|
| Docs / i18n | Bangla nurse quick-reference improvements; clearer runbooks | Invent clinical claims |
| Connectors | A new mapping for a real HIS code your hospital uses (with sign-off) | Guess units into the model |
| Tests | Extra failure-injection scenario; role-matrix case | Weaken operator 403s |
| Fleet / ops | Backup-status field on the heartbeat allowlist (both sides) | Add patient fields to the heartbeat |
| Frontend | Accessibility, empty states, evidence-page clarity | Hide TrustGate / disclaimer |

## Hard refusals

- Do not modify the frozen Run 4 model weights or claim a new clinical AUROC.
- Do not centralise patient data into the fleet console.
- Do not add treatment, dosing or diagnosis generation.
- Do not present synthetic or PhysioNet replay as a live Bangladesh hospital.

## How to propose work

1. Open an issue describing the change and which safety rule it respects.
2. Keep PRs small and reversible; include or update a test.
3. For anything touching patient routes, update `infra/judge_e2e_check.py`.
4. For anything touching the heartbeat, update **both** the site allowlist and
   the console allowlist in the same PR.

## NRB / global reviewer path (non-code)

If you prefer to review rather than code: use the one-page invitation in
`docs/nrb-global-builder-pack.md`. A bounded written review (architecture,
safety case, or integration readiness) with your affiliation and permission to
name is more valuable to us than an unbounded endorsement.
