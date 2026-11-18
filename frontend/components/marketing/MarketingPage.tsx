import Link from "next/link";
import type { ReactNode } from "react";

export function MarketingHero({
  eyebrow,
  title,
  description,
  primaryHref = "/contact",
  primaryLabel = "Request a Consultation",
  secondaryHref = "/signin",
  secondaryLabel = "Sign In",
}: {
  eyebrow: string;
  title: ReactNode;
  description: string;
  primaryHref?: string;
  primaryLabel?: string;
  secondaryHref?: string;
  secondaryLabel?: string;
}) {
  return (
    <section className="auralis-container-public grid gap-10 py-16 lg:grid-cols-[1.15fr_0.85fr] lg:py-24">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-teal">{eyebrow}</p>
        <h1 className="mt-5 max-w-3xl font-display text-4xl font-semibold leading-[1.1] tracking-tight text-ink sm:text-5xl lg:text-6xl">{title}</h1>
        <p className="mt-6 max-w-xl text-base leading-7 text-muted sm:text-lg">{description}</p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link href={primaryHref} className="auralis-btn-primary">{primaryLabel}</Link>
          <Link href={secondaryHref} className="auralis-btn-secondary">{secondaryLabel}</Link>
        </div>
      </div>
      <aside className="auralis-panel self-start bg-muted-surface">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">Truthful product boundary</p>
        <ul className="mt-4 space-y-3 text-sm leading-6 text-ink">
          <li>Clinical data remains hospital-local in a site deployment.</li>
          <li>Clinicians retain decision authority for every patient action.</li>
          <li>No invented hospitals, outcome claims, or regulatory approvals.</li>
        </ul>
      </aside>
    </section>
  );
}

export function MarketingSection({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <section className="border-t border-border py-14 lg:py-20">
      <div className="auralis-container-public">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-teal">{eyebrow}</p>
        <h2 className="mt-3 max-w-2xl font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl">{title}</h2>
        {description && <p className="mt-4 max-w-2xl text-sm leading-7 text-muted">{description}</p>}
        <div className="mt-8">{children}</div>
      </div>
    </section>
  );
}

export function FeatureGrid({ items }: { items: Array<{ title: string; body: string }> }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {items.map((item) => (
        <article key={item.title} className="auralis-panel">
          <h3 className="font-display text-lg font-semibold text-ink">{item.title}</h3>
          <p className="mt-3 text-sm leading-6 text-muted">{item.body}</p>
        </article>
      ))}
    </div>
  );
}

export function MarketingCta() {
  return (
    <section className="border-t border-border bg-muted-surface py-14">
      <div className="auralis-container-public flex flex-wrap items-end justify-between gap-6">
        <div>
          <h2 className="font-display text-3xl font-semibold tracking-tight text-ink">Ready to discuss a hospital path?</h2>
          <p className="mt-3 max-w-xl text-sm leading-6 text-muted">Start with a site assessment. Silent evaluation and clinical governance come before interruptive alerts.</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link href="/contact" className="auralis-btn-primary">Request a Consultation</Link>
          <Link href="/security" className="auralis-btn-secondary">Review security</Link>
        </div>
      </div>
    </section>
  );
}
