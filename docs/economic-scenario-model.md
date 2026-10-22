# Societal & economic scenario model — Bangladesh ICU sepsis

A transparent planning model, not a results claim. Every input is either
cited from published literature/rate cards or labelled **assumption** and
varied across a range. Its purpose is to size the problem a hospital pilot
would measure — and to show what would have to be true for earlier
recognition to matter at national scale. PredictRx Sentinel claims **no**
deaths avoided, bed-days freed, or money saved: those numbers can only come
from a named site's adjudicated pilot.

## Sourced inputs

| Input | Value used | Source |
|---|---|---|
| ICU beds in Bangladesh | 2,177 (190 ICUs); 1.8 critical-care beds/100k | Asian critical-care survey, *Lancet Reg Health West Pac* 2023 [5 in impact dossier] |
| Districts with no critical-care beds | 38 of 64 | Bangladesh survey, *BCCJ* 2022 |
| Sepsis share of ICU admissions | 22% (Rajshahi, 305/1,367) to 41% severe sepsis (BIRDEM, 95/228) | *Adv Infect Dis* 2020; *BCCJ* 2015 |
| Sepsis ICU mortality | 46.9% (Rajshahi) to 49.2% (14-ICU study) | *Adv Infect Dis* 2020; *BCCJ* 2013 |
| ICU bed charge (private, published) | Tk 9,000–12,500/day bed-only | Popular Hospitals and Millennium Specialized Hospital rate cards |
| All-in private ICU cost (reported) | Tk 30,000–50,000+/day with ventilation, medicines, tests | Rate-card components; *The Business Standard* 2021 reporting |
| Effect of earlier engagement (external) | Alert confirmed ≤3 h associated with −3.34 pp adjusted mortality; survivor stay −11.6 h median | TREWS prospective study, *Nat Med* 2022 (observational) |

## Assumptions (varied, never hidden)

| Assumption | Conservative | Base | Stretch | Note |
|---|---|---|---|---|
| Mean ICU length of stay (days) | 7 | 5 | 4 | Planning assumption; not a Bangladesh measurement |
| ICU occupancy | 80% | 85% | 90% | Planning assumption |
| Sepsis share of admissions | 22% | 30% | 41% | Brackets the two Bangladeshi cohorts |
| Sepsis mortality | 47% | 48% | 49% | Brackets the two Bangladeshi cohorts |

Admissions per ICU bed per year = 365 × occupancy ÷ length of stay
(≈42 / 62 / 82 across the three scenarios).

## Scenario results (arithmetic on the inputs above)

| Quantity (national, per year) | Conservative | Base | Stretch |
|---|---|---|---|
| ICU admissions (2,177 beds) | ≈ 91,000 | ≈ 135,000 | ≈ 179,000 |
| Sepsis admissions | ≈ 20,000 | ≈ 40,500 | ≈ 73,000 |
| Sepsis deaths at 47–49% mortality | ≈ 9,400 | ≈ 19,400 | ≈ 35,800 |

Per single 20-bed ICU (base scenario): ≈ 1,240 admissions/year, of which
≈ 370 sepsis, of whom ≈ 180 die. One ICU, one year.

**Family cost exposure (base):** a 6-day sepsis ICU stay at the published
all-in range is roughly **Tk 1.8–3.0 lakh** out of pocket in the private
sector — against a lower-middle-income household budget, a catastrophic
expenditure by any definition used in the health-economics literature. The
public sector avoids the bill but not the scarcity: the same bed-days are
the system's binding constraint.

## What earlier recognition would be worth — IF a pilot proves it

Threshold framing only. The TREWS association (−3.34 pp mortality when a
provider confirms within 3 hours) comes from five US hospitals with a
different model and workflow; it is used here solely to size the prize:

| Hypothetical local effect (to be tested, not claimed) | Per 20-bed ICU-year (base) | National (base) |
|---|---|---|
| Mortality −1 percentage point among sepsis admissions | ≈ 4 fewer deaths | ≈ 400 fewer deaths |
| Mortality −3.34 pp (TREWS association, if it transferred) | ≈ 12 fewer deaths | ≈ 1,350 fewer deaths |
| Survivor stay −11.6 h (TREWS association, if it transferred) | ≈ 90 bed-days freed | ≈ 9,800 bed-days freed |

Read this table as: *the effect sizes worth powering a pilot to detect*.
If a silent pilot cannot move review time, none of these rows are in play —
which is precisely why the KPI contract (`docs/impact-evidence.md` §3)
measures process first and keeps interruptive alerting off until then.

## What this model deliberately excludes

- No DALY/QALY monetisation and no "value of a statistical life" figure;
  Bangladeshi willingness-to-pay parameters would be invented precision.
- No product price and no return-on-investment claim; pricing evidence is
  founder research, and ROI requires a measured local effect.
- No assumption that US effect sizes transfer to Bangladesh. Calibration
  slope 0.80 on a distinct US cohort is the standing warning against that.
