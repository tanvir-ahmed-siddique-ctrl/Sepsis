"use client";

import type { ReactNode } from "react";
import { Panel, Pill } from "@/components/ui";
import { api } from "@/lib/api";
import { humanize } from "@/lib/pilot";
import { usePoll } from "@/lib/usePoll";

type Ready = {
  status: string;
  checks: Record<string, boolean>;
  site_mode: string;
  model_version: string;
  model_hash: string;
};

const SECTIONS = [
  ["problem", "Problem"],
  ["solution", "Solution"],
  ["architecture", "Architecture"],
  ["ai", "AI core"],
  ["evidence", "Evidence"],
  ["safety", "Responsible AI"],
  ["deployment", "Deployment & roles"],
  ["business", "Business model"],
  ["scale", "Scale & standards"],
  ["roadmap", "Roadmap & ask"],
] as const;

const PIPELINE = [
  ["Connect", "FHIR R4, HL7 v2 ORU/ADT, lab CSV, native API, MLLP edge relay, offline bedside charting"],
  ["Validate", "Versioned LOINC/unit registry, range checks, quarantine, idempotency, late-data revision"],
  ["Represent", "Past-only 24-hour trends, freshness, missingness, ratios and organ-context features"],
  ["Predict", "Frozen LightGBM Run 4, calibrated, hash-verified at start-up"],
  ["Explain", "TreeSHAP drivers in plain language; cited guideline context that refuses treatment queries"],
  ["Govern", "TrustGate: Alert, Watch, Verify data or Abstain; site gates keep alerts off until evidence passes"],
];

const AI_STACK = [
  ["Sepsis-risk model", "LightGBM gradient boosting on temporal features", "Ranks 6-hour deterioration risk", "Frozen; selected against rule and logistic baselines; neural and graph challengers rejected"],
  ["Explainability", "TreeSHAP + organ-system knowledge graph", "Shows what moved the score", "Associative, never causal"],
  ["TrustGate", "Coverage, input-shift, perturbation stability, disagreement", "Decides whether a score may be shown", "False-alert benefit not yet established"],
  ["Mapping copilot", "Keyword + vector hybrid retrieval (Qwen3 embeddings, rank fusion) + on-premises Qwen 3.5 4B choice, JSON-schema output", "Proposes local-code → LOINC mappings, incl. Bangla and BD lab terms; 37-case internal benchmark: recall@5 68% → 90%, top-1 with Qwen 55% → 68%, 6/6 unknown concepts abstained", "Proposal only; human sign-off bound to registry SHA"],
  ["Patient context policy", "Physician-documented conditions and goals of care, versioned deterministic rules", "Flags chronic-baseline drivers, possible under-calling, out-of-scope populations", "Never edits the score; entries expire"],
  ["Evidence retrieval", "Versioned guideline registry, lexical retrieval with citations", "Context for review", "Refuses dosing/treatment questions"],
  ["MCP server", "Model Context Protocol, 8 read-only tools", "Lets AI assistants inspect site health and readiness", "Operator role: no patient data"],
];

const SAFEGUARDS = [
  "Interruptive alerts disabled until nine readiness gates pass",
  "Silent mode blinds bedside users to scores during local evaluation",
  "Abstain and Verify-data states instead of forcing a number",
  "Frozen model and thresholds; no tuning on site data",
  "Hash-chained audit log of every prediction, action and correction",
  "Role separation: doctor, nurse, hospital admin, metadata-only platform operator",
  "Pseudonymised research exports with salted identifiers",
  "Subgroup and failure-case reporting, including missed detections",
  "Copilot refuses identifier-like input; LLM answers outside retrieved candidates are discarded",
  "Ward NEWS2 kept separate from ICU machine learning",
  "Comfort care and out-of-scope populations keep alerts shadow-only; suppression lapses at the review deadline",
  "Fleet heartbeat is allowlisted, HMAC-signed and patient-free",
];

function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section id={id} className="scroll-mt-20 space-y-3">
      <h2 className="font-display text-2xl">{title}</h2>
      {children}
    </section>
  );
}

