import Link from "next/link";
import type { ReactNode } from "react";
import { Reveal } from "@/components/marketing/MotionPrimitives";
import { Icon } from "@/components/ui/Icon";

export function MarketingHero({
  eyebrow,
  title,
  description,
  primaryHref = "/contact",
  primaryLabel = "Book a consultation",
  secondaryHref = "/signin",
  secondaryLabel = "Open live ICU board",
  specs,
  asideTitle = "Safety boundaries",
  asideItems = [
    "Patient data and scoring stay inside the hospital network.",
    "Clinicians keep full decision authority.",
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
    <section className="overflow-x-clip border-b border-border bg-white py-10 sm:py-14 lg:py-20">
      <div className="auralis-container-public">
        <div className="grid min-w-0 gap-8 lg:grid-cols-[1.25fr_0.75fr] lg:items-center lg:gap-10">
          <Reveal className="min-w-0">
            <span className="auralis-eyebrow">{eyebrow}</span>
            <h1 className="mt-3 max-w-3xl text-[1.65rem] font-semibold leading-[1.15] tracking-[-0.03em] text-ink sm:mt-4 sm:text-4xl sm:leading-[1.08] lg:text-5xl">{title}</h1>
            <p className="mt-4 max-w-2xl text-[15px] leading-7 text-muted sm:mt-5 sm:text-lg sm:leading-8">{description}</p>
            <div className="mt-6 flex w-full flex-col gap-2.5 sm:mt-8 sm:w-auto sm:flex-row sm:flex-wrap sm:items-center sm:gap-3">
              <Link href={primaryHref} className="group auralis-btn-primary w-full justify-center px-6 sm:w-auto">
                {primaryLabel}
                <Icon name="arrow-right" size={16} className="transition-transform group-hover:translate-x-0.5" />
              </Link>
              <Link href={secondaryHref} className="auralis-btn-secondary w-full justify-center px-5 sm:w-auto">
                {secondaryLabel}
              </Link>
            </div>
          </Reveal>

          <Reveal delayMs={90} as="aside" className="rounded-xl border border-border bg-canvas p-6 sm:p-7">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted">{asideTitle}</p>
            <ul className="mt-4 space-y-3.5 text-sm leading-6 text-ink">
              {asideItems.map((line, idx) => (
                <li key={idx} className="flex items-start gap-3">
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-teal-soft text-teal-dark">
                    <Icon name="check" size={13} strokeWidth={2.25} />
                  </span>
                  <span>{line}</span>
                </li>
              ))}
            </ul>
          </Reveal>
        </div>

        {specs && specs.length > 0 && (
          <Reveal delayMs={150} className="mt-12 grid gap-px overflow-hidden rounded-xl border border-border bg-border sm:grid-cols-2 lg:grid-cols-4">
            {specs.map((spec) => (
              <div key={spec.label} className="bg-white px-5 py-4">
                <p className="text-xs font-medium text-muted">{spec.label}</p>
                <p className="mt-1 text-base font-semibold text-ink">{spec.value}</p>
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
  const toneClasses = tone === "muted" || tone === "dark" ? "bg-canvas" : "bg-white";

  return (
    <section className={`overflow-x-clip border-t border-border py-12 sm:py-16 lg:py-24 ${toneClasses}`}>
      <div className="auralis-container-public">
        <Reveal className="max-w-3xl min-w-0">
          <span className="auralis-eyebrow">{eyebrow}</span>
          <h2 className="mt-3 text-[1.65rem] font-semibold leading-tight tracking-[-0.025em] text-ink sm:text-[2.5rem] sm:leading-[1.12]">{title}</h2>
          {description && <p className="mt-3 text-[15px] leading-7 text-muted sm:mt-4 sm:text-base">{description}</p>}
        </Reveal>
        <div className="mt-8 min-w-0 sm:mt-10">{children}</div>
      </div>
    </section>
  );
}

export function FeatureGrid({ items }: { items: Array<{ title: string; body: string; tag?: string }> }) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {items.map((item, idx) => (
        <Reveal
          key={item.title}
          delayMs={Math.min(idx * 50, 200)}
          as="article"
          className="rounded-xl border border-border bg-white p-6 shadow-soft transition-all hover:-translate-y-px hover:shadow-card"
        >
          {item.tag && <span className="text-xs font-semibold uppercase tracking-[0.12em] text-teal">{item.tag}</span>}
          <h3 className="mt-1.5 text-lg font-semibold text-ink">{item.title}</h3>
          <p className="mt-2 text-sm leading-6 text-muted">{item.body}</p>
        </Reveal>
      ))}
    </div>
  );
}

export function MarketingCta() {
  return (
    <section className="overflow-x-clip bg-white py-12 sm:py-16 lg:py-24">
      <div className="auralis-container-public">
        <Reveal className="relative overflow-hidden rounded-2xl bg-navy px-4 py-8 sm:px-8 sm:py-12 lg:flex lg:items-center lg:justify-between lg:gap-10 lg:px-12">
          <svg className="pointer-events-none absolute -right-10 top-1/2 hidden h-[140%] -translate-y-1/2 text-white/[0.06] lg:block" viewBox="0 0 400 200" fill="none" aria-hidden="true">
            <path d="M0 110h90l26-60 40 120 32-84 18 28h194" stroke="currentColor" strokeWidth="10" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <div className="relative min-w-0 max-w-2xl">
            <span className="text-xs font-semibold uppercase tracking-[0.14em] text-[#73C3CF]">Next step</span>
            <h2 className="mt-3 text-[1.65rem] font-semibold leading-tight tracking-[-0.025em] text-white sm:text-4xl">
              Open the board, or book a site talk.
            </h2>
            <p className="mt-3 text-[15px] leading-7 text-white/65 sm:text-base">
              Try the ICU workspace, or talk feeds and readiness with our engineers.
            </p>
          </div>
          <div className="relative mt-6 flex w-full flex-col gap-2.5 sm:mt-8 sm:w-auto sm:flex-row sm:flex-wrap sm:items-center sm:gap-3 lg:mt-0 lg:shrink-0">
            <Link href="/signin" className="group inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-white px-6 text-sm font-semibold text-navy transition-colors hover:bg-[#E8EDF0] sm:w-auto">
              Open live ICU board
              <Icon name="arrow-right" size={16} className="transition-transform group-hover:translate-x-0.5" />
            </Link>
            <Link href="/contact" className="inline-flex h-11 w-full items-center justify-center rounded-lg border border-white/20 px-6 text-sm font-semibold text-white transition-colors hover:border-white/40 hover:bg-white/5 sm:w-auto">
              Book a consultation
            </Link>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
