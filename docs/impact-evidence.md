# Impact & ethics evidence dossier

Why this problem, why this design, what benefit would look like as a number,
and which ethical controls are already shipped and verifiable. Every external
figure below is cited; every figure of our own is labelled *measured*,
*modelled scenario*, or *pilot target (not yet achieved)*. Nothing in this
document claims a clinical outcome for PredictRx Sentinel: there is no
Bangladesh validation and no prospective evidence yet, and this dossier is
written so that a judge can see exactly where the evidence ends.

## 1. The problem is large, lethal, and time-critical

- **Global.** Sepsis caused an estimated 48.9 million cases and 11.0 million
  deaths in 2017 — 19.7% of all deaths worldwide — with the highest burden in
  sub-Saharan Africa, Oceania, south and southeast Asia (Rudd et al., *The
  Lancet* 2020; GBD 2017). [1]
- **Bangladesh ICUs.** In a prospective study across 14 Bangladeshi ICUs,
  hospital mortality for severe sepsis was **49.2%**, and compliance with the
  complete Surviving Sepsis Campaign bundle was **zero**; the authors
  attribute this to delayed diagnosis and delayed bundle application. [2] At
  BIRDEM, severe sepsis accounted for **41% of ICU admissions** (95/228). [3]
  At Rajshahi Medical College (2014–15), 22% of ICU admissions were sepsis
  with **46.9% mortality**. [4] These are small, single-country cohorts using
  older definitions — cited as burden signals, not national incidence.
- **Capacity makes delay deadlier.** Bangladesh has about **2,177 ICU beds
  (190 ICUs), 1.8 critical-care beds per 100,000 people** (Lancet Regional
  Health – Western Pacific Asian survey; Bangladesh survey: 2,139 ICU beds,
  1.70/100k, with 38 of 64 districts having no critical-care beds at all).
  [5][6] When a bed is this scarce, late recognition wastes the scarcest
  resource in the system.
- **Time is the mechanism.** In septic shock, each hour of delay to effective
  antimicrobials over the first 6 hours was associated with an average 7.6%
  decrease in survival (Kumar et al., *Critical Care Medicine* 2006; adjusted
  odds of death ×1.119 per hour). [7] A system that shortens recognition time
  targets the variable the literature says matters — and that is measurable
  locally within weeks, unlike mortality.

## 2. What the evidence says about sepsis AI — both directions

**It can help when clinicians actually engage.** In the prospective,
five-hospital TREWS study (590,736 patients monitored; 6,877 with sepsis
identified before antibiotics), provider confirmation of the alert within
3 hours was associated with **3.34 percentage points lower adjusted
in-hospital mortality (18.2% relative)**, 1.85 hours faster first antibiotic
order, and 89% of alerts evaluated by a provider (Adams et al. and companion,
*Nature Medicine* 2022). [8][9] Observational, not an RCT — cited as proof the
mechanism is plausible, not as an effect PredictRx claims.

**It harms trust when deployed unvalidated.** The proprietary Epic Sepsis
Model, installed in hundreds of US hospitals, externally validated at AUROC
**0.63**, alerted on **18% of hospitalizations**, missed **67%** of sepsis
cases, with a positive predictive value of 12% — clinicians would evaluate 8
patients to find one case (Wong et al., *JAMA Internal Medicine* 2021). [10]
Clinicians override **49–96%** of computerised safety alerts (van der Sijs
et al., *JAMIA* 2006; 2020 systematic review: 46.2–96.2%). [11][12]

PredictRx Sentinel is designed *against* the Epic failure mode, point by
point: no proprietary black box (frozen, hash-verified, published model
card); no alerting before local silent evaluation and nine readiness gates;
abstention (`Verify data` / `Abstain`) instead of confident scores on bad
data; alert burden measured per 100 patient-hours (2.05 false alerts on the
geographically distinct Dataset B replay, hour-level specificity 0.839)
rather than asserted; and human acknowledgement with a recorded reason for
every dismissal.

## 3. Measurable benefit: the KPI contract

We do not ask any hospital — or judge — to believe a benefit we have not
measured. The pilot is structured so benefit, if any, appears first in
process KPIs that are computable from the audit log within weeks:

| KPI | How the product measures it | Baseline | Pilot target (not yet achieved) |
|---|---|---|---|
| Feed coverage: % of ICU beds with fresh required signals | TrustGate freshness per bed, `/operations` | Measured at commissioning | ≥ 95% of occupied beds |
| Quarantine rate (unknown codes/units, implausible values) | Integration hub quarantine queue | Measured at commissioning | Downward trend to < 2% of observations as mappings are signed off |
| Alert burden | Shadow alerts per 100 patient-hours (retrospective replay: 2.05 false alerts/100 pt-hours on Dataset B) | Replay-measured | No worse than replay baseline at equal sensitivity |
| Review responsiveness | Alert raised → acknowledged time, from audit chain | — (system is new) | Median ≤ 30 min; TREWS' 3-hour confirmation window is the outer bound [8] |
| Override/dismissal pattern | Dismissals require a reason; reasons are audited | — | 100% of dismissals reasoned; rising override rate triggers gate review, not blame |
| Handoff completeness | Structured handoff generated per shift | Manual baseline at site | Every shift change has a complete generated handoff |
| Subgroup parity | Sensitivity by sex, age band, ICU type, missingness in `/pilot` | Public-data gaps disclosed (§4) | No subgroup > 10 pp below overall without a documented governance decision |

