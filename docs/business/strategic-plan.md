# PredictRx Sentinel — strategic plan, finance and go-to-market (2026–2029)

Status: planning document. Market figures are cited; prices, volumes and
financials are **assumptions to test**, not forecasts or quotes. No customer,
partner, investor, adviser or grant exists unless written evidence is in the
data room. Frozen Run 4 is retrospective and not approved for clinical use.

## 1. The decision: research, sell, or humanitarian?

Do all three, in a fixed order, with separate money buckets:

| Track | What it is | Who pays | Why it comes first/second/third |
|---|---|---|---|
| **1. Research** | Methods papers now; local validation studies with hospitals | Research grants, academic partners (company is the technology partner) | Without local evidence no hospital should use the score and no serious investor will price the model. Papers become the sales asset. |
| **2. Commercial** | Readiness assessment → SafeLaunch silent pilot → workflow/data-quality subscription for private hospitals | Private hospitals and groups | Pays salaries; proves willingness to pay; sellable even before the model is validated because the workflow and data-quality layer have value on their own. |
| **3. Public-interest** | Open core and subsidised deployments for public/district ICUs | Grants, donors, CSR, government programmes | Largest health impact, slowest procurement; funded only by dedicated money so it never drains the commercial track. |

The pitch line: **"We earn from workflow and data quality today, build
evidence with researchers, and only then let the model speak at the bedside."**
If local validation of Run 4 fails, the company still has a product: the data
layer, governance and silent-evaluation tooling. That survival property is the
core of the investor case.

## 2. Problem and market (cited)

| Fact | Source |
|---|---|
| 48.9 million sepsis cases and 11.0 million sepsis-related deaths worldwide in 2017 (19.7% of all deaths); highest burden includes South Asia | Rudd et al., *Lancet* 2020 [1] |
| Bangladesh sepsis death rate reported as 136 per 100,000 in the same GBD 2017 analysis | Press summary of [1] [2] |
| 2,139 adult ICU beds and 717 HDU beds in 208 hospitals (129 private); 1.70 critical-care beds per 100,000; 38 of 64 districts without critical-care beds (2022 survey) | *Bangladesh Critical Care Journal* [3] |
| 1,372 ICU beds in 74 public hospitals, 55% in Dhaka; many district ICUs idle for lack of staff (2025) | DGHS data via The Business Standard [4] |
| Private Dhaka ICU bed charge alone: about BDT 4,250–16,500 per day (2025 price lists) | Hospital price pages [5] |
| A widely deployed proprietary sepsis model externally validated at AUC 0.63, missed 67% of sepsis cases while alerting on 18% of admissions | Wong et al., *JAMA Intern Med* 2021 [6] |
| First FDA-authorised AI sepsis tool (Prenosis, De Novo, 2024); Prenosis raised a USD 20M Series A plus a USD 20M BARDA contract (Jan 2026); Bayesian Health sepsis device cleared April 2026 | FDA, company releases [7][8][9] |
| India: about 95,000 ICU beds, 59,262 private (2020 estimate) | Kapoor et al., medRxiv 2020 [10] |
| Bangladesh healthtech venture funding is small: about USD 12.6M raised across 15 funded companies to Dec 2025 | Tracxn [11] |

What this means:

1. The clinical problem is large, and the category is investable: regulators
   authorise sepsis AI and investors fund it.
2. Models that are not validated locally fail. Our "validate silently before
   speaking" design answers a documented failure, not a theoretical one.
3. **Bangladesh alone is a small software market.** Our honest numbers are in
   section 4. The venture case therefore needs (a) more than ICU-only
   revenue (wards/HDU, research services) and (b) expansion to South Asia
   after local proof.

## 3. Customers and offer ladder

**Beachhead:** Dhaka/Chattogram private hospitals with 8–30 adult ICU beds, an
HIS or LIS that can export data, and a named ICU director or quality lead as
champion. Buyers: CEO/COO, medical director, ICU head, CIO.

| Offer | Price hypothesis (BDT) | Deliverable |
|---|---|---|
| ICU Data Readiness Check (lead generator) | Free, 1 day | 10-question data/workflow scan and a one-page gap report |
| Readiness assessment | 1–2.5 lakh | Source inventory, data-quality baseline, governance gaps, scoped pilot plan |
| SafeLaunch silent pilot (8–12 weeks, one ICU) | 4–12 lakh | Installation, mapping, training, silent scoring, adjudication support, closeout report |
| Workflow + data-quality subscription | 60,000–1.5 lakh per hospital/month | ICU board, chart, handoff, feed monitoring, audit, updates, support |
| Ward/HDU module (NEWS2 board) | +25,000–40,000/month | Ward observations and completeness, NEWS2 only |
| Research/validation pack | +30,000–50,000/month or per study | Cohort tools, adjudication, pseudonymised export, statistician time |
| Public/district deployment | Grant- or CSR-funded | Open core plus training; no charge to the public hospital |

