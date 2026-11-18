# Auralis completion record

Status date: 2026-11-18 (working tree; not a production release claim).

### Verification snapshot (this session)
- Control-plane: **11 passed** (`test_partnership_domain` + commercial + enterprise governance)
- Frontend: `tsc --noEmit` clean; eslint 0 errors; **22 tests passed**; production build succeeded (Next.js security upgrade reminder still present on 16.4.2)
- Business/FDE ecosystem: consultation, opportunities, org/site profiles, FDE readiness, equipment, proposals, education events, partnership plans, public hospital pages, private business docs
- Reconciliation: `docs/architecture/business-ecosystem-reconciliation.md`
- **Not pushed** to GitHub or Docker Hub (awaiting explicit authorization)

Late explorers ([Explore Auralis IAM gaps](9c7e0c4a-6dc3-4942-9571-56253e4f8ec6), [Explore commercial clinical gaps](d748fb62-6545-4ebe-8453-dee84209427f)) partially predate this session’s IAM work. Treat rows below as authoritative over those reports where they conflict (permission registry, portal invites, clinical_it/viewer, approvals).

Legend: **Implemented** = code present · **Tested** = automated tests passing in this environment · **Runtime-verified** = exercised in a running container/process here · **External** = requires founder/hospital/counsel · **Not done** = remaining software work.

---

## 1. Identity and access

| Item | Status | Evidence / notes |
|---|---|---|
| Configurable permission registry (`control-plane/permissions.py`) | Implemented + Tested | Matrix endpoint `/v1/permissions/matrix`; role→permission map for vendor + customer |
| Per-organization customer roles | Implemented + Tested | `memberships.role`; cross-org isolation tests |
| Vendor account directory, disable/reactivate, session revoke | Implemented + Tested | Account service tests |
| Customer invitations (vendor + portal owner) | Implemented + Tested | Accept-invitation + portal invite tests; portal UI invite form |
| Approval workflow for customer role changes | Implemented + Tested | `/v1/vendor/approvals` |
| Hospital roles `clinical_it`, `clinical_viewer` | Implemented + Tested | Auth/accounts/schemas + route guards + `test_roles.py` + AppNav |
| HttpOnly browser session (replace client token storage) | Not done | Still bearer/localStorage pattern for hospital UI |
| Vendor staff site-level assignments | Not done | Vendor roles remain global within control plane |
| Break-glass time-limited elevation | Not done | MFA + reasons exist; no timed elevation API |
| Password recovery / session device list | Not done | Change-password and revoke-all-on-change exist |
| Email delivery of invitations | External | Tokens returned once; secure channel is operational |
| Hospital IdP production bind | External | OIDC config exists; hospital must supply IdP |

## 2. Commercial / customer / vendor workflows

| Item | Status | Evidence / notes |
|---|---|---|
| CRM leads, inquiries, contacts, assessments | Implemented + Tested | `commercial_domain` tests |
| Public consultation requests + vendor confirmation | Implemented + Tested | `partnership_domain`; pending ≠ booked; no live calendar |
| Hospital opportunity pipeline (16+ stages) | Implemented + Tested | Extends CRM; does not replace quotes/contracts |
| Org/site profiles + readiness tiers + relationship status | Implemented + Tested | Vendor partnership workspace; customer sees redacted profile |
| FDE projects + readiness passport checklist | Implemented + Tested | Explicit states; no invented score |
| Equipment records + draft proposals + education events + internal partnership plans | Implemented + Tested | Empty-state safe; pricing assumptions internal-only |
| Quotes, revisions, contracts, licences, invoices, payments, renewals | Implemented + Tested | Integer minor units; no payment gateway |
| Documents with encryption + approval | Implemented + Tested | Fernet + scanner hook; evaluation uses synthetic_clean |
| Support tickets, assets, compliance, training, offboarding | Implemented + Tested | operations + account tests |
| Customer portal member list + invite UI | Implemented | `CustomerWorkspace` → portal invitations API |
| Support SLA clock / escalation against tickets | Implemented + Tested | Plan `response_target_minutes` + severity caps; breach list; escalation level |
| Licence revoke/suspend + entitlement invalidation | Implemented + Tested | `/v1/vendor/licences/{id}/entitlement`; signed invalidation package; hospital `licensing.status` blocks new live eligibility only |
| Document retention/review lifecycle | Implemented + Tested | retention policy/until, review_on, archive/destroy (content wipe); legal_hold blocks destroy; e-signature provider still External |
| Asset lifecycle / warranty | Implemented + Tested | ordered→disposed transitions; warranty_expired flag |
| QMS/CAPA/incident library | Implemented + Tested | `capa_records` + `qms_findings` with link/close evidence rules |
| Live bank/payment gateway | Not done (by design) | Manual verification records only |
| Legally binding contract language | External | Draft refs only |
| Auto-renewal commercial linkage | Partial | Renewals exist; not auto-tied to entitlement clocks |
| Qualified e-signature provider | External | Approval reason recorded; not a signature service |