Mortality and length-of-stay are recorded during a pilot as *outcomes under
study*, never as marketing claims. TREWS' shorter survivor length of stay
(median −11.6 h) and Kumar's hour-by-hour survival gradient define why these
KPIs are worth collecting; they are not PredictRx results. [7][8]

**Economic relevance, stated carefully.** A published Dhaka private
hospital rate chart lists an ICU bed at Tk 9,000–12,500/day before oxygen,
ventilation, medicines and tests (Popular Hospitals; Millennium Specialized
Hospital rate cards); reported all-in private ICU costs reach Tk
30,000–50,000+ per day. [13][14][15] In a country with 1.8 critical-care
beds per 100,000 people, an ICU bed-day occupied by a late-recognised,
deteriorating patient is simultaneously a family-level financial shock and a
bed denied to the next patient. PredictRx claims no savings; it claims the
process KPIs above are the honest precursors any savings case must be built
on, and they are measurable before a single outcome claim is made.

## 4. Bias and fairness: what is disclosed, what is monitored

High-risk-band sensitivity of the frozen model, by subgroup (full detail in
`docs/model-card.md`):

| Group | Internal test | Dataset B (distinct cohort) |
|---|---|---|
| Female / male | 0.266 / 0.333 | 0.352 / 0.326 |
| Age 18–44 / 45–64 / 65–79 / 80+ | 0.376 / 0.308 / 0.260 / 0.343 | 0.316 / 0.330 / 0.381 / 0.258 |
| MICU / SICU / unknown | 0.250 / 0.329 / 0.343 | 0.264 / 0.384 / 0.360 |
| Missingness low / medium / high | — | 0.371 / 0.281 / 0.295 |

Disclosed without softening: gaps above 10 percentage points exist (age
18–44 vs 65–79 internally; 65–79 vs 80+ and SICU vs MICU on Dataset B);
overall high-risk sensitivity is modest (0.314 on Dataset B); calibration
slope is 0.80, so local recalibration is mandatory. The weakest group differs
between datasets, consistent with small septic counts per cell — which is
exactly why the product, not the paper, carries the mitigation:

1. **The model cannot be silently re-fit on site.** It is frozen and
   SHA-256-verified at start-up; any recalibration is a new, separately
   evaluated model version with its own model card.
2. **Subgroup performance is a pilot output, not an afterthought.** The
   silent-pilot cockpit recomputes sensitivity, calibration, alert burden
   and lead time by sex, age, unit type and missingness from local
   adjudications (`/pilot`, `docs/model-card.md` §Local monitoring).
3. **Data-poor patients are protected from confident scores.** Missing or
   stale required signals produce `Verify data`/`Abstain`, never a
   reassuring number — the missingness subgroup is where score-only systems
   fail silently.
4. **Clinical context the model cannot see** (pregnancy, comfort-focused
   care, immunosuppression, chronic organ disease) is documented by
   clinicians and modulates alerting under a fixed, audited policy — it
   never edits the probability (`docs/safety-ethics.md`).
5. **A >10 pp local subgroup gap is a governance event**: live alerting
   stays off for the affected pathway until the site's named owners record
   a decision. This is a policy this dossier commits us to; the readiness
   gates are where it is enforced.

Known residual bias risk, stated plainly: the training data are US ICU
records (PhysioNet 2019), much of the signal is care-process (how often
clinicians measure), and none of it is Bangladeshi. The honest mitigation is
the staged pathway itself — retrospective local check, silent evaluation,
subgroup report, governance sign-off — before any interruptive alert exists.

## 5. Responsible data use and transparency (WHO-aligned, verifiable)

Mapped to WHO's *Ethics and governance of artificial intelligence for
health* (2021) six principles [16] — "aligned with", never "certified
compliant":

| WHO principle | Product control | Verify at |
|---|---|---|
| Protect human autonomy | Human acknowledgement/dismiss/escalate on every alert; no automated clinical action; no treatment generation | `/alerts`, `docs/safety-ethics.md` |
| Promote well-being & safety | Silent-first deployment; nine readiness gates before interruptive alerts; abstention on unreliable data | `/readiness`, `/pilot` |
| Transparency & explainability | Published model card with failures and CIs; per-prediction drivers; this dossier; `/evidence` page | `/model`, `/evidence` |
| Responsibility & accountability | Hash-chained audit of every action; named role accountability; dismissal requires a reason | `/operations`, audit verify |
| Inclusiveness & equity | Subgroup disclosure + local parity monitoring (§4); hospital-local deployment keeps data under the hospital's control | `/pilot`, `docs/model-card.md` |
| Responsive & sustainable | Small CPU model (~5 ms/prediction, 1.9 MB) runs on a hospital server; no per-call cloud dependency; decommissioning returns/erases site data with a certificate | `docs/operator-guide.md` §9 |