Anchor for buyers: the full subscription is roughly the bed charge of one
private ICU bed for 6–10 days per month, for the whole hospital.

## 4. Financial plan (assumption-driven scenario)

Assumptions: BDT 122 = USD 1; average subscription BDT 1 lakh per
hospital/month; SafeLaunch BDT 6 lakh; readiness BDT 1.5 lakh; research
contract BDT 10–12 lakh; salaries modest (founder stipends in year 1).

| Base case | Year 1 (Nov 2026–Oct 2027) | Year 2 | Year 3 |
|---|---:|---:|---:|
| Paid readiness assessments | 3 | 4 | 6 |
| SafeLaunch pilots | 1 | 3 | 5 |
| Subscribing hospitals at year end | 0 | 4 | 10 |
| Subscription site-months | 0 | 24 | 84 |
| Research/validation contracts | 0 | 1 | 2 |
| **Revenue (BDT lakh)** | **10.5** | **58** | **147** |
| Operating cost (BDT lakh) | 47 | 85 | 150 |
| **Net before grants and equity (BDT lakh)** | **−36.5** | **−27** | **−3** |
| Revenue (USD) | ~8.6k | ~47.5k | ~120k |

Year-1 cost breakdown (BDT lakh): team stipends 28.8, legal/regulatory advice
and insurance 5, security penetration test 3, paid clinical adjudication
honoraria 4, travel/on-site 3, cloud/demo/devices 3.

Unit economics to verify at the first sites:

| Unit | Price | Direct cost assumption | Gross margin |
|---|---:|---|---:|
| SafeLaunch | 6 lakh | 25 FDE days, adjudication, statistician, travel ≈ 3 lakh | ~50% |
| Subscription | 1 lakh/month | 3 support days, monitoring, updates ≈ 0.2 lakh | ~80% |

Subscriptions run on hospital hardware, so there is no hosting cost per site.
That keeps gross margin high once mappings repeat.

**Downside case:** first paid pilot slips to Q4 2027; year-2 revenue about
BDT 25 lakh. Response: keep the team at 4, live on grants and research
contracts, and do not raise at a bad valuation.

**Upside case:** a hospital group adopts after one pilot (3–5 sites at once).
Sales cost per site falls sharply because mappings are shared.

## 5. Funding stack

Sequence money from cheapest to most expensive:

| Stage | Source (verify current calls; none are secured) | Typical size | Use |
|---|---|---|---|
| Now | Congress prizes, university/innovation competitions | small | Demo, legal setup |
| Non-dilutive, local | iDEA (ICT Division) startup grants, up to BDT 10 lakh in the 2025 youth programme [12] | ≤10 lakh | First pilot costs |
| Research, local | BMRC research grants: six-month projects, *IT & Digital Health* and *Health System & Informatics* are listed areas; disbursement depends on government funds [13] | not stated | Data-readiness study led by a clinician PI |
| Research, international | Wellcome, NIHR global health, Gates/Grand Challenges calls. EVAH (Wellcome, Gates, Novo Nordisk; up to USD 1M per evaluation) currently targets primary/community care, so it does **not** fit an ICU tool today [14] | USD 50k–1M | Multi-site validation with an academic PI |
| Equity, pre-seed | Startup Bangladesh (government VC, lists healthcare as a priority) [15]; local and regional angel networks; accelerators active in Bangladesh healthtech (for example Iterative, which backed PulseTech) [16] | USD 100–150k | 18–24 months of runway after the first paid pilot |
| Equity, seed | Regional health/impact VCs | USD 1–1.5M | South Asia expansion, regulatory file |

**Pre-seed ask (when the first paid pilot is signed):** USD 150k on a SAFE.
Use of funds: 45% team (one forward-deployed engineer, one clinical
informatics lead), 15% validation study costs (ethics, adjudication,
statistician), 15% security, legal, regulatory and insurance, 15% sales and
marketing, 10% reserve.

**Seed trigger (not before):** three paying hospitals, a published or
preprinted local silent-validation report, renewal intent from site one, and
one signed partner pilot outside Bangladesh.

