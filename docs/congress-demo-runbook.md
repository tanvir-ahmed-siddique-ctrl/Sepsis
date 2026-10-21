# AI Congress demo runbook

## Readiness verdict

The Congress build is ready as an **offline research-prototype demonstration**:
frozen Run 4, held-out replay, TrustGate, bedside/ward workflow, integration
hub, readiness gates and explicit non-clinical disclaimers. It is not a
finished medical device and must not be presented as validated for Bangladesh
or as improving patient outcomes.

## Before leaving for the venue

1. Run `docker compose up -d --build`.
2. Run `.venv/Scripts/python.exe infra/congress_demo.py check`.
3. Open `/presentation`, `/`, `/integration`, `/chart`, `/ward`, `/readiness`
   and `/admin/setup` once so browser assets are cached.
4. Disconnect Wi-Fi and repeat the check plus the presentation replay.
5. Carry the laptop charger, HDMI/USB-C adapters, a mouse and a local copy of
   the pitch PDF/video fallback.
6. Do not carry real patient data or production secrets.

## Three-minute judged story

The team-judging slot is three minutes, followed by one minute for scoring. Use
only `/presentation`; opening extra pages is a backup for questions.

| Time | Screen | Message |
|---|---|---|
| 0:00–0:25 | Hero + evidence strip | ICU AI fails when fragmented, stale or differently measured data is treated as certainty. PredictRx earns the right to alert. |
| 0:25–0:55 | Connect → Verify → Reason → Govern | Hospital-local FHIR/HL7/CSV/monitor/chart inputs enter one canonical, auditable pipeline. Unknown data is quarantined, not guessed. |
| 0:55–1:45 | Held-out replay | Show risk rising, visible drivers and TrustGate. The system can Watch, request data verification or Abstain; it never prescribes. |
| 1:45–2:15 | Differentiation + scale | Safety is part of the intelligence. Standards and local data planes support reuse without centralising patient records. |
| 2:15–2:40 | Commercial path + first-deployment measures | Sell readiness, integration and workflow/research operations before any clinical claim. Measure feed quality, adoption, burden, restore and implementation cost. |
| 2:40–3:00 | Ask | Seek one Bangladesh hospital for a paid one-ICU readiness and workflow/research deployment with silent scoring and explicit stop rules. |

Do not attempt to show every module during the judged slot. For questions, use:

- `/integration` for connector, mapping and quarantine depth;
- `/patient/{id}` for provenance, freshness and explanation;
- `/admin/setup` for users, units and deployment readiness;
- `/readiness` for the nine live-alert gates;
- `/chart` and `/ward` for offline charting and deterministic NEWS2.

## Safe claims

- “Retrospective Dataset B AUROC was 0.808 for frozen Run 4.”
- “This case is from the held-out PhysioNet internal test split and selected by
  a fixed median-warning-time rule.”
- “The product supports local retrospective and silent-pilot evidence
  collection.”
- “Ward NEWS2 is deterministic RCP 2017 logic and is separate from the ICU
  machine-learning model.”

Do **not** say that the product diagnoses sepsis, reduces mortality, is
Bangladesh-validated, is regulatory-approved, recommends treatment, or is
ready for autonomous/live use.

## Recovery

- Replay stuck: press **Restart** or run
  `.venv/Scripts/python.exe infra/congress_demo.py reset`.
- Browser problem: open `http://127.0.0.1:3000/presentation` in a fresh tab.
- API problem: `docker compose restart api`; wait for `/ready`.
- Full reset: `docker compose down` then `docker compose up -d`. Do not add
  `-v`, because that deletes the local database.
- Venue failure: play the local recording and continue with architecture,
  evidence and pilot slides. Never improvise a clinical claim.

## After the demo

Capture interested hospital, clinician, ethics, IT and funding contacts
separately. The next step is a discovery/data-mapping workshop—not immediate
live deployment. Use the [pilot proposal](business/pilot-proposal.md) and
[hospital onboarding runbook](hospital-onboarding.md).
