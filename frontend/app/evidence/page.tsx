"use client";

import Link from "next/link";
import { ApiError, KeyValue, Panel, Pill, Stat } from "@/components/ui";
import { api } from "@/lib/api";
import { humanize } from "@/lib/pilot";
import { useSession } from "@/lib/session";
import { usePoll } from "@/lib/usePoll";

type Ready = {
  status: string;
  checks: Record<string, boolean>;
  site_mode: string;
  model_version: string;
  model_hash: string;
};

type ModelInfo = {
  model_version: string;
  frozen: boolean;
  model_hash: string;
  cpu_latency_ms_per_prediction?: number;
  holdout_dataset_b?: { auroc?: number; auprc?: number } | null;
};

type OpsStatus = {
  scale: {
    api_encounters: number;
    replay_encounters: number;
    audit_events: number;
    snapshot_last_persist_ms: number | null;
    snapshot_kb_written_total: number;
  };
  audit: { events_verified: number; linkage_valid: boolean; content_hash_mismatches: number };
  database: { healthy: boolean; dialect: string };
};

const CRITERIA: Array<{
  name: string;
  claim: string;
  proof: Array<[string, string]>;
  measured: string;
  status: "Measured" | "Built" | "External proof pending";
  gap: string;
}> = [
  {
    name: "Innovation",
    claim: "Sepsis ML is missing from hospitals because of EHR lock-in and unsafe transfer — not missing math. PredictRx unlocks both: a Connection Ladder (paper→HL7/FHIR→SMART) that keeps our IP out of the EHR vendor, and a Transfer Shield that blocks alerts until local calibration and measurement habits clear.",
    proof: [["/connection", "Connection & Transfer Shield"], ["/presentation", "Replay"], ["/icu", "TrustGate board"]],
    measured: "L0–L3+U0 shipped with conformance; L4 adapter contract + U1/U2 SMART/CDS path specified; Transfer Shield S1–S8 named; international pathway timeline documented.",
    status: "Built",
    gap: "Epic Showroom listing is commercial roadmap — not claimed live today.",
  },
  {
    name: "Technical execution",
    claim: "Six connector paths converge on one audited observation contract before a frozen, hash-verified model scores past-only data.",
    proof: [["/integration", "Integration hub"], ["/operations", "Operations console"], ["/api-reference", "Integration API"]],
    measured: "147 backend tests; public E2E 50/50; connector conformance 6/6 (FHIR/HL7/CSV/JSON); failure injection 11/11; recovery drill with measured RTO; live-rate soak 3,600 obs / 0 errors; scale check 9,600 obs; shipped-image vuln rescan 0; SBOM + release manifest with rollback. Full dossier: docs/technical-production-evidence.md.",
    status: "Measured",
    gap: "Independent penetration test remains a hospital-stage engagement — not a prototype gap.",
  },
  {
    name: "Business & global readiness",
    claim: "Hospitals adopt in stages: readiness → integration → silent evaluation → governed alerting, on standards-based connectors.",
    proof: [["/readiness", "Readiness passport"], ["/admin/setup", "Site setup"], ["/docs", "Technical dossier"]],
    measured: "No customer, LOI or revenue is claimed. Pricing and procurement evidence are founder research in progress.",
    status: "External proof pending",
    gap: "Named buyer, budget owner, procurement route and written interest.",
  },
  {
    name: "Impact & ethical AI",
    claim: "A high-burden ICU problem, handled with abstention, human acknowledgement, subgroup disclosure and site-local data control.",
    proof: [["/pilot", "Silent-pilot evidence"], ["/model", "Subgroups & limitations"], ["/patient/BED-06", "Patient-level explanation"]],
    measured: "Sourced burden (49.2% severe-sepsis mortality in 14 BD ICUs; 1.8 ICU beds/100k); Dataset B retrospective AUROC 0.808, AUPRC 0.079, calibration slope 0.80, subgroup gaps >10 pp disclosed; KPI contract defined with pilot targets labelled unachieved. No outcome or lives-saved claim is made.",
    status: "Measured",
    gap: "Bangladesh validation and locally measured workflow KPIs require a hospital partner.",
  },
  {
    name: "Scalability & collaboration",
    claim: "Each hospital is an isolated data plane; the vendor sees only signed, patient-free fleet metadata, so sites scale without centralising patient records.",
    proof: [["/fleet", "Fleet console"], ["/operations", "Scale & lease status"], ["/docs", "Deployment section"]],
    measured: "Two scale axes documented: one-hospital capacity (scale + soak measured) and multi-hospital isolation (patient-free heartbeats). Enrolment + canary→cohort→fleet release rings documented. Global corroboration dossier cites Duke silent periods, TREWS, FDA GMLP, WHO, on-prem PHI practice. CONTRIBUTING + NRB invitation pack ready for remote builders today.",
    status: "Measured",
    gap: "A named NRB person would strengthen collaboration optics; readiness and published global alignment are already shipped without fabricating one.",
  },
];