## 6. How researchers fund it (without selling data)

Researchers fund research, not products. Make PredictRx the infrastructure that
makes their study possible and their grant budget pays for it:

1. **Clinician PI leads, company is technology partner.** The grant has a
   budget line for installation, support and data-quality tooling.
2. **Hospital owns the data; company owns the software; nobody sells data.**
   Publications follow ICMJE authorship. No sponsor veto, and negative results
   get published.
3. **Publication pipeline:**

| Paper | Needs a hospital? | Target |
|---|---|---|
| Data-quality-gated sepsis scoring: TrustGate abstention on public ICU data | No (do now) | Preprint, then a critical-care informatics journal |
| Bangla/English clinical code mapping with local LLMs: open benchmark | No; needs clinician-labelled cases | Health informatics venue |
| ICU data readiness across Bangladeshi hospitals | Yes, readiness assessments + ethics | Regional critical-care journal |
| Silent prospective external validation of a frozen sepsis model in Bangladesh | Yes, SafeLaunch site + ethics | Higher-impact journal; regulatory evidence |

4. **Open assets attract collaborators:** release the copilot benchmark and the
   TrustGate evaluation code; cite-able tools bring universities to you.

## 7. Public-interest track

- Open-core: bedside chart, NEWS2 ward board and data-quality monitoring can be
  released under an open-source licence later; the subscription sells support,
  integrations, security, upgrades and validation operations.
- Public district ICUs get the open core plus training funded by grants or CSR,
  never by quietly discounting private contracts.
- Separate accounting per grant so funders can audit that money went where
  promised.

## 8. Go-to-market and marketing

**Positioning:** "The safe way for a Bangladeshi ICU to get AI-ready: one
traceable flowsheet, visible data quality, and a sepsis model that stays
silent until your own data proves it."

**Funnel:** free Readiness Check → paid assessment → SafeLaunch → subscription
→ group rollout.

| Channel | Action | Metric |
|---|---|---|
| Clinical champions | Intensivists and ICU nurse leads; teach "why sepsis models fail without local validation" (the 0.63 AUC story) | Champions with a scheduled readiness check |
| Professional meetings | Critical-care and nursing conferences, medical-college grand rounds | Talks given, leads |
| Hospital IT and HIS vendors | Integration partnership: we bring the ICU layer, they keep the HIS | Signed integration MoUs (written only) |
| Content | Monthly LinkedIn post or short article on ICU data quality; Bangla nurse quick-reference cards | Inbound requests |
| Proof | Congress result, open benchmark, preprints, case study only with written permission | Assets published |

Sales cycle assumption: 3–9 months for private hospitals, 9–18 months public.
Founder-led sales until three sites.

**KPIs every month:** qualified pipeline, readiness → pilot conversion,
deployment days per site, mapping reuse %, quarantine rate, adjudications
completed, active users per shift, renewal intent, cash runway.

## 9. Investor narrative (one minute)

1. Sepsis kills about 11 million people a year; South Asia carries a heavy share.
2. Sepsis AI is a real category: FDA authorised tools in 2024 and 2026, and
   one company closed a USD 20M Series A plus a USD 20M BARDA contract in
   January 2026.
3. Those models fail when moved without local validation: AUC 0.63 and 67%
   missed in a famous external validation.
4. Bangladeshi ICUs cannot buy US tools and should not trust unvalidated ones.
   They lack clean data, governance and a safe evaluation path.
5. PredictRx installs that path on-premises: data-quality layer, governed silent
   evaluation, and a frozen model that abstains when data is poor. No central
   patient data.
6. We earn from workflow and data quality first, so the business survives even
   if the model needs retraining.
7. Bangladesh is the proving ground; India alone has about 59,000 private ICU beds.

## 10. Milestones (12 months)

| When | Milestone | Evidence |
|---|---|---|
| Nov 2026 | Congress; company registration plan; contract and DPA templates | Documents |
| Dec 2026–Jan 2027 | 15 real discovery conversations; 5 free Readiness Checks offered | Dated notes, permission to cite |
| Q1 2027 | First paid readiness assessment; TrustGate methods preprint; iDEA/other grant applications | Invoice, preprint DOI, submissions |
| Q2 2027 | First SafeLaunch install; ethics approval for silent pilot | Signed SOW, ethics letter |
| Q3–Q4 2027 | 28+ day silent pilot; local validation report; pre-seed round | Pilot report, SAFE |

## 11. Risks and kill criteria

