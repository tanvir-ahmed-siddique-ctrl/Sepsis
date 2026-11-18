Bangladesh ICU Research Handoff (Compact)
Purpose: Give a new AI assistant the minimum context needed to continue the research without repeating completed work. Read this as a project brief, not as proof that every claim has been independently re-verified.
1. Project in one minute
Veyra (formerly PredictRx Sentinel) is a research-stage AI clinical decision-support prototype for adult ICU sepsis / clinical-deterioration early warning in Bangladesh. Intended approach: use existing hospital data (EHR/HIS, LIS, bedside monitors, authorized observations), estimate risk, show interpretable signals, and support—not replace—clinical judgment. Wearables are not a mandatory product requirement.

Current described prototype: frozen LightGBM model; retrospective evaluation on public ICU datasets; ingestion design for CSV, HL7 v2, FHIR and vendor adapters; risk/explanation and alert workflow components; synthetic-data demo.

Evidence boundary: No validation on Bangladeshi adult ICU patients; no live Bangladesh hospital EHR/monitor integration; no prospective clinical study; no demonstrated clinical benefit, workflow safety or patient-outcome improvement. Treat as a research prototype, not a clinically validated/approved product. Do not describe the synthetic demo as a real hospital deployment.
2. Bangladesh sepsis / ML research already identified
A. PLOS Digital Health (30 Oct 2024)
“A novel digital health approach to improving global pediatric sepsis care in Bangladesh using wearable technology and machine learning.” icddr,b Hospital, Dhaka; Feb–Dec 2022; 100 children aged 2 months–17 years with suspected sepsis/serious infection.
- Used a commercial VitalPatch, not a researcher-built wearable. Bluetooth → smartphone → cloud/dashboard.
- Signals: HR, RR, temperature, ECG-related signals and HRV. Clinical observations were hourly; labs at admission and generally every 12 hours. Mean monitoring ~2.2 days; reported data capture quality >99%.
- Target: advanced pediatric sepsis using pSOFA. Ridge-model AUROCs: Model A wearable + selected clinical data 0.69; B wearable + MAP + SpO₂:FiO₂ 0.86; C wearable-only features 0.78.
- Reported timing: model detection ~6.88 h before the analysis reference point; clinician EHR documentation ~4.19 h before it (difference ~2.7 h). EHR documentation time is not necessarily the moment clinicians first recognized deterioration. No proof that model alerts changed treatment or outcomes.
B. American Journal of Tropical Medicine and Hygiene (published 18 Nov 2025; issue Jan 2026)
“Predicting Pediatric Sepsis and Mortality Using Wearable Device Data and Machine Learning in Bangladesh.” Same research programme/cohort, not independent external validation; 100 original participants, 96 suitable for Phoenix Sepsis Score analysis.
- LASSO on wearable-derived features; leave-one-group-out cross-validation.
- AUROC: sepsis 0.78, septic shock 0.85, mortality 0.84–0.87 (abstract/table discrepancy: abstract 0.87, main table 0.84). Adding manual SpO₂:FiO₂ raised sepsis AUROC to 0.89.
- Sepsis/shock tasks are mainly recognition/classification against criteria during monitoring windows; mortality used first 12 h of wearable data to estimate eventual in-hospital death. Do not call all tasks future sepsis prediction.
- Small, single-hospital pediatric cohort; internal validation; no nationwide deployment or proven outcome benefit. Larger multicentre validation and real-time integration remain needed.
C. Pediatric Reports (3 Jul 2026)
“Utilizing Machine Learning for Diagnostic Assistance of Pediatric Sepsis and Septic Shock in Resource-Limited Settings.” Clinical-data-based models using the same 100-child cohort; seven algorithms; features included age, HR, RR, BP, temperature, GCS and SpO₂:FiO₂.
- Reported AUROC: sepsis classification 0.945; septic shock 0.878.
- Used most abnormal clinical values in the same 24-hour period for classification. This is not equivalent to forecasting future deterioration. Different definitions, windows and features mean results are not directly comparable with wearable studies. External validation required.
D. Existing-record ML example
A separate icddr,b study used SHEBA EHR records (2011–2019) from children aged 0–59 months in ICU to predict mortality using routine clinical, biochemical and haematological data. It is not a sepsis-specific model, but shows that research using existing hospital records is possible.

Positioning implication: Bangladesh already has pediatric sepsis-related ML research. Never claim “AI sepsis prediction is entirely new in Bangladesh” or that Veyra is the first. Veyra's intended distinction is adult ICU focus plus local validation, existing-data integration and accountable clinical workflow—none yet proven locally.
3. Why wearables were used; are they required?
The identified research used wearables mainly to capture continuous physiological patterns (e.g., minute-by-minute HR/RR and HRV) that intermittent chart entries may miss—not simply because the hospital had no digital records. icddr,b reportedly had SHEBA EHR since 2009 and routine telemetry/clinical documentation. Wearables were separately used to obtain dense time-series data.

