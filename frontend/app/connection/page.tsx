"use client";

import Link from "next/link";
import { Panel, Pill, Stat } from "@/components/ui";

const LADDER: Array<{
  tier: string;
  name: string;
  region: string;
  how: string;
  status: "Shipped" | "Specified";
  href?: string;
}> = [
  { tier: "L0", name: "Bedside chart", region: "Any / paper wards", how: "Nurse enters vitals & labs in our chart UI (offline queue). HIS unchanged.", status: "Shipped", href: "/chart" },
  { tier: "L1", name: "Controlled file drop", region: "BD / LMIC HIS without APIs", how: "Shift/nightly CSV or Vendor Adapter JSON → lab/native ingest. Schema in docs/adapters/.", status: "Shipped", href: "/integration" },
  { tier: "L2", name: "HL7 v2 (ADT/ORU) + edge MLLP", region: "BD analyzers & US interface engines", how: "LIS/monitors already speak HL7 more often than FHIR. Edge relay on the LAN.", status: "Shipped", href: "/integration" },
  { tier: "L3", name: "FHIR R4 Bundle / NDJSON", region: "OpenMRS+, national HIE, modern HIS", how: "Standards path; unknown codes quarantined until human-signed mapping.", status: "Shipped", href: "/integration" },
  { tier: "L4", name: "Vendor Adapter Pack", region: "Proprietary HIS/LIS", how: "Hospital/vendor implements our minimal outbound contract — we never write their DB.", status: "Specified" },
  { tier: "L5", name: "Soft-landing sidecar", region: "HIS will not change", how: "PredictRx = ICU intelligence UI; HIS keeps registration/billing. Feed via L1–L3.", status: "Specified" },
  { tier: "U0", name: "Interface-engine pull", region: "US Epic/Cerner sites", how: "Duke-style: engine pushes HL7/FHIR to our on-prem API. Model stays ours.", status: "Shipped", href: "/integration" },
  { tier: "U1", name: "SMART on FHIR app", region: "Epic / Oracle Health", how: "In-chart launch via OAuth; we read FHIR, score locally. Listed as OUR app — not Epic’s model.", status: "Specified" },
  { tier: "U2", name: "CDS Hooks + Launch Card", region: "Epic ecosystem", how: "Event card in the EHR opens our SMART app. Epic is the shell; PredictRx keeps IP & revenue.", status: "Specified" },
];

const SHIELD: Array<[string, string, string]> = [
  ["S1 Freeze", "Model SHA-256 verified at start-up; no silent re-fit on site PHI", "Shipped"],
  ["S2 Quarantine", "Unknown codes, bad units, implausible values never score", "Shipped"],
  ["S3 Abstain", "Stale/missing required signals → Verify data or Abstain", "Shipped"],
  ["S4 Silent mirror", "Weeks of local scores + chart review before any interrupt", "Shipped"],
  ["S5 Calibration gate", "Local slope/threshold simulation required before live mode", "Shipped"],
  ["S6 Habit fingerprint", "Flag >2× shift in vital measurement cadence vs commissioning baseline", "Specified"],
  ["S7 Subgroup stop", ">10 pp sensitivity gap keeps that pathway off", "Shipped"],
  ["S8 Context policy", "Pregnancy/comfort care modulate alerts; never edit probability", "Shipped"],
];

const LAYERS = [
  ["1. Sources", "Monitors, LIS, HIS/OpenMRS, paper chart, or Epic/Cerner FHIR context"],
  ["2. Carry", "HL7 MLLP / FHIR / CSV / Vendor Adapter JSON / SMART token — never guess identity"],
  ["3. Validate", "Map codes & units, quarantine unknowns, idempotent late corrections"],
  ["4. Score", "Frozen Run 4 on hospital server only — past-only features"],
  ["5. Shield", "TrustGate + Transfer Shield (calibration & habit checks)"],
  ["6. Act", "Silent → nine readiness gates → human acknowledge/dismiss — then alert"],
];

