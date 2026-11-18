"use client";

import Link from "next/link";
import { useState } from "react";

type SurfaceSpec = {
  index: string;
  id: string;
  name: string;
  plane: "Hospital-Local Clinical Plane" | "Isolated Account & Vendor Plane" | "Isolated Synthetic Plane";
  audience: string;
  routeLabel: string;
  href: string;
  summary: string;
  dataBoundary: string;
  capabilities: string[];
};

const SURFACES: SurfaceSpec[] = [
  {
    index: "01",
    id: "hospital-workspace",
    name: "Hospital Workspace",
    plane: "Hospital-Local Clinical Plane",
    audience: "ICU Consultants · Bedside Nurses · Hospital Administrators · Clinical Viewers",
    routeLabel: "/app/icu · /signin",
    href: "/signin",
    summary: "The clinical heart of Auralis inside the hospital network: unit-wide ICU risk board, longitudinal patient charts, TrustGate status, SLA-tracked alert acknowledgement, ward NEWS2 surveillance and shift handoff.",
    dataBoundary: "Runs on hospital-approved compute. Patient identifiers and clinical observations never leave the hospital boundary.",
    capabilities: [
      "Unit-level ICU risk board with signal freshness and review state",
      "Longitudinal flowsheet with ranked physiological slope drivers",
      "Accountable alert review & shift-to-shift handoff ledger",
      "Role-scoped permissions (Clinician, Nurse, Clinical Viewer, Hospital Admin)",
    ],
  },
  {
    index: "02",
    id: "deployment-console",
    name: "Deployment Console",
    plane: "Hospital-Local Clinical Plane",
    audience: "Hospital Clinical IT · Forward Deployed Engineers",
    routeLabel: "/deploy · /signin",
    href: "/signin",
    summary: "Site commissioning and interface engineering console for HL7v2, FHIR R4 and approved feeds. Tracks connector health, quarantine queues, silent-pilot gates, backup verification and offline licence packages.",
    dataBoundary: "Operates inside the site boundary. Quarantine inspection protects the bedside chart from malformed or wrong-unit segments.",
    capabilities: [
      "Connector health, clock skew and payload quarantine inspection",
      "Stepwise readiness gates before silent or live mode transitions",
      "Offline Ed25519-signed licence verification without blocking admissions",
      "Backup and restore verification checklists",
    ],
  },
  {
    index: "03",
    id: "customer-portal",
    name: "Customer Portal",
    plane: "Isolated Account & Vendor Plane",
    audience: "Hospital Leadership · Procurement & Finance · Technical Contacts",
    routeLabel: "/portal · /signin",
    href: "/signin",
    summary: "Organization-scoped institutional portal for hospital leadership to review site readiness passports, commercial proposals, signed contracts, licences, invoices, support tickets and training schedules.",
    dataBoundary: "Strictly separated from the clinical database. Contains zero patient records or bedside observations.",
    capabilities: [
      "Organization and multi-site profile & readiness visibility",
      "Issued quotations, contracts, licences and payment verification records",
      "SLA-tracked operational support tickets and escalation visibility",
      "Encrypted commercial document vault with malware scanning",
    ],
  },
  {
    index: "04",
    id: "vendor-control-plane",
    name: "Vendor Control Plane",
    plane: "Isolated Account & Vendor Plane",
    audience: "Auralis FDE Leads · Commercial & Support Operations · Security/Compliance",
    routeLabel: "/platform/overview · /signin",
    href: "/signin",
    summary: "Internal Auralis operational system for managing consultation requests, hospital opportunity pipelines, FDE delivery projects, readiness checklists, equipment coordination and QMS/CAPA governance.",
    dataBoundary: "Receives signed, patient-free technical heartbeats and commercial metadata only. Vendor staff never get chart access here.",
    capabilities: [
      "Consultation intake, opportunity pipeline and proposal authoring",
      "FDE delivery project workspace & 16-item site readiness passport",
      "Equipment ownership tracking & support SLA breach monitoring",
      "61-permission role matrix with four-eyes approval controls",
    ],
  },
  {
    index: "05",
    id: "evaluation-environment",
    name: "Evaluation Environment",
    plane: "Isolated Synthetic Plane",
    audience: "Prospective Hospital Evaluators · Clinical & Technical Reviewers",
    routeLabel: "/system-check",
    href: "/system-check",
    summary: "Dedicated sandboxed runtime populated with de-identified PhysioNet replay cases and synthetic HL7/FHIR streams so hospital teams can inspect the full workflow before any local installation.",
    dataBoundary: "Hard-isolated by EVALUATION_RUNTIME guards. Never touches live hospital infrastructure or real patient data.",
    capabilities: [
      "Pre-seeded de-identified ICU replay trajectories",
      "Interactive role switching across clinical and administrative views",
      "Full inspection of TrustGate abstention and driver explanations",
      "Zero production credentials or hospital network prerequisites",
    ],
  },
];