Veyra should be existing-data-first. Suitability depends on each hospital's actual data frequency, completeness, timestamps and export capability:
- EHR/HIS + labs → clinical-data model.
- Exportable monitor streams → time-series analysis.
- Both → combined model, if justified.
- Paper/manual records → feasibility assessment and structured collection.
- Poor/inconsistent data → missingness safeguards; do not assume usable real-time integration.
Inventory first: vital-sign frequency; monitor make/model and export/API capability; lab timestamps; lactate/culture access; medication/antibiotic timestamps; clinical escalation/intervention timestamps. A monitor displaying a value does not mean it can export data to Veyra.
4. Alerts, NEWS2 and Bangladesh evidence
Distinguish three things:
1. Bedside monitor alarms: thresholds for HR, SpO₂, BP, RR, etc. Equipment/configuration/central monitoring/response practices vary; no comprehensive national inventory was established.
2. NEWS2: rule-based general deterioration score. A 2023 Tropical Doctor quality-improvement report from Square Hospitals, Dhaka, describes NEWS2 training/use in an HDU and statistically significant reductions in cardiac arrest and ICU transfer associated with unrecognized deterioration. This is one hospital QI setting—not AI, and not proof of nationwide use.
3. AI sepsis alerts: Bangladesh has pediatric wearable/clinical-data ML studies and clinician-feasibility research. Prior research did not establish nationwide routine deployment of an integrated AI sepsis-predictive alert system. Do not claim there are no alerts in Bangladesh.
A 2025 JMIR Formative Research qualitative study interviewed 18 doctors/nurses at icddr,b Dhaka Hospital, Kushtia General Hospital and the Institute of Child and Mother Health. Reported needs/preferences included alerts for HR, RR, SpO₂ and temperature; audio/visual warnings; multi-patient monitoring; affordability/reliability; simple workflow; connectivity and trust; and avoidance of alarm fatigue. This is clinician feedback, not deployment evidence.

NEWS2 basics: National Early Warning Score 2 uses respiratory rate, oxygen saturation, supplemental oxygen, systolic BP, pulse/HR, temperature and consciousness/new confusion. General interpretation: 0–4 lower risk; any single parameter scoring 3 needs attention; 5–6 medium/urgent; ≥7 high/emergency. Follow local protocol. NEWS2 is not sepsis-specific; high score does not prove sepsis and low score does not rule out early sepsis.

NEWS2 vs Veyra: NEWS2 uses predefined thresholds to flag current physiological deterioration. Veyra is designed as ML risk estimation using the preceding 24 h of clinical features for following 6 h deterioration risk. Veyra has not been shown superior. A same-cohort, same-outcome head-to-head evaluation is needed.
5. Bangladesh hospital / ICU structure
There is no single verified ICU reporting structure that applies to every hospital. Map three authority lines separately:
- Administrative: Director, Superintendent, institutional management—operations, staffing, budget, procurement and facilities.
- Clinical: ICU Head/Clinical Lead/Intensivist, HOD, consultants, duty doctors and nursing leadership—patient care, supervision and escalation.
- IT/data: IT/ICT head, HIS/system/database administrators, biomedical engineering—accounts, infrastructure, interfaces, access controls, logs and technical maintenance.
A Dean is not automatically the ICU's operational or clinical head. Academic, hospital-administrative and clinical reporting lines may differ. One documented example: Bangladesh Medical University places its ICU division under the Department of Anaesthesia, Analgesia & Intensive Care Medicine; its official page lists 40 ICU and 14 HDU beds. This is an institutional example, not a national template.

ICU teams may include: intensivist/ICU lead; duty doctors/medical officers/registrars/residents; nurses and nurse-in-charge; specialty consultants (medicine, cardiology, nephrology, neurology, surgery, infectious disease, pediatrics, etc.); laboratory/microbiology, radiology, respiratory therapy, physiotherapy, pharmacy, dietetics, dialysis, blood bank, biomedical engineering/equipment technicians, infection control, IT and support staff. Not every hospital has all roles as dedicated staff.

Open vs closed ICU: In an open ICU, admitting/specialty teams retain a substantial management role with ICU input; in a closed ICU, the ICU team takes primary responsibility and specialists consult. A 2010 Dhaka survey reported 85% open / 15% closed, but this is historical only; current national distribution is unknown.

Possible ICU deterioration pathway: bedside monitor/nurse identifies issue → nurse and duty doctor assess → senior/ICU clinician is notified → ICU lead coordinates → relevant specialty/resuscitation/lab/respiratory support as needed. Outside ICU, ward nurse/duty doctor/emergency/ICU/anesthesia may be involved according to local protocol. Do not assume every hospital has a 24/7 Rapid Response Team or Code Blue team.

