"use client";

import { useState } from "react";
import { Icon, type IconName } from "@/components/ui/Icon";

const STEPS: Array<{
  id: string;
  name: string;
  icon: IconName;
  summary: string;
  detail: string;
  points: string[];
}> = [
  {
    id: "acquire",
    name: "Acquire",
    icon: "plug",
    summary: "Connect monitors, labs and flowsheets.",
    detail: "Connectors run inside the hospital network and accept the formats your systems already emit.",
    points: ["HL7 v2 ORU messages from monitors and LIS", "FHIR R4 Observation bundles", "CSV batch import and bedside manual entry"],
  },
  {
    id: "qualify",
    name: "Qualify",
    icon: "shield",
    summary: "Hold stale labs and wrong units.",
    detail: "TrustGate checks every input before a score can be shown. Bad data produces an abstention, not a guess.",
    points: ["Timestamp freshness windows per signal", "Unit and scale validation at the connector", "Quarantine queue for messages that fail mapping"],
  },
  {
    id: "score",
    name: "Score",
    icon: "activity",
    summary: "Six-hour sepsis risk per bed.",
    detail: "A frozen, locally hosted model estimates the probability of sepsis onset within the next six hours.",
    points: ["Probability with risk band", "Trend across recent scoring windows", "Top contributing physiological drivers"],
  },
  {
    id: "respond",
    name: "Respond",
    icon: "bell",
    summary: "Review, alert SLA and handoff.",
    detail: "Elevated risk becomes a named, timed task for the care team, never an autonomous order.",
    points: ["Acknowledge, snooze or record feedback", "Escalation timers with named ownership", "Structured shift handoff of open concerns"],
  },
];

export function PipelineExplorer() {
  const [active, setActive] = useState(0);
  const step = STEPS[active];

  return (
    <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
      <ol className="relative space-y-2" role="tablist" aria-label="Auralis pipeline" aria-orientation="vertical">
        <span className="absolute bottom-9 left-[28px] top-9 w-px bg-border" aria-hidden="true" />
        {STEPS.map((item, idx) => {
          const selected = idx === active;
          return (
            <li key={item.id} className="relative">
              <button
                type="button"
                role="tab"
                id={`pipeline-${item.id}`}
                aria-selected={selected}
                aria-controls="pipeline-panel"
                onClick={() => setActive(idx)}
                onMouseEnter={() => setActive(idx)}
                className={`flex w-full items-center gap-4 rounded-xl border px-3 py-3 text-left transition-all ${
                  selected ? "border-border bg-white shadow-card" : "border-transparent hover:bg-white/60"
                }`}
              >
                <span
                  className={`relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg transition-colors ${
                    selected ? "bg-navy text-white" : "border border-border bg-white text-muted"
                  }`}
                >
                  <Icon name={item.icon} size={16} />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-baseline gap-2">
                    <span className="text-xs font-medium tabular-nums text-muted" aria-hidden="true">0{idx + 1}</span>
                    <span className="text-base font-semibold text-ink">{item.name}</span>
                  </span>
                  <span className="block text-sm text-muted">{item.summary}</span>
                </span>
                <Icon name="chevron-right" size={16} className={`text-muted transition-all ${selected ? "translate-x-0 opacity-100" : "-translate-x-1 opacity-0"}`} />
              </button>
            </li>
          );
        })}
      </ol>

      <div id="pipeline-panel" role="tabpanel" aria-labelledby={`pipeline-${step.id}`} className="rounded-xl border border-border bg-white p-6 shadow-soft sm:p-8">
        <div key={step.id} className="auralis-fade-up">
          <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-soft text-teal-dark">
            <Icon name={step.icon} size={20} />
          </span>
          <h3 className="mt-5 text-xl font-semibold text-ink">{step.name}</h3>
          <p className="mt-2 max-w-lg text-[15px] leading-7 text-muted">{step.detail}</p>
          <ul className="mt-6 divide-y divide-border border-y border-border">
            {step.points.map((point) => (
              <li key={point} className="flex items-center gap-3 py-3 text-sm text-ink">
                <Icon name="check" size={16} className="text-teal" strokeWidth={2} />
                {point}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