export function SurfaceBoundaryLedger() {
  const [selected, setSelected] = useState(0);
  const current = SURFACES[selected] || SURFACES[0];

  return (
    <div className="grid gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-start">
      {/* Left interactive index */}
      <div className="divide-y divide-white/10 border-y border-white/15">
        {SURFACES.map((surface, idx) => {
          const active = idx === selected;
          return (
            <button
              key={surface.id}
              type="button"
              onClick={() => setSelected(idx)}
              onMouseEnter={() => setSelected(idx)}
              className={`group flex w-full items-start justify-between gap-4 py-5 text-left transition-colors ${
                active ? "text-white" : "text-[#8FA8A5] hover:text-white"
              }`}
            >
              <div className="flex items-baseline gap-4">
                <span className={`font-mono text-xs ${active ? "text-[#6CE5DB]" : "text-[#6E8784]"}`}>
                  {surface.index}
                </span>
                <div>
                  <span className="block font-display text-xl font-semibold tracking-tight">{surface.name}</span>
                  <span className="mt-1 block font-mono text-[11px] text-[#7E9996]">{surface.plane}</span>
                </div>
              </div>
              <span
                className={`mt-1 font-mono text-xs transition-transform ${
                  active ? "translate-x-1 text-[#6CE5DB]" : "text-[#6E8784] group-hover:translate-x-1"
                }`}
              >
                Inspect →
              </span>
            </button>
          );
        })}
      </div>

      {/* Right architectural specification sheet */}
      <div className="border border-white/15 bg-[#10212B] p-6 sm:p-8">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-4 font-mono text-xs">
          <span className="text-[#6CE5DB]">SURFACE {current.index} · {current.plane.toUpperCase()}</span>
          <span className="text-[#8FA8A5]">{current.routeLabel}</span>
        </div>

        <h3 className="mt-5 font-display text-2xl font-semibold text-white sm:text-3xl">{current.name}</h3>
        <p className="mt-2 font-mono text-xs text-[#9BB5B2]">Authorized operators: {current.audience}</p>
        <p className="mt-4 text-base leading-7 text-[#D2E2E0]">{current.summary}</p>

        <div className="mt-6 border-l-2 border-[#24B3A8] bg-[#0B171E] p-4">
          <p className="font-mono text-[11px] uppercase tracking-wider text-[#6CE5DB]">Data & Security Boundary</p>
          <p className="mt-1.5 text-sm leading-6 text-[#D2E2E0]">{current.dataBoundary}</p>
        </div>

        <div className="mt-6">
          <p className="font-mono text-[11px] uppercase tracking-wider text-[#8FA8A5]">Operational Scope</p>
          <ul className="mt-3 grid gap-2.5 sm:grid-cols-2">
            {current.capabilities.map((cap) => (
              <li key={cap} className="border border-white/10 bg-[#0B171E]/70 p-3 text-xs leading-5 text-[#D2E2E0]">
                {cap}
              </li>
            ))}
          </ul>
        </div>

        <div className="mt-7 flex flex-wrap items-center justify-between gap-4 border-t border-white/10 pt-5">
          <Link
            href={current.href}
            className="inline-flex min-h-11 items-center bg-[#24B3A8] px-5 text-sm font-semibold text-[#08151C] transition-colors hover:bg-[#6CE5DB]"
          >
            Open {current.name} →
          </Link>
          <Link href="/security" className="font-mono text-xs text-[#9BB5B2] underline underline-offset-4 hover:text-white">
            Read plane-isolation architecture
          </Link>
        </div>
      </div>
    </div>
  );
}
