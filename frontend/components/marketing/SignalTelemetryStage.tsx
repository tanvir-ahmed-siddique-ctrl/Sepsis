"use client";

import { useEffect, useState } from "react";

type TelemetryPreset = {
  id: string;
  label: string;
  bed: string;
  feedMode: string;
  freshness: string;
  trustGate: "PASS" | "ABSTAIN · MISSING LACTATE" | "QUARANTINED · UNIT MISMATCH";
  trustTone: "pass" | "warn" | "quarantine";
  horizon: string;
  probability: string;
  band: string;
  vitals: Array<{ code: string; name: string; value: string; unit: string; delta: string; source: string }>;
  drivers: Array<{ label: string; weight: number; detail: string }>;
  pathPoints: string;
  reviewState: string;
};

const PRESETS: TelemetryPreset[] = [
  {
    id: "verified-trajectory",
    label: "01 · Verified 6h trajectory",
    bed: "ICU-A · Bed 04 (Replay specimen)",
    feedMode: "HL7v2 + LabLIS · Site-local",
    freshness: "Last observation 11m ago",
    trustGate: "PASS",
    trustTone: "pass",
    horizon: "6-hour sepsis risk window",
    probability: "0.74",
    band: "Elevated review band · Frozen Run-4 model",
    vitals: [
      { code: "HR", name: "Heart rate", value: "112", unit: "bpm", delta: "+14 / 3h", source: "Bedside monitor" },
      { code: "MAP", name: "Mean arterial pressure", value: "63", unit: "mmHg", delta: "-9 / 3h", source: "Arterial line" },
      { code: "LAC", name: "Arterial lactate", value: "2.9", unit: "mmol/L", delta: "+1.1 / 4h", source: "LIS verified" },
      { code: "RR", name: "Respiratory rate", value: "26", unit: "/min", delta: "+6 / 3h", source: "Bedside monitor" },
    ],
    drivers: [
      { label: "MAP downward slope (4h)", weight: 84, detail: "Sustained drop below 65 mmHg with rising heart rate" },
      { label: "Lactate elevation + shock index", weight: 72, detail: "Paired rise across serial arterial draws" },
      { label: "Respiratory tachypnea trend", weight: 56, detail: " progressive increase over 6h observation window" },
    ],
    pathPoints: "M 16 108 C 72 104, 118 98, 170 86 C 220 74, 268 62, 320 44 C 358 31, 392 24, 424 20",
    reviewState: "Awaiting named ICU clinician acknowledgement · SLA clock 15m",
  },
  {
    id: "trustgate-abstain",
    label: "02 · TrustGate abstention",
    bed: "ICU-A · Bed 09 (Stale lab window)",
    feedMode: "FHIR R4 Observation · Site-local",
    freshness: "Vitals 6m ago · Chemistry 9h stale",
    trustGate: "ABSTAIN · MISSING LACTATE",
    trustTone: "warn",
    horizon: "Scoring withheld by TrustGate",
    probability: "—",
    band: "Abstained · Required fresh context unavailable",
    vitals: [
      { code: "HR", name: "Heart rate", value: "98", unit: "bpm", delta: "+3 / 3h", source: "Bedside monitor" },
      { code: "MAP", name: "Mean arterial pressure", value: "71", unit: "mmHg", delta: "-2 / 3h", source: "Cuff NIBP" },
      { code: "LAC", name: "Lactate", value: "STALE", unit: ">8h", delta: "Gate hold", source: "Awaiting LIS" },
      { code: "TEMP", name: "Core temperature", value: "37.9", unit: "°C", delta: "+0.4 / 4h", source: "Flowsheet" },
    ],
    drivers: [
      { label: "Freshness gate triggered", weight: 92, detail: "Auralis refuses to emit a misleading score when core inputs exceed staleness bounds" },
      { label: "Provenance preserved", weight: 64, detail: "Clinicians see which feed is delayed instead of a fabricated imputed alert" },
      { label: "Zero interruptive paging", weight: 40, detail: "Suppresses low-trust alarm noise until feed recovery" },
    ],
    pathPoints: "M 16 86 C 72 84, 118 82, 170 79 C 220 78, 268 78, 320 78 L 424 78",
    reviewState: "No interruptive alert emitted · Feed lag visible to Clinical IT",
  },
  {
    id: "quarantine-guard",
    label: "03 · Unit quarantine guard",
    bed: "ICU-B · Connector commissioning",
    feedMode: "HL7 ORU_R01 · Sandbox gate",
    freshness: "Payload intercepted at ingress",
    trustGate: "QUARANTINED · UNIT MISMATCH",
    trustTone: "quarantine",
    horizon: "Ingress validation boundary",
    probability: "HOLD",
    band: "Quarantined before patient timeline",
    vitals: [
      { code: "CREA", name: "Creatinine payload", value: "184", unit: "µmol/L vs mg/dL", delta: "Unit conflict", source: "Quarantine queue" },
      { code: "TS", name: "Observation timestamp", value: "+06:00", unit: "UTC offset", delta: "Verified", source: "Connector map" },
      { code: "MAP", name: "Arterial pressure", value: "68", unit: "mmHg", delta: "Valid", source: "Monitor gateway" },
      { code: "SPO2", name: "Pulse oximetry", value: "96", unit: "%", delta: "Valid", source: "Monitor gateway" },
    ],
    drivers: [
      { label: "Unit & scale verification", weight: 96, detail: "Detects µmol/L vs mg/dL mismatch before corrupting model features" },
      { label: "Isolated quarantine queue", weight: 78, detail: "FDE and Hospital IT inspect raw HL7 segments without polluting bedside charts" },
      { label: "Audited mapping release", weight: 58, detail: "Requires explicit mapping sign-off before promotion" },
    ],
    pathPoints: "M 16 94 C 84 92, 148 64, 212 64 L 284 64 L 424 64",
    reviewState: "Held in Deployment Console quarantine · Bedside chart protected",
  },
];