## 3. Hospital clinical workspace

| Item | Status | Evidence / notes |
|---|---|---|
| ICU board, patient chart, alerts, handoff, TrustGate, provenance | Implemented | Existing hospital API/UI |
| Shift roster / staff / profile / PWA hooks | Implemented | Prior hospital UI work |
| Role-specific nav for clinical_it / clinical_viewer | Implemented | `SurfaceFrame` / `WorkspaceShell` role link sets + CLINICAL_READ / CLINICAL_IT route guards |
| Frozen model + inference unchanged | Preserved | Do not rescore Dataset B; frozen SHA discipline remains |
| Live hospital HIS data | External | Replay/PhysioNet or synthetic only until partnership |

## 4. Commissioning / runtime

| Item | Status | Evidence / notes |
|---|---|---|
| Docker compose files (site, evaluation, accounts, public demo) | Implemented | Compose present |
| ClamAV live scan in this environment | Runtime-verified | `docker-compose.accounts-standalone.yml`: accounts healthy on `:8101`, clamd PONG, vendor login, permission matrix (61 permissions), PDF upload returned draft document with sha256 after live scanner path |
| Evaluation isolation | Implemented + Tested | EVALUATION_RUNTIME guards |
| Offline clinical plane design | Implemented | Local auth/API/model; hospital network proof is External |
| Backup/restore drill on hospital storage | External | Scripts/docs ≠ hospital drill |
| Licence bed-band governance without blocking admission | Implemented + Tested | revoke/suspend invalidate new live eligibility only; running bedside never interrupted by control-plane entitlement APIs |

## 5. Integration / validation readiness

| Item | Status | Evidence / notes |
|---|---|---|
| FHIR/HL7 connectors, quarantine, mapping copilot | Implemented | Hospital integration routes |
| Synthetic evaluation generator | Implemented + Tested | `demo/generate_synthetic_eval.py` |
| Clinical validation on hospital data | External | See `REAL_WORLD_ACTION_PLAN.md` |
| Regulatory approval | External | Never claim from repo alone |

## 6. Frontend product surfaces (redesign)

| Surface | Status | Routes / components |
|---|---|---|
| Design system | Implemented + Tested | Manrope + Inter; tokens `#F7F8F6/#FFFFFF/#142832/#64747B/#087E83/#075F65/#DCE5E3/#EEF3F1`; `globals.css` + `tailwind.config.js` + `components/ui.tsx` |
| Public marketing website | Implemented + Build | `PublicHeader` / `PublicFooter`; `/`, `/product`, `/aurie`, `/solutions`, `/for-hospitals`, `/deployment-integration`, `/security`, `/resources`, `/about`, `/contact` (+ prior docs/evidence/model pages) |
| Central sign-in + workspace connector | Implemented + Build | `/signin` / `/login`: auth form + Choose Your Workspace destinations (hospital, vendor, deployment, customer, evaluation) |
| Hospital Workspace | Implemented + Build | Role-specific sidebar via `SurfaceFrame` (admin / doctor-nurse clinical / clinical_it / clinical_viewer) |
| Vendor Control Plane | Implemented + Build | `/platform/*` shell; accounts/commercial/service/documents headers reskinned |
| Hospital Deployment Console | Implemented + Build | `/deploy` home + `/app/admin/*` surface shell; access limited in UI to admin / clinical_it / operator |
| Customer Portal | Implemented + Build | `/portal*` customer shell; organization / commercial / service / documents |
| Evaluation Environment | Implemented + Build | Evaluation shell + synthetic labelling; `/system-check` gate |
| User-facing “Demo” copy | Implemented + Tested | Replaced with Evaluation Environment / evaluation replay language; API mode value `demo` preserved |

Outstanding frontend gaps: deeper per-screen visual polish on every legacy clinical panel; HttpOnly session migration; optional Next.js security upgrade (see verification note).

## 7. Competition honesty boundary

Congress-style criteria (innovation, architecture, commercial, scale/impact, responsible AI) can be **demonstrated with software + labelled evaluation data**. They are **not** earned by claiming BD ICU outcome improvement or regulatory clearance without External rows above.

Primary founder doc for external work: [`REAL_WORLD_ACTION_PLAN.md`](../../REAL_WORLD_ACTION_PLAN.md).
