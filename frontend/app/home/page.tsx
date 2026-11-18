import type { Metadata } from "next";
import Link from "next/link";
import { MarketingCta } from "@/components/marketing/MarketingPage";
import { Reveal } from "@/components/marketing/MotionPrimitives";
import { ProductShowcaseCarousel } from "@/components/marketing/ProductShowcaseCarousel";

export const metadata: Metadata = {
  title: "Auralis | Hospital-Local ICU Early Warning & Technology Partner",
  description:
    "Early six-hour ICU sepsis risk detection, bedside clinical workflows, and on-site hospital integration engineering.",
};

const PIPELINE = [
  {
    step: "01",
    name: "Acquire",
    summary: "Connect monitors, LIS labs & flowsheets.",
    detail: "Supports HL7v2, FHIR R4, CSV or bedside entry — deployed inside your hospital network.",
  },
  {
    step: "02",
    name: "Qualify",
    summary: "Filter out stale labs & wrong units.",
    detail: "TrustGate checks timestamps and scales first, holding scores rather than firing false alarms.",
  },
  {
    step: "03",
    name: "Score",
    summary: "6-hour sepsis risk with clear drivers.",
    detail: "Runs our frozen model locally and shows the exact vital and lab trends behind every rise.",
  },
  {
    step: "04",
    name: "Respond",
    summary: "Clinician review & shift handoff.",
    detail: "Routes alerts to named ICU doctors with SLA timers and one-click shift continuity.",
  },
];

const HOSPITAL_TIERS = [
  {
    badge: "Foundation",
    title: "Servers, networking & device readiness",
    body: "Need local IT infrastructure or monitor connectivity first? Our engineers assess networks, servers, and medical devices before any AI software is introduced.",
    href: "/technology-enablement",
    linkText: "Technology enablement →",
  },
  {
    badge: "Connected",
    title: "HL7 / FHIR integration & data mapping",
    body: "Have digital labs or monitors with integration gaps? Forward Deployed Engineers build local connectors, align units, and verify feed quality.",
    href: "/deployment-integration",
    linkText: "Integration engineering →",
  },
  {
    badge: "Advanced",
    title: "Silent pilot & live ICU deployment",
    body: "Ready for clinical evaluation? Run a non-interruptive silent pilot to verify alert burden, then go live only after hospital governance sign-off.",
    href: "/for-hospitals",
    linkText: "Hospital adoption path →",
  },
];

