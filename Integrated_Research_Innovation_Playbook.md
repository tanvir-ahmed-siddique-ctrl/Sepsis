# Veyra — Integrated Research, Deployment & Innovation Playbook

**Purpose:** One compact handoff combining prior Bangladesh ICU/sepsis research with international evidence on why AI sepsis prediction models are not universally deployed. It is designed for another AI assistant to continue the work without repeating completed research. Not every claim has been independently re-verified in this file.

## 1. Project in one minute

**Veyra** (formerly PredictRx Sentinel) is a research-stage AI clinical decision-support prototype for **adult ICU sepsis / clinical-deterioration early warning** in Bangladesh. Intended approach: use existing hospital data (EHR/HIS, LIS, bedside monitors, authorized observations), estimate risk, show interpretable signals, and support—not replace—clinical judgment. Wearables are **not** a mandatory product requirement.

Current described prototype: frozen LightGBM model; retrospective evaluation on public ICU datasets; ingestion design for CSV, HL7 v2, FHIR and vendor adapters; risk/explanation and alert workflow components; synthetic-data demo.

**Evidence boundary:** No validation on Bangladeshi adult ICU patients; no live Bangladesh hospital EHR/monitor integration; no prospective clinical study; no demonstrated clinical benefit, workflow safety or patient-outcome improvement. Treat as a research prototype, not a clinically validated/approved product. Do not describe the synthetic demo as a real hospital deployment.

## 2. Bangladesh sepsis / ML research already identified

### A. PLOS Digital Health (30 Oct 2024)
**“A novel digital health approach to improving global pediatric sepsis care in Bangladesh using wearable technology and machine learning.”** icddr,b Hospital, Dhaka; Feb–Dec 2022; 100 children aged 2 months–17 years with suspected sepsis/serious infection.

- Used a **commercial VitalPatch**, not a researcher-built wearable. Bluetooth → smartphone → cloud/dashboard.
- Signals: HR, RR, temperature, ECG-related signals and HRV. Clinical observations were hourly; labs at admission and generally every 12 hours. Mean monitoring ~2.2 days; reported data capture quality >99%.
- Target: advanced pediatric sepsis using pSOFA. Ridge-model AUROCs: Model A wearable + selected clinical data **0.69**; B wearable + MAP + SpO₂:FiO₂ **0.86**; C wearable-only features **0.78**.
- Reported timing: model detection ~6.88 h before the analysis reference point; clinician EHR documentation ~4.19 h before it (difference ~2.7 h). **EHR documentation time is not necessarily the moment clinicians first recognized deterioration.** No proof that model alerts changed treatment or outcomes.

### B. American Journal of Tropical Medicine and Hygiene (published 18 Nov 2025; issue Jan 2026)
**“Predicting Pediatric Sepsis and Mortality Using Wearable Device Data and Machine Learning in Bangladesh.”** Same research programme/cohort, not independent external validation; 100 original participants, 96 suitable for Phoenix Sepsis Score analysis.

- LASSO on wearable-derived features; leave-one-group-out cross-validation.
- AUROC: sepsis **0.78**, septic shock **0.85**, mortality **0.84–0.87** (abstract/table discrepancy: abstract 0.87, main table 0.84). Adding manual SpO₂:FiO₂ raised sepsis AUROC to **0.89**.
- Sepsis/shock tasks are mainly recognition/classification against criteria during monitoring windows; mortality used first 12 h of wearable data to estimate eventual in-hospital death. Do **not** call all tasks future sepsis prediction.
- Small, single-hospital pediatric cohort; internal validation; no nationwide deployment or proven outcome benefit. Larger multicentre validation and real-time integration remain needed.

### C. Pediatric Reports (3 Jul 2026)
**“Utilizing Machine Learning for Diagnostic Assistance of Pediatric Sepsis and Septic Shock in Resource-Limited Settings.”** Clinical-data-based models using the same 100-child cohort; seven algorithms; features included age, HR, RR, BP, temperature, GCS and SpO₂:FiO₂.

- Reported AUROC: sepsis classification **0.945**; septic shock **0.878**.
- Used most abnormal clinical values in the same 24-hour period for classification. This is **not equivalent to forecasting future deterioration**. Different definitions, windows and features mean results are not directly comparable with wearable studies. External validation required.

### D. Existing-record ML example
A separate icddr,b study used SHEBA EHR records (2011–2019) from children aged 0–59 months in ICU to predict mortality using routine clinical, biochemical and haematological data. It is **not a sepsis-specific model**, but shows that research using existing hospital records is possible.

**Positioning implication:** Bangladesh already has pediatric sepsis-related ML research. Never claim “AI sepsis prediction is entirely new in Bangladesh” or that Veyra is the first. Veyra's intended distinction is adult ICU focus plus local validation, existing-data integration and accountable clinical workflow—none yet proven locally.

## 3. Why wearables were used; are they required?

The identified research used wearables mainly to capture continuous physiological patterns (e.g., minute-by-minute HR/RR and HRV) that intermittent chart entries may miss—not simply because the hospital had no digital records. icddr,b reportedly had SHEBA EHR since 2009 and routine telemetry/clinical documentation. Wearables were separately used to obtain dense time-series data.

**Veyra should be existing-data-first.** Suitability depends on each hospital's actual data frequency, completeness, timestamps and export capability:
- EHR/HIS + labs → clinical-data model.
- Exportable monitor streams → time-series analysis.
- Both → combined model, if justified.
- Paper/manual records → feasibility assessment and structured collection.
- Poor/inconsistent data → missingness safeguards; do not assume usable real-time integration.

Inventory first: vital-sign frequency; monitor make/model and export/API capability; lab timestamps; lactate/culture access; medication/antibiotic timestamps; clinical escalation/intervention timestamps. A monitor displaying a value does **not** mean it can export data to Veyra.

## 4. Alerts, NEWS2 and Bangladesh evidence

Distinguish three things:
1. **Bedside monitor alarms:** thresholds for HR, SpO₂, BP, RR, etc. Equipment/configuration/central monitoring/response practices vary; no comprehensive national inventory was established.
2. **NEWS2:** rule-based general deterioration score. A 2023 Tropical Doctor quality-improvement report from Square Hospitals, Dhaka, describes NEWS2 training/use in an HDU and statistically significant reductions in cardiac arrest and ICU transfer associated with unrecognized deterioration. This is one hospital QI setting—not AI, and not proof of nationwide use.
3. **AI sepsis alerts:** Bangladesh has pediatric wearable/clinical-data ML studies and clinician-feasibility research. Prior research did not establish nationwide routine deployment of an integrated AI sepsis-predictive alert system. Do not claim there are no alerts in Bangladesh.

A 2025 JMIR Formative Research qualitative study interviewed **18 doctors/nurses** at icddr,b Dhaka Hospital, Kushtia General Hospital and the Institute of Child and Mother Health. Reported needs/preferences included alerts for HR, RR, SpO₂ and temperature; audio/visual warnings; multi-patient monitoring; affordability/reliability; simple workflow; connectivity and trust; and avoidance of alarm fatigue. This is clinician feedback, not deployment evidence.

**NEWS2 basics:** National Early Warning Score 2 uses respiratory rate, oxygen saturation, supplemental oxygen, systolic BP, pulse/HR, temperature and consciousness/new confusion. General interpretation: 0–4 lower risk; any single parameter scoring 3 needs attention; 5–6 medium/urgent; ≥7 high/emergency. Follow local protocol. NEWS2 is not sepsis-specific; high score does not prove sepsis and low score does not rule out early sepsis.

**NEWS2 vs Veyra:** NEWS2 uses predefined thresholds to flag current physiological deterioration. Veyra is designed as ML risk estimation using the preceding 24 h of clinical features for following 6 h deterioration risk. Veyra has **not** been shown superior. A same-cohort, same-outcome head-to-head evaluation is needed.

## 5. Bangladesh hospital / ICU structure

There is no single verified ICU reporting structure that applies to every hospital. Map three authority lines separately:
- **Administrative:** Director, Superintendent, institutional management—operations, staffing, budget, procurement and facilities.
- **Clinical:** ICU Head/Clinical Lead/Intensivist, HOD, consultants, duty doctors and nursing leadership—patient care, supervision and escalation.
- **IT/data:** IT/ICT head, HIS/system/database administrators, biomedical engineering—accounts, infrastructure, interfaces, access controls, logs and technical maintenance.

A Dean is not automatically the ICU's operational or clinical head. Academic, hospital-administrative and clinical reporting lines may differ. One documented example: Bangladesh Medical University places its ICU division under the Department of Anaesthesia, Analgesia & Intensive Care Medicine; its official page lists 40 ICU and 14 HDU beds. This is an institutional example, not a national template.

ICU teams may include: intensivist/ICU lead; duty doctors/medical officers/registrars/residents; nurses and nurse-in-charge; specialty consultants (medicine, cardiology, nephrology, neurology, surgery, infectious disease, pediatrics, etc.); laboratory/microbiology, radiology, respiratory therapy, physiotherapy, pharmacy, dietetics, dialysis, blood bank, biomedical engineering/equipment technicians, infection control, IT and support staff. Not every hospital has all roles as dedicated staff.