export function SignalTelemetryStage() {
  const [activeIndex, setActiveIndex] = useState(0);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    if (paused) return;
    if (typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const timer = window.setInterval(() => {
      setActiveIndex((current) => (current + 1) % PRESETS.length);
    }, 6500);
    return () => window.clearInterval(timer);
  }, [paused]);

  const active = PRESETS[activeIndex];

  return (
    <div
      className="relative overflow-hidden border border-[#1E3542] bg-[#0B171E] text-[#E6F0EE] shadow-[0_28px_70px_-24px_rgba(9,22,29,0.65)]"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      {/* Subtle architectural grid & top instrument bar */}
      <div className="auralis-dark-grid border-b border-white/10 px-5 py-3.5 sm:px-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <span className="relative flex h-2.5 w-2.5">
              <span className="auralis-pulse-dot absolute inline-flex h-full w-full rounded-full bg-[#24B3A8]" />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-[#24B3A8]" />
            </span>
            <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-[#9BB5B2]">
              Auralis Local Signal Plane · Architecture Specimen
            </span>
          </div>
          <span className="font-mono text-[11px] text-[#7E9996]">{active.feedMode}</span>
        </div>

        {/* Interactive mode selector tabs */}
        <div className="mt-3.5 grid grid-cols-1 gap-1.5 sm:grid-cols-3" role="tablist" aria-label="Signal telemetry states">
          {PRESETS.map((preset, idx) => {
            const selected = idx === activeIndex;
            return (
              <button
                key={preset.id}
                type="button"
                role="tab"
                aria-selected={selected}
                onClick={() => {
                  setActiveIndex(idx);
                  setPaused(true);
                }}
                className={`border px-3 py-2 text-left font-mono text-[11px] transition-all ${
                  selected
                    ? "border-[#24B3A8] bg-[#122833] text-white"
                    : "border-white/10 bg-[#0E1E27]/70 text-[#8FA8A5] hover:border-white/25 hover:text-white"
                }`}
              >
                {preset.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Main telemetry canvas */}
      <div className="p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-white/10 pb-4">
          <div>
            <p className="font-mono text-xs text-[#8FA8A5]">{active.bed}</p>
            <p className="mt-1 font-display text-lg font-semibold text-white">{active.band}</p>
          </div>
          <div className="flex flex-col items-start sm:items-end">
            <span
              className={`inline-flex items-center gap-1.5 border px-2.5 py-1 font-mono text-[11px] font-semibold uppercase tracking-wider ${
                active.trustTone === "pass"
                  ? "border-[#24B3A8]/50 bg-[#0F3538] text-[#6CE5DB]"
                  : active.trustTone === "warn"
                  ? "border-[#D99B26]/50 bg-[#33260E] text-[#F7C96E]"
                  : "border-[#D95C50]/50 bg-[#381818] text-[#F7988E]"
              }`}
            >
              TrustGate · {active.trustGate}
            </span>
            <span className="mt-1.5 font-mono text-[11px] text-[#8FA8A5]">{active.freshness}</span>
          </div>
        </div>

        {/* SVG trajectory & probability read-out */}
        <div className="mt-5 grid gap-5 lg:grid-cols-[1.35fr_0.65fr]">
          <div className="border border-white/10 bg-[#081218] p-4">
            <div className="flex items-center justify-between font-mono text-[11px] text-[#7E9996]">
              <span>OBSERVATION TRAJECTORY (T-6H → NOW)</span>
              <span>{active.horizon}</span>
            </div>
            <svg
              viewBox="0 0 440 132"
              className="mt-3 h-32 w-full overflow-visible"
              role="img"
              aria-label={`Clinical signal trajectory for ${active.label}`}
            >
              <defs>
                <linearGradient id="auralisAreaGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#24B3A8" stopOpacity="0.28" />
                  <stop offset="100%" stopColor="#24B3A8" stopOpacity="0.0" />
                </linearGradient>
              </defs>
              {/* Reference threshold lines */}
              <line x1="16" y1="34" x2="424" y2="34" stroke="rgba(247, 201, 110, 0.22)" strokeDasharray="4 4" />
              <line x1="16" y1="74" x2="424" y2="74" stroke="rgba(255, 255, 255, 0.08)" />
              <line x1="16" y1="112" x2="424" y2="112" stroke="rgba(255, 255, 255, 0.08)" />
              <text x="20" y="28" fill="#D9B46A" fontSize="9" fontFamily="monospace">
                REVIEW THRESHOLD (FROZEN)
              </text>

              {/* Filled area under curve */}
              <path d={`${active.pathPoints} L 424 118 L 16 118 Z`} fill="url(#auralisAreaGrad)" />

              {/* Primary trajectory curve */}
              <path
                d={active.pathPoints}
                fill="none"
                stroke={active.trustTone === "pass" ? "#24B3A8" : active.trustTone === "warn" ? "#E5A93B" : "#E06D62"}
                strokeWidth="2.5"
              />
              {/* Animated signal carrier overlay */}
              <path
                d={active.pathPoints}
                fill="none"
                stroke="#FFFFFF"
                strokeOpacity="0.65"
                strokeWidth="1.5"
                className="auralis-signal-line"
              />

              {/* Sampled time-series nodes */}
              {[
                [16, 108],
                [118, 96],
                [220, 76],
                [320, 48],
                [424, active.trustTone === "pass" ? 20 : active.trustTone === "warn" ? 78 : 64],
              ].map(([cx, cy], index) => (
                <g key={index}>
                  <circle
                    cx={cx}
                    cy={cy}
                    r={index === 4 ? 5 : 3}
                    fill={index === 4 ? "#FFFFFF" : "#0B171E"}
                    stroke="#24B3A8"
                    strokeWidth="2"
                  />
                </g>
              ))}
            </svg>
            <div className="mt-2 flex justify-between font-mono text-[10px] text-[#6E8784]">
              <span>-6.0h</span>
              <span>-4.5h</span>
              <span>-3.0h</span>
              <span>-1.5h</span>
              <span>NOW (LOCAL)</span>
            </div>
          </div>

          {/* Probability & provenance box */}
          <div className="flex flex-col justify-between border border-white/10 bg-[#0E1E27] p-4">
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-[#8FA8A5]">6h Sepsis Risk Index</p>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="font-mono text-4xl font-semibold tracking-tight text-white">{active.probability}</span>
                <span className="font-mono text-xs text-[#6CE5DB]">
                  {active.trustTone === "pass" ? "inspectable" : "gated"}
                </span>
              </div>
              <p className="mt-2 text-xs leading-5 text-[#9BB5B2]">
                Assistive early-warning score only. Never an autonomous diagnosis or treatment order.
              </p>
            </div>
            <div className="mt-4 border-t border-white/10 pt-3 font-mono text-[11px] text-[#8FA8A5]">
              <span className="block text-[10px] uppercase tracking-wider text-[#6E8784]">Accountability state</span>
              <span className="mt-1 block text-[#D5E4E2]">{active.reviewState}</span>
            </div>
          </div>
        </div>

        {/* 4-column observation provenance strip */}
        <div className="mt-4 grid grid-cols-2 gap-2.5 sm:grid-cols-4">
          {active.vitals.map((vital) => (
            <div key={vital.code} className="border border-white/10 bg-[#0E1E27]/80 p-3">
              <div className="flex items-center justify-between font-mono text-[11px]">
                <span className="font-semibold text-[#6CE5DB]">{vital.code}</span>
                <span className="text-[10px] text-[#8FA8A5]">{vital.delta}</span>
              </div>
              <div className="mt-1.5 flex items-baseline gap-1">
                <span className="font-mono text-xl font-semibold text-white">{vital.value}</span>
                <span className="font-mono text-[11px] text-[#8FA8A5]">{vital.unit}</span>
              </div>
              <p className="mt-1 truncate font-mono text-[10px] text-[#7E9996]">{vital.source}</p>
            </div>
          ))}
        </div>

        {/* Top feature attribution bars */}
        <div className="mt-4 border-t border-white/10 pt-4">
          <div className="flex items-center justify-between font-mono text-[11px] text-[#8FA8A5]">
            <span>INSPECTABLE DRIVER ATTRIBUTION</span>
            <span>Clinician-in-the-loop</span>
          </div>
          <div className="mt-2.5 space-y-2">
            {active.drivers.map((driver) => (
              <div key={driver.label} className="grid gap-1.5 sm:grid-cols-[12rem_1fr] sm:items-center">
                <span className="font-mono text-xs text-white">{driver.label}</span>
                <div>
                  <div className="h-1.5 w-full overflow-hidden bg-white/10">
                    <div
                      className="h-full bg-[#24B3A8] transition-all duration-500"
                      style={{ width: `${driver.weight}%` }}
                    />
                  </div>
                  <p className="mt-1 text-xs text-[#9BB5B2]">{driver.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom hospital-boundary telemetry footer */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-white/10 bg-[#081218] px-5 py-2.5 font-mono text-[11px] text-[#7E9996]">
        <span>PATIENT DATA BOUNDARY · INSIDE HOSPITAL LAN</span>
        <span>OUTBOUND HEARTBEAT · SIGNED METADATA ONLY (0 PHI)</span>
      </div>
    </div>
  );
}
