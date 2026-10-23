# EHR / HIS partnership & commercial strategy (legal-safe paths)

Status: business planning. Not legal advice. Bangladesh DGDA / US FDA / CE
paths need qualified counsel. PredictRx Sentinel remains a research prototype
and is **not approved for clinical use**. No Epic, Oracle Health, Cerner, or
OpenMRS partnership is claimed unless a signed agreement exists in the data room.

## 1. What we sell (and what we refuse)

| We sell | We refuse |
|---|---|
| Hospital-owned PredictRx instance (on-prem or hospital VPC) | Giving Epic/Cerner our model weights or IP |
| Connection Ladder L0–L5 + U0–U2 integration into *their* systems | Claiming “Epic Showroom listed” before gallery approval |
| Silent-first evaluation + Transfer Shield gates | Interruptive alerts before local readiness |
| Workflow / data-quality / research ops layer | Outcome or mortality claims without local evidence |

**Commercial spine:** the hospital (or health group) is the customer. The EHR
vendor is a *channel shell*, not the product owner.

## 2. Legal ways to sit beside an EHR (US / high-maturity HIS)

### 2.1 Interface-engine feed (U0) — lowest legal friction

1. Hospital IT (or their interface vendor: Corepoint, Rhapsody, Cloverleaf, etc.)
   configures an outbound HL7 v2 ORU/ADT or FHIR subscription **to PredictRx**.
2. Contract is hospital ↔ PredictRx (BAA / DPA as required). Epic/Cerner is not
   a party unless the hospital’s MSA already covers third-party interfaces.
3. We never write orders back; read-only clinical observations + census.

**Why this is first:** no app gallery, no SMART OAuth registration delay, IP stays ours.

### 2.2 SMART on FHIR app (U1) — hospital Vendor Services

1. Hospital registers **PredictRx** as *their* SMART app under Epic Vendor
   Services / Oracle Health app program (hospital is sponsor).
2. OAuth against the **hospital** FHIR authorization server; launch context
   opens our cockpit; scoring stays on the hospital-local node.
3. We implement SMART App Launch 2.x (`/v1/ehr/smart/*` sandbox shipped).
   Production listing is a commercial milestone — not claimed today.

**Legal notes:** follow the vendor’s terms; do not scrape EHR UI; do not store
tokens longer than policy; PHI stays in the hospital boundary.

### 2.3 CDS Hooks (U2) — informational cards only

1. Hospital enables a CDS Hooks endpoint pointing at PredictRx
   (`/v1/ehr/cds-services`).
2. Cards are **info / link only** — open PredictRx cockpit. **No** medication
   or order suggestions (avoids higher CDS / clinical-decision regulatory load
   and vendor policy landmines).
3. Document in the site safety case that CDS output is non-directive.

### 2.4 What we do **not** do

- Resell Epic’s model or imply we are “inside” Epic AI Marketplace without listing.
- Reverse-engineer proprietary EHR databases.
- Pay for “preferred placement” that conflicts with anti-kickback / transparency rules
  without counsel review (US) or local equivalent.
- Process PHI in our founder laptops or public Render demo — demo is synthetic / lockdown.

## 3. Bangladesh / LMIC HIS paths (often no FHIR)

| Ladder | Commercial move | Contract artifact |
|---|---|---|
| L0 Chart | Sell workflow even when HIS is paper/offline | Site MoU + training schedule |
| L1 CSV drop | Nightly export SOP with hospital IT | Data-export SOP + mapping sign-off |
| L2 HL7 | LIS/analyzer already HL7 — cheapest real-time | Interface profile + quarantine runbook |
| L3 FHIR | OpenMRS+ / national HIE when available | Mapping registry SHA sign-off |
| L4 Vendor Adapter | Pay local HIS vendor a **small adapter fee** to emit `predictrx-vendor-adapter/1` | Adapter SOW (outbound only; no HIS DB write) |
| L5 Soft-landing | Position PredictRx as ICU intelligence UI; HIS keeps billing/ADT | Soft-landing addendum: non-replacement of HIS |

**L4 tactic:** do not ask the HIS vendor for deep API access. Give them the JSON
schema in `docs/adapters/vendor-adapter-contract.v1.json` and a fixed fee to emit
it. PredictRx never writes their database — that is the legal and political unlock.

## 4. Partnership shapes (only with counsel + signed paper)

1. **Hospital design partner** — paid silent pilot; publication rights negotiated;
   no exclusive IP grant away from PredictRx.
2. **HIS OEM / referral** — HIS vendor refers hospitals; PredictRx remains licensor;
   revenue share only on *new* seats they introduce (written referral agreement).
3. **Academic / NGO** — research MoU; commercial license separate; donor funds
   cannot buy regulatory claims.
4. **Government / DGHS path** — treat as public procurement later; do not claim
   national endorsement early.

## 5. How the business manages this (operating cadence)

| Cadence | Owner | Action |
|---|---|---|
| Weekly | Founder + FDE | Integration Hub health, quarantine, habit fingerprint, gate board |
| Per site | Integration lead | Mapping sign-off, soft-landing flag, connector choice L0–U2 |
| Monthly | Commercial | Pipeline by ladder tier (how many L1 vs L4 vs U0 conversations) |
| Quarterly | Counsel review | BAAs, DPIA updates, vendor terms, advertising claims scrub |
| Before live mode | Clinical governance | All readiness gates (incl. S6 habit) green |

**Revenue hypothesis (test, don’t claim):** charge for readiness + SafeLaunch +
subscription; charge HIS vendors only for optional L4 adapter certification,
never for “access to Epic.”

## 6. Claims discipline (Congress + sales)

Allowed: “We implement SMART/CDS Hooks standards; sandbox shipped; production
requires hospital registration.”

Forbidden until evidence: “Partnered with Epic,” “Listed in Showroom,”
“Approved for clinical use,” “Reduces mortality,” “Works without local validation.”

Evidence links: `/connection`, `/integration`, `/readiness`,
`docs/innovation-adoption-barriers.md`, this file.

## 7. Near-term actions (founder-owned)

1. Pick one Dhaka private ICU for L1/L2 design partner (CSV or HL7).
2. Offer local HIS vendors a one-page L4 adapter SOW + fixed fee.
3. For any US exploratory call: lead with U0 interface-engine, mention U1/U2 as
   standards path — do not promise gallery dates.
4. Keep soft-landing language in every pilot proposal: HIS stays system of record
   for registration/billing.
