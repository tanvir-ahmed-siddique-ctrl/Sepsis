# Global corroboration dossier — independent published alignment

We do not invent a named NRB reviewer. Instead, this dossier shows that
independent researchers, regulators and implementers worldwide have already
published findings that **corroborate the exact design choices** PredictRx
Sentinel made — hospital-local data plane, silent-first evaluation,
evidence-gated alerting, human-in-the-loop, transparency. Citation is not
endorsement of PredictRx; it is evidence that our trade-offs match the
emerging global consensus for clinical AI safety.

## 1. Unvalidated score-only alerting fails in the field

Wong et al. (*JAMA Internal Medicine* 2021) externally validated the
proprietary Epic Sepsis Model across 38,455 hospitalizations: hospitalization-level
AUROC **0.63**, alerts on **18%** of hospitalizations, **67% of sepsis cases
missed**, PPV 12%. Clinicians would evaluate eight patients to find one case.
This is the failure mode PredictRx is built against: no proprietary black box,
no live alerts before local silent evaluation, abstention on bad data, published
model card with failures disclosed.

## 2. Silent / shadow evaluation before live alerts is best practice

- Sendak et al., Sepsis Watch at Duke (*JMIR Medical Informatics* 2020): a
  **three-month silent period** before launch — real-time data, clinical leaders
  reviewing outputs, workflow tested, **no routine alerts influencing care**
  until the silent period completed. PredictRx's silent-first site mode and
  nine readiness gates are the same pattern, software-enforced.
- Tonekaboni et al., "Silent trial protocol for evaluation of real-time models
  at ICU" (*Proceedings of MLResearch* 2022): a formal silent-trial protocol
  for ICU ML prior to deployment, emphasising formative testing of performance
  and fit to the intended environment. Our `/pilot` cockpit is that protocol
  productised.

## 3. When clinicians engage, early-warning systems can help

Adams et al. / Henry et al. (*Nature Medicine* 2022), TREWS across five
hospitals: provider confirmation of an alert within 3 hours was associated
with **3.34 percentage points lower adjusted mortality** and antibiotics
**1.85 hours faster**, with **89% of alerts evaluated**. Observational, not an
RCT — cited as mechanism corroboration. PredictRx claims none of that effect;
it measures review time first and keeps interruptive alerts off until the site
earns them.

## 4. Regulators ask for local site acceptance and human–AI team performance

FDA / Health Canada / MHRA *Good Machine Learning Practice* guiding principles
(2021) require, among others: multi-disciplinary expertise across the lifecycle;
independent training/test sets; **focus on the performance of the Human–AI
team**; clear essential information for users; deployed performance monitoring;
and (in related FDA transparency guidance) **how to conduct local site-specific
acceptance testing or validation**. PredictRx's frozen model + silent pilot +
subgroup monitoring + human acknowledgement is GMLP-aligned by design. We do
not claim FDA clearance or certification.

## 5. Hospital-local / on-premise inference is a deliberate privacy architecture

Independent implementers and researchers argue that PHI-heavy clinical
inference should stay inside the hospital perimeter:

- Responsible Clinical AI architecture guidance: the single most consequential
  decision is where the model runs; cross-tenant or uncontrolled cloud PHI
  flow is the company-ending failure mode.
- UK Bonn University Hospital prospective pilot of on-premise open-weights LLMs
  in radiology (arXiv 2026): isolation-first, network-segmented local
  inference was required to process unanonymised PHI under institutional
  governance.
- Edge/local CDSS literature: every hop that leaves the hospital boundary
  changes the privacy and compliance profile; keeping sensitive fields local
  reduces exposure.

PredictRx's per-hospital data plane + patient-free HMAC fleet heartbeat is
this consensus in product form — not a shortcut around cloud, a deliberate
architecture for PHI.

## 6. WHO ethics principles for AI in health

WHO *Ethics and governance of artificial intelligence for health* (2021) —
six principles: autonomy; well-being & safety; transparency & explainability;
responsibility & accountability; inclusiveness & equity; responsive &
sustainable. Mapped control-by-control in `docs/impact-evidence.md` §5.
"Principles-aligned", never "WHO-certified".

## How this substitutes for a named NRB reviewer (honestly)

| What a named reviewer would give | What this dossier gives | What it still does not give |
|---|---|---|
| Independent person saying "your design is sound" | Independent published literature converging on the same design | A person who reviewed *our* code and named themselves |
| Global collaboration signal | Explicit invitation pack + CONTRIBUTING so any NRB/global builder can join today (`docs/nrb-global-builder-pack.md`) | A signed contribution already in the git log |
| Cross-border credibility | Citations to US (Duke, Michigan/Epic validation, Johns Hopkins TREWS), UK/EU (on-prem LLM pilot), WHO, FDA/IMDRF | A Bangladesh-based named co-author |

When a named NRB or global reviewer becomes available, their bounded statement
slots into this dossier under §7 (reserved). Until then, the global published
record is the corroboration we can defend without fabricating people.

## Reserved — named reviewer (blank until real)

| Field | Value |
|---|---|
| Name / affiliation | |
| Contribution (bounded) | |
| Date reviewed | |
| Permission to name publicly | |
| Statement (their words) | |