export default function HomePage() {
  return (
    <div className="bg-white text-ink">
      {/* 1. CLEAN, BREATHABLE WHITE HERO + INTERACTIVE PRODUCT CAROUSEL */}
      <section className="pt-12 pb-16 sm:pt-16 lg:pb-24">
        <div className="auralis-container-public">
          <Reveal className="mx-auto max-w-3xl text-center">
            <span className="auralis-eyebrow">
              <span className="h-2 w-2 rounded-full bg-teal" />
              Hospital-Local Clinical Intelligence
            </span>
            <h1 className="mt-5 font-display text-4xl font-bold leading-[1.08] tracking-tight text-ink sm:text-6xl">
              Spot ICU sepsis risk{" "}
              <span className="font-serif italic font-normal text-teal">hours earlier.</span>
            </h1>
            <p className="mx-auto mt-5 max-w-2xl text-base leading-7 text-muted sm:text-lg">
              Auralis gives ICU teams a 6-hour early-warning radar, transparent vital drivers, and seamless shift handoffs — running 100% inside your hospital with on-site engineering support.
            </p>

            <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
              <Link href="/signin" className="auralis-btn-primary px-7">
                Open Live ICU Dashboard →
              </Link>
              <Link href="/contact" className="auralis-btn-secondary px-6">
                Book Hospital Consultation
              </Link>
            </div>
          </Reveal>

          {/* Interactive 4-Slide Product Carousel */}
          <Reveal delayMs={120} className="mt-12 lg:mt-14">
            <ProductShowcaseCarousel />
          </Reveal>
        </div>
      </section>

      {/* 2. HOW IT WORKS: CLEAN 4-STEP SIGNAL FLOW */}
      <section className="border-y border-border bg-[#F8FAFA] py-18 lg:py-24">
        <div className="auralis-container-public">
          <Reveal className="flex flex-wrap items-end justify-between gap-6">
            <div className="max-w-xl">
              <span className="auralis-eyebrow">How Auralis Works</span>
              <h2 className="mt-4 font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
                From bedside monitor to clinician decision.
              </h2>
            </div>
            <Link href="/product" className="text-sm font-semibold text-teal hover:underline">
              Explore full platform →
            </Link>
          </Reveal>

          <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {PIPELINE.map((item, idx) => (
              <Reveal
                key={item.step}
                delayMs={idx * 65}
                as="article"
                className="relative rounded-2xl border border-border bg-white p-6 shadow-[0_1px_3px_rgba(15,31,38,0.03)] transition-all hover:-translate-y-0.5 hover:border-teal/40 hover:shadow-md"
              >
                <div className="flex items-center justify-between">
                  <span className="flex h-9 w-9 items-center justify-center rounded-full bg-teal/10 font-display text-xs font-bold text-teal">
                    {item.step}
                  </span>
                  {idx < 3 && <span className="hidden text-muted/40 lg:inline">→</span>}
                </div>
                <h3 className="mt-5 font-display text-xl font-semibold text-ink">{item.name}</h3>
                <p className="mt-1 text-sm font-medium text-ink/85">{item.summary}</p>
                <p className="mt-2 text-xs leading-5 text-muted">{item.detail}</p>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* 3. BUILT FOR EVERY HOSPITAL'S STARTING POINT */}
      <section className="bg-white py-18 lg:py-24">
        <div className="auralis-container-public">
          <Reveal className="max-w-2xl">
            <span className="auralis-eyebrow">Forward Deployed Partnership</span>
            <h2 className="mt-4 font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
              We work with the hospital infrastructure you have today.
            </h2>
            <p className="mt-3 text-base leading-7 text-muted">
              Not every hospital starts with a modern FHIR server. Our engineers assess your rooms, monitors, and IT capacity on-site and build the right path forward.
            </p>
          </Reveal>

          <div className="mt-10 grid gap-6 lg:grid-cols-3">
            {HOSPITAL_TIERS.map((tier, idx) => (
              <Reveal
                key={tier.badge}
                delayMs={idx * 75}
                as="article"
                className="flex flex-col justify-between rounded-2xl border border-border bg-[#FAFBFA] p-7 transition-all hover:border-teal/40 hover:bg-white hover:shadow-sm"
              >
                <div>
                  <span className="inline-block rounded-full bg-white px-3 py-1 text-xs font-semibold text-teal shadow-sm ring-1 ring-border">
                    {tier.badge}
                  </span>
                  <h3 className="mt-4 font-display text-xl font-semibold text-ink">{tier.title}</h3>
                  <p className="mt-2.5 text-sm leading-6 text-muted">{tier.body}</p>
                </div>
                <Link href={tier.href} className="mt-6 inline-block text-sm font-semibold text-teal hover:underline">
                  {tier.linkText}
                </Link>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* 4. DIRECT WORKSPACE ACCESS + CLINICAL INTEGRITY */}
      <section className="border-t border-border bg-[#F8FAFA] py-18 lg:py-24">
        <div className="auralis-container-public grid gap-10 lg:grid-cols-[1fr_1.05fr] lg:items-center">
          <Reveal>
            <span className="auralis-eyebrow">Privacy & Clinical Safety</span>
            <h2 className="mt-4 font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
              Patient data never leaves your hospital. Doctors stay in command.
            </h2>
            <p className="mt-4 text-base leading-7 text-muted">
              Auralis separates the hospital clinical system from vendor billing and support by design. Aurie AI surfaces protocol checklists beside each alert without changing the frozen model probability or issuing autonomous orders.
            </p>

            <div className="mt-6 flex flex-wrap gap-5 text-sm font-semibold text-teal">
              <Link href="/aurie" className="hover:underline">
                How Aurie AI assists →
              </Link>
              <Link href="/security" className="hover:underline">
                Security architecture →
              </Link>
              <Link href="/evidence" className="hover:underline">
                Validation & limits →
              </Link>
            </div>
          </Reveal>

          <Reveal delayMs={90} className="grid gap-3 sm:grid-cols-2">
            {[
              {
                title: "ICU Clinical Dashboard",
                desc: "Live beds, 6h risk curves, alerts & shift handoff.",
                href: "/signin?next=/app/icu",
              },
              {
                title: "Ward NEWS2 View",
                desc: "General ward vitals & deterioration tracking.",
                href: "/signin?next=/app/ward",
              },
              {
                title: "Deployment Console",
                desc: "HL7/FHIR feed health, quarantine & readiness.",
                href: "/signin?next=/deploy",
              },
              {
                title: "Vendor & FDE Plane",
                desc: "Hospital CRM, readiness checklists & licences.",
                href: "/signin?next=/platform/accounts",
              },
            ].map((ws) => (
              <Link
                key={ws.title}
                href={ws.href}
                className="group rounded-2xl border border-border bg-white p-5 transition-all hover:border-teal hover:shadow-sm"
              >
                <div className="flex items-center justify-between">
                  <h3 className="font-display text-base font-semibold text-ink group-hover:text-teal">
                    {ws.title}
                  </h3>
                  <span className="text-xs font-semibold text-teal transition-transform group-hover:translate-x-0.5">
                    Open →
                  </span>
                </div>
                <p className="mt-2 text-xs leading-5 text-muted">{ws.desc}</p>
              </Link>
            ))}
          </Reveal>
        </div>
      </section>

      {/* 5. CLEAN CLOSING CTA */}
      <MarketingCta />
    </div>
  );
}
