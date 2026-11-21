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
    <div className="grid min-w-0 gap-4 sm:gap-6 lg:grid-cols-[0.9fr_1.1fr]">
      {/* Mobile: horizontal step chips; desktop: vertical list */}
      <div className="min-w-0 lg:hidden" role="tablist" aria-label="Auralis pipeline">
        <div className="flex gap-2 overflow-x-auto pb-1 [scrollbar-width:none]">
          {STEPS.map((item, idx) => {
            const selected = idx === active;
            return (
              <button
                key={item.id}
                type="button"
                role="tab"
                id={`pipeline-m-${item.id}`}
                aria-selected={selected}
                aria-controls="pipeline-panel"
                onClick={() => setActive(idx)}
                className={`flex shrink-0 items-center gap-2 rounded-full border px-3 py-2 text-left transition-all ${
                  selected ? "border-navy bg-navy text-white" : "border-border bg-white text-ink"
                }`}
              >
                <span className="text-[11px] font-medium tabular-nums opacity-70">0{idx + 1}</span>
                <span className="text-sm font-semibold">{item.name}</span>
              </button>
            );
          })}
        </div>
      </div>

      <ol className="relative hidden space-y-2 lg:block" role="tablist" aria-label="Auralis pipeline" aria-orientation="vertical">
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

      <div id="pipeline-panel" role="tabpanel" aria-labelledby={`pipeline-${step.id}`} className="min-w-0 rounded-xl border border-border bg-white p-4 shadow-soft sm:p-6 lg:p-8">
        <div key={step.id} className="auralis-fade-up">
          <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-soft text-teal-dark">
            <Icon name={step.icon} size={20} />
          </span>
          <h3 className="mt-4 text-lg font-semibold text-ink sm:mt-5 sm:text-xl">{step.name}</h3>
          <p className="mt-2 max-w-lg text-sm leading-6 text-muted sm:text-[15px] sm:leading-7">{step.detail}</p>
          <ul className="mt-5 divide-y divide-border border-y border-border sm:mt-6">
            {step.points.map((point) => (
              <li key={point} className="flex items-start gap-3 py-2.5 text-sm text-ink sm:items-center sm:py-3">
                <Icon name="check" size={16} className="mt-0.5 shrink-0 text-teal sm:mt-0" strokeWidth={2} />
                <span className="min-w-0">{point}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