For every alert, identify: recipient; acknowledgement; clinical assessor/decision-maker; response expectation; escalation if unanswered; documentation; and audit owner. Director and IT Head are not automatically bedside clinical decision-makers.
6. Data systems and interoperability
Potential data sources:
- Bedside monitors: HR, SpO₂, BP, RR, sometimes temperature and alarm/event data.
- LIS: CBC, chemistry, lactate, blood culture and other results.
- HIS/EHR: demographics, diagnosis, history, orders, medicines, notes, observations and investigations.
- Ventilators/equipment: settings, respiratory measurements and device status.
Systems may be paper-based, digital but separate, or integrated. DGHS Shared Health Record / Health Information Exchange work and Bangladesh Core FHIR implementation guidance have been identified. These do not prove that every hospital has a live FHIR interface or connected ICU monitors. Verify by hospital, vendor, device model and actual data-flow demonstration.
7. Access control and privacy
Recommended principle: role-based access + need-to-know + minimum necessary data. This is a proposed design, not a verified description of every hospital's permissions.
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

Prior research notes Bangladesh Personal Data Protection Act, 2026 (Act No. 63 of 2026) and treats health information as sensitive. Re-check the Act, commencement, rules and applicable lawful bases against official sources before relying on this legal summary. Clinical treatment and external commercial product development/ML reuse are different purposes. Before any pilot, obtain hospital authorization; establish lawful basis/consent as applicable; data-sharing agreement; ethics/institutional approvals where required; minimization; retention/deletion rules; encryption; access logs; and controls on third-party disclosure. Seek qualified local legal/privacy advice.
8. Other Bangladesh ICU evidence previously identified
- “Gaps and Needs in Critical Care Services in Bangladesh” (2023): Save the Children / USAID MaMoni MNCSP / Bangladesh Society of Anaesthesiologists Critical Care and Pain Physicians; assessment of 73 ICU/HDU-designated facilities in 2022; documented critical-care capacity/readiness gaps, particularly in some peripheral medical college and district hospitals.
- “Knowledge and Implementation Practices of Standard Intensive Care Services” (2025 publication): Barisal; Feb–May 2023; 80 doctors/nurses; ICU experience/training associated with knowledge/practice. District-level, not nationally representative.
- “An Audit of Intensive Care Services in Bangladesh” (2010): Dhaka; 40 ICU/ventilator-supported CCU units; 64% run by anesthesiologists and 85% open ICU. Historical only.
- Daily Star report (Apr 2026): Rajshahi division reportedly had 94 ICU beds, 44 unused/non-operational due to staffing shortage. Regional reporting, not national statistic.
- DGHS National ICU Quality Improvement Framework/monitoring checklist documentation exists; existence does not prove implementation in every facility.
9. Main unresolved research gap
Prior work did not establish a current, comprehensive national mapping of: ICU parent departments and organograms; clinical vs administrative reporting; day/night escalation workflows; open/closed ICU prevalence; monitor brands/models and exportability; vital-sign recording frequency; HIS/EHR/LIS adoption and integration; alarm/NEWS2 use; routine AI-alert deployment; alert recipients/acknowledgement/response times; IT access permissions; third-party integration approval; and rules for research/data sharing. Do not guess these answers or generalize from one hospital.
10. Practical primary-research plan
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
11. Implications and safe implementation sequence
1. Discover first: map clinical, administrative and technical owners; inventory data sources and actual exportability.
2. Govern data: define purpose, legal basis, approvals, minimum fields, read-only access where appropriate, role-based access, audit and retention.
3. Validate locally: obtain approved historical adult-ICU data; test temporal/patient-level leakage, missingness, calibration, false alerts and missed cases. Compare with current workflow/NEWS2 where appropriate.
4. Silent prospective pilot: generate risk scores without directing care; assess data reliability, alert burden, workflow fit and response accountability.
5. Consider live clinical alerts only after adequate evidence, approvals, safety review and clinician agreement.
Proposed views (not claims about existing hospital software): nurse—assigned patient, warning, trends, acknowledgement; duty doctor—risk trend and supporting data; ICU head—ICU overview and escalation status; management—aggregate operational metrics.
12. Instructions for the next AI assistant
- Continue from this brief; do not repeat the completed background research unless a source needs verification.
- Prioritize original papers, official hospital/DGHS documents, peer-reviewed studies and direct institutional evidence. Give working links/citations.
- For each study state publication date and study period, hospital, population, sample size, outcome definition, prediction window, validation method and limitations.
- Separate recognition/classification from forecasting; AUROC from clinical utility/outcomes; retrospective analysis from prospective study; qualitative feedback from deployment; prototype from routine clinical use; technical compatibility from a real integration.
- Do not compare AUROCs across studies as though tasks/cohorts/windows were identical.
- Do not infer national practice from one hospital or old surveys. Mark assumptions and unknowns.
- Verify legal claims against current official Bangladeshi sources.
- Do not claim Veyra is Bangladesh's first AI sepsis system, clinically validated locally, connected to a real hospital, or proven to improve outcomes.
Core conclusion: Bangladesh has pediatric sepsis ML research, wearable and clinical-data studies, NEWS2 implementation evidence in at least one HDU, and clinician feedback on CDSS. The unresolved opportunity is not simply “another model”: it is evidence-backed adult-ICU validation plus a feasible, secure, hospital-specific data integration and accountable alert workflow in Bangladesh.