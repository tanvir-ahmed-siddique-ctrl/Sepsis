# PredictRx Sentinel — clinician and hospital IT discovery brief

Use this as a founder briefing for a short, no-patient-data conversation. It is
not a clinical protocol, validation report, endorsement, or deployment request.

## The correction to the pasted evidence note

Do not say, “We have no clinical evidence.” That is too broad. PredictRx was
trained and retrospectively evaluated on de-identified, real ICU records from
the public PhysioNet/CinC 2019 Sepsis Challenge. Dataset A was split by patient
into 70% training, 15% validation, and 15% internal test. A second public,
geographically distinct cohort, Dataset B, was scored once after the model was
frozen. The project reports retrospective discrimination and calibration
metrics on those cohorts.

Do say: **“We have retrospective evidence on de-identified public ICU data,
including a geographically distinct held-out cohort. We do not yet have
Bangladesh hospital validation, prospective evaluation, evidence of improved
care outcomes, or proof that the product's alert workflow is safe or useful in
routine care.”**

The Dataset B result is AUROC 0.808 and AUPRC 0.079. Its calibration slope is
0.80, and the model card says local recalibration is needed before any local
use. At the displayed high-risk threshold, Dataset B sensitivity is 0.314,
specificity is 0.957, and alert precision is 0.132. These are retrospective
benchmark metrics, not expected Bangladesh hospital performance.

The label also needs precise wording. The Challenge-compatible label becomes
positive six hours before its defined onset and remains positive afterwards.
The model's output is therefore a **Challenge-label score**, not a validated
probability of a new sepsis event occurring within exactly six hours.

## PredictRx in plain language

Sepsis is life-threatening organ dysfunction caused by a dysregulated response
to infection. PredictRx is a research prototype that explores whether routine
hourly ICU measurements can identify patterns associated with the PhysioNet
Challenge's sepsis label. It does not diagnose infection, decide treatment, or
replace the bedside team.

The product idea is broader than the model: hospital observations arrive from
different systems and may be late, missing, mislabeled, or measured in
different units. PredictRx validates and timestamps incoming observations,
makes data gaps visible, runs a frozen score where inputs are eligible, shows
the major model factors, and records a human review workflow. If the data are
not trustworthy enough, it can ask for verification or abstain rather than
present a confident score.

## What happens from source data to screen

1. **Hospital sources:** an EHR/HIS, laboratory system, bedside monitor, or
   existing charting process may provide encounters and observations. A real
   hospital connection is not present in the public demo.
2. **Connector:** the prototype has adapters for FHIR R4, HL7 v2 messages,
   CSV, and a native observation API. The hospital and its interface owner
   would decide what is actually available and permitted.
3. **Mapping and validation:** each source code and unit is mapped to a
   canonical observation such as heart rate, blood pressure, oxygen saturation,
   temperature, or lactate. Timestamps, encounter/unit scope, plausible ranges,
   duplicates, and unknown mappings are checked. Rejected or uncertain inputs
   are quarantined for review rather than guessed.
4. **Feature construction:** the system uses the current and prior hourly
   measurements to compute temporal features, changes, measurement frequency,
   missingness, and clinical-score-like features. It uses past-only information
   so a prediction does not use future observations.
5. **Frozen model:** a hash-verified LightGBM model produces the
   Challenge-label score. It is not retrained or re-thresholded in a hospital
   session. The separate optional mapping copilot proposes terminology
   mappings; it is not the sepsis predictor.
6. **Reliability check:** TrustGate considers required-vital freshness,
   availability, and perturbation stability. Depending on the score and data
   quality, the screen can show Alert, Watch, Verify data, or Abstain. The
   current public simulation is not a hospital feed.
7. **Human workflow:** designated staff can review an alert, claim or release
   ownership, acknowledge/escalate, and write a handoff. Actions are recorded
   for later audit. There is no automated treatment action.

Short version: **source → validate/map → build past-only features → frozen
LightGBM → TrustGate → explain and show the state → clinician review and audit.**

## A 30-second introduction

> I am building PredictRx Sentinel, a hospital-local ICU workflow and
> data-quality platform with a frozen sepsis-risk research model. It accepts
> observations through standards-based or file-based connectors, checks their
> mappings and freshness, and shows a retrospective-model score with its main
> factors and a data-reliability state. We have evaluated the model on
> de-identified PhysioNet ICU cohorts, including a held-out public cohort. We
> have not validated it in a Bangladesh hospital or shown that it improves
> outcomes. I am speaking with clinicians and hospital IT to learn whether the
> workflow fits, what data are actually available, and what evidence and
> approvals would be needed before any local evaluation.

For the personal “why I started this” question, use your real reason. Do not
invent an origin story. A truthful template is: “I chose this problem because
[your actual observation, experience, or reason]. The first thing I wanted to
understand was [specific question].”

## Highest-value, lowest-friction first step

Ask one ICU doctor for a 25-minute discovery conversation. The goal is to
understand the current workflow and to ask the doctor to critique the intended
use and screen wording. Do not ask them to certify the model. If they see a
real fit, ask whether they can introduce you to the ICU nurse lead or the
hospital IT/HIS contact for a separate conversation.

An especially useful first outcome is a one-page, participant-corrected note
that records:

