import type { Metadata } from "next";
import Link from "next/link";
import { MarketingCta } from "@/components/marketing/MarketingPage";
import { Reveal } from "@/components/marketing/MotionPrimitives";
import { ProductShowcaseCarousel } from "@/components/marketing/ProductShowcaseCarousel";

export const metadata: Metadata = {
  title: "Auralis | Hospital-Local ICU Early Warning & Technology Partner",
  description:
    "Six-hour-ahead ICU sepsis risk, bedside workflows, TrustGate safety, and on-site Forward Deployed Engineering.",
};

const PIPELINE = [
  {
    step: "01",
    name: "Acquire",
    summary: "Connect monitors, LIS labs & flowsheets.",
    detail: "HL7v2, FHIR R4, CSV or bedside entry — inside your hospital network.",
  },
  {
    step: "02",
    name: "Qualify",
    summary: "Hold stale labs & wrong units.",
    detail: "TrustGate checks timestamps and scales before any score is shown.",
  },
  {
    step: "03",
    name: "Score",
    summary: "Six-hour-ahead sepsis risk.",
    detail: "Frozen local model with probability, trend and explainable drivers.",
  },
  {
    step: "04",
    name: "Respond",
    summary: "Review, alert SLA & handoff.",
    detail: "Named ownership, acknowledgment timers and shift continuity.",
  },
];

const SURFACES = [
  {
    title: "ICU board",
    body: "Every adult ICU bed with six-hour risk, freshness and open alerts — live polling.",
    href: "/signin?next=/app/icu",
  },
  {
    title: "Charting & Ward NEWS2",
    body: "Bedside vitals entry plus general-ward NEWS2 surveillance for non-ICU units.",
    href: "/signin?next=/app/ward",
  },
  {
    title: "Alerts & handoff",
    body: "Open alert queue with SLA timers and a clean outgoing/incoming shift board.",
    href: "/signin?next=/app/handoff",
  },
  {
    title: "Deployment console",
    body: "Clinical IT view for connectors, quarantine, readiness and site operations.",
    href: "/signin?next=/deploy",
  },
  {
    title: "Hospital admin",
    body: "Staff access, unit settings and silent evaluation — without vendor CRM clutter.",
    href: "/signin?next=/app/admin/overview",
  },
  {
    title: "Vendor control plane",
    body: "Tenants, commercial and FDE projects via vendor@auralis.demo (separate identity).",
    href: "/signin?next=/platform/accounts",
  },
];

const HOSPITAL_TIERS = [
  {
    badge: "Foundation",
    title: "Servers, networking & device readiness",
    body: "On-site assessment of networks, servers and medical devices before any AI software.",
    href: "/technology-enablement",
    linkText: "Technology enablement",
  },
  {
    badge: "Connected",
    title: "HL7 / FHIR integration & mapping",
    body: "Forward Deployed Engineers build connectors, align units and verify feed quality.",
    href: "/deployment-integration",
    linkText: "Integration engineering",
  },
  {
    badge: "Governed",
    title: "Silent evaluation then go-live",
    body: "Shadow-mode pilot, hospital sign-off gates, then interruptive alerts only when ready.",
    href: "/for-hospitals",
    linkText: "Hospital adoption path",
  },
];

