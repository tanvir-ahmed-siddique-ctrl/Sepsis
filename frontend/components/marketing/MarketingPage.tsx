import Link from "next/link";
import type { ReactNode } from "react";
import { Reveal } from "@/components/marketing/MotionPrimitives";

export function MarketingHero({
  eyebrow,
  title,
  description,
  primaryHref = "/contact",
  primaryLabel = "Book a Consultation",
  secondaryHref = "/signin",
  secondaryLabel = "Open Live Demo",
  specs,
  asideTitle = "Core Safety Guarantees",
  asideItems = [
    "100% hospital-local patient data & scoring.",
    "Doctors retain full clinical decision authority.",
    "TrustGate holds scores when lab or vital feeds are stale.",
  ],
}: {
  eyebrow: string;
  title: ReactNode;
  description: string;
  primaryHref?: string;
  primaryLabel?: string;
  secondaryHref?: string;
  secondaryLabel?: string;
  specs?: Array<{ label: string; value: string }>;
  asideTitle?: string;
  asideItems?: string[];
}) {
  return (
    <section className="border-b border-border bg-white py-14 lg:py-20">
      <div className="auralis-container-public">
        <div className="grid gap-10 lg:grid-cols-[1.2fr_0.8fr] lg:items-center">
          <Reveal>
            <span className="auralis-eyebrow">{eyebrow}</span>
            <h1 className="mt-5 max-w-3xl font-display text-4xl font-semibold leading-[1.08] tracking-tight text-ink sm:text-5xl">
              {title}
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-muted sm:text-lg">{description}</p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link href={primaryHref} className="auralis-btn-primary px-6">
                {primaryLabel}
              </Link>
              <Link href={secondaryHref} className="auralis-btn-secondary px-5">
                {secondaryLabel}
              </Link>
            </div>
          </Reveal>

          <Reveal delayMs={90} as="aside" className="rounded-2xl border border-border bg-[#F8FAFA] p-6 sm:p-7">
            <p className="text-xs font-semibold uppercase tracking-wider text-teal">{asideTitle}</p>
            <ul className="mt-4 space-y-3 text-sm leading-6 text-ink">
              {asideItems.map((line, idx) => (
                <li key={idx} className="flex items-start gap-3">
                  <span className="mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-teal/10 text-xs font-semibold text-teal">
                    ✓
                  </span>
                  <span>{line}</span>
                </li>
              ))}
            </ul>
          </Reveal>
        </div>

        {specs && specs.length > 0 && (
          <Reveal delayMs={150} className="mt-12 grid gap-4 border-t border-border pt-7 sm:grid-cols-2 lg:grid-cols-4">
            {specs.map((spec) => (
              <div key={spec.label} className="rounded-xl bg-[#F8FAFA] px-4 py-3.5">
                <p className="text-xs font-medium text-muted">{spec.label}</p>
                <p className="mt-1 font-display text-base font-semibold text-ink">{spec.value}</p>
              </div>
            ))}
          </Reveal>
        )}
      </div>
    </section>
  );
}

export function MarketingSection({
  eyebrow,
  title,
  description,
  tone = "light",
  children,
}: {
  eyebrow: string;
  title: ReactNode;
  description?: string;
  tone?: "light" | "muted" | "dark";
  children: ReactNode;
}) {
  const toneClasses = tone === "muted" || tone === "dark" ? "bg-[#F8FAFA] border-t border-border" : "bg-white border-t border-border";

  return (
    <section className={`py-16 lg:py-22 ${toneClasses}`}>
      <div className="auralis-container-public">
        <Reveal className="max-w-3xl">
          <span className="auralis-eyebrow">{eyebrow}</span>
          <h2 className="mt-4 font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl">{title}</h2>
          {description && <p className="mt-3 text-base leading-7 text-muted">{description}</p>}
        </Reveal>
        <div className="mt-10">{children}</div>
      </div>
    </section>
  );
}

export function FeatureGrid({ items }: { items: Array<{ title: string; body: string; tag?: string }> }) {
  return (
    <div className="grid gap-5 md:grid-cols-2">
      {items.map((item, idx) => (
        <Reveal
          key={item.title}
          delayMs={Math.min(idx * 50, 200)}
          as="article"
          className="rounded-2xl border border-border bg-white p-6 transition-all hover:border-teal/40 hover:shadow-sm"
        >
          {item.tag && <span className="text-xs font-semibold text-teal">{item.tag}</span>}
          <h3 className="mt-1 font-display text-lg font-semibold text-ink">{item.title}</h3>
          <p className="mt-2 text-sm leading-6 text-muted">{item.body}</p>
        </Reveal>
      ))}
    </div>
  );
}

export function MarketingCta() {
  return (
    <section className="border-t border-border bg-white py-16 lg:py-22">
      <div className="auralis-container-public">
        <Reveal className="rounded-3xl border border-teal/20 bg-gradient-to-br from-[#F2F9F9] via-white to-[#F7FAFA] p-8 sm:p-12 lg:flex lg:items-center lg:justify-between lg:gap-10">
          <div className="max-w-2xl">
            <span className="auralis-eyebrow">Get Started</span>
            <h2 className="mt-4 font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
              Explore the live ICU workspace or book a site assessment.
            </h2>
            <p className="mt-3 text-base leading-7 text-muted">
              Try the interactive demo dashboard immediately with one click, or talk with our engineering team about HL7/FHIR integration and hospital readiness.
            </p>
          </div>
          <div className="mt-7 flex flex-wrap items-center gap-3 lg:mt-0 lg:shrink-0">
            <Link href="/signin" className="auralis-btn-primary px-6">
              Launch Live Dashboard →
            </Link>
            <Link href="/contact" className="auralis-btn-secondary px-6">
              Book Consultation
            </Link>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