export default function DocsPage() {
  const ready = usePoll(() => api<Ready>("/ready"), 15000);

  return (
    <div className="grid gap-8 lg:grid-cols-[12rem_1fr]">
      <nav aria-label="Documentation sections" className="hidden lg:block">
        <ul className="sticky top-6 space-y-1 text-sm">
          {SECTIONS.map(([id, label]) => (
            <li key={id}><a className="text-ink/60 hover:text-ink" href={`#${id}`}>{label}</a></li>
          ))}
        </ul>
      </nav>

      <div className="space-y-10">
        <header className="space-y-3">
          <p className="text-xs uppercase tracking-[0.2em] text-accent">PredictRx Sentinel · technical whitepaper & live status</p>
          <h1 className="font-display text-4xl">Earn the right to alert.</h1>
          <p className="max-w-3xl text-lg text-ink/65">
            A hospital-local ICU workflow and data-quality layer that connects fragmented data, exposes uncertainty, can
            abstain, and lets each hospital earn the right to show an AI alert through local evidence and governance gates.
          </p>
          <p className="text-xs text-ink/50">
            Research prototype. Not approved for clinical use. Not validated on Bangladeshi patients.
          </p>
        </header>

        <Panel title="Live system status">
          {ready.error && <p className="text-sm text-risk-high">API unreachable: {ready.error.message}</p>}
          {ready.data && (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <Pill tone={ready.data.status === "ready" ? "success" : "danger"}>{humanize(ready.data.status)}</Pill>
                <span>Site mode: <strong>{humanize(ready.data.site_mode)}</strong></span>
                <span>Model: <strong>{ready.data.model_version}</strong></span>
                <code className="text-xs text-ink/55">SHA-256 {ready.data.model_hash.slice(0, 16)}…</code>
              </div>
              <div className="flex flex-wrap gap-2">
                {Object.entries(ready.data.checks).map(([check, passed]) => (
                  <Pill key={check} tone={passed ? "success" : "danger"}>{humanize(check)}</Pill>
                ))}
              </div>
            </div>
          )}
          {!ready.data && !ready.error && <p className="text-sm text-ink/55">Checking live API…</p>}
        </Panel>

        <Section id="problem" title="Problem">
          <p className="max-w-3xl text-sm text-ink/70">
            Bangladesh&apos;s government ICU capacity is limited and concentrated: the DGHS January 2024 facility table lists
            778 ICU beds across the reporting public hospitals, and reporting citing DGHS places 55% of public ICU beds in
            Dhaka. Published Bangladesh ICU cohorts have reported sepsis mortality near 47–49%. ICU data is split across
            paper charts, monitors, lab systems and HIS screens, so deterioration signals arrive late, incomplete or
            unit-inconsistent—and AI trained elsewhere can fail silently on that data.
          </p>
          <p className="text-xs text-ink/50">
            Context sources: DGHS ICU/CCU/HDU inventory (2024); Bangladesh Critical Care Journal 14-ICU cohort; Rajshahi
            Medical College ICU cohort; BIRDEM SOFA cohort. These describe need, not PredictRx performance.
          </p>
        </Section>

        <Section id="solution" title="Solution">
          <div className="grid gap-px overflow-hidden border border-ink/10 bg-ink/10 sm:grid-cols-2 lg:grid-cols-3">
            {PIPELINE.map(([step, detail], index) => (
              <div key={step} className="bg-paper p-4">
                <p className="font-medium">{index + 1} · {step}</p>
                <p className="mt-1 text-sm text-ink/60">{detail}</p>
              </div>
            ))}
          </div>
        </Section>

        <Section id="architecture" title="Architecture">
          <ul className="max-w-3xl list-disc space-y-1 pl-5 text-sm text-ink/70">
            <li><strong>Hospital data plane (on-premises):</strong> Next.js web app, FastAPI service, PostgreSQL, edge MLLP relay; runs offline on CPU.</li>
            <li><strong>Canonical semantics:</strong> every connector maps into one encounter-scoped observation contract with provenance.</li>
            <li><strong>Inference:</strong> past-only features shared by training and serving code; model and registry hashes verified at start-up.</li>
            <li><strong>Operations:</strong> Prometheus metrics, health/readiness probes, backup/restore, single-writer lease, hash-chained audit.</li>
            <li><strong>Control plane:</strong> each site pushes an outbound, HMAC-signed heartbeat (release, model hash, gates, feed health, counts); the vendor fleet console rejects any non-allowlisted field, so patient records never leave the hospital.</li>
          </ul>
        </Section>

        <Section id="ai" title="AI core — what each component does and does not do">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-ink/10 text-xs uppercase text-ink/50">
                <tr><th className="py-2 pr-3">Component</th><th className="pr-3">Technique</th><th className="pr-3">Role</th><th>Boundary</th></tr>
              </thead>
              <tbody>
                {AI_STACK.map(([name, technique, role, boundary]) => (
                  <tr key={name} className="border-b border-ink/5 align-top">
                    <td className="py-2 pr-3 font-medium">{name}</td>
                    <td className="pr-3 text-ink/70">{technique}</td>
                    <td className="pr-3 text-ink/70">{role}</td>
                    <td className="text-ink/55">{boundary}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-ink/55">
            Model selection rewarded evidence, not complexity: GRU-D, causal TCN, organ-graph and residual-hazard
            challengers failed the preregistered utility gate and were rejected. See the Model transparency page.
          </p>
        </Section>

        <Section id="evidence" title="Evidence">
          <div className="grid gap-3 sm:grid-cols-3">
            {[
              ["0.808", "Dataset B held-out retrospective AUROC"],
              ["40,336", "public ICU stays (PhysioNet/CinC 2019)"],
              ["9", "readiness gates before any live alert"],
            ].map(([value, label]) => (
              <div key={label} className="border border-ink/10 bg-white/90 p-4 text-center">
                <p className="font-display text-3xl text-accent">{value}</p>
                <p className="mt-1 text-xs text-ink/55">{label}</p>
              </div>
            ))}
          </div>
          <p className="max-w-3xl text-sm text-ink/70">
            Retrospective results on US ICU data do not transfer automatically. Measurement-pattern features alone reach
            about 89% of the full model&apos;s cross-validated utility, which is why local validation, silent operation and
            site gates are product features rather than paperwork.
          </p>
        </Section>

        <Section id="safety" title="Responsible AI safeguards">
          <ul className="grid gap-2 text-sm sm:grid-cols-2">
            {SAFEGUARDS.map((item) => <li key={item} className="border-l-2 border-accent pl-3 text-ink/70">{item}</li>)}
          </ul>
        </Section>

        <Section id="deployment" title="Deployment and roles">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["Doctor", "Patient list, chart, risk explanation, alert acknowledgement, outcome adjudication"],
              ["Nurse", "Charting, observations, handoff, ward NEWS2, bed and ownership workflow"],
              ["Hospital admin", "Users and roles, units and beds, integrations, mapping sign-off, site mode"],
              ["Platform operator", "Health, feeds, readiness gates and model provenance — no patient data"],
            ].map(([role, scope]) => (
              <div key={role} className="border border-ink/10 bg-white/90 p-4">
                <p className="font-medium">{role}</p>
                <p className="mt-1 text-sm text-ink/60">{scope}</p>
              </div>
            ))}
          </div>
          <p className="text-sm text-ink/70">
            Each hospital runs its own installation; identifiable data stays inside the hospital network. Hospital
            administrators create staff accounts. The vendor operates releases and monitoring through the operator role
            and approved metadata only.
          </p>
        </Section>

        <Section id="business" title="Business model">
          <ol className="max-w-3xl list-decimal space-y-1 pl-5 text-sm text-ink/70">
            <li>Paid readiness and source-system assessment (no patient data required).</li>
            <li>Fixed-scope one-ICU SafeLaunch installation, integration and training.</li>
            <li>Recurring workflow, data-quality and research-operations subscription.</li>
            <li>Clinical alert module only after local evidence, institutional approval and regulatory review.</li>
          </ol>
          <p className="text-xs text-ink/50">
            Discovery pricing hypotheses (not quotations): pilot BDT 300k–1.2m; subscription BDT 75k–250k per site per month.
          </p>
        </Section>

        <Section id="scale" title="Scale and global readiness">
          <p className="max-w-3xl text-sm text-ink/70">
            Standards-first connectors (FHIR R4, HL7 v2, LOINC, IEEE 11073 relay) and Bangladesh Core FHIR alignment make
            mapping packs reusable across hospitals and countries. CPU-only inference and offline operation suit
            low-connectivity sites; Docker packaging, health probes and metrics support repeatable deployment.
          </p>
        </Section>

        <Section id="roadmap" title="Roadmap and ask">
          <ul className="max-w-3xl list-disc space-y-1 pl-5 text-sm text-ink/70">
            <li>Now: problem interviews and source-system inventories with Bangladesh hospitals.</li>
            <li>Next: one paid design partner; partner mapping acceptance; installation and restore drills.</li>
            <li>Then: retrospective local validation and approved silent operation with stop rules.</li>
            <li>Later: second site on the fleet console, signed updates with rollback, hospital-approved time-limited support access, independent security assessment.</li>
          </ul>
          <p className="text-sm font-medium">
            Ask: one Bangladesh hospital partner for a paid one-ICU readiness and workflow/research deployment, plus
            clinical-informatics and interoperability reviewers.
          </p>
        </Section>
      </div>
    </div>
  );
}
