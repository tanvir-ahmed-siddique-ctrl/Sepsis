"use client";

import { useEffect, useRef, useState } from "react";

type StageSpec = {
  index: string;
  key: "acquire" | "qualify" | "score" | "respond";
  title: string;
  subtitle: string;
  lead: string;
  protocol: string;
  gateRule: string;
  inputs: string[];
  output: string;
  artifactTitle: string;
  artifactLines: Array<{ k: string; v: string; status: "ok" | "hold" | "accent" }>;
};

const STAGES: StageSpec[] = [
  {
    index: "01",
    key: "acquire",
    title: "Acquire",
    subtitle: "Site-commissioned clinical feeds & bedside capture",
    lead: "Auralis never assumes every hospital already runs a clean FHIR bus. Forward Deployed Engineers inventory actual bedside monitors, LIS exports, HL7v2 segments or structured flowsheet feeds and bind each observation to its source timestamp and unit.",
    protocol: "HL7v2 ORU_R01 · FHIR R4 Observation · Approved CSV / Bedside flowsheet",
    gateRule: "Every observation carries source system ID, collection timestamp and raw unit before entering the pipeline.",
    inputs: ["Arterial & cuff haemodynamics", "Serial laboratory panels", "Respiratory & temperature trends", "Medication & fluid context"],
    output: "Canonical site-local observation ledger with full source provenance",
    artifactTitle: "INGRESS CONNECTOR SPECIMEN · SITE GATEWAY",
    artifactLines: [
      { k: "SOURCE_ADAPTER", v: "hl7v2-icu-monitor-gw (commissioned)", status: "ok" },
      { k: "CLOCK_ALIGNMENT", v: "UTC+06:00 verified · max skew 4s", status: "ok" },
      { k: "UNIT_MAPPING", v: "Lactate mmol/L · Creatinine µmol/L→mg/dL", status: "accent" },
      { k: "PATIENT_BOUNDARY", v: "Hospital LAN only · 0 cloud egress", status: "ok" },
    ],
  },
  {
    index: "02",
    key: "qualify",
    title: "Qualify",
    subtitle: "TrustGate freshness, range & quarantine enforcement",
    lead: "Clinical AI fails when silent unit mismatches or 18-hour-old labs are fed into a model as if they were current. TrustGate inspects completeness, physiological plausibility and staleness windows — quarantining bad payloads and abstaining when required context is missing.",
    protocol: "TrustGate Deterministic Pre-Score Filter · Quarantine Queue",
    gateRule: "If required vital signs are missing or out-of-window, Auralis abstains openly rather than fabricating an imputed alert.",
    inputs: ["Staleness clock per signal class", "Unit & scale reconciliation", "Duplicate segment deduplication", "Missingness pattern check"],
    output: "Qualified feature vector OR explicit abstention / quarantine record",
    artifactTitle: "TRUSTGATE DECISION MATRIX · PRE-INFERENCE",
    artifactLines: [
      { k: "VITAL_FRESHNESS", v: "HR / MAP / RR within 60m window → PASS", status: "ok" },
      { k: "UNIT_SANITY_CHECK", v: "Out-of-range segment routed to Quarantine", status: "hold" },
      { k: "MISSING_CORE_INPUT", v: "Explicit ABSTAIN state (no guessed score)", status: "accent" },
      { k: "IT_VISIBILITY", v: "Quarantine count exposed to Clinical IT", status: "ok" },
    ],
  },
  {
    index: "03",
    key: "score",
    title: "Score",
    subtitle: "Frozen six-hour sepsis-risk model with driver attribution",
    lead: "When TrustGate passes, the frozen Run-4 model computes a six-hour sepsis-risk probability locally inside the hospital boundary. Every score is paired with its top physiological drivers, historical trajectory and model SHA so clinicians can inspect why the signal rose.",
    protocol: "Frozen Run-4 Gradient Boosted Ensemble · Local CPU Inference",
    gateRule: "No autonomous online weight drift. Aurie AI provides retrieved clinical context alongside the score without altering model probability.",
    inputs: ["48-feature temporal trajectory", "Slopes, deltas & shock ratios", "Frozen threshold calibration", "SHA-pinned model artefact"],
    output: "Inspectable 6h risk score + ranked physiological drivers + provenance",
    artifactTitle: "LOCAL INFERENCE RECORD · FROZEN ARTEFACT",
    artifactLines: [
      { k: "MODEL_ARTEFACT", v: "run4_frozen · SHA-pinned · no online drift", status: "ok" },
      { k: "PREDICTION_HORIZON", v: "6-hour early-warning review window", status: "accent" },
      { k: "EXPLAINABILITY", v: "Top longitudinal vital/lab slope drivers", status: "ok" },
      { k: "AURIE_BOUNDARY", v: "Context retrieval separated from probability", status: "ok" },
    ],
  },
  {
    index: "04",
    key: "respond",
    title: "Respond",
    subtitle: "Accountable clinician review, SLA clock & shift handoff",
    lead: "In silent pilot mode, scores are logged without interrupting staff so alert burden and calibration can be audited first. Once governed commissioning gates are signed off, alerts route to named ICU clinicians with acknowledgement states and structured shift handoff.",
    protocol: "Silent Pilot Shadow Log → Governed Bedside Review & Handoff",
    gateRule: "Software informs review; named clinicians hold all diagnostic and treatment authority.",
    inputs: ["Role-scoped ICU board & bed chart", "SLA-tracked acknowledgement workflow", "Structured clinician feedback capture", "Shift-to-shift handoff summary"],
    output: "Audited clinical review trail & longitudinal quality evidence",
    artifactTitle: "GOVERNED RESPONSE & HANDOFF TRAIL",
    artifactLines: [
      { k: "OPERATING_MODE", v: "Silent evaluation OR commissioned live review", status: "accent" },
      { k: "CLINICIAN_ACTION", v: "Acknowledge · Reassess · Escalate · Defer", status: "ok" },
      { k: "SHIFT_HANDOFF", v: "Watched beds & unresolved alerts carried forward", status: "ok" },
      { k: "AUDIT_CHAIN", v: "Tamper-evident local operational log", status: "ok" },
    ],
  },
];

