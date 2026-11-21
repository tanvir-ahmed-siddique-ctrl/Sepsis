import Link from "next/link";
import type { Metadata } from "next";
import { Icon, type IconName } from "@/components/ui/Icon";

export const metadata: Metadata = {
  title: "Judge tour | Auralis PredictRx",
  description: "Ordered walkthrough for International AI Builders Congress judges — presentation, evidence, architecture, integration RAG, ICU board.",
  robots: { index: false, follow: false },
};

const TOUR: Array<{ step: string; title: string; body: string; href: string; icon: IconName; minutes: string }> = [
  {
    step: "01",
    title: "180-second pitch replay",
    body: "Problem → solution → live replay → AI → impact. Timer and frozen-model case built for Congress format.",
    href: "/presentation",
    icon: "activity",
    minutes: "3 min",
  },
  {
    step: "02",
    title: "Evidence & honesty boundary",
    body: "Dataset B holdout metrics, what is claimed, what is not (no BD clinical validation, no lives-saved claim).",
    href: "/evidence",
    icon: "shield",
    minutes: "2 min",
  },
  {
    step: "03",
    title: "Connection ladder & TrustGate",
    body: "HL7 / FHIR / CSV paths, quarantine, and why a score can abstain.",
    href: "/connection",
    icon: "plug",
    minutes: "2 min",
  },
  {
    step: "04",
    title: "Mapping copilot (hybrid RAG)",
    body: "Bangla/local lab labels → LOINC proposals. Retrieval mode visible. Analyst must confirm.",
    href: "/integration",
    icon: "layers",
    minutes: "2 min",
  },
  {
    step: "05",
    title: "ICU board + patient chart",
    body: "Sign in as ICU consultant. Open Main ICU, then a bed for SHAP drivers and Auri guideline context.",
    href: "/signin?next=/app/icu",
    icon: "grid",
    minutes: "3 min",
  },
  {
    step: "06",
    title: "Model card",
    body: "Frozen LightGBM, challenger rejection, thresholds chosen on validation only.",
    href: "/model",
    icon: "doc",
    minutes: "1 min",
  },
];

const RUBRIC = [
  ["Innovation & AI-native", "Frozen predictive ML + TrustGate + hybrid mapping RAG + knowledge graphs"],
  ["Technical excellence", "On-prem FastAPI/Next, connectors, audit chain, dockerized demo"],
  ["Business viability", "Staged readiness → silent → live; annual site licence hypothesis"],
  ["Scalability & impact", "Hospital-local data plane; LMIC connection ladder; BD beachhead narrative"],
  ["Responsible AI", "Abstention, no invented outcomes, data sovereignty by default"],
];

export default function JudgeTourPage() {
  return (
    <div className="min-h-screen bg-[#F7FBFC] text-ink">
      <div className="auralis-container-public py-12 lg:py-16">
        <header className="max-w-3xl border-b border-border pb-8">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-teal">Congress judges</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight text-navy sm:text-5xl">
            PredictRx judge tour
          </h1>
          <p className="mt-4 max-w-2xl text-[15px] leading-7 text-muted">
            HealthSphere · PredictRx. Walk this order for a fair score against the official five-component rubric.
            Password for sample roles: <code className="rounded border border-border bg-white px-1.5 py-0.5 font-mono text-[12px]">auralis-demo-2026</code>
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link href="/presentation" className="auralis-btn-primary h-11 px-5">
              Start at presentation
              <Icon name="arrow-right" size={16} />
            </Link>
            <Link href="/signin?next=/app/icu" className="auralis-btn-secondary h-11 px-5">
              Open ICU board
            </Link>
            <Link href="/system-check" className="auralis-btn-ghost h-11 px-5">
              Isolated eval check
            </Link>
          </div>
        </header>

        <section className="mt-10 grid gap-3 lg:grid-cols-2">
          {TOUR.map((item) => (
            <Link
              key={item.step}
              href={item.href}
              className="group flex gap-4 rounded-2xl border border-[#D5E8EC] bg-white p-5 transition-colors hover:border-teal/40"
            >
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[#E5F3F5] text-teal-dark">
                <Icon name={item.icon} size={18} />
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex items-center justify-between gap-2">
                  <span className="text-xs font-semibold uppercase tracking-[0.12em] text-teal">{item.step}</span>
                  <span className="text-xs text-muted">{item.minutes}</span>
                </span>
                <span className="mt-1 block text-[15px] font-semibold text-ink group-hover:text-teal-dark">{item.title}</span>
                <span className="mt-1 block text-sm leading-6 text-muted">{item.body}</span>
              </span>
            </Link>
          ))}
        </section>

        <section className="mt-12 rounded-2xl border border-[#D5E8EC] bg-white p-6 sm:p-8">
          <h2 className="text-xl font-semibold text-navy">Rubric map (100 pts)</h2>
          <ul className="mt-5 space-y-3">
            {RUBRIC.map(([title, body]) => (
              <li key={title} className="grid gap-1 border-b border-border/70 pb-3 last:border-0 sm:grid-cols-[14rem_1fr] sm:gap-4">
                <span className="text-sm font-semibold text-ink">{title}</span>
                <span className="text-sm leading-6 text-muted">{body}</span>
              </li>
            ))}
          </ul>
          <p className="mt-5 text-xs leading-6 text-muted">
            Honest boundary: retrospective public-data evidence only. No Bangladesh clinical validation, customer, or
            outcome-improvement claim is made. Judges should score architecture and safeguards, not invented impact.
          </p>
        </section>
      </div>
    </div>
  );
}