- the workflow problem, in the clinician's words;
- how the team handles it today and who owns each step;
- what could make a new alert unsafe, noisy, or easy to miss;
- which data and systems are present, and who owns integration;
- what approvals, local evaluation, and success/stop measures would be needed;
- one concrete next step, its owner, and date.

This is **problem/workflow evidence**. It is not clinical validation, a pilot
approval, an endorsement, a hospital partnership, or permission to use patient
data. An introduction to IT and permission to return with a revised workflow
are stronger signals than a polite “looks interesting.”

## 25-minute clinician conversation

Open with: “I am doing product discovery, not asking you to use a clinical
score. I do not need patient records or identifiers. May I take notes? I will
not quote or name you without separate permission.”

Ask about recent, concrete practice. Avoid starting with “Would you use AI?” or
“Would this save lives?” Those invite guesses and compliments.

1. “Could you walk me through the last shift handoff for a deteriorating ICU
   patient, without using any patient name or identifier?”
2. “Which observations or changes made the team concerned? Where did those
   values come from?”
3. “What was delayed, missing, duplicated, or hard to find?”
4. “Who first noticed the change, who was contacted, and how was responsibility
   handed over?”
5. “What happens when several patients need attention at once?”
6. “What kinds of alerts do staff ignore, and what makes an alert worth
   interrupting someone for?”
7. “Which patient groups or situations would make a population score
   misleading?”
8. “If a screen showed a score plus ‘verify data’ or ‘insufficient data,’ what
   would you expect it to explain?”
9. “What would you measure to decide whether this workflow helped or added
   burden?”
10. “Who else should review the workflow, and what would be the appropriate
    next step?”

Only after listening, show the demo for five minutes. Ask the doctor to narrate
what they think each label means; do not teach the answer first. Note
misunderstandings, missing context, and any label that could cause an unsafe
interpretation. Ask permission before recording, quoting, naming, or sharing
the notes.

## What to ask hospital IT/HIS

Explain that the demo uses synthetic encounters and no hospital EHR is
connected. Ask for system metadata or a non-production schema only; do not
request live patient records.

- Which HIS/EHR, LIS, monitor, and interface-engine products and versions are
  used in the target ICU?
- Which interfaces are available today: HL7 v2, FHIR, vendor API, CSV, or a
  controlled database export? Who owns each interface?
- Are non-production endpoints and synthetic/test messages available?
- How are patient, encounter, unit, bed, and transfer identifiers assigned?
- Who owns local lab codes, units, timestamp/timezone rules, and the bed master?
- What network boundary, hosting location, identity provider, TLS, secrets,
  backup, logging, and vulnerability-review requirements apply?
- Who can approve a read-only retrospective evaluation? Which ethics, privacy,
  security, research, procurement, and clinical-safety reviews are required?
- What data retention and deletion rules apply, and who verifies backup and
  closeout?
- What would a small technical feasibility assessment need to deliver, and who
  would approve that work?

The useful output is a source inventory: system/vendor/version, interface
type, data owner, terminology/unit owner, test environment, expected cadence,
security boundary, approvals, and next technical action. No patient values or
identifiers are needed for this inventory.

## Honest scalability explanation

> The architecture is modular: several connector formats map into one
> canonical observation contract, and the intended hospital data plane can run
> locally with CPU inference. The public demo is a single simulated site. It
> does not prove multi-hospital scale: the current state writer is single-writer
> and horizontal API scaling is disabled. Before a real deployment we need
> site-specific interface conformance, load/soak and recovery testing,
> installation/rollback, security review, local identity and backup setup,
> monitoring/support ownership, and regulatory/institutional review.

Do not say “works at any hospital” until more than one site's integration and
operating constraints have been tested. Standards reduce adapter work; they do
not eliminate site-specific mapping, security, governance, or procurement.

## What the founder can do next

1. Prepare the 30-second introduction and one-page architecture sketch above.
2. Get one warm introduction to an ICU clinician; conduct the 25-minute
   interview without opening the demo first.
3. Ask for permission to send a factual one-page summary for correction.
4. Request an introduction to an IT/HIS contact only if the clinician agrees
   it is appropriate.
5. Update the product's problem statement from what people actually report,
   including evidence that disagrees with the original idea.
6. Keep the interview summary separate from retrospective model results and
   from any future pilot or commercial commitment.

For actual clinical use or a study using hospital data, ask the hospital's
clinical research, privacy, security, and regulatory owners to determine the
required approvals. DGDA published an approval notice for a Bangladesh
healthcare AI and medical robotics regulation guideline on 22 April 2026; read
the actual guideline with qualified local regulatory advice before making a
deployment or classification claim.

## Sources to cite in a competition answer

- Project facts and split/metrics: [`model-card.md`](../model-card.md) and
  [`data-card.md`](../data-card.md).
- Public challenge cohort and dataset description: [PhysioNet/CinC 2019
  Challenge dataset](https://physionet.org/content/challenge-2019/1.0.0/).
- Challenge paper: [Early Prediction of Sepsis from Clinical Data: the
  PhysioNet/Computing in Cardiology Challenge 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6964870/).
- Sepsis-3 consensus definition: [Singer et al., JAMA
  2016](https://jamanetwork.com/journals/jama/fullarticle/2492881).
- Bangladesh notice: [DGDA notices](https://dgda.gov.bd/pages/notices/) — locate the 22 April 2026 notice and read the actual guideline before making regulatory or deployment claims.
