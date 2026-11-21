import type { Metadata } from "next";
import Link from "next/link";
import { BrandSplash } from "@/components/marketing/BrandSplash";
import { HeroEntrance } from "@/components/marketing/HeroEntrance";
import { HeroHeadline } from "@/components/marketing/HeroHeadline";
import { IntegrationOrbit } from "@/components/marketing/IntegrationOrbit";
import { MarketingCta } from "@/components/marketing/MarketingPage";
import { ParallaxFrame, Reveal } from "@/components/marketing/MotionPrimitives";
import { PipelineExplorer } from "@/components/marketing/PipelineExplorer";
import { ProductShowcaseCarousel } from "@/components/marketing/ProductShowcaseCarousel";
import { Icon, type IconName } from "@/components/ui/Icon";

export const metadata: Metadata = {
  title: "Auralis | Clinical intelligence for hospital ICUs",
  description: "Earlier signal. Risk you can explain. Six-hour sepsis risk on your hospital LAN.",
};

const SURFACES: Array<{ title: string; body: string; href: string; icon: IconName; audience: string }> = [
  {
    title: "ICU board",
    body: "Every adult ICU bed with six-hour risk, freshness and open alerts.",
    href: "/signin?next=/app/icu",
    icon: "grid",
    audience: "Clinicians",
  },
  {
    title: "Charting and ward NEWS2",
    body: "Bedside vitals entry plus NEWS2 for general wards.",
    href: "/signin?next=/app/ward",
    icon: "clipboard",
    audience: "Nurses",
  },
  {
    title: "Alerts and handoff",
    body: "Alert queue with SLA timers and a structured shift board.",
    href: "/signin?next=/app/handoff",
    icon: "bell",
    audience: "Care teams",
  },
  {
    title: "Deployment console",
    body: "Connectors, quarantine, mapping and feed health.",
    href: "/signin?next=/deploy",
    icon: "server",
    audience: "Clinical IT",
  },
  {
    title: "Hospital administration",
    body: "Staff access, units and silent evaluation — apart from vendor tooling.",
    href: "/signin?next=/app/admin/overview",
    icon: "building",
    audience: "Administrators",
  },
  {
    title: "Vendor control plane",
    body: "Tenants, licences, documents and FDE projects.",
    href: "/signin?next=/platform/accounts",
    icon: "layers",
    audience: "Auralis staff",
  },
];

const ENGAGEMENT = [
  {
    badge: "Foundation",
    title: "Rooms, networks, devices",
    body: "On-site readiness before software lands.",
    href: "/technology-enablement",
    linkText: "Technology enablement",
  },
  {
    badge: "Connected",
    title: "HL7 / FHIR mapping",
    body: "Engineers wire feeds and verify quality on your LAN.",
    href: "/deployment-integration",
    linkText: "Integration",
  },
  {
    badge: "Governed",
    title: "Silent, then live",
    body: "Shadow evaluation first. Bedside alerts only after sign-off.",
    href: "/for-hospitals",
    linkText: "Adoption path",
  },
];

const SCORE_PARTS = [
  { label: "Probability", value: "Sepsis onset chance in the next six hours." },
  { label: "Risk band", value: "Stable, watch or high — hospital thresholds." },
  { label: "Trend", value: "Direction across recent scoring windows." },
  { label: "Drivers", value: "Signals that moved this score." },
  { label: "Abstention", value: "Bad or stale data → no score, with a reason." },
];

const DEMO_ROLES = [
  { user: "demo-clinician", role: "ICU board" },
  { user: "demo-nurse", role: "Charting and ward" },
  { user: "demo-admin", role: "Hospital administration" },
  { user: "demo-it", role: "Deployment console" },
  { user: "vendor@auralis.demo", role: "Vendor control plane" },
];