const COMPARISON: Array<[string, string, string, string]> = [
  ["Score on incomplete data", "Usually shown anyway", "Shown with a confidence number", "Verify data or Abstain until required signals are fresh"],
  ["Unknown codes / wrong units", "Often silently dropped", "Often silently dropped", "Quarantined with provenance; never guessed into the model"],
  ["Alert authority", "Configured on", "Configured on", "Software-gated by nine local readiness gates; silent first"],
  ["Model change on site", "Vendor update", "Possible retraining", "Frozen artefact, SHA-256 verified at start-up; no on-site tuning"],
  ["Vendor access", "Central patient database", "Central patient database", "Hospital-local data; vendor receives signed metadata only"],
  ["Failure evidence", "Best cases", "Best cases", "Missed detection and false-alert cases are part of the evaluation evidence"],
];

export default function EvidencePage() {
  const { me, isAdmin, isOperator } = useSession();
  const ready = usePoll(() => api<Ready>("/ready"), 20000);
  const model = usePoll(() => api<ModelInfo>("/v1/model"), 30000);
  const ops = usePoll(
    () => (isAdmin || isOperator ? api<OpsStatus>("/v1/ops/status") : Promise.resolve(null)),
    30000,
    [isAdmin, isOperator],
  );

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <header className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">Evidence centre</p>
        <h1 className="font-display text-4xl">Every claim, its proof, and what is still missing.</h1>
        <p className="max-w-3xl text-ink/65">
          Auralis is a hospital-local ICU intelligence layer that must earn the right to alert.
          This page separates what is built, what has been measured, and what still requires external proof —
          so nothing here needs to be taken on trust.
        </p>
      </header>

      {(ready.error || model.error) && <ApiError error={(ready.error ?? model.error) as Error} />}

      <div className="flex flex-wrap gap-3">
        <Stat label="Site mode" value={ready.data ? humanize(ready.data.site_mode) : "…"} />
        <Stat label="Model frozen" value={model.data ? (model.data.frozen ? "Yes" : "No") : "…"} />
        <Stat
          label="Audit events"
          value={ops.data ? ops.data.audit.events_verified.toLocaleString() : "—"}
        />
        <Stat
          label="Audit chain"
          value={ops.data ? (ops.data.audit.linkage_valid && ops.data.audit.content_hash_mismatches === 0 ? "Valid" : "Broken") : "—"}
          color={ops.data && !(ops.data.audit.linkage_valid && ops.data.audit.content_hash_mismatches === 0) ? "text-risk-high" : "text-ink"}
        />
        <Stat label="Encounters (API)" value={ops.data ? ops.data.scale.api_encounters : "—"} />
        <Stat
          label="Last snapshot"
          value={ops.data?.scale.snapshot_last_persist_ms != null ? `${ops.data.scale.snapshot_last_persist_ms} ms` : "—"}
        />
      </div>

      {model.data && (
        <Panel title="Frozen model — verify it yourself">
          <dl>
            <KeyValue label="Model version" value={model.data.model_version} />
            <KeyValue label="SHA-256 (checked at start-up)" value={<code className="break-all text-xs">{model.data.model_hash}</code>} />
            <KeyValue
              label="Dataset B retrospective"
              value={
                model.data.holdout_dataset_b
                  ? `AUROC ${model.data.holdout_dataset_b.auroc ?? "—"} · AUPRC ${model.data.holdout_dataset_b.auprc ?? "—"}`
                  : "see Model transparency"
              }
            />
            <KeyValue label="CPU latency / prediction" value={model.data.cpu_latency_ms_per_prediction ? `≈ ${model.data.cpu_latency_ms_per_prediction} ms` : "—"} />
          </dl>
          <p className="mt-3 text-sm text-ink/60">
            Dataset B is a geographically distinct public cohort scored once after freezing. It is retrospective
            evidence, not Bangladesh validation and not proof of clinical benefit.
          </p>
        </Panel>
      )}

      <section className="space-y-4">
        <h2 className="font-display text-2xl">Judging criteria — claim → proof → measurement → gap</h2>
        {CRITERIA.map((item) => (
          <Panel key={item.name} title={item.name}>
            <div className="space-y-3 text-sm">
              <p><strong>Claim.</strong> {item.claim}</p>
              <p>
                <strong>Live proof.</strong>{" "}
                {item.proof.map(([href, label], index) => (
                  <span key={href}>
                    {index > 0 && " · "}
                    <Link href={href} className="font-medium text-accent underline">{label}</Link>
                  </span>
                ))}
              </p>
              <p><strong>Measured.</strong> {item.measured}</p>
              <p className="flex flex-wrap items-center gap-2">
                <Pill tone={item.status === "Measured" ? "success" : item.status === "Built" ? "info" : "warning"}>{item.status}</Pill>
                <span className="text-ink/60"><strong>Still missing:</strong> {item.gap}</span>
              </p>
            </div>
          </Panel>
        ))}
      </section>

      <Panel title="Why this is not a score-only dashboard">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="text-ink/50">
              <tr>
                <th className="py-2 pr-3">Situation</th>
                <th className="py-2 pr-3">Rule-based EHR alert</th>
                <th className="py-2 pr-3">Score-only ML</th>
                <th className="py-2">Auralis</th>
              </tr>
            </thead>
            <tbody>
              {COMPARISON.map(([situation, rule, scoreOnly, ours]) => (
                <tr key={situation} className="border-t border-ink/5 align-top">
                  <td className="py-2 pr-3 font-medium">{situation}</td>
                  <td className="py-2 pr-3 text-ink/65">{rule}</td>
                  <td className="py-2 pr-3 text-ink/65">{scoreOnly}</td>
                  <td className="py-2 text-ink/85">{ours}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs text-ink/50">
          Generic archetypes for mechanism comparison — not claims about any named product.
        </p>
      </Panel>

      <section className="space-y-4">
        <h2 className="font-display text-2xl">Impact &amp; ethics — the sourced case</h2>
        <div className="flex flex-wrap gap-3">
          <Stat label="Sepsis cases / deaths, 2017 (global)" value="48.9M / 11.0M" />
          <Stat label="Of all deaths worldwide" value="19.7%" />
          <Stat label="Severe-sepsis mortality, 14 BD ICUs" value="49.2%" />
          <Stat label="Critical-care beds per 100k (BD)" value="1.8" />
          <Stat label="Survival lost per hour of antibiotic delay (shock)" value="≈7.6%" />
        </div>
        <p className="text-xs text-ink/50">
          Sources: Rudd et al., The Lancet 2020 (GBD); Bangladesh Crit Care J 2013 (complete bundle compliance was zero);
          Lancet Regional Health – Western Pacific 2023 and BCCJ 2022 (2,177 ICU beds; 38 of 64 districts have none);
          Kumar et al., Critical Care Medicine 2006. Full dossier: <code>docs/impact-evidence.md</code>.
        </p>

        <Panel title="Why the field's own evidence shaped this design">
          <div className="space-y-3 text-sm text-ink/80">
            <p>
              <strong>The failure mode.</strong> The proprietary Epic Sepsis Model, deployed in hundreds of US
              hospitals, externally validated at AUROC 0.63: it alerted on 18% of hospitalizations, missed 67% of
              sepsis cases, and had a positive predictive value of 12% (Wong et al., JAMA Internal Medicine 2021).
              Clinicians override 49–96% of computerised safety alerts (van der Sijs 2006). Unvalidated,
              unexplained alerting at scale is itself a patient-safety hazard.
            </p>
            <p>
              <strong>The plausible benefit.</strong> In the prospective five-hospital TREWS study, alert
              confirmation within 3 hours was associated with 3.34 percentage points lower adjusted mortality
              and antibiotics 1.85 hours faster (Adams et al., Nature Medicine 2022 — observational, not an RCT).
              PredictRx claims none of that effect: it is the reason the product measures review time first, and
              why alerting stays off until a site has silently proven its own data and workflow.
            </p>
            <p>
              <strong>Our measured position.</strong> On a geographically distinct public cohort scored once after
              freezing: AUROC 0.808 with 2.05 false alerts per 100 patient-hours and hour-level specificity 0.839 —
              reported with calibration slope 0.80 (local recalibration mandatory), subgroup sensitivity gaps
              above 10 percentage points disclosed rather than hidden, and TrustGate&apos;s false-alert benefit
              explicitly not established (paired confidence interval crosses zero).
            </p>
          </div>
        </Panel>

        <Panel title="The KPI contract — benefit must appear here before any outcome claim">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead className="text-ink/50">
                <tr>
                  <th className="py-2 pr-3">KPI</th>
                  <th className="py-2 pr-3">Measured in the product</th>
                  <th className="py-2">Pilot target (not yet achieved)</th>
                </tr>
              </thead>
              <tbody>
                {[
                  ["Feed coverage", "TrustGate freshness per bed", "≥95% of occupied beds fresh"],
                  ["Quarantine rate", "Integration hub quarantine queue", "Falling trend to <2% of observations"],
                  ["Alert burden", "Shadow alerts per 100 patient-hours", "No worse than replay baseline (2.05 false alerts)"],
                  ["Review responsiveness", "Alert → acknowledged time in the audit chain", "Median ≤30 min (TREWS window: 3 h)"],
                  ["Override discipline", "Dismissals require a recorded reason", "100% reasoned; rising overrides trigger gate review"],
                  ["Subgroup parity", "Sensitivity by sex, age, unit, missingness", "No subgroup >10 pp below overall without a governance decision"],
                ].map(([kpi, how, target]) => (
                  <tr key={kpi} className="border-t border-ink/5 align-top">
                    <td className="py-2 pr-3 font-medium">{kpi}</td>
                    <td className="py-2 pr-3 text-ink/65">{how}</td>
                    <td className="py-2 text-ink/85">{target}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs text-ink/50">
            Mortality, length of stay and cost are recorded during a pilot as outcomes under study — never as
            marketing claims. Safeguards are mapped to WHO&apos;s six AI-in-health ethics principles (2021) in
            the dossier; alignment is claimed, certification is not.
          </p>
        </Panel>

        <Panel title="Fairness, audited from the scored artefacts (Dataset B holdout)">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead className="text-ink/50">
                <tr>
                  <th className="py-2 pr-3">Dimension</th>
                  <th className="py-2 pr-3">Subgroup sensitivities (high-risk band)</th>
                  <th className="py-2 pr-3">Gap</th>
                  <th className="py-2">Weakest group</th>
                </tr>
              </thead>
              <tbody>
                {[
                  ["Sex", "Female 0.352 · Male 0.326", "2.6 pp", "Male"],
                  ["Age", "18–44: 0.316 · 45–64: 0.330 · 65–79: 0.381 · 80+: 0.258", "12.3 pp", "80+"],
                  ["ICU type", "MICU 0.264 · SICU 0.384 · Unknown 0.360", "12.0 pp", "MICU"],
                  ["Missingness", "Low 0.371 · Medium 0.281 · High 0.295", "9.0 pp", "Medium"],
                ].map(([dim, values, gap, weakest]) => (
                  <tr key={dim} className="border-t border-ink/5 align-top">
                    <td className="py-2 pr-3 font-medium">{dim}</td>
                    <td className="py-2 pr-3 text-ink/65">{values}</td>
                    <td className="py-2 pr-3 text-ink/85">{gap}</td>
                    <td className="py-2 text-ink/85">{weakest}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-sm text-ink/70">
            Pre-committed rule: in a local pilot, any subgroup more than 10 percentage points below overall keeps
            interruptive alerting off for that pathway until the site&apos;s owners record a governance decision.
            On Dataset A validation the system also declined to present a confident actionable score in 11.6% of
            eligible hours (Verify data / Abstain) — abstention is measured behaviour, not a slogan. Full audit:
            <code> docs/evidence/fairness-audit.md</code>.
          </p>
        </Panel>

        <Panel title="Global corroboration — independent published alignment (NRB-smart path)">
          <div className="space-y-3 text-sm text-ink/80">
            <p>
              We do not invent a named reviewer. Independent work already converges on this design:
              Wong et al. (JAMA 2021) showed unvalidated score-only sepsis alerts fail in the field;
              Sendak et al. (JMIR 2020) and Tonekaboni et al. (2022) established silent/shadow evaluation
              before live alerts; Adams/Henry (Nature Medicine 2022) showed clinician engagement is the
              mechanism of benefit; FDA GMLP asks for Human–AI team performance and local site acceptance;
              on-premise clinical AI pilots keep PHI inside the hospital perimeter.
            </p>
            <p>
              PredictRx productises that consensus: silent-first gates, hospital-local data plane,
              patient-free fleet heartbeats, frozen hash-verified model. Remote builders join via{" "}
              <code>CONTRIBUTING.md</code>; the invitation pack is in{" "}
              <code>docs/nrb-global-builder-pack.md</code>. Full citations:{" "}
              <code>docs/global-corroboration.md</code>.
            </p>
          </div>
        </Panel>

        <Panel title="International hospitals already ran this pathway — timeline that validates ours">
          <p className="mb-3 text-sm text-ink/70">
            Pathway validation only: PredictRx is not installed at these sites. The table shows that continuous
            feeds, mapping, silent evaluation and human-gated alerts are how careful deployments actually worked —
            and that wide deploy without local proof (Epic ESM) is the failure mode we gate against.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="text-ink/50">
                <tr>
                  <th className="py-2 pr-3">When</th>
                  <th className="py-2 pr-3">System / place</th>
                  <th className="py-2 pr-3">How they connected</th>
                  <th className="py-2">PredictRx equivalent</th>
                </tr>
              </thead>
              <tbody>
                {[
                  [
                    "5 Nov 2018",
                    "Duke Sepsis Watch — ED go-live after 3-month silent period",
                    "Epic web services every 5 min → on-prem DB → model → RRT web app",
                    "Silent mode + readiness gates; FHIR/HL7/CSV connectors; hospital-local plane",
                  ],
                  [
                    "2018–2019",
                    "Duke Health — scaled to all 3 system EDs",
                    "Same Epic pull; nurse-verified EHR data; tablet workflow",
                    "Per-site install; role-scoped alerts with ownership",
                  ],
                  [
                    "2018–2020",
                    "TREWS — 5 hospitals, 590k encounters (Nature Medicine 2022)",
                    "EHR-native non-interruptive alert → dashboard → confirm/dismiss",
                    "Acknowledge / dismiss-with-reason; engagement before benefit",
                  ],
                  [
                    "~2015–now",
                    "Epic Sepsis Model — hundreds of US hospitals",
                    "Built into Epic chart (no separate connector)",
                    "Cautionary: external AUROC 0.63 — why we freeze, disclose, and gate live alerts",
                  ],
                  [
                    "2022+",
                    "Multi-EHR commentary on TREWS",
                    "Authors flag FHIR / HL7 / SMART for dissimilar EHRs",
                    "Standards-first connectors + measured conformance 6/6",
                  ],
                ].map(([when, where, how, ours]) => (
                  <tr key={when + where} className="border-t border-ink/5 align-top">
                    <td className="py-2 pr-3 font-medium whitespace-nowrap">{when}</td>
                    <td className="py-2 pr-3 text-ink/85">{where}</td>
                    <td className="py-2 pr-3 text-ink/65">{how}</td>
                    <td className="py-2 text-ink/85">{ours}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs text-ink/50">
            Full timeline, connection patterns (A/B/C) and non-claims:{" "}
            <code>docs/international-deployment-validation.md</code>.
          </p>
        </Panel>

        <Panel title="What is at stake in one 20-bed Bangladeshi ICU (scenario, not a claim)">
          <div className="space-y-3 text-sm text-ink/80">
            <p>
              Under stated planning assumptions (5-day mean stay, 85% occupancy, 30% sepsis share, 48%
              mortality — bracketing the published Bangladeshi cohorts), one 20-bed ICU admits roughly{" "}
              <strong>1,240 patients a year, of whom ≈370 have sepsis and ≈180 die</strong>. A 6-day private
              sepsis stay at published all-in rates is roughly <strong>Tk 1.8–3.0 lakh</strong> out of pocket.
            </p>
            <p>
              Threshold framing only: <em>if</em> a local pilot reproduced even a 1-percentage-point absolute
              mortality reduction, that is ≈4 fewer deaths per ICU-year (≈400 nationally). If review times do
              not move in the silent pilot, none of this is in play — the gates keep alerting off, and that
              result gets published too. Model and sources: <code>docs/economic-scenario-model.md</code>.
            </p>
          </div>
        </Panel>
      </section>

      <Panel title="Boundaries we will not cross">
        <ul className="list-disc space-y-1 pl-5 text-sm text-ink/75">
          <li>No diagnosis, treatment or dosing output; the evidence copilot refuses those questions.</li>
          <li>No Bangladesh clinical validation, outcome improvement or lives-saved claim exists today.</li>
          <li>Public evaluation data is de-identified public replay plus disclosed synthetic commissioning data — never presented as a live hospital feed.</li>
          <li>The platform operator role cannot open patient pages; the vendor fleet console receives allowlisted, signed metadata only.</li>
          <li>Interruptive alerts stay off until all ten readiness gates pass at a real site.</li>
          {!me && <li>Sign in (Session) as Hospital admin or Platform operator to see live operations counters on this page.</li>}
        </ul>
      </Panel>
    </div>
  );
}
