# PredictRx Sentinel — pitch outline

## Ground rules for every pitch

Say early and plainly:

> PredictRx Sentinel is a retrospective research prototype, not approved for clinical use. It has not been validated in Bangladesh. We do not claim it improves outcomes, prevents sepsis, reduces mortality, or saves cost.

Do not present retrospective metrics as clinical effectiveness. Do not imply hospital, advisor, regulator, sponsor, or funder endorsement without written evidence. Refer to Bangladesh regulatory classification and DGDA obligations as requiring qualified legal/regulatory review.

## 10-slide hospital / investor pitch

### 1. Title — ICU workflow first, responsible AI evaluation second

**Message:** PredictRx Sentinel gives hospitals a digital ICU flowsheet, structured handoff, and quality dashboard, with sepsis scoring kept silent while local evidence is built.

**Proof to show:** workflow screens and explicit research-only banner.

### 2. Problem — fragmented workflow and imported-model uncertainty

**Message:** ICU observations, handoff ownership, missing data, and quality review can be difficult to see in one auditable place. A model trained elsewhere cannot be assumed to transfer to Bangladesh.

**Do not say:** that these problems cause a quantified number of deaths or that this product fixes mortality without evidence.

### 3. Product wedge — value without trusting the model

**Message:** sell what can be evaluated now:

- longitudinal flowsheet and provenance;
- shift handoff and ownership;
- feed health and missing-signal visibility;
- quality/research cohorts and audit export.

The frozen Run 4 score runs silently for evaluation only.

### 4. Current evidence — retrospective, bounded, reproducible

**Message:** Run 4 was evaluated retrospectively on a held-out public US hospital cohort. Its recorded Dataset B AUROC is 0.808 and AUPRC is 0.079; calibration slope is 0.80. Those results are not Bangladesh validation, prospective evidence, or an outcome claim. Measurement-pattern dependence increases transfer risk.

**Do not say:** “clinically proven,” “six-hour probability,” “validated in Bangladesh,” or “reduces false alarms” as an established clinical effect.

### 5. SafeLaunch — 8–12 weeks

**Message:** discover and govern; map data; deploy workflow; validate retrospectively; operate scores silently if approved; decide go, extend, redesign, or stop.

**Boundary:** unchanged Run 4, no threshold tuning, no interruptive alerts, no treatment advice, no autonomous action.

### 6. Success — explicit gates

**Message:** agree targets before analysis across governance, security, data quality, adoption, handoff, research validity, and implementation economics.

**Example starting points:** 90% expected-message coverage after exclusions, 95% provenance, 80% designated-user training, 100 encounters, 30 adjudications, no unresolved critical security event, and a successful restore test. These are discovery assumptions, not validated clinical standards.

### 7. Buyer and route to market

**Message:** start with paid workflow/research pilots for Bangladesh private hospitals, where a defined buyer and implementation budget can shorten learning cycles. Develop public, NGO, university, and open-core routes for wider access and independent research.

**Users:** ICU clinicians, nursing/shift coordinators, quality/research teams, and hospital IT. Not sold to patients.

### 8. Business model — assumptions to test

**Message:** paid implementation plus recurring workflow/research operations and support.

- 8–12 week pilot discovery range: BDT 300,000–1,200,000;
- setup/integration hypothesis: BDT 200,000–500,000;
- recurring hypothesis: BDT 75,000–250,000 per hospital per month;
- public/NGO deployments may use grants, procurement, cost recovery, or open-core delivery.

These are interview and quotation ranges, not established willingness-to-pay or market prices.

### 9. Why disciplined ML, not more complex ML

**Message:** no reinforcement learning now because there is no safe exploration, validated reward, causal attribution, or permission for automated action. No federated learning until at least three sites align intended use, semantics, labels, governance, security, and evaluation; otherwise federation can hide incompatibility.

### 10. Ask

**Hospital ask:** a 60–90 minute discovery workshop, named cross-functional owners, data-feasibility review, and agreement on whether to scope a paid SafeLaunch.

**Grant/sponsor ask:** support governed local evaluation, hospital capacity, integration, security, biostatistics, and dissemination—not clinical rollout claims.