| Risk | Mitigation |
|---|---|
| Model underperforms locally | Stay silent, sell the data/workflow layer, plan governed recalibration study (new model version, never edit Run 4) |
| Regulation: DGDA treats standalone software as a medical device (2023 Act) [17] | Research/silent use only until a regulatory adviser confirms the class and path; build QMS habits early |
| Data protection: health data is sensitive personal data under the Personal Data Protection Ordinance 2025 [18] | Hospital as controller, on-prem processing, DPA, breach process, no central PHI |
| Long sales cycles | Free readiness check, small fixed-scope paid steps, grant-funded pilots |
| Small home market | Ward/HDU and research modules; regional expansion only after local proof |
| Founder bandwidth | Scope to one beachhead; hire an FDE with pre-seed money |

**Stop or pivot if** by Q4 2027 there is no paid pilot and no funded research
partner, or if hospitals want the score shown clinically before validation.

## Sources

1. Rudd KE et al. Global, regional, and national sepsis incidence and mortality, 1990–2017. *Lancet* 2020. <https://pubmed.ncbi.nlm.nih.gov/31954465/>
2. New Indian Express summary of [1], 19 Jan 2020. <https://www.newindianexpress.com/states/karnataka/2020/Jan/19/india-has-2nd-highest-sepsis-death-rate-in-south-asia-2091487.html>
3. Critical care bed capacity of Bangladesh: a pre and post COVID-19 pandemic survey. *Bangladesh Crit Care J* 2022. <https://doi.org/10.3329/bccj.v10i2.62200>
4. The Business Standard: Covid-era ICU investments lie idle. <https://www.tbsnews.net/bangladesh/health/covid-era-icu-investments-lie-idle-public-hospitals-face-critical-staff-shortage>
5. Public ICU price lists: Square Hospitals <https://www.squarehospital.com/post/63/room-rent>; Millennium Specialized <https://mshlbd.com/room-rate>; AMZ Hospital <https://amzhospitalbd.com/pages/bed-charge>; eHospitalbd <https://ehospitalbd.com/service-icu.php>
6. Wong A et al. External validation of a widely implemented proprietary sepsis prediction model. *JAMA Intern Med* 2021. <https://jamanetwork.com/journals/jamainternalmedicine/fullarticle/2781307>
7. FDA De Novo DEN230036, Sepsis ImmunoScore. <https://www.accessdata.fda.gov/cdrh_docs/pdf23/DEN230036.pdf>
8. Prenosis: USD 20M BARDA contract and USD 20M Series A, 29 Jan 2026. <https://prenosis.com/news/prenosis-announces-barda-contract-series-a-financing-round/>
9. FDA 510(k) K250680, Bayesian Health Sepsis Flagging Device. <https://www.accessdata.fda.gov/cdrh_docs/pdf25/K250680.pdf>
10. Kapoor G et al. State-wise estimates of hospital beds, ICU beds and ventilators in India. medRxiv 2020. <https://doi.org/10.1101/2020.06.16.20132787>
11. Tracxn: HealthTech in Bangladesh (Dec 2025). <https://tracxn.com/d/explore/healthtech-startups-in-bangladesh/__aA2UNIfBCLiWMXsaQKZbrLTpltfvnFU7qQb7FFdBmA8>
12. The Business Standard: iDEA National Youth Summit Startup Grant Programme, Feb 2025. <https://www.tbsnews.net/economy/corporates/idea-project-launches-national-youth-summit-startup-grant-programme-1060981>
13. BMRC research grant call FY 2026–27. <https://bmrcbd.org/Notice_board/2026-05-03__Research-Grant.pdf>
14. J-PAL: Evidence for AI in Health (EVAH) RFP. <https://www.povertyactionlab.org/initiative/evidence-ai-health-evah-rfp>
15. Startup Bangladesh Ltd. investments update, Jan 2025. <https://www.startupbangladesh.vc/startup-bangladeshs-strategic-investments-continue-to-accelerate-growth-across-key-sectors/>
16. The Daily Star: PulseTech raises USD 3M, Dec 2025. <https://www.thedailystar.net/tech-startup/news/bangladeshi-startup-pulsetech-raises-3m-bid-tackle-counterfeit-medicines-4050016>
17. RegDesk: Bangladesh medical device regulations (DGDA). <https://www.regdesk.co/regulations-library/bangladesh/>
18. Personal Data Protection Ordinance 2025 (Ordinance No. 61 of 2025). <http://bdlaws.minlaw.gov.bd/act-details-1574.html>