export default function HomePage() {
  return (
    <div className="auralis-home-green min-w-0 overflow-x-clip bg-[#F4FAF6] text-ink">
      <BrandSplash />
      {/* Hero */}
      <section className="relative overflow-x-clip border-b border-[#C9E6D6]/80">
        <div className="auralis-mist auralis-mist-green pointer-events-none absolute inset-0" aria-hidden="true" />
        <HeroEntrance
          copy={
            <>
              <div data-hero-slot="1" className="min-w-0">
                <HeroHeadline />
              </div>
              <p data-hero-slot="2" className="mt-5 max-w-md text-[15px] leading-6 text-[#4A6356] sm:mt-8 sm:text-[16px] sm:leading-7">
                Hospital-local intelligence. Explainable drivers. Clinician still in command.
              </p>
              <div data-hero-slot="3" className="mt-6 flex w-full flex-col gap-2.5 sm:mt-9 sm:w-auto sm:flex-row sm:flex-wrap sm:items-center sm:gap-3">
                <Link href="/signin?next=/app/icu" className="group auralis-btn-primary h-11 w-full justify-center px-5 sm:w-auto">
                  Open ICU board
                  <Icon name="arrow-right" size={16} className="transition-transform group-hover:translate-x-0.5" />
                </Link>
                <Link href="/contact" className="auralis-btn-secondary h-11 w-full justify-center px-5 sm:w-auto">
                  Book a consultation
                </Link>
              </div>
              <dl data-hero-slot="4" className="mt-8 grid max-w-md grid-cols-3 gap-2 border-t border-border/80 pt-5 sm:mt-12 sm:gap-3 sm:pt-6">
                {[
                  ["Horizon", "6 hours"],
                  ["Where", "On-prem"],
                  ["Feeds", "HL7 / FHIR"],
                ].map(([label, value]) => (
                  <div key={label} className="min-w-0">
                    <dt className="text-[11px] text-muted sm:text-xs">{label}</dt>
                    <dd className="mt-1 text-[12px] font-semibold leading-snug text-ink sm:text-sm">{value}</dd>
                  </div>
                ))}
              </dl>
            </>
          }
          showcase={<ProductShowcaseCarousel />}
        />
      </section>

      {/* Model + deployment — short */}
      <section className="relative overflow-x-clip border-b border-[#C9E6D6]/70 bg-[#F4FAF6] py-12 sm:py-16 lg:py-20">
        <div className="auralis-container-public relative">
          <Reveal className="max-w-2xl" variant="left">
            <h2 className="text-[1.65rem] font-semibold leading-tight tracking-[-0.03em] text-navy sm:text-[2.25rem]">
              Holdout-proven model. Real hospital pipes.
            </h2>
            <p className="mt-3 max-w-xl text-[15px] leading-7 text-muted">
              Frozen six-hour sepsis ML that beat simpler baselines on Dataset B — plus on-site feed engineering so the
              score actually lands on a ward board.
            </p>
          </Reveal>
          <div className="mt-8 grid gap-5 sm:mt-10 sm:grid-cols-3 sm:gap-6">
            {[
              ["Model", "Holdout ~0.81 AUROC, SHAP drivers, TrustGate."],
              ["Pipes", "HL7 / FHIR, units, quarantine on your LAN."],
              ["Go-live", "Silent first. Alerts only after sign-off."],
            ].map(([title, body], idx) => (
              <Reveal key={title} as="article" delayMs={idx * 90} variant="up">
                <h3 className="text-sm font-semibold uppercase tracking-[0.12em] text-teal">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-muted">{body}</p>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Pipeline */}
      <section className="border-b border-[#C9E6D6]/70 bg-[#EAF6EF] py-12 sm:py-16 lg:py-20">
        <div className="auralis-container-public">
          <Reveal className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between sm:gap-4" variant="up">
            <div className="max-w-xl">
              <h2 className="text-[1.65rem] font-semibold leading-tight tracking-[-0.03em] text-navy sm:text-[2.25rem]">
                Bedside signal → clinician decision.
              </h2>
              <p className="mt-3 text-[15px] leading-7 text-muted">Four stages. A safety check between each.</p>
            </div>
            <Link href="/product" className="auralis-link self-start">
              Platform
              <Icon name="arrow-right" size={16} />
            </Link>
          </Reveal>
          <Reveal delayMs={80} variant="scale" className="mt-8 min-w-0 sm:mt-10">
            <PipelineExplorer />
          </Reveal>
        </div>
      </section>

      {/* Connection story — mid page, wide, flat scroll-lit */}
      <section className="relative overflow-x-clip border-b border-[#C9E6D6]/70 bg-white py-12 sm:py-16 lg:py-24">
        <div className="pointer-events-none absolute -right-16 top-10 h-56 w-56 rounded-full bg-[#A8D9BE]/45 blur-3xl sm:-right-24 sm:h-72 sm:w-72" aria-hidden="true" />
        <div className="relative mx-auto w-full max-w-[110rem] px-4 sm:px-8 lg:px-12 xl:px-16">
          <Reveal className="mx-auto max-w-3xl text-center" variant="up">
            <h2 className="text-[1.65rem] font-semibold leading-tight tracking-[-0.03em] text-navy sm:text-[2.35rem]">
              How a hospital actually connects.
            </h2>
            <p className="mt-3 text-[15px] leading-7 text-muted sm:text-base">
              Scroll — sources wake, the LAN pipe lights, risk reaches the board.
            </p>
          </Reveal>
          <Reveal delayMs={80} variant="up" className="mt-8 min-w-0 sm:mt-10">
            <IntegrationOrbit />
          </Reveal>
          <Reveal delayMs={120} className="mt-7 flex flex-wrap justify-center gap-x-5 gap-y-2">
            <Link href="/deployment-integration" className="auralis-link">
              Integration path
              <Icon name="arrow-right" size={15} />
            </Link>
            <Link href="/model" className="auralis-link">
              Model card
              <Icon name="arrow-right" size={15} />
            </Link>
          </Reveal>
        </div>
      </section>

      {/* Score anatomy */}
      <section className="relative overflow-x-clip border-b border-[#C9E6D6]/70 bg-[#F4FAF6] py-12 sm:py-16 lg:py-20">
        <div className="pointer-events-none absolute right-0 top-0 h-48 w-48 rounded-full bg-[#B7E0C8]/40 blur-3xl sm:h-64 sm:w-64" aria-hidden="true" />
        <div className="auralis-container-public relative grid gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-center lg:gap-16">
          <Reveal variant="left">
            <h2 className="text-[1.65rem] font-semibold leading-tight tracking-[-0.03em] text-navy sm:text-[2.25rem]">
              Never an unexplained number.
            </h2>
            <p className="mt-3 max-w-md text-[15px] leading-7 text-muted">
              Probability, band, trend, drivers — and silence when data is unsafe.
            </p>
            <Link href="/model" className="auralis-link mt-5">
              Model card
              <Icon name="arrow-right" size={16} />
            </Link>
          </Reveal>
          <Reveal delayMs={100} variant="right">
            <ParallaxFrame speed={0.05}>
              <dl className="border-y border-[#D5E8EC]">
                {SCORE_PARTS.map((part) => (
                  <div
                    key={part.label}
                    className="grid gap-1 border-b border-[#D5E8EC]/80 py-3 last:border-b-0 sm:grid-cols-[8.5rem_1fr] sm:gap-5 sm:py-3.5"
                  >
                    <dt className="font-display text-sm font-semibold text-ink">{part.label}</dt>
                    <dd className="text-sm leading-6 text-muted">{part.value}</dd>
                  </div>
                ))}
              </dl>
            </ParallaxFrame>
          </Reveal>
        </div>
      </section>

      {/* Product surfaces */}
      <section className="border-b border-[#C9E6D6]/70 bg-[#EEF7F1] py-12 sm:py-16 lg:py-20">
        <div className="auralis-container-public">
          <Reveal className="max-w-xl">
            <h2 className="text-[1.65rem] font-semibold leading-tight tracking-[-0.03em] text-navy sm:text-[2.25rem]">
              One platform. Every role.
            </h2>
          </Reveal>
          <div className="mt-8 grid gap-3 sm:mt-10 sm:grid-cols-2 lg:grid-cols-3">
            {SURFACES.map((item, idx) => (
              <Reveal key={item.title} delayMs={(idx % 3) * 70} variant="up">
                <Link
                  href={item.href}
                  className="group flex h-full flex-col rounded-2xl border border-[#D5E8EC] bg-white/90 p-4 transition-colors hover:border-teal/35 hover:bg-white sm:p-5"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#D8EFE3] text-[#267352]">
                      <Icon name={item.icon} size={17} />
                    </span>
                    <span className="text-xs text-muted">{item.audience}</span>
                  </div>
                  <h3 className="mt-3 text-[15px] font-semibold text-ink sm:mt-4">{item.title}</h3>
                  <p className="mt-1.5 flex-1 text-sm leading-6 text-muted">{item.body}</p>
                  <span className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-teal">
                    Open
                    <Icon name="arrow-right" size={14} className="transition-transform group-hover:translate-x-0.5" />
                  </span>
                </Link>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* FDE */}
      <section className="relative overflow-x-clip bg-navy py-12 text-white sm:py-16 lg:py-20">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_20%_0%,rgba(115,195,207,0.18),transparent_55%)]" aria-hidden="true" />
        <div className="auralis-container-public relative">
          <Reveal className="grid gap-4 lg:grid-cols-[1fr_auto] lg:items-end lg:gap-5">
            <div className="max-w-xl">
              <h2 className="text-[1.65rem] font-semibold leading-tight tracking-[-0.03em] text-white sm:text-[2.25rem]">
                Model worth deploying. Engineers who stay.
              </h2>
              <p className="mt-3 text-[15px] leading-7 text-white/65">
                We start with what you have — then connect, prove, and go live.
              </p>
            </div>
            <Link href="/forward-deployed-engineering" className="group inline-flex items-center gap-1.5 self-start text-sm font-semibold text-[#A8D8E0] lg:self-auto">
              How engagements work
              <Icon name="arrow-right" size={16} className="transition-transform group-hover:translate-x-0.5" />
            </Link>
          </Reveal>
          <div className="mt-8 grid gap-px overflow-hidden rounded-2xl border border-white/10 bg-white/10 sm:mt-10 lg:grid-cols-3">
            {ENGAGEMENT.map((tier, idx) => (
              <Reveal key={tier.badge} as="article" delayMs={idx * 90} variant="up" className="flex flex-col bg-navy/90 p-5 transition-colors hover:bg-navy-800 sm:p-6">
                <span className="text-xs font-semibold uppercase tracking-[0.14em] text-[#73C3CF]">{tier.badge}</span>
                <h3 className="mt-3 text-base font-semibold text-white sm:mt-4 sm:text-lg">{tier.title}</h3>
                <p className="mt-2 flex-1 text-sm leading-6 text-white/60">{tier.body}</p>
                <Link href={tier.href} className="mt-5 inline-flex items-center gap-1.5 text-sm font-semibold text-white/90 hover:text-white">
                  {tier.linkText}
                  <Icon name="arrow-right" size={14} />
                </Link>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Safety + sign-in */}
      <section className="border-b border-[#C9E6D6]/70 bg-white py-12 sm:py-16 lg:py-20">
        <div className="auralis-container-public grid gap-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-start lg:gap-16">
          <Reveal>
            <h2 className="text-[1.65rem] font-semibold leading-tight tracking-[-0.03em] text-navy sm:text-[2.25rem]">
              Data stays local. Clinicians decide.
            </h2>
            <ul className="mt-7 space-y-4">
              {[
                ["shield", "TrustGate", "Stale or conflicting inputs → no misleading score."],
                ["user", "Auri AI", "Local co-pilot for mapping & context — never changes the sepsis probability. Language: English / বাংলা."],
                ["lock", "Separate planes", "Vendor tooling never shares the clinical data path."],
              ].map(([icon, title, body]) => (
                <li key={title} className="flex gap-3.5">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[#D8EFE3] text-[#267352]">
                    <Icon name={icon as IconName} size={16} />
                  </span>
                  <div>
                    <p className="text-[15px] font-semibold text-ink">{title}</p>
                    <p className="mt-0.5 text-sm leading-6 text-muted">{body}</p>
                  </div>
                </li>
              ))}
            </ul>
            <div className="mt-7 flex flex-wrap gap-x-5 gap-y-2">
              <Link href="/security" className="auralis-link">
                Security
                <Icon name="arrow-right" size={15} />
              </Link>
              <Link href="/evidence" className="auralis-link">
                Evidence
                <Icon name="arrow-right" size={15} />
              </Link>
            </div>
          </Reveal>

          <Reveal delayMs={60} className="rounded-2xl border border-[#D5E8EC] bg-[#F7FBFC] p-4 sm:p-6">
            <p className="text-sm font-semibold text-ink">Try a role</p>
            <p className="mt-1.5 text-sm text-muted">
              Password for all samples:{" "}
              <code className="rounded-md border border-border bg-white px-1.5 py-0.5 font-mono text-[12px] text-ink">
                auralis-demo-2026
              </code>
            </p>
            <ul className="mt-4 divide-y divide-border overflow-hidden rounded-xl border border-border bg-white">
              {DEMO_ROLES.map((item) => (
                <li key={item.user} className="flex flex-col gap-0.5 px-3 py-2.5 text-sm sm:flex-row sm:items-center sm:justify-between sm:gap-3 sm:px-4">
                  <span className="min-w-0 truncate font-mono text-[12px] text-ink">{item.user}</span>
                  <span className="shrink-0 text-xs text-muted">{item.role}</span>
                </li>
              ))}
            </ul>
            <Link href="/signin" className="group auralis-btn-primary mt-5 w-full">
              Sign in
              <Icon name="arrow-right" size={16} className="transition-transform group-hover:translate-x-0.5" />
            </Link>
          </Reveal>
        </div>
      </section>

      <MarketingCta />
    </div>
  );
}