Data protection specifics: patient data never leaves the hospital server;
the vendor receives only HMAC-signed, allowlisted metadata heartbeats (the
fleet console rejects non-allowlisted fields); the metadata-only `operator`
role is refused patient routes (machine-verified, 50/50 public checks);
backups stay hospital-controlled; offboarding is a certified erase
(`ops_cli decommission`). In Bangladesh the hospital is the data controller
under the Personal Data Protection Ordinance 2025 framing used in
`docs/operator-guide.md`. The public demo contains only de-identified
PhysioNet 2019 records (CC BY 4.0) and clearly labelled synthetic feeds.

## 6. What would change our mind (pre-committed honesty)

- If a silent pilot shows review times do not improve, alert burden exceeds
  the replay baseline at equal sensitivity, or a subgroup gap > 10 pp
  persists after mapping quality is fixed, the correct action is to keep
  alerting off and publish that result. The readiness gates make "off" the
  default state, not a failure state.
- TrustGate's false-alert benefit is **not established** (paired 95% CI
  crosses zero on Dataset A validation); it is presented strictly as a
  data-quality and safety layer. Claiming otherwise would be the kind of
  over-claim §2 criticises.
- No mortality, length-of-stay, cost-saving, or "lives saved" figure for
  PredictRx exists. Any future figure must come from a named site's
  adjudicated pilot data, reported with its denominators.

## References

1. Rudd KE et al. Global, regional, and national sepsis incidence and
   mortality, 1990–2017. *The Lancet* 2020;395:200–211.
   doi:10.1016/S0140-6736(19)32989-7
2. Implementation of Sepsis Bundles in Intensive Care Units of Bangladesh: A
   Prospective Observational Study. *Bangladesh Crit Care J* 2013;1(1).
   doi:10.3329/bccj.v1i1.14359
3. Spectrum of Severe Sepsis in Critically Ill Adult Patients of Bangladesh.
   *Bangladesh Crit Care J* 2015;3(2). doi:10.3329/bccj.v3i2.25102
4. Management of Sepsis in Intensive Care Units in Rajshahi Medical College,
   Bangladesh. *Adv Infect Dis* 2020;10. doi:10.4236/aid.2020.101002
5. Critical care bed capacity in Asian countries and regions. *Lancet Reg
   Health West Pac* 2023. (Bangladesh: 190 ICUs, 2,177 ICU beds, 2,915
   critical-care beds, 1.8/100,000.)
6. Critical care bed capacity of Bangladesh: A Pre and Post COVID-19
   pandemic survey. *Bangladesh Crit Care J* 2022;10(2).
   doi:10.3329/bccj.v10i2.62200
7. Kumar A et al. Duration of hypotension before initiation of effective
   antimicrobial therapy is the critical determinant of survival in human
   septic shock. *Crit Care Med* 2006;34:1589–1596.
   doi:10.1097/01.CCM.0000217961.75225.E9
8. Adams R et al. Prospective, multi-site study of patient outcomes after
   implementation of the TREWS machine learning-based early warning system
   for sepsis. *Nat Med* 2022;28:1455–1460. doi:10.1038/s41591-022-01894-0
9. Henry KE et al. Factors driving provider adoption of the TREWS system
   and its effects on sepsis treatment timing. *Nat Med* 2022.
   doi:10.1038/s41591-022-01895-z
10. Wong A et al. External Validation of a Widely Implemented Proprietary
    Sepsis Prediction Model in Hospitalized Patients. *JAMA Intern Med*
    2021;181(8):1065–1070. doi:10.1001/jamainternmed.2021.2626
11. van der Sijs H et al. Overriding of drug safety alerts in computerized
    physician order entry. *J Am Med Inform Assoc* 2006;13(2):138–147.
    doi:10.1197/jamia.M1809
12. Appropriateness of Overridden Alerts in Computerized Physician Order
    Entry: Systematic Review. *J Med Internet Res* 2020. PMC7400042.
13. Popular Medical College & Hospital Ltd, published rate chart (ICU bed
    Tk 9,000/day). popular-hospital.com/rates
14. Millennium Specialized Hospital Ltd, published room rate (ICU Tk
    12,500/day). mshlbd.com/room-rate
15. "Managing ICU surge during COVID-19 pandemic: Cry for ICU." *The
    Business Standard*, 2021 (reported private all-in ICU costs Tk
    50,000–100,000/day during the pandemic).
16. WHO. *Ethics and governance of artificial intelligence for health.*
    Geneva, 2021. who.int/publications/i/item/9789240029200