**Open vs closed ICU:** In an open ICU, admitting/specialty teams retain a substantial management role with ICU input; in a closed ICU, the ICU team takes primary responsibility and specialists consult. A 2010 Dhaka survey reported 85% open / 15% closed, but this is historical only; current national distribution is unknown.

**Possible ICU deterioration pathway:** bedside monitor/nurse identifies issue → nurse and duty doctor assess → senior/ICU clinician is notified → ICU lead coordinates → relevant specialty/resuscitation/lab/respiratory support as needed. Outside ICU, ward nurse/duty doctor/emergency/ICU/anesthesia may be involved according to local protocol. Do not assume every hospital has a 24/7 Rapid Response Team or Code Blue team.

For every alert, identify: recipient; acknowledgement; clinical assessor/decision-maker; response expectation; escalation if unanswered; documentation; and audit owner. Director and IT Head are not automatically bedside clinical decision-makers.

## 6. Data systems and interoperability

Potential data sources:
- **Bedside monitors:** HR, SpO₂, BP, RR, sometimes temperature and alarm/event data.
- **LIS:** CBC, chemistry, lactate, blood culture and other results.
- **HIS/EHR:** demographics, diagnosis, history, orders, medicines, notes, observations and investigations.
- **Ventilators/equipment:** settings, respiratory measurements and device status.

Systems may be paper-based, digital but separate, or integrated. DGHS Shared Health Record / Health Information Exchange work and Bangladesh Core FHIR implementation guidance have been identified. These do **not** prove that every hospital has a live FHIR interface or connected ICU monitors. Verify by hospital, vendor, device model and actual data-flow demonstration.

## 7. Access control and privacy

Recommended principle: **role-based access + need-to-know + minimum necessary data**. This is a proposed design, not a verified description of every hospital's permissions.

- Nurse: assigned-patient vitals, alarms, nursing chart, medicines/care plan.
- Duty doctor: relevant patient history, vitals, labs, diagnosis, medicines and notes.
- ICU lead: relevant ICU patient-care data, trends and oversight.
- Specialty consultant: records relevant to consultation.
- Lab/radiology: ordered tests/images and matching patient/workflow data.
- Director: operational metrics and legitimately required reports.
- IT/HIS admin: accounts, system status, interfaces, logs and troubleshooting; technical privilege does not itself authorize unrelated browsing.
- External researcher/vendor: approved, purpose-limited, preferably de-identified data; identifiable access only with proper authorization/legal basis.
- Family: appropriate updates through authorized treating personnel.

Controls: individual accounts; role/assigned-patient restrictions; view/export audit logs; minimum access; time-limited support access; restricted development environments; monitoring for unauthorized access/export.

Prior research notes Bangladesh **Personal Data Protection Act, 2026 (Act No. 63 of 2026)** and treats health information as sensitive. **Re-check the Act, commencement, rules and applicable lawful bases against official sources before relying on this legal summary.** Clinical treatment and external commercial product development/ML reuse are different purposes. Before any pilot, obtain hospital authorization; establish lawful basis/consent as applicable; data-sharing agreement; ethics/institutional approvals where required; minimization; retention/deletion rules; encryption; access logs; and controls on third-party disclosure. Seek qualified local legal/privacy advice.

## 8. Other Bangladesh ICU evidence previously identified

- **“Gaps and Needs in Critical Care Services in Bangladesh” (2023):** Save the Children / USAID MaMoni MNCSP / Bangladesh Society of Anaesthesiologists Critical Care and Pain Physicians; assessment of 73 ICU/HDU-designated facilities in 2022; documented critical-care capacity/readiness gaps, particularly in some peripheral medical college and district hospitals.
- **“Knowledge and Implementation Practices of Standard Intensive Care Services” (2025 publication):** Barisal; Feb–May 2023; 80 doctors/nurses; ICU experience/training associated with knowledge/practice. District-level, not nationally representative.
- **“An Audit of Intensive Care Services in Bangladesh” (2010):** Dhaka; 40 ICU/ventilator-supported CCU units; 64% run by anesthesiologists and 85% open ICU. Historical only.
- **Daily Star report (Apr 2026):** Rajshahi division reportedly had 94 ICU beds, 44 unused/non-operational due to staffing shortage. Regional reporting, not national statistic.
- DGHS National ICU Quality Improvement Framework/monitoring checklist documentation exists; existence does not prove implementation in every facility.

## 9. Main unresolved research gap

Prior work did not establish a current, comprehensive national mapping of: ICU parent departments and organograms; clinical vs administrative reporting; day/night escalation workflows; open/closed ICU prevalence; monitor brands/models and exportability; vital-sign recording frequency; HIS/EHR/LIS adoption and integration; alarm/NEWS2 use; routine AI-alert deployment; alert recipients/acknowledgement/response times; IT access permissions; third-party integration approval; and rules for research/data sharing. **Do not guess these answers or generalize from one hospital.**

## 10. Practical primary-research plan

Interview a cross-section, not only the ICU Head:
- ICU Head/intensivist — clinical ownership and escalation.
- Duty doctor — actual detection/response.
- Nurse-in-charge and frontline nurse — charting, alarms, workload, alarm fatigue.
- Anaesthesia/Medicine HOD — parent department and specialty authority.
- Director/Superintendent — administrative approval/procurement.
- HIS/IT head/system admin — databases, interfaces, permissions, cybersecurity.
- Lab/microbiology lead — results and timestamps.
- Biomedical engineer — monitor/device connectivity.
- Quality/infection-control and research ethics/privacy contacts — incident workflow, approvals and data sharing.

Suggested exploratory sample: one large public teaching hospital, one private tertiary hospital and one district-level hospital. This would not be nationally representative.

Core questions: (1) Which department formally owns the ICU? (2) Who is clinical head? (3) Who handles administrative reporting? (4) Who is senior on night shifts? (5) Who first detects deterioration? (6) Who assesses, decides and receives escalation? (7) How are consultants contacted? (8) Where are vitals, labs, medicines and notes stored? (9) Are monitor readings auto-exported or manually entered? (10) What can nurses/doctors/HOD/directors/IT access? (11) Who authorizes software integration and research-data sharing? (12) Who receives, acknowledges and acts on a high-risk alert? Verify interviews with authorized organograms, policies and system demonstrations where possible.

## 11. Implications and safe implementation sequence

1. **Discover first:** map clinical, administrative and technical owners; inventory data sources and actual exportability.
2. **Govern data:** define purpose, legal basis, approvals, minimum fields, read-only access where appropriate, role-based access, audit and retention.
3. **Validate locally:** obtain approved historical adult-ICU data; test temporal/patient-level leakage, missingness, calibration, false alerts and missed cases. Compare with current workflow/NEWS2 where appropriate.
4. **Silent prospective pilot:** generate risk scores without directing care; assess data reliability, alert burden, workflow fit and response accountability.
5. Consider live clinical alerts only after adequate evidence, approvals, safety review and clinician agreement.

Proposed views (not claims about existing hospital software): nurse—assigned patient, warning, trends, acknowledgement; duty doctor—risk trend and supporting data; ICU head—ICU overview and escalation status; management—aggregate operational metrics.

## 12. Instructions for the next AI assistant

- Continue from this brief; do not repeat the completed background research unless a source needs verification.
- Prioritize original papers, official hospital/DGHS documents, peer-reviewed studies and direct institutional evidence. Give working links/citations.
- For each study state publication date **and** study period, hospital, population, sample size, outcome definition, prediction window, validation method and limitations.
- Separate recognition/classification from forecasting; AUROC from clinical utility/outcomes; retrospective analysis from prospective study; qualitative feedback from deployment; prototype from routine clinical use; technical compatibility from a real integration.
- Do not compare AUROCs across studies as though tasks/cohorts/windows were identical.
- Do not infer national practice from one hospital or old surveys. Mark assumptions and unknowns.
- Verify legal claims against current official Bangladeshi sources.
- Do not claim Veyra is Bangladesh's first AI sepsis system, clinically validated locally, connected to a real hospital, or proven to improve outcomes.

**Core conclusion:** Bangladesh has pediatric sepsis ML research, wearable and clinical-data studies, NEWS2 implementation evidence in at least one HDU, and clinician feedback on CDSS. The unresolved opportunity is not simply “another model”: it is evidence-backed adult-ICU validation plus a feasible, secure, hospital-specific data integration and accountable alert workflow in Bangladesh.

---

# 13. Why AI sepsis prediction models are not used in every hospital worldwide

**Core distinction:** sepsis screening is not the same as AI-based sepsis prediction. Hospitals may use:

1. **Manual/rule-based screening:** clinicians assess vital signs and clinical criteria or use scores such as NEWS2/SIRS.
2. **Automated EHR rules/alerts:** software triggers an alert when predefined thresholds or criteria are met.
3. **ML/AI prediction:** a model estimates future sepsis or deterioration risk from patient data.

A hospital having a sepsis program or an electronic alert does not prove it uses an ML/AI prediction model. There is no single reliable global census establishing the exact percentage of all hospitals using AI sepsis models. The evidence below is therefore used to explain adoption barriers, not to claim a worldwide adoption rate.

## 13.1 Real-world surveys: screening is more common than predictive AI

### United States CDC/NHSN survey (2022; published 25 Aug 2023)

A survey of **5,221 US acute-care hospitals** reported:

| Practice | Hospitals reporting it |
|---|---:|
| Sepsis committee/program | 73% |
| EHR-generated SIRS alerts | 65% |
| Manual sepsis screening | 47% |
| Predictive models | 33% |
| No standardized process for rapid sepsis identification | 10% |

**Interpretation:** sepsis programs and automated rules were more common than predictive models. The survey's 33% “predictive models” figure must **not** be described as 33% ML/AI adoption; the category was not a clean measure of ML-only deployment.

Source: [CDC MMWR — Sepsis Program Activities in Acute Care Hospitals](https://www.cdc.gov/mmwr/volumes/72/wr/mm7234a2.htm)

### United States CDC/NHSN survey (2025)

A later survey included **5,430 US hospitals**. It reported:

- 93% used a standard sepsis screening process at admission and during hospitalization.
- 82% reported having a sepsis program or committee.
- 32% reported data analytics, IT and quality-improvement support for the sepsis program.
- 31% regularly reported sepsis treatment/outcome data to hospital leadership and frontline staff.

**Interpretation:** widespread screening does not equal widespread AI. The support and feedback figures also show that even hospitals with sepsis programs may lack the infrastructure to evaluate and maintain advanced predictive tools.

Source: [CDC — Hospital Sepsis Management and Practices, 2025](https://www.cdc.gov/sepsis/hcp/core-elements/reports-2025.html)

## 13.2 Model performance changes across hospitals

### Epic Sepsis Model v2: four-system prospective validation (2026)

Wong et al. evaluated Epic Sepsis Model v2 across **four US health systems**, covering **227,091 inpatient encounters**, of which **7,401 met Sepsis-3 criteria**.

| Measure | Reported range/result |
|---|---:|
| Encounter-level AUROC | 0.82–0.92 |
| 12-hour prediction AUROC | 0.75–0.85 |
| Positive predictive value (PPV) | 13–26% |
| Alerts managed/silenced per sepsis case detected (12-hour prediction) | approximately 21–35, depending on system |

The same model did not perform identically across health systems. The study supports local validation rather than assuming that performance at one hospital transfers to another.

A practical data dependency was also reported: reliable prediction required a CBC result within the first hour after admission. At the University of Michigan, up to 30% of sepsis cases did not receive a reliable prediction before onset because of this data limitation.

**Interpretation:** an algorithm may be technically deployable but still depend on laboratory turnaround, data completeness, local patient mix and workflow. The reported PPV also means a substantial proportion of alerts may not correspond to a sepsis case, creating operational workload.

Source: [Wong et al. — Multicenter Prospective Validation of an Updated Proprietary Sepsis Prediction Model](https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2845595)

### Epic Sepsis Model v1: external validation (2021)

A separate academic medical-centre evaluation included **38,455 hospitalizations**:

- Hospitalization-level AUROC: **0.63**.
- Alerts were generated in **18%** of hospitalizations.
- The model failed to identify **67%** of sepsis cases in that evaluation.

This is evidence about the older **v1** model, not v2. It illustrates why commercial availability or deployment does not, by itself, establish dependable clinical performance.

Source: [Rhee et al. — External Validation of a Widely Implemented Sepsis Prediction Model](https://pmc.ncbi.nlm.nih.gov/articles/PMC8218233/)

## 13.3 Research-to-deployment gap

A **2026 global scoping review** in the *International Journal of Medical Informatics* reviewed **161 predictive-analytics research articles from 2014–2025**. These figures cover healthcare predictive analytics generally, not sepsis models alone:

| Implementation stage | Share of studies |
|---|---:|
| Development | 86.3% |
| Validation | 6.2% |
| Pilot | 1.9% |
| Operational deployment | 5.6% |

The review also reported:

- 69.6% identified data quality/interoperability barriers.
- 64.6% identified validation or transferability barriers.
- 8.7% discussed routine clinical-workflow integration.
- 79.5% of included studies came from high-income settings (128 of 161).

**Interpretation:** publishing a model is much more common than validating it independently, piloting it in clinical workflows or sustaining operational deployment. These percentages describe the reviewed literature, not the percentage of hospitals worldwide.

Source: [PubMed — Predictive Analytics for Health-System Decision Support (2026 scoping review)](https://pubmed.ncbi.nlm.nih.gov/42727547/)

## 13.4 Hospital integration and implementation take substantial work

A qualitative study interviewed **21 implementation leaders across 15 US medical centres** about sepsis risk-prediction tools. Reported challenges included EHR integration, local validation, alert optimization, IT coordination and clinician acceptance. Some implementation efforts took roughly **3 months to 3 years**, longer than expected.

This supports a key distinction: a model's ability to accept data in a software demo does not prove that a hospital can reliably supply timestamped, clinically meaningful data in production.

Source: [Joshi et al. — Implementation Approaches and Barriers for Sepsis Risk Prediction Tools](https://academic.oup.com/jamiaopen/article/5/2/ooac022/6569861)

## 13.5 Clinician trust, workflow disruption and alarm fatigue

A **2023 critical-care physician survey** invited 99 physicians and received 47 responses. It was about ML/AI in critical care generally, not sepsis models specifically.

- 15% said they had previously used an ML-based clinical tool.
- Mean willingness-to-use score was **3.32/5**.
- Important factors for willingness included credible evidence of performance better than trained clinicians (**4.28/5**), data transparency (**4.13/5**) and minimal workflow interruption (**4.09/5**).
- Among free-text responses, concerns included accuracy/reliability (39%), workflow interruption/alert fatigue (33%), data bias (11%) and patient safety (6%).

These percentages describe concerns mentioned in the survey responses; they are not population-wide estimates and are not sepsis-specific.

Source: [Mlodzinski et al. — Assessing Barriers to Implementation of ML and AI in Critical Care](https://periop.jmir.org/2023/1/e41056)

## 13.6 Consolidated reasons adoption remains limited

| Barrier | Why it matters in a hospital |
|---|---|
| Local validation | A model trained elsewhere may not perform reliably on local patients, practice patterns or data. |
| False positives / low PPV | Too many non-actionable alerts increase workload and alarm fatigue. |
| False negatives | A reassuring score can miss a deteriorating patient; clinicians must not rely on it alone. |
| Data availability and timing | Missing vitals, delayed CBC/lactate, inconsistent timestamps or incomplete records can prevent timely prediction. |
| Interoperability | EHR/HIS, LIS, bedside monitors and device vendors may use separate systems and formats. |
| Clinical workflow | The alert must reach the right person at the right time and fit existing rounds, handovers and escalation pathways. |
| Clinician trust | Staff need transparent evidence, understandable outputs and confidence that the tool is safe and useful. |
| Ownership and governance | A hospital must assign clinical, IT, administrative and safety responsibilities. |
| Cost and maintenance | Integration, infrastructure, training, cybersecurity, monitoring and recalibration require ongoing resources. |
| Outcome evidence | Good AUROC does not prove earlier treatment, reduced mortality, fewer complications or better workflow. |

**Central conclusion:** the bottleneck is not simply inventing a prediction algorithm. It is proving that the model works locally, has acceptable alert burden, can access reliable data, fits clinical workflows, has accountable owners and improves care without creating unacceptable risk.

---

# 14. Integrated implications for Veyra

Veyra's potential value should not be framed as “another AI model” or as the first sepsis AI system in Bangladesh. Bangladesh already has published pediatric sepsis-related ML research, while international evidence shows that even deployed models face transferability, data, alert-burden and workflow problems.

A defensible differentiation pathway for Veyra is to demonstrate, step by step:

1. **Adult ICU relevance:** clearly specify the adult ICU population, outcome definition and prediction horizon; do not use pediatric research as proof of adult-model performance.
2. **Existing-data feasibility:** establish which local hospitals can provide timely, exportable EHR/LIS/monitor data. Do not require wearables unless local discovery proves they are needed.
3. **Local scientific validation:** validate on approved Bangladeshi adult ICU data; report AUROC alongside sensitivity, specificity, PPV, calibration, lead time, missingness, false alerts per patient-day and missed cases.
4. **Fair baseline comparison:** compare with existing bedside alarms, NEWS2 or local screening using the same cohort, time windows and outcome definitions. Do not claim superiority without this test.
5. **Workflow accountability:** define who receives, acknowledges, assesses and escalates each alert on day and night shifts.
6. **Silent prospective evaluation:** first assess the system without directing clinical intervention; measure alert burden, reliability, acknowledgement and clinician feedback.
7. **Safety and governance:** obtain institutional, legal, privacy and ethics approvals; apply minimum necessary access, audit logs and retention controls.
8. **Clinical utility:** only make outcome claims after evidence demonstrates that use of the system improves care or patient outcomes.

## 14.1 Suggested Veyra evaluation metrics

Do not report AUROC alone. Include:

- Discrimination: AUROC and AUPRC (especially with low event prevalence).
- Classification: sensitivity, specificity, PPV and NPV at the chosen threshold.
- Calibration: calibration plot, calibration slope/intercept or Brier score.
- Timing: lead time before a clearly defined clinical reference point.
- Alert burden: alerts per patient-day, actionable-alert proportion and alerts per true sepsis case.
- Safety: false negatives, missed-case review and subgroup performance.
- Data operations: missingness, timestamp delay, data latency and uptime.
- Workflow: acknowledgement time, escalation completion and clinician feedback.
- Outcomes: treatment timing, ICU resource use, complications or mortality only when measured in an appropriately designed study.

## 14.2 Important wording for pitches and research reports

Use:

> “Veyra is a research-stage adult-ICU clinical decision-support prototype. Retrospective evaluation on public ICU datasets exists; Bangladesh adult-ICU validation, prospective workflow-safety evidence, live hospital integration and clinical outcome benefit have not yet been established.”

Avoid:

- “AI sepsis models do not exist in Bangladesh.”
- “Veyra is the first AI sepsis system in Bangladesh.”
- “The model prevents sepsis/deaths” without outcome evidence.
- “The model is clinically validated” based only on retrospective public datasets.
- “Every hospital can integrate it” without hospital-specific data and workflow assessment.

---

# 15. Final consolidated research takeaway

1. Bangladesh has published pediatric sepsis ML research, including wearable-based advanced sepsis recognition, septic-shock recognition, mortality prediction and clinical-data-based classification. These studies are not adult-ICU validation of Veyra.
2. Wearables in the identified icddr,b studies primarily enabled continuous physiological data capture; they were not used simply because no hospital digital records existed. Existing-data-first remains a reasonable Veyra design, subject to local data inventory.
3. Bangladesh has evidence of NEWS2 quality-improvement use in at least one HDU setting, bedside monitor alarms and clinician feedback research. This does not establish nationwide integrated AI sepsis-alert deployment.
4. Bangladesh ICU structures, data systems, escalation pathways and permissions vary by hospital; a national, current map has not been established in the prior research.
5. International surveys show that standard sepsis screening and sepsis programs are more common than evidence of predictive AI use. The US CDC surveys are not global estimates, and “predictive model” does not necessarily mean ML.
6. Multicentre validation shows that model performance, PPV, data dependencies and alert burden vary across hospitals. Local validation is essential.
7. A 2026 scoping review of general healthcare predictive analytics shows a large literature-to-deployment gap; it is not a sepsis-only or hospital-adoption census.
8. The main barriers are local validation, false alerts, data quality and timing, system integration, clinician trust, workflow ownership, governance, ongoing cost and lack of proven clinical utility.
9. Veyra's next meaningful milestone is not another model claim. It is documented hospital discovery, approved local adult-ICU validation, baseline comparison, silent prospective workflow evaluation and safety evidence.

**Instruction to the next AI assistant:** treat this document as the existing research handoff. Do not repeat the research from zero. Verify high-impact claims against original papers and official sources before external use; distinguish source findings from inference; record publication date and study period separately; and keep all population, setting, validation and evidence limitations explicit.

---

# 16. NEW INNOVATION TRACK — SOLVING THE DEPLOYMENT BARRIERS

**Status of this section:** This is a proposed product and business architecture derived from the research and the user's design direction. Unless a feature is separately verified in the codebase and tested with a real hospital, describe it as a design/prototype plan—not as a deployed clinical capability.

The important shift is from “we built a sepsis model” to:

> **Veyra is designed to make a locally validated sepsis decision-support service deployable across hospitals with different data systems, infrastructure, staffing and clinical workflows—without requiring every hospital to replace its HIS or hand its model IP to an EHR vendor.**

This addresses two connected problems:

1. **Interoperability / EHR lock-in:** getting reliable, authorized data from very different hospital systems.
2. **Model transferability / local fit:** deciding whether the model is appropriate for a specific hospital and adapting safely when it is not.

A third enabling problem is **deployment without a hospital data centre or IT department**. The proposed Veyra architecture must support this without weakening privacy, security or clinical accountability.

## 16.1 First, correct the EHR-market assumption

The earlier shorthand—“almost all US hospitals use Epic”—is too broad. The US market is concentrated, but it is not a single-vendor market.

The US Office of the National Coordinator for Health IT (ONC), using 2010–2024 AHA survey data, reports that in 2024:

- The **top three EHR developers served over 4 in 5 non-federal acute-care hospitals**.
- **Epic was the market leader, used by nearly half of hospitals**.
- The same EHR developer was used across inpatient and outpatient settings by over 90% of hospitals.
- The main large hospital EHR ecosystems include **Epic**, **Oracle Health (formerly Cerner)** and **MEDITECH**; other vendors also exist.

This does not mean every hospital uses Epic, nor that every AI product can automatically be installed inside an EHR. EHR-specific approval, API scopes, security review, procurement, configuration and workflow integration are still required.

Source: [ONC, Hospital EHR Adoption 2008–2024 (published 2026)](https://healthit.gov/data/data-briefs/non-federal-acute-care-hospital-electronic-health-record-adoption-2008-2024/). The concentration and Epic share are described in the findings section; Cerner's transition to Oracle Health is also explained there.

### What this means for Veyra's business

Do not build Veyra as a feature that only exists inside one EHR vendor's product. Build the **clinical intelligence and inference layer as Veyra-owned infrastructure**, and make the EHR only one of several ways to connect to it.

Possible commercial relationships:

- **Direct hospital license:** the hospital contracts with Veyra; Veyra runs its own inference service on a Veyra-managed edge appliance, approved hospital server or approved cloud environment.
- **EHR marketplace / app partnership:** Veyra remains the app/model provider; the EHR vendor provides an approved launch and data-access route. The vendor is an integration/channel partner, not automatically the owner of Veyra's model.
- **Systems-integrator channel:** an existing hospital IT vendor or regional integrator implements and maintains the connector under an agreement; Veyra licenses the model and platform.
- **Private deployment:** the hospital or its contracted hosting provider runs a Veyra container; the model weights and software remain licensed Veyra IP, subject to contract and deployment terms.

The commercial principle is: **sell Veyra as a separately governed clinical service that integrates with the EHR, not as an algorithm surrendered to the EHR vendor.** The exact IP, hosting, support, data-use and revenue-sharing clauses must be negotiated contractually. A standards-based interface does not remove the need for vendor and hospital permission.

## 16.2 International EHR integration: how Veyra stays vendor-neutral

### Route A — SMART on FHIR app

When the EHR exposes a suitable FHIR API and supports SMART App Launch, a clinician can launch Veyra from within an EHR session. The EHR provides a launch context (for example, the current patient), the app obtains an authorized OAuth 2.0 token, then reads only the permitted FHIR resources within the granted scopes.

Typical sequence:

1. Hospital/EHR administrator registers Veyra as an approved application.
2. Veyra registers its launch and redirect URLs.
3. Clinician opens a patient chart and launches Veyra.
4. EHR passes the launch context.
5. Veyra requests authorization and receives a scoped token.
6. Veyra retrieves permitted resources, validates them and runs the risk assessment.
7. Veyra displays the risk summary in its own app surface; any write-back requires a separate approved use case and API permission.

This is a **standardized integration path**, not a guarantee that every Epic, Oracle Health or MEDITECH installation exposes every resource or scope. Each site and EHR version must be checked.

Official standard: [HL7 SMART App Launch 2.2.0](https://hl7.org/fhir/smart-app-launch/app-launch.html).

### Route B — CDS Hooks

Where the EHR supports HL7 CDS Hooks, a clinical workflow event (such as opening a patient chart) can call a Veyra CDS service. Veyra can return a concise card and, when needed, a link to open the fuller Veyra app. This helps the result appear at a relevant point in the clinician workflow instead of requiring a separate dashboard at all times.

CDS Hooks is an integration pattern/specification. It does not make an EHR compatible by itself; the EHR must implement the relevant hook, the hospital must enable it, and the clinical content must be approved.

Official standard: [HL7 CDS Hooks 2.0.1](https://cds-hooks.hl7.org/).

### Route C — Interface engine / hospital-side connector

Where SMART/FHIR is unavailable or insufficient, Veyra can connect through an approved interface engine or a Veyra Bridge appliance. This is particularly relevant when the hospital already has HL7 v2 interfaces or vendor-specific exports.

- Receive only the agreed message types and fields.
- Normalize incoming data into Veyra's canonical clinical data contract.
- Keep the original EHR as the system of record.
- Return only approved Veyra outputs through a supported interface; do not write directly into the vendor database.

### Protecting Veyra's IP

Veyra's model should be callable as a separately licensed service through an authenticated API or a signed on-prem container. The EHR need not receive the model weights. EHR integration can pass patient context and allowed observations to Veyra, then show Veyra's response. This is a commercial architecture option, not a guarantee that an EHR vendor will approve or support it without procurement and security review.

**Do not promise:** “Epic makes integration automatic.” Say instead: “For EHRs that support SMART on FHIR/CDS Hooks, Veyra offers a standardized app and decision-support path; for other systems, it uses a hospital-approved connector.”

## 16.3 Bangladesh and LMIC hospitals: do not wait for every HIS/LIS to become FHIR-native

### Bangladesh already has a national FHIR direction—but not proof of universal hospital adoption

As of 5 November 2026, the official DGHS Bangladesh Core FHIR Implementation Guide is at **version 0.5.0**, based on **FHIR R4 (4.0.1)**. It describes national profiles, value sets and terminology bindings. DGHS also provides a live sandbox for testing and conformance checks. The current guide labels itself **Informative** and **Maturity Level 1**. This is important progress, but it does **not** prove that every public/private hospital, HIS vendor, LIS vendor or bedside monitor is already connected to FHIR in production.

The DGHS Shared Health Record/HIE information page describes the use of FHIR, LOINC, ICD-10 and DICOM as part of its interoperability direction. Again, an official national architecture and sandbox are not equivalent to universal local implementation.

Sources:
- [DGHS Bangladesh Core FHIR IG v0.5.0](https://fhir.dghs.gov.bd/core/) — version, status, maturity and FHIR R4 sandbox details.
- [DGHS Shared Health Record — Health Information Exchange](https://en.info.shr.dghs.gov.bd/hie/) — national HIE and standards overview.

### The Veyra Connector Ladder

Veyra should use the **highest reliable, supported integration level available at each hospital**, rather than demand one exact technology everywhere.

| Level | Hospital situation | Data route | What Veyra can realistically provide |
|---|---|---|---|
| **L0 — Paper / no digital HIS** | Records are paper-based or not exportable | Structured bedside entry by authorized staff; approved manual observations; later CSV upload where possible | Feasibility/readiness workflow first. Do not label it real-time automated monitoring if data are manually entered or delayed. |
| **L1 — CSV / Excel export** | HIS/LIS can generate files but has no usable API | Scheduled encrypted CSV export or secure file transfer (SFTP); strict template and validation | Batch or near-real-time scoring depending on export frequency. Every file needs patient/encounter ID, timestamps, units and source. |
| **L2 — HL7 v2 / interface engine** | Hospital or lab can transmit standard messages | Hospital-approved HL7 v2 feed via an interface engine/edge connector; commonly relevant message families include ADT for admission/transfer events and ORU for observation/result messages, subject to actual source support | Near-real-time feed when the source actually emits timely messages. Map local codes and units before scoring. |
| **L3 — Vendor API / approved read-only database view** | HIS/LIS vendor has a private API, export endpoint or documented read-only view | Vendor-supported REST/API, read-only replica/view or approved integration service | Site-specific connector with a documented mapping. No undocumented database scraping or direct production writes. |
| **L4 — FHIR facade / normalized FHIR repository** | Legacy source is not FHIR-native, but hospital authorizes a translation or staging layer | Adapter translates approved source records into FHIR R4 resources; optionally stores a controlled read-only FHIR repository | Makes downstream Veyra services use one canonical interface while preserving the original HIS/LIS. |
| **L5 — SMART / CDS Hooks** | EHR offers compatible FHIR APIs and workflow hooks | SMART App Launch and/or CDS Hooks | Embedded launch and contextual alert card, subject to EHR support, site approval and clinical governance. |
| **Device path — monitor gateway** | Bedside monitor/central station exposes supported output | Vendor-approved device API, gateway, serial/Ethernet output or interface-engine feed | Continuous/regular vital-sign stream only where the exact device model, configuration and export rights are verified. |

**Important:** HL7 v2, FHIR, CSV, a vendor API and a medical-device protocol are not interchangeable. The connector must know the exact source, message format, identifier, code, unit, timestamp semantics and data rights. Do not assume that every analyzer speaks HL7 or ASTM, or that every monitor exposes an API. Check each installed make/model and its vendor documentation.

### Three ways to bridge a legacy system

#### 1. FHIR facade (on-demand translation)

A FHIR facade sits in front of an authorized legacy interface, API or read-only data view. When Veyra requests an Observation, Patient or Encounter resource, the facade maps the source fields into the required FHIR structure. It does not need to rebuild the hospital's existing HIS.

Use when:
- The hospital/vendor permits documented read access.
- The source data structure is stable enough to map.
- Read-only retrieval is the main initial need.

Limitations:
- The facade still requires a source connector, field mapping, identity matching and ongoing maintenance.
- It cannot manufacture missing data or timestamps.
- Direct queries against a proprietary production database are not acceptable without explicit authorization and vendor support.

A 2025 peer-reviewed implementation paper describes a reusable HAPI FHIR-based facade for an EAV-style legacy health information system, supporting the feasibility of this pattern. It is an example, not proof that every legacy system can be converted easily.

Source: [Jafarpour et al., 2025 — Bridging the Legacy Interoperability Gap](https://pubmed.ncbi.nlm.nih.gov/40588950/).

#### 2. Synchronization / staging repository

When the hospital and vendor approve it, a connector can copy selected changes from the source into a separate, access-controlled staging repository. Change Data Capture (CDC) may be one technical method if the source database and vendor support it. A controlled FHIR repository can then expose normalized read data.

Use when:
- Read queries against the production HIS should be minimized.
- A separate queryable store is justified.
- The source can safely and lawfully provide a change stream or replica.

Limitations:
- CDC is not automatically real-time, zero-load or risk-free.
- It requires database/vendor approval, monitoring, reconciliation, duplicate handling, failure recovery and storage governance.
- The repository becomes another sensitive-data environment that must be secured and audited.

#### 3. Hybrid connector (recommended design target)

A hospital-side Veyra Bridge can consume supported HL7/API/file feeds, keep a limited local normalized cache and expose only an authenticated Veyra interface. A FHIR facade may translate reads; approved Veyra outputs can be sent back using a supported API or an EHR workflow integration.

For an early-warning product, the safest first release is **read-only ingestion plus a separate Veyra alert surface**. If an EHR write-back is later approved, write only the specific CDS artefact the hospital has authorized (for example, a reviewed flag/task/communication through a supported API). Do not write diagnoses, orders, medication changes or treatment decisions automatically, and never write directly to the HIS database.

Reference architecture for interoperability layers: [OpenHIE Interoperability Layer](https://ohie.org/practice-area/interoperability-layer/) describes security control, a single entry point, message transformation, routing and flow monitoring.

### Exact real-life data acquisition sequence

1. **Discover the source:** list the HIS, LIS, bedside monitor/central station, ventilator, manual observation chart and any current interface engine. Record product/vendor, version, module owner and system-of-record role.
2. **Obtain permission:** hospital data owner and relevant clinical/administrative authorities approve a data inventory and read-only integration scope. The software vendor gives documented interface access where required.
3. **Define a minimum data contract:** patient and encounter identifiers; observation code; value; unit; timestamp/effective time; source device/user; result status; and correction/version information. Add labs and medication timestamps only if approved and reliably available.
4. **Connect through the available route:** FHIR API, SMART-authorized FHIR access, HL7 v2 feed, vendor API, approved read-only replica/view, SFTP/CSV, or structured manual entry. Never assume a route exists before testing.
5. **Match the patient and encounter:** reconcile hospital patient ID, visit/admission ID, ICU bed/ward and timestamps. Do not rely on patient name alone.
6. **Normalize meaning:** map local test codes to appropriate standard codes where defensible (for example LOINC); map units to a controlled unit system (for example UCUM); preserve the original value, original code and mapping provenance. Do not silently guess uncertain mappings.
7. **Validate and quarantine:** detect missing/stale/duplicate/impossible values, wrong units, delayed labs, timestamp order errors and mismatched IDs. Invalid or uncertain data are held out of scoring.
8. **Score only within the validated input envelope:** send valid features to the frozen model; record model version, site configuration and data lineage.
9. **Apply the local safety gate:** TransferShield checks whether this hospital's data and model behaviour remain within the approved range. If not, abstain/hold the alert and route to ordinary clinical care.
10. **Present and audit:** show the result in the approved Veyra/EHR surface, record who received and acknowledged it, and log data, model and policy versions.

### Veyra's canonical data contract

All connectors should map to a single internal schema before model input. A minimum conceptual record is:

```json
{
  "facility_id": "site-code",
  "patient_ref": "pseudonymous-local-reference",
  "encounter_ref": "icu-encounter-reference",
  "observation_code": "LOINC-or-local-mapped-code",
  "value": 98.0,
  "unit": "%",
  "effective_time": "2026-11-05T12:30:00+06:00",
  "source_system": "monitor-or-HIS-LIS",
  "source_record_id": "source-id",
  "quality_status": "validated",
  "mapping_version": "site-map-v1"
}
```

This is a design example, not a real patient record and not a claim that every source can provide all fields. Keep local identifiers and re-identification keys under the hospital's control wherever possible.

## 16.4 Hospitals without their own data centre or IT department

This is not a reason to exclude a hospital. It changes the hosting and operational model. A hospital does **not** need to own a full data centre to use a properly governed system; it does need an accountable data owner, an approved processing arrangement, secure connectivity/storage, backup and support.

### Correct the BAA / PHI explanation

The earlier explanation needs an important legal qualification:

- **PHI/ePHI and BAA are US HIPAA concepts.** Under HIPAA, identifiable health information is PHI in the hands of a HIPAA covered entity/business associate. If a cloud service provider creates, receives, maintains or transmits ePHI on behalf of a covered entity/business associate, the CSP is generally a business associate and a HIPAA-compliant BAA is required—even if the CSP only stores encrypted ePHI and cannot decrypt it.
- **A BAA is not a universal global rule.** A Bangladeshi hospital does not sign a US HIPAA BAA merely because it stores health data in a cloud. Bangladesh's own data protection, health-sector, contract, procurement and cross-border requirements must be assessed.
- **A cloud provider's marketing claim is not enough.** The hospital must verify the exact service/product, region, subprocessors, access controls, logging, encryption, backup, incident reporting, retention/deletion and support arrangements.

Official US source: [HHS — Guidance on HIPAA & Cloud Computing](https://www.hhs.gov/hipaa/for-professionals/special-topics/health-information-technology/cloud-computing/index.html).

### Bangladesh privacy-law checkpoint (legal review required)

The official Bangladesh Laws database lists the **Personal Data Protection Act, 2026 (Act No. 63 of 2026)**, dated 10 April 2026. The text:

- Defines health-related data as sensitive personal data (sections 2(21)–2(22)).
- Sets conditions for processing sensitive personal data, including specific consent and other defined legal bases; healthcare and emergency-treatment provisions are expressly addressed (section 7).
- Allows a data fiduciary to engage a processor under a lawful contract and keeps the data fiduciary responsible for the processing performed on its behalf (section 8).
- Provides data-security, retention, breach, recordkeeping and audit-related requirements (including sections 17–22).
- Includes conditions for cross-border transfer of classified personal data (section 29), including consent/contract-related grounds and destination safeguards prescribed by regulation. It should not be simplified into either “all cloud is prohibited” or “all cloud is automatically permitted.”

The Act's commencement clause says most provisions are deemed effective from 6 November 2025, while sections 23 and 31–35 are tied to a later government-notified commencement after 18 months from issuance. Before a hospital deployment, counsel should check the latest regulations, gazette notifications, prescribed transfer conditions and how the Act applies to the specific data flow.

Official legal sources:
- [Personal Data Protection Act, 2026 — official Bangladesh Laws database](https://bdlaws.minlaw.gov.bd/act-print-1692.html)
- [Section 29 — classification, storage and transfer of personal data](https://bdlaws.minlaw.gov.bd/act-1692/act-chapter-print-2699.html)
- [Bangladesh Government Press — April 2026 Extraordinary Gazette listing](https://dpp.gov.bd/bgpress/index.php/document/extraordinary_gazettes_monthly/2026-04-14)

This is a technical research summary, not legal advice. Do not promise a cloud hosting location or cross-border transfer route until a Bangladesh-qualified lawyer and the hospital's data-governance authority approve it.

### Three hosting models Veyra should offer

| Mode | Best-fit hospital | Where PHI is processed | Operational trade-off |
|---|---|---|---|
| **H1 — Hospital-edge / on-prem appliance** | Hospital has no data centre but can provide a secure room, power and network port | On a Veyra-managed, hospital-installed edge appliance or approved local server | Strong local control and offline resilience; requires device maintenance, patching, UPS, backup and a named local contact. |
| **H2 — Approved managed hosting / private cloud** | Hospital has no IT team or server but can approve an external managed environment | Contracted hosting/data-centre environment in a legally approved location | Low hospital infrastructure burden; depends on data-transfer approval, provider due diligence, contract, connectivity and incident-response arrangements. |
| **H3 — Hybrid edge + cloud control plane** | Hospital needs local patient-data processing but central fleet management | Clinical data and inference stay on the approved local edge; central plane receives only configuration and carefully minimized/pseudonymized operational telemetry | Good balance for multi-site operations; remote support must not expose patient data by default. Any remote PHI access triggers the applicable legal/security requirements. |

**Recommended default:** H3 where feasible; H1 when local processing is required; H2 only after data-location, legal and security review. The actual choice is site-specific.

### Veyra Edge Lite for hospitals with no IT department

Proposed managed package:

- A small, supported edge computer/appliance—not a hospital-owned data centre.
- Secure boot where available, full-disk encryption, device identity, firewall, least-privilege service accounts and encrypted backups.
- Outbound-only secure connection where possible; no public inbound database exposure.
- Local encrypted queue during internet outage; upload/synchronization resumes only under configured rules.
- Automatic health checks, signed updates, rollback and remote maintenance logs.
- A named hospital contact for power/network/access and a contracted managed-service function for patching, backups and incident response.
- No shared administrator password; MFA for remote access; time-limited support accounts.

**No IT team does not mean no owner.** The hospital must still name an authorized administrative sponsor and a clinical owner. IT operations can be outsourced to Veyra or an approved managed service partner under contract, but the hospital's legal and clinical responsibilities do not disappear.

### Minimum governance when the hospital has no IT department

| Responsibility | Minimum accountable role | May be outsourced? |
|---|---|---|
| Clinical use and alert recipient | ICU Head/intensivist or formally designated senior clinician | No; clinical accountability must stay with the hospital's authorized clinical leadership. |
| Nursing workflow | Nurse-in-charge / nursing lead | Support can be provided, but nursing practice decisions remain local. |
| Contract, budget, institutional permission | Director/Superintendent or authorized management | No; must be an authorized hospital signatory. |
| Infrastructure, access, backup, patching | Named IT/security contact or contracted managed-service provider | Yes, with defined SLA, access restrictions and audit. |
| Data protection and lawful processing | Hospital data fiduciary/privacy/legal authority, as applicable | Specialist advice can be outsourced; statutory accountability cannot simply be delegated away. |
| Model operation and technical support | Veyra | Veyra is not the treating clinician and cannot decide treatment. |

If the hospital cannot identify a responsible clinical owner, data owner and secure hosting/operations route, Veyra may do discovery or a de-identified feasibility exercise, but **must not activate live clinical alerts**.

## 16.5 Local model transferability: Calibration + measurement habits

A model's AUROC can change across hospitals because patient mix, disease prevalence, outcome definitions, testing practice, observation timing, device calibration, coding, missingness and clinical workflows differ. “Calibration” and “measurement habits” are related but distinct problems.

### A. Calibration: what it means and what it can/cannot fix

If a model predicts 30% risk for 100 comparable patients, a well-calibrated model should have roughly 30 events in that group over the defined outcome horizon. A model can rank patients reasonably well (discrimination/AUROC) while its probability estimates are systematically too high or too low at a new hospital.

Proposed response:

1. Lock the baseline model version and define the target population, label and time horizon.
2. Run external retrospective validation on a permitted, representative local dataset.
3. Review AUROC/AUPRC, sensitivity, specificity, PPV, calibration curve, calibration intercept/slope and Brier score.
4. If discrimination is acceptable but probabilities are miscalibrated, test a site-specific calibration layer (for example logistic/Platt or isotonic calibration) on a separate, representative local calibration set.
5. Choose alert thresholds with the clinical team using sensitivity, PPV and acceptable alert workload—not by selecting the most attractive dashboard number.
6. Validate the frozen model + calibrator on a separate temporal holdout before silent operation.

**Limit:** calibration can adjust predicted probabilities; it does not repair poor discrimination, missing predictors, incorrect labels or a major feature-distribution shift. If AUROC/AUPRC or subgroup safety is unacceptable, do not “fix” it with a threshold or a calibrator. Reassess the model, collect better data or develop a separately governed site-specific version.

### B. Measurement habits: the hospital's data-collection fingerprint

Example: Hospital A records blood pressure every hour; Hospital B records it every four hours unless the patient deteriorates. The model may see very different time-series density and missingness. Missing values may also be informative: a value may be absent because the test was not ordered, the monitor was disconnected, the patient was stable, or the ward was understaffed. These are not equivalent explanations.

Veyra should build a **Site Data Fingerprint** before scoring live patients. It records, at minimum:

- Measurement interval distributions by feature (median, spread and long gaps).
- Data freshness and latency from measurement to ingestion.
- Missingness rate and missingness pattern by feature and shift.
- Unit/code/device distribution and mapping confidence.
- Lab turnaround and result availability patterns.
- Duplicate, corrected and out-of-order records.
- Population and case-mix summaries permitted for validation.
- Differences between day and night shifts where data support the comparison.

Proposed engineering mitigations:

- Preserve measurement timestamps and the time since the last observation; never treat a stale measurement as current.
- Build features that understand irregularly sampled observations (for example last value, trend, variability, measurement count and elapsed time), only if these features are validated for the model.
- Use explicit missingness/freshness indicators where the model was designed and validated to use them.
- Normalize units and map codes through a reviewed site-specific terminology table.
- Quarantine impossible, contradictory, stale or unmapped values.
- Test robustness with simulated missingness/cadence perturbations during development, then validate with real site data. Simulation alone is not local validation.
- If input availability is outside the validated range, return **insufficient data / abstain**, not a reassuring low-risk score.

### C. Veyra TransferShield — proposed S0–S8 site safety gates

TransferShield is a proposed product module. It is not a claim that these gates have already been clinically validated.

| Gate | Check | Pass condition | If it fails |
|---|---|---|---|
| **S0 — Model lock** | Model artifact, code, feature definition and label/horizon version | Signed/hash-verified, approved model package | Stop deployment; reconcile version. |
| **S1 — Data contract** | Field availability, units, timestamps, patient/encounter IDs and code maps | Required fields mapped and traceable | Quarantine unmapped fields; no silent guesses. |
| **S2 — Data quality** | Missingness, delay, duplicates, impossible ranges, stale data | Meets prespecified thresholds from validation plan | Abstain or restrict to safe non-clinical analysis. |
| **S3 — Local retrospective validation** | Discrimination, calibration, sensitivity, PPV, subgroup results and lead time | Meets site-specific protocol signed by clinical governance | No silent/live alert; improve data or model. |
| **S4 — Site calibration** | Probability calibration and threshold suitability | Independent local holdout supports it | Keep original probabilities clearly labelled or do not score; no unvalidated threshold. |
| **S5 — Silent mirror** | Prospective shadow scoring without clinician-facing alerts | Prespecified data-completeness, safety and workload criteria met over adequate case volume/time | Extend, investigate, or stop; duration is evidence-driven, not a universal “one-to-three-month” rule. |
| **S6 — Workflow gate** | Recipient, acknowledgement, escalation, downtime and ownership | Named clinical owner and tested workflow | Do not turn on live alerts. |
| **S7 — Subgroup and drift watch** | Calibration/performance by relevant subgroups; cadence and data drift | Within agreed monitoring limits | Hold/disable affected scope and investigate. |
| **S8 — Change control / rollback** | Any model, connector, code-map, threshold or policy change | Re-validation, approvals, versioning and rollback path complete | Retain previous approved version or disable. |

TransferShield must not silently retrain the model or silently change thresholds in production. Any adaptation creates a versioned change requiring local validation and approval.

### D. Site deployment tiers: decide whether to activate, calibrate or hold

| Tier | Hospital fit | Veyra action |
|---|---|---|
| **T0 — Not ready** | No reliable data, no owner, no legal route, unsafe timestamps or insufficient outcome labels | Readiness assessment only; no patient-level risk alert. |
| **T1 — Data-connected, not locally validated** | Authorized data feed exists, but local retrospective validation is incomplete | Data-quality monitoring and offline evaluation only. |
| **T2 — Validated, calibration/threshold review required** | Discrimination acceptable; calibration or alert threshold differs locally | Apply a separately versioned site calibration/threshold only after adequate local data and approval. |
| **T3 — Silent prospective eligible** | Local retrospective validation and workflow plan pass; prospective shadow period approved | Shadow mode; no clinical intervention recommendation. |
| **T4 — Live-alert eligible** | Silent evaluation, safety, governance, regulatory/legal and clinical gates pass | Limited approved live rollout with continuous monitoring and rollback. |

Do not equate T4 with regulatory clearance. Any required medical-device/software authorization must be assessed for the jurisdiction and intended use.

## 16.6 Veyra Super Admin: one control plane, hospital-specific unlocks

The user's product direction is to keep a central Super Admin area where Veyra configures the appropriate integration and deployment package for each hospital. This should be implemented as a **control plane**, separate from the **patient-data plane**.

### A. Control plane vs data plane

- **Control plane (Veyra Super Admin):** hospital registry, contract/package status, connector type, model version, site profile, gate status, edge appliance health, approved users, audit summaries and support tickets. It should not expose raw patient charts by default.
- **Data plane (hospital):** patient-identifiable records, connector traffic, local normalization, model inference, site calibrator and clinical alert events. It runs in the hospital-approved location (edge/on-prem, managed host or approved cloud).
- **Hospital clinical console:** authorized hospital clinicians see patient-level results under hospital role-based access. Veyra platform administrators do not become clinical users just because they administer the platform.

### B. Super Admin onboarding wizard

For each new hospital, configure:

1. Hospital type, number of ICU beds, adult/pediatric scope and intended pilot purpose.
2. Clinical owner, nursing lead, administrative signatory and IT/security contact (internal or managed service provider).
3. Source inventory: HIS, LIS, monitors, manual charts, vendor/version and data owner.
4. Connection mode: L0–L5 connector and device path.
5. Hosting mode: H1 edge, H2 managed hosting or H3 hybrid.
6. Data contract and local mappings: patient IDs, encounters, LOINC/local codes, units, timestamps and missingness.
7. Model compatibility and Site Data Fingerprint.
8. TransferShield gates and evaluation status.
9. Alert recipients, acknowledgement, escalation and downtime plan.
10. Sign-offs, audit trail, support SLA, renewal and offboarding/data deletion plan.

### C. Feature unlocks must be evidence-based

| Hospital profile | Package unlocked | What is not unlocked yet |
|---|---|---|
| Paper-based / no IT | Readiness + structured capture / CSV assessment | Real-time automated monitor prediction or live alert. |
| CSV-capable legacy HIS/LIS | Veyra Bridge CSV + batch quality checks | Real-time integration unless export frequency supports it. |
| HL7 v2 available | Veyra Bridge HL7 + canonical mapping | Clinical alerting before local validation and workflow sign-off. |
| Vendor API/read-only view | Site-specific vendor adapter | Any unsupported direct database access or automatic write-back. |
| FHIR/SMART-enabled EHR | FHIR connector + SMART launch; CDS Hooks if supported | Unapproved scopes/hooks or automatic treatment actions. |
| Monitor gateway available | Device connector for the validated make/model | Universal compatibility with other monitor brands/models. |
| Data-quality or model-fit failure | Restricted data-readiness / shadow assessment | Live risk score/alert for the failed scope. |

**The Super Admin may configure technical availability, but cannot unilaterally approve clinical go-live.** Live activation must require the hospital's designated clinical sign-off and authorized institutional approval, along with required legal/privacy/security approvals.

### D. Suggested Veyra module family

- **Veyra Bridge:** connector and interoperability layer (CSV, HL7, FHIR, vendor APIs, device gateways).
- **Veyra Edge:** local processing, store-and-forward, encrypted queue and connectivity management.
- **Veyra Core:** frozen inference service and explanation output.
- **Veyra TransferShield:** local fit, data-quality, calibration, cadence/drift and rollout gates.
- **Veyra Workflow:** roles, alert routing, acknowledgement, escalation and audit.
- **Veyra Control Plane:** Super Admin, fleet deployment and per-hospital configuration.

These are suggested product/module names; use only names that the project team adopts.

## 16.7 Business model: make integration and local readiness a product, not free custom work

The following is a proposed commercial model, not a validated price list.

### Revenue structure

1. **Readiness / discovery assessment:** one-time assessment of systems, fields, monitor access, governance and clinical workflows. Can be credited partly toward implementation if the hospital proceeds.
2. **Connector onboarding fee:** scoped by L0–L5 complexity, device count, vendor access, number of interfaces and mapping effort.
3. **Site or ICU-bed subscription:** recurring fee for the approved Veyra modules and model monitoring. Price by site/ICU capacity or deployment tier—not by number of alerts, which could create a bad incentive to generate more alerts.
4. **Managed Edge / Managed Operations:** recurring support for appliance maintenance, patching, backups, monitoring and integration uptime when the hospital lacks IT staff.
5. **Optional integration partner revenue:** a local HIS vendor, system integrator or managed-service provider can earn implementation/support fees under a defined partner agreement.
6. **Expansion modules:** additional approved wards, HDU, device feeds, analytics, or other clinical use cases only after separate validation and governance.

### Illustrative package ladder

| Package | Target buyer | Included scope | Commercial logic |
|---|---|---|---|
| **Discover** | Hospital exploring readiness | Data/workflow inventory, connectivity test, risk register, integration recommendation | Fixed assessment fee; no clinical alerting. |
| **Bridge Start** | Paper/CSV or small hospital | CSV/structured input, data-quality checks, limited batch assessment | Lower onboarding cost; not marketed as real-time if data are delayed. |
| **Bridge Connect** | Legacy HIS/LIS hospital | HL7/API/vendor connector, mapping, edge gateway and support | Setup + recurring site/bed subscription. |
| **FHIR / EHR App** | Modern EHR hospital | FHIR/SMART app; CDS Hooks only where available; vendor/security approval | Site license + integration/partner fee. |
| **Managed Edge** | Hospital without data centre or IT team | Veyra appliance, managed updates, backup/monitoring and support | Hardware/setup + recurring managed-service fee. |
| **Validated Clinical Pilot** | Hospital with local evidence and approvals | Silent evaluation, workflow/safety metrics, approved limited live stage only after sign-off | Milestone-based pilot agreement; never promise outcomes in advance. |

### IP and data ownership principles

- Hospital remains the owner/controller of its identifiable clinical records, subject to applicable law and contract.
- Veyra receives only the data-processing rights needed for the contracted purpose.
- Veyra retains ownership/licensed control of its model, software, connector code and generic platform IP, subject to negotiated contract terms.
- Site-specific calibration parameters and configuration should be tenant-separated and versioned. Contract should define rights to use, export and delete these artifacts.
- Do not train a cross-hospital model on identifiable or hospital-provided data unless there is a separate, explicit lawful authorization, data-sharing agreement and ethics/governance approval where required.
- EHR vendors may be integration partners or channels; they do not automatically own the Veyra model.

## 16.8 One judge-ready architecture diagram

Use this conceptual sequence in the presentation. It is a proposed architecture, not proof of current real-hospital integration:

```text
HOSPITAL SOURCES
  HIS / EHR | LIS | Bedside monitor | Manual observation | Ventilator
             |
             v
HOSPITAL-APPROVED CONNECTOR
  SMART/FHIR | HL7 v2 | Vendor API | Read-only replica/view | SFTP/CSV | Device gateway
             |
             v
VEYRA BRIDGE + EDGE
  Authentication | Patient/encounter matching | Mapping | Store-and-forward
             |
             v
CANONICAL CLINICAL DATA CONTRACT
  LOINC/local code map | UCUM/unit normalization | Timestamps | Provenance
             |
             v
DATA QUALITY + QUARANTINE
  Missing/stale/duplicate/wrong-unit/out-of-range checks
             |
             v
VEYRA TRANSFERSHIELD
  Site fingerprint | Local validation | Calibration gate | Cadence/drift watch | Abstain
             |
             v
FROZEN VEYRA MODEL INFERENCE
  Versioned risk estimate + evidence/explanation
             |
             v
CLINICAL WORKFLOW SURFACE
  Veyra dashboard / SMART app / CDS Hooks card / approved alert route
             |
             v
SILENT → GOVERNANCE GATES → LIMITED LIVE ALERT (only if approved)
  Acknowledgement | Escalation | Audit | Monitoring | Rollback
```

### Presentation narrative

“Veyra does not ask every hospital to replace its HIS, buy wearables or build a data centre. We first discover what that hospital can reliably provide, connect through the safest supported interface, normalize the data, test whether our model transfers to that site's patient population and measurement habits, and only then unlock the appropriate deployment level. The hospital keeps its data and clinical authority; Veyra keeps its licensed clinical intelligence platform.”

**Judge one-liner:**

> “The barrier is not only predicting sepsis; it is safely deploying a model across different hospital data systems and clinical environments. Veyra's proposed solution is one clinical core, multiple connector paths, and a hospital-specific safety gate before alerts are enabled.”

## 16.9 What is existing, what is proposed, and what still needs proof

| Item | Status to communicate |
|---|---|
| Bangladesh Core FHIR IG and DGHS FHIR sandbox | Officially documented national resources; do not infer all hospitals have implemented them. |
| SMART App Launch and CDS Hooks | Published interoperability specifications; use depends on each EHR's implementation and site approval. |
| FHIR facade / interoperability layer | Established architectural patterns; a 2025 peer-reviewed facade paper and OpenHIE reference architecture exist. |
| Veyra's multi-path connector ladder | Proposed product architecture unless each connector has passed an actual integration test. |
| Veyra Edge for no-data-centre hospitals | Proposed managed deployment package until hardware, security, offline, backup and operational tests are completed. |
| TransferShield S0–S8 | Proposed local-transferability and rollout framework; requires retrospective and prospective validation. |
| Veyra Super Admin control plane | Proposed fleet and per-hospital configuration/business model; do not claim full implementation unless verified in the live product. |
| Vendor partnerships / EHR marketplace access | Commercial opportunities; require actual agreements and technical approvals. |
| Site-specific calibrator or model adaptation | Requires adequate local labelled data, independent validation, clinical governance and version control. |

## 16.10 Open research and product tasks before external claims

1. Identify the actual HIS, LIS and monitor brands/models in target Bangladeshi hospitals through interviews and on-site inventories; do not infer the vendor landscape from general market assumptions.
2. Ask each vendor for supported integration documents, test endpoints, HL7/FHIR/API capability, export policy, costs and contract terms.
3. Test the DGHS FHIR sandbox with BD Core FHIR profiles; separately determine the production onboarding process and which facilities are connected.
4. Build a connector proof-of-concept against synthetic/sample messages for each integration level; label it a simulation until a hospital authorizes and tests it.
5. Define a data dictionary and mapping QA process for HR, RR, BP, SpO₂, temperature, CBC, creatinine, lactate, cultures, medications and timestamps.
6. Define the minimum viable Veyra Edge hardware and security baseline; verify offline queue, UPS, encrypted backup, update/rollback, remote access and incident workflow.
7. Have Bangladesh counsel review the Personal Data Protection Act, 2026, applicable regulations, cross-border data handling, hospital contract, data processing agreement and research/clinical approvals.
8. Create a site validation protocol with an adequate event count, temporal holdout, calibration plan, threshold policy, subgroup checks and alert-burden limits.
9. Conduct clinician and nursing workflow interviews to assign alert recipients and escalation responsibilities before silent testing.
10. Keep the Super Admin and hospital clinical governance roles separate; platform-level “unlock” must never replace hospital sign-off.

## 16.11 User-shared implementation note — verify before claiming

The user supplied a prior AI-generated update claiming that the following had been created/pushed: `docs/innovation-adoption-barriers.md`, `docs/adapters/vendor-adapter-contract.v1.json`, `/connection` judge page, navigation/Judge Desk/Evidence/Docs pipeline, Git commit `fea178b`, and Docker digest prefix `5ee53040…`, with Render Manual Deploy still required. This was **not independently verified in this research task**. Before using this in a judge presentation, inspect the actual repository, commit, deployed service and `/connection` page; distinguish code shipped, deployed, and tested with a real hospital.

---

# 17. Sources added for the deployment-innovation track

1. [ONC — Non-Federal Acute Care Hospital EHR Adoption, 2008–2024](https://healthit.gov/data/data-briefs/non-federal-acute-care-hospital-electronic-health-record-adoption-2008-2024/)
2. [HL7 — SMART App Launch v2.2.0](https://hl7.org/fhir/smart-app-launch/app-launch.html)
3. [HL7 — CDS Hooks v2.0.1](https://cds-hooks.hl7.org/)
4. [DGHS — Bangladesh Core FHIR Implementation Guide v0.5.0](https://fhir.dghs.gov.bd/core/)
5. [DGHS — Shared Health Record / Health Information Exchange](https://en.info.shr.dghs.gov.bd/hie/)
6. [OpenHIE — Interoperability Layer](https://ohie.org/practice-area/interoperability-layer/)
7. [Jafarpour et al. (2025) — Bridging the Legacy Interoperability Gap: FHIR Facade for EAV-Based Systems](https://pubmed.ncbi.nlm.nih.gov/40588950/)
8. [HHS — Guidance on HIPAA & Cloud Computing](https://www.hhs.gov/hipaa/for-professionals/special-topics/health-information-technology/cloud-computing/index.html)
9. [Bangladesh — Personal Data Protection Act, 2026 (official law database)](https://bdlaws.minlaw.gov.bd/act-print-1692.html)
10. [Bangladesh — Personal Data Protection Act, 2026, Chapter 7 / Section 29](https://bdlaws.minlaw.gov.bd/act-1692/act-chapter-print-2699.html)
11. [Bangladesh Government Press — April 2026 Extraordinary Gazette index](https://dpp.gov.bd/bgpress/index.php/document/extraordinary_gazettes_monthly/2026-04-14)

**Citation discipline:** These sources support the newly added architecture and regulatory discussion. For the global adoption barriers and model-validation statistics in earlier sections, retain the original citations already listed in Sections 13–15. Before investor, judge, regulatory or hospital-facing use, re-open sources and verify dates, sample sizes and wording.

## 16.12 Corrections to common shorthand in the planning notes

These distinctions should be used in technical discussions and judge answers:

- **EHR lock-in is not proof that an EHR vendor always blocks competitors or charges a special fee.** It is the practical dependence created by proprietary interfaces, data models, contracts, security approvals, integration effort, vendor support and workflow configuration. Some vendors provide mature app/API ecosystems; access is still governed by the specific installation and contract.
- **The US is concentrated, not one-EHR-only.** ONC reports Epic at nearly half of hospitals and the top three vendors above 80% in 2024. Do not say almost every US hospital uses Epic.
- **FHIR does not automatically make two systems interoperable.** They still need compatible profiles, identifiers, terminology, units, timestamps, authorization scopes and working endpoints. A FHIR sandbox is not a live hospital connection.
- **FHIR facade is an established pattern, not the only or universally easiest answer.** It is suitable only when an authorized, stable source interface exists. CSV/SFTP, HL7 v2, approved APIs, a read-only replica, manual structured capture or a device gateway may be better in a given hospital.
- **CDC/replication is not automatically “zero load” or the only solution when vendors refuse direct access.** It requires explicit permission and operational controls. If no lawful supported source exists, do not extract data by scraping, bypassing controls or reverse-engineering a production database.
- **Hybrid architecture is not “100% safe” by definition.** It reduces some integration burdens but creates a new sensitive-data store, network, keys, backups and failure modes that must be secured and monitored.
- **BAA is specific to US HIPAA relationships.** Do not call a Bangladeshi cloud contract a BAA unless the arrangement is actually subject to HIPAA and the parties are signing a HIPAA-compliant BAA. Elsewhere use the correct local processor/data-processing contract and legal basis.
- **FDA/IMDRF GMLP is guidance, not a blanket rule that every hospital must recalibrate a model.** The FDA's transparency principles recommend explaining how site-specific acceptance testing/validation and ongoing performance monitoring are handled. The legal/regulatory obligations depend on the product's intended use and jurisdiction.
- **A one-to-three-month silent period is not a universal requirement.** Set duration and minimum case/event volume in the protocol. The aim is adequate prospective data and operational learning, not simply waiting a fixed number of days.

Sources:
- [FDA — Good Machine Learning Practice Guiding Principles](https://www.fda.gov/medical-devices/artificial-intelligence-enabled-medical-devices/good-machine-learning-practice-medical-device-development-guiding-principles)
- [FDA — Transparency for Machine Learning-Enabled Medical Devices](https://www.fda.gov/medical-devices/artificial-intelligence-enabled-medical-devices/transparency-machine-learning-enabled-medical-devices-guiding-principles)
- [BMJ 2024 — How to undertake an external validation study](https://www.bmj.com/content/384/bmj-2023-074820)
- [Systematic review — Methodological guidance for evaluating/updating clinical prediction models](https://pmc.ncbi.nlm.nih.gov/articles/PMC9742671/)