**Investor/partner ask:** fund repeatable deployment learning and workflow productization, with model use gated by evidence.

## Three-minute spoken outline

**0:00–0:25 — problem and insight**

“An ICU prediction is only as trustworthy as the fragmented monitors, labs,
identities and timestamps beneath it. Yet imported models often turn those
differences into a confident-looking number. PredictRx Sentinel is designed to
earn the right to alert.”

**0:25–0:55 — product**

“FHIR, HL7, monitor, lab-file or offline bedside data enters one hospital-local
pipeline. PredictRx validates codes and units, quarantines what it cannot
trust, builds a past-only patient timeline, and runs a frozen sepsis model.
TrustGate can Alert, Watch, request data verification or Abstain. It never
diagnoses or prescribes.”

**0:55–1:45 — live proof**

“This is a genuine held-out PhysioNet case, selected by a fixed rule and
replayed hour by hour through the running model. The risk trajectory, current
drivers, freshness and reliability decision are visible. The frozen model's
held-out Dataset B AUROC was 0.808—but this is retrospective US evidence, not
Bangladesh validation or a claim of clinical benefit.”

**1:45–2:15 — differentiation and scale**

“The innovation is not another risk score. Safety and deployment discipline are
part of the intelligence: explicit missingness, abstention, audit, silent mode
and nine gates before a live alert. A hospital-local data plane protects
identifiable records while reusable FHIR, HL7, LOINC and IEEE 11073 mappings
create a global integration path.”

**2:15–2:40 — business and measurable value**

“We sell a paid readiness assessment, one-ICU integration, and recurring
workflow/research operations before any clinical-alert claim. A first
deployment measures feed coverage, provenance, adoption, quarantine, alert
burden, restore success and implementation cost—not mortality.”

**2:40–3:00 — ask**

“We are seeking one Bangladesh hospital partner for a paid one-ICU readiness
and workflow/research deployment: one bounded data source, silent scoring,
named clinical and IT owners, and explicit stop rules. We are asking to prove
the system responsibly—not asking anyone to trust an unvalidated alert.”

## Objection handling

### “Can clinicians see the sepsis score?”

Not in SafeLaunch. The score stays silent and separate from care. Any future clinical visibility requires local evidence, prospective evaluation, institutional approval, a clinical safety case, and legal/regulatory review.

### “Is DGDA approval required?”

The project team should not give a definitive answer. Intended use, functionality, deployment, and local law affect classification. Qualified Bangladesh legal/regulatory counsel and relevant authorities must review it.

### “Will this reduce mortality or length of stay?”

Unknown. Retrospective and silent evaluation cannot establish that. A separately approved prospective study would be needed.

### “Why not retrain on our data?”

The first need is to measure transfer, labels, missingness, and workflow without moving the goalposts. Run 4 stays frozen. Any future retraining needs a prespecified protocol, sufficient sample, held-out evaluation, version governance, and separate approval.

### “Why no reinforcement learning?”

There is no validated reward, causal basis, safe exploration mechanism, or authorization for automated clinical action. Clicks and acknowledgements are not patient-benefit rewards.

### “Why no federated learning?”

With fewer than three aligned sites, federation adds complexity without demonstrating generalization. It is considered only after three or more sites align definitions, semantics, data quality, governance, security, and evaluation.

### “Who pays?”

The hypothesis is that private hospitals pay for workflow integration, quality tooling, and support. Public or NGO programmes may use procurement, grants, cost recovery, or an open-core route. Discovery must identify the actual budget owner and procurement path.

## Words to use and avoid

| Use | Avoid |
|---|---|
| retrospective research prototype | clinically proven |
| silent scoring/evaluation | live early-warning system |
| held-out retrospective performance | improves patient outcomes |
| Challenge-compatible early-warning score | exact six-hour sepsis probability |
| local validation required | works in Bangladesh |
| workflow/research pilot | clinical deployment |
| simulated alert burden | fewer harmful alerts |
| legal/regulatory review required | DGDA approved / DGDA not required |
| pricing assumption / discovery range | market price / validated willingness-to-pay |