export function ArchitectureFlowSection() {
  const [activeIdx, setActiveIdx] = useState(0);
  const stepRefs = useRef<Array<HTMLElement | null>>([]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const elements = stepRefs.current.filter((el): el is HTMLElement => el !== null);
    if (!elements.length) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible[0]) {
          const idx = Number(visible[0].target.getAttribute("data-stage-index"));
          if (!Number.isNaN(idx)) setActiveIdx(idx);
        }
      },
      {
        rootMargin: "-22% 0px -42% 0px",
        threshold: [0.15, 0.35, 0.6],
      },
    );

    for (const el of elements) observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const current = STAGES[activeIdx] || STAGES[0];

  return (
    <section className="relative border-y border-border bg-white py-20 lg:py-28">
      <div className="auralis-container-public">
        <div className="grid gap-8 border-b border-border pb-12 lg:grid-cols-[0.9fr_1.1fr] lg:items-end">
          <div>
            <p className="auralis-eyebrow">Signal-to-Action Architecture</p>
            <h2 className="mt-4 font-display text-3xl font-semibold tracking-tight text-ink sm:text-5xl">
              Four governed stages.<br />
              <span className="font-serif italic font-normal text-teal">Zero black-box leaps.</span>
            </h2>
          </div>
          <p className="max-w-2xl text-base leading-7 text-muted">
            Every hospital approves its own interface path, data-quality rules and operating mode. Scroll through the four stages below — or select a stage directly — to inspect how observations move from raw hospital feeds to accountable clinician review.
          </p>
        </div>

        <div className="mt-12 grid gap-10 lg:grid-cols-[0.95fr_1.05fr] lg:items-start">
          {/* Left Sticky Architectural Schematic */}
          <div className="lg:sticky lg:top-24">
            <div className="border border-ink bg-[#0E1E26] p-6 text-[#E6F0EE] sm:p-7">
              <div className="flex items-center justify-between border-b border-white/10 pb-4">
                <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#6CE5DB]">
                  STAGE {current.index} / 04 · {current.title.toUpperCase()}
                </span>
                <span className="font-mono text-[11px] text-[#8FA8A5]">Hospital-Local Runtime</span>
              </div>

              {/* Interactive pipeline node bar */}
              <div className="mt-5 grid grid-cols-4 gap-2" role="tablist" aria-label="Pipeline stages">
                {STAGES.map((stage, idx) => {
                  const active = idx === activeIdx;
                  const passed = idx < activeIdx;
                  return (
                    <button
                      key={stage.key}
                      type="button"
                      role="tab"
                      aria-selected={active}
                      onClick={() => {
                        setActiveIdx(idx);
                        stepRefs.current[idx]?.scrollIntoView({ behavior: "smooth", block: "center" });
                      }}
                      className={`border px-2.5 py-2.5 text-left transition-all ${
                        active
                          ? "border-[#24B3A8] bg-[#14303B] text-white"
                          : passed
                          ? "border-[#24B3A8]/40 bg-[#10242D] text-[#A9C6C3]"
                          : "border-white/10 bg-[#0A161C] text-[#7E9996] hover:border-white/25"
                      }`}
                    >
                      <span className="block font-mono text-[10px] text-[#6CE5DB]">{stage.index}</span>
                      <span className="mt-0.5 block font-display text-sm font-semibold">{stage.title}</span>
                    </button>
                  );
                })}
              </div>

              {/* Animated SVG schematic of the 4-stage pipeline */}
              <div className="mt-5 border border-white/10 bg-[#081218] p-4">
                <svg viewBox="0 0 480 86" className="h-20 w-full" role="img" aria-label="Acquire Qualify Score Respond schematic">
                  <line x1="58" y1="43" x2="422" y2="43" stroke="rgba(255,255,255,0.14)" strokeWidth="2" />
                  <line
                    x1="58"
                    y1="43"
                    x2={58 + activeIdx * 121}
                    y2="43"
                    stroke="#24B3A8"
                    strokeWidth="2.5"
                  />
                  <line
                    x1="58"
                    y1="43"
                    x2="422"
                    y2="43"
                    stroke="#6CE5DB"
                    strokeWidth="1.5"
                    className="auralis-signal-line"
                  />
                  {STAGES.map((stage, idx) => {
                    const cx = 58 + idx * 121;
                    const isCurrent = idx === activeIdx;
                    const isDone = idx <= activeIdx;
                    return (
                      <g key={stage.key}>
                        <circle
                          cx={cx}
                          cy="43"
                          r={isCurrent ? 16 : 12}
                          fill={isCurrent ? "#087E83" : isDone ? "#12353C" : "#0B171E"}
                          stroke={isDone ? "#24B3A8" : "rgba(255,255,255,0.25)"}
                          strokeWidth={isCurrent ? "2.5" : "1.5"}
                        />
                        <text
                          x={cx}
                          y="47"
                          textAnchor="middle"
                          fill="#FFFFFF"
                          fontSize="10"
                          fontFamily="monospace"
                        >
                          {stage.index}
                        </text>
                        <text
                          x={cx}
                          y="74"
                          textAnchor="middle"
                          fill={isCurrent ? "#6CE5DB" : "#8FA8A5"}
                          fontSize="10"
                          fontFamily="monospace"
                        >
                          {stage.title.toUpperCase()}
                        </text>
                      </g>
                    );
                  })}
                </svg>
              </div>

              {/* Stage technical inspection ledger */}
              <div className="mt-5">
                <p className="font-mono text-[11px] uppercase tracking-wider text-[#8FA8A5]">{current.artifactTitle}</p>
                <div className="mt-2.5 divide-y divide-white/10 border border-white/10 bg-[#0A161C] font-mono text-xs">
                  {current.artifactLines.map((row) => (
                    <div key={row.k} className="flex flex-wrap items-center justify-between gap-2 px-3.5 py-2.5">
                      <span className="text-[#8FA8A5]">{row.k}</span>
                      <span
                        className={
                          row.status === "accent"
                            ? "text-[#6CE5DB]"
                            : row.status === "hold"
                            ? "text-[#F7C96E]"
                            : "text-white"
                        }
                      >
                        {row.v}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-5 border-l-2 border-[#24B3A8] pl-3.5 text-xs leading-5 text-[#B4C8C5]">
                <strong className="font-mono uppercase tracking-wider text-white">Governance invariant: </strong>
                {current.gateRule}
              </div>
            </div>
          </div>

          {/* Right Scroll Narrative Chapters */}
          <div className="divide-y divide-border">
            {STAGES.map((stage, idx) => {
              const active = idx === activeIdx;
              return (
                <article
                  key={stage.key}
                  ref={(el) => {
                    stepRefs.current[idx] = el;
                  }}
                  data-stage-index={idx}
                  onMouseEnter={() => setActiveIdx(idx)}
                  className={`py-10 transition-opacity duration-300 first:pt-0 last:pb-0 ${
                    active ? "opacity-100" : "opacity-75 hover:opacity-100"
                  }`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-mono text-xs font-semibold uppercase tracking-[0.2em] text-teal">
                      Stage {stage.index} · {stage.title}
                    </span>
                    <span className="font-mono text-xs text-muted">{stage.protocol}</span>
                  </div>
                  <h3 className="mt-3 font-display text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
                    {stage.subtitle}
                  </h3>
                  <p className="mt-4 text-base leading-7 text-muted">{stage.lead}</p>

                  <div className="mt-6 grid gap-3 sm:grid-cols-2">
                    <div className="border-l-2 border-border bg-canvas px-4 py-3">
                      <p className="font-mono text-[11px] uppercase tracking-wider text-muted">Observed / Checked</p>
                      <ul className="mt-2 space-y-1.5 text-sm text-ink">
                        {stage.inputs.map((item) => (
                          <li key={item} className="flex items-center gap-2">
                            <span className="h-1.5 w-1.5 bg-teal" />
                            <span>{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div className="border-l-2 border-teal bg-muted-surface/70 px-4 py-3">
                      <p className="font-mono text-[11px] uppercase tracking-wider text-teal">Stage Output</p>
                      <p className="mt-2 text-sm font-medium leading-6 text-ink">{stage.output}</p>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
