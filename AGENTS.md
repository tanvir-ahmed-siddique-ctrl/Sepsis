# Instructions for AI coding agents

PredictRx Sentinel is a hospital-local ICU research prototype. Treat the rules
below as invariants.

## Never

- Modify, retrain or re-threshold the frozen Run 4 model in `ml/artifacts`.
  Start-up verifies its SHA-256.
- Run Dataset B evaluation commands; Dataset B was scored once after freeze.
- Add real or realistic patient identifiers to code, tests, fixtures or docs.
- Claim clinical validation, outcome improvement, regulatory approval,
  customers, revenue, advisers or partners that are not documented.
- Let any route that returns patient-level data accept the `operator` role.
- Let an LLM invent codes, unit conversions, diagnoses or treatments.
- Let patient context change a model probability, or suppress an alert
  without a documented reason and a review deadline.
- Add a field to the fleet heartbeat without adding it to both allowlists
  (`backend/app/fleet.py` and `control-plane/fleet_console.py`) and
  confirming it carries no patient, bed, user or free-text value.
- Erase site data any way other than `ops_cli decommission`, which first proves
  the hospital holds a verified backup identical to the live database.
- Put patient data on the public demo stack (`docker-compose.public-demo.yml`).

## Always

- Map new source formats into the existing canonical observation contract.
- Keep interruptive alerts behind the site readiness gates.
- Record security- or mapping-relevant actions in the audit log.
- Run the checks below before reporting work as done.

## Checks

```bash
# backend (from backend/)
../.venv/Scripts/python.exe -m pytest -q
# frontend (from frontend/)
npx tsc --noEmit && npm run lint && npm test -- --run && npm run build
# edge (from the repository root)
.venv/Scripts/python.exe -m pytest -q edge/tests
# copilot benchmark (optional, needs Ollama; from backend/)
COPILOT_LLM_URL=http://127.0.0.1:11434 COPILOT_EMBED_MODEL=qwen3-embedding:0.6b \
  ../.venv/Scripts/python.exe -m app.integrations.copilot_benchmark
# full stack, after docker compose up -d --build
python infra/congress_demo.py check
```