export default function ConnectionPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <header className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">Innovation — adoption unlock</p>
        <h1 className="font-display text-4xl">Why sepsis ML is not everywhere — and how we unlock it.</h1>
        <p className="max-w-3xl text-ink/65">
          Two barriers stop hospitals: EHR/HIS lock-in, and unsafe transfer of a model trained elsewhere.
          PredictRx does not hand our model to Epic. We climb a Connection Ladder into whatever system the
          hospital already has, and we refuse to alert until Transfer Shield clears locally.
        </p>
      </header>

      <div className="flex flex-wrap gap-3">
        <Stat label="Ladder tiers" value="L0–L5 + U0–U2" />
        <Stat label="Connectors shipped" value="L0–L3, U0" />
        <Stat label="Transfer Shield layers" value="8" />
        <Stat label="Live alerts until gates" value="Blocked" />
      </div>

      <Panel title="Presentation spine — six layers from hospital data to governed alert">
        <ol className="space-y-2 text-sm">
          {LAYERS.map(([title, body], i) => (
            <li key={title} className="flex gap-3 border-t border-ink/5 py-2 first:border-0">
              <span className="font-display text-lg text-accent">{i + 1}</span>
              <div>
                <p className="font-medium">{title}</p>
                <p className="text-ink/65">{body}</p>
              </div>
            </li>
          ))}
        </ol>
      </Panel>

      <section className="space-y-4">
        <h2 className="font-display text-2xl">Barrier 1 — Connection Ladder (we keep the IP)</h2>
        <p className="text-sm text-ink/65">
          US Epic sites get AI easily when it is Epic’s built-in model — that makes the hospital dependent and
          leaves nothing for an independent company. Our answer: sell PredictRx to the hospital; use SMART on FHIR
          / CDS Hooks or an interface-engine feed so Epic is only the shell. Bangladesh / LMIC sites often lack one
          EHR — they get the same ladder from paper chart up through HL7/FHIR and a Vendor Adapter Pack.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="text-ink/50">
              <tr>
                <th className="py-2 pr-3">Tier</th>
                <th className="py-2 pr-3">Name</th>
                <th className="py-2 pr-3">Where</th>
                <th className="py-2 pr-3">How data enters</th>
                <th className="py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {LADDER.map((row) => (
                <tr key={row.tier} className="border-t border-ink/5 align-top">
                  <td className="py-2 pr-3 font-mono text-xs">{row.tier}</td>
                  <td className="py-2 pr-3 font-medium">
                    {row.href ? (
                      <Link href={row.href} className="text-accent underline">
                        {row.name}
                      </Link>
                    ) : (
                      row.name
                    )}
                  </td>
                  <td className="py-2 pr-3 text-ink/65">{row.region}</td>
                  <td className="py-2 pr-3 text-ink/80">{row.how}</td>
                  <td className="py-2">
                    <Pill tone={row.status === "Shipped" ? "success" : "info"}>{row.status}</Pill>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="font-display text-2xl">Barrier 2 — Transfer Shield (calibration & measurement habits)</h2>
        <p className="text-sm text-ink/65">
          Another hospital’s AUROC can fail here because case-mix changes calibration (our Dataset B slope is
          already 0.80) and because much of the model’s signal is measurement habit — how often vitals are charted.
          Transfer Shield makes mismatch visible and blocking; it does not quietly retrain on live PHI.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="text-ink/50">
              <tr>
                <th className="py-2 pr-3">Layer</th>
                <th className="py-2 pr-3">Control</th>
                <th className="py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {SHIELD.map(([id, control, status]) => (
                <tr key={id} className="border-t border-ink/5 align-top">
                  <td className="py-2 pr-3 font-mono text-xs">{id}</td>
                  <td className="py-2 pr-3 text-ink/80">{control}</td>
                  <td className="py-2">
                    <Pill tone={status === "Shipped" ? "success" : "info"}>{status}</Pill>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-sm text-ink/60">
          Live proof: <Link href="/pilot" className="text-accent underline">Silent pilot</Link>
          {" · "}
          <Link href="/readiness" className="text-accent underline">Readiness gates</Link>
          {" · "}
          <Link href="/model" className="text-accent underline">Model card / subgroups</Link>
          {" · "}
          <Link href="/evidence" className="text-accent underline">Evidence centre</Link>
        </p>
      </section>

      <Panel title="One sentence for the jury">
        <p className="text-sm text-ink/80">
          Sepsis ML is missing from most hospitals because of lock-in and unsafe transfer — not because prediction
          is impossible. PredictRx keeps the company alive by never giving the model to the EHR vendor, reaches
          Bangladesh through a standards-first ladder down to paper, and refuses to alert until local calibration
          and measurement habits clear Transfer Shield.
        </p>
        <p className="mt-2 text-xs text-ink/50">
          Full write-up: <code>docs/innovation-adoption-barriers.md</code>
        </p>
      </Panel>
    </div>
  );
}