function Chevron({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg viewBox="0 0 16 16" className={className} fill="none" aria-hidden>
      <path d="M6 3.5 10.5 8 6 12.5" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function HomePage() {
  return (
    <div className="bg-white text-ink">
      <section className="relative overflow-hidden border-b border-border bg-[radial-gradient(1200px_600px_at_80%_-10%,rgba(8,126,131,0.12),transparent_60%),linear-gradient(180deg,#ffffff_0%,#F7FAFA_100%)]">
        <div className="auralis-container-public grid items-center gap-12 py-14 lg:grid-cols-[1.05fr_0.95fr] lg:py-20">
          <Reveal>
            <p className="font-display text-sm font-semibold uppercase tracking-[0.22em] text-teal">Auralis</p>
            <h1 className="mt-4 max-w-xl font-display text-4xl font-bold leading-[1.05] tracking-tight text-ink sm:text-5xl lg:text-6xl">
              Six-hour-ahead ICU sepsis risk —{" "}
              <span className="font-serif italic font-normal text-teal">inside your hospital.</span>
            </h1>
            <p className="mt-5 max-w-lg text-base leading-7 text-muted sm:text-lg">
              Probability, trends and explainable drivers for ICU teams. TrustGate validates data. Forward Deployed
              Engineers connect FHIR, HL7 and vendor feeds on-site.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link href="/signin?next=/app/icu" className="auralis-btn-primary gap-2 px-7">
                Open live ICU board
                <Chevron />
              </Link>
              <Link href="/contact" className="auralis-btn-secondary px-6">
                Book hospital consultation
              </Link>
            </div>
            <dl className="mt-10 grid max-w-lg grid-cols-3 gap-4 border-t border-border/80 pt-6 text-sm">
              <div>
                <dt className="text-xs uppercase tracking-wide text-muted">Horizon</dt>
                <dd className="mt-1 font-display text-lg font-semibold">6 hours</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-muted">Runtime</dt>
                <dd className="mt-1 font-display text-lg font-semibold">On-prem</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-muted">Feeds</dt>
                <dd className="mt-1 font-display text-lg font-semibold">HL7 · FHIR</dd>
              </div>
            </dl>
          </Reveal>

          <Reveal delayMs={100} className="lg:pl-4">
            <ProductShowcaseCarousel />
          </Reveal>
        </div>
      </section>

      <section className="border-b border-border bg-white py-16 lg:py-20">
        <div className="auralis-container-public">
          <Reveal className="flex flex-wrap items-end justify-between gap-6">
            <div className="max-w-xl">
              <span className="auralis-eyebrow">How it works</span>
              <h2 className="mt-4 font-display text-3xl font-semibold tracking-tight sm:text-4xl">
                From bedside signal to clinician decision.
              </h2>
            </div>
            <Link href="/product" className="inline-flex items-center gap-1 text-sm font-semibold text-teal hover:underline">
              Full platform
              <Chevron className="h-3.5 w-3.5" />
            </Link>
          </Reveal>

          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {PIPELINE.map((item, idx) => (
              <Reveal
                key={item.step}
                delayMs={idx * 60}
                as="article"
                className="rounded-2xl border border-border bg-[#FAFBFA] p-6 transition-all hover:-translate-y-0.5 hover:border-teal/35 hover:bg-white hover:shadow-sm"
              >
                <span className="font-display text-xs font-bold text-teal">{item.step}</span>
                <h3 className="mt-4 font-display text-xl font-semibold">{item.name}</h3>
                <p className="mt-1 text-sm font-medium text-ink/90">{item.summary}</p>
                <p className="mt-2 text-xs leading-5 text-muted">{item.detail}</p>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className="border-b border-border bg-[#F7FAFA] py-16 lg:py-20">
        <div className="auralis-container-public">
          <Reveal className="max-w-2xl">
            <span className="auralis-eyebrow">Product surfaces</span>
            <h2 className="mt-4 font-display text-3xl font-semibold tracking-tight sm:text-4xl">
              Clinical, admin, deployment and vendor planes — clearly separated.
            </h2>
          </Reveal>
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {SURFACES.map((item, idx) => (
              <Reveal key={item.title} delayMs={idx * 50}>
                <Link
                  href={item.href}
                  className="group flex h-full flex-col rounded-2xl border border-border bg-white p-6 transition-all hover:border-teal hover:shadow-sm"
                >
                  <h3 className="font-display text-lg font-semibold group-hover:text-teal">{item.title}</h3>
                  <p className="mt-2 flex-1 text-sm leading-6 text-muted">{item.body}</p>
                  <span className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-teal">
                    Enter demo
                    <Chevron className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
                  </span>
                </Link>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className="border-b border-border bg-white py-16 lg:py-20">
        <div className="auralis-container-public">
          <Reveal className="max-w-2xl">
            <span className="auralis-eyebrow">Forward Deployed Engineering</span>
            <h2 className="mt-4 font-display text-3xl font-semibold tracking-tight sm:text-4xl">
              We meet the hospital infrastructure you have today.
            </h2>
            <p className="mt-3 text-base leading-7 text-muted">
              Assess rooms and networks, connect devices, deploy locally, then support silent evaluation, governance and
              ongoing operations.
            </p>
          </Reveal>
          <div className="mt-10 grid gap-5 lg:grid-cols-3">
            {HOSPITAL_TIERS.map((tier, idx) => (
              <Reveal
                key={tier.badge}
                delayMs={idx * 70}
                as="article"
                className="flex flex-col rounded-2xl border border-border bg-[#FAFBFA] p-7 transition-all hover:border-teal/40 hover:bg-white"
              >
                <span className="text-xs font-semibold uppercase tracking-[0.16em] text-teal">{tier.badge}</span>
                <h3 className="mt-4 font-display text-xl font-semibold">{tier.title}</h3>
                <p className="mt-2.5 flex-1 text-sm leading-6 text-muted">{tier.body}</p>
                <Link href={tier.href} className="mt-6 inline-flex items-center gap-1 text-sm font-semibold text-teal hover:underline">
                  {tier.linkText}
                  <Chevron className="h-3.5 w-3.5" />
                </Link>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-[#F7FAFA] py-16 lg:py-20">
        <div className="auralis-container-public grid gap-10 lg:grid-cols-2 lg:items-center">
          <Reveal>
            <span className="auralis-eyebrow">Safety & privacy</span>
            <h2 className="mt-4 font-display text-3xl font-semibold tracking-tight sm:text-4xl">
              Patient data stays in the hospital. Clinicians stay in command.
            </h2>
            <p className="mt-4 text-base leading-7 text-muted">
              TrustGate abstains on bad inputs. Aurie AI shows protocol context without changing the frozen probability
              or writing orders. Vendor billing never shares the clinical plane.
            </p>
            <div className="mt-6 flex flex-wrap gap-4 text-sm font-semibold text-teal">
              <Link href="/security" className="inline-flex items-center gap-1 hover:underline">
                Security
                <Chevron className="h-3.5 w-3.5" />
              </Link>
              <Link href="/aurie" className="inline-flex items-center gap-1 hover:underline">
                Aurie AI
                <Chevron className="h-3.5 w-3.5" />
              </Link>
              <Link href="/evidence" className="inline-flex items-center gap-1 hover:underline">
                Evidence
                <Chevron className="h-3.5 w-3.5" />
              </Link>
            </div>
          </Reveal>
          <Reveal delayMs={80} className="rounded-2xl border border-border bg-white p-7 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-teal">Live demo credentials</p>
            <p className="mt-3 text-sm text-muted">
              Password for all hospital demo roles:{" "}
              <code className="rounded bg-muted-surface px-1.5 py-0.5 font-mono text-ink">auralis-demo-2026</code>
            </p>
            <ul className="mt-4 space-y-2 text-sm">
              <li>
                <span className="font-mono text-xs text-muted">demo-clinician</span> · ICU board
              </li>
              <li>
                <span className="font-mono text-xs text-muted">demo-nurse</span> · Charting / ward
              </li>
              <li>
                <span className="font-mono text-xs text-muted">demo-admin</span> · Hospital admin
              </li>
              <li>
                <span className="font-mono text-xs text-muted">demo-it</span> · Deployment console
              </li>
              <li>
                <span className="font-mono text-xs text-muted">vendor@auralis.demo</span> · Vendor CRM
              </li>
            </ul>
            <Link href="/signin" className="auralis-btn-primary mt-6 gap-2">
              Go to sign-in
              <Chevron />
            </Link>
          </Reveal>
        </div>
      </section>

      <MarketingCta />
    </div>
  );
}
