import Link from "next/link";

const offers = [
  { step: "01", title: "Readiness assessment", fee: "One-time fee", detail: "Source inventory, sample export, timestamp and mapping review, security and governance route. Ends with a scoped go/no-go report." },
  { step: "02", title: "Silent evaluation", fee: "Fixed pilot fee", detail: "Hospital-approved, non-interruptive evaluation of data quality, local model behavior, alert burden and clinician workflow." },
  { step: "03", title: "Implementation", fee: "One-time project fee", detail: "Connector commissioning, hospital identity setup, training by shift, restore exercise and governance sign-off." },
  { step: "04", title: "Annual site licence", fee: "Recurring subscription", detail: "One ICU site with governed workflow, audit, updates and a contracted support tier. Additional units and adapters are scoped separately." },
];

export default function BusinessPage() {
  return <div className="mx-auto max-w-6xl space-y-10 pb-16">
    <header className="max-w-3xl pt-8"><p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">For hospitals</p>
      <h1 className="mt-3 font-display text-4xl leading-tight sm:text-5xl">A measured path from ICU data to a usable early warning workflow.</h1>
      <p className="mt-5 text-lg leading-8 text-ink/70">PredictRx combines hospital-local data mapping, input quality checks, model abstention, clinician review and silent evaluation. The hospital chooses whether evidence supports a later clinical rollout.</p>
      <div className="mt-6 flex flex-wrap gap-3"><Link href="/connection" className="bg-accent px-5 py-3 text-sm font-medium text-white">Explore integration</Link><Link href="/judge" className="bg-white px-5 py-3 text-sm font-medium text-ink">Review evidence</Link></div>
    </header>
    <section aria-labelledby="offer-title"><h2 id="offer-title" className="font-display text-3xl">How a hospital adopts</h2>
      <div className="mt-5 grid gap-6 md:grid-cols-2">{offers.map(offer=><article key={offer.step} className="bg-white p-6 shadow-sm"><p className="text-xs font-semibold tracking-widest text-accent">{offer.step} / {offer.fee}</p><h3 className="mt-3 font-display text-2xl">{offer.title}</h3><p className="mt-3 text-sm leading-7 text-ink/70">{offer.detail}</p></article>)}</div>
    </section>
    <section className="grid gap-6 bg-ink p-7 text-white md:grid-cols-2"><div><h2 className="font-display text-3xl">Commercial model</h2><p className="mt-3 text-sm leading-7 text-white/75">A scoped readiness fee, a fixed pilot, implementation services and an annual one-ICU subscription. Pricing depends on source systems, site support needs and procurement. We do not charge per alert or per patient.</p></div><div><h3 className="text-sm font-semibold uppercase tracking-wider text-white/60">What the hospital receives</h3><ul className="mt-3 space-y-2 text-sm leading-6"><li>Data and mapping assessment before a clinical claim</li><li>Staff training and agreed support ownership</li><li>Local performance, burden and data-quality review</li><li>Versioned changes, audit and an exit/backup process</li></ul></div></section>
    <p className="text-xs leading-6 text-ink/55">Current status: working prototype with retrospective public-data evidence. No live hospital integration, Bangladesh clinical validation, confirmed customer or outcome-improvement claim. Indicative commercial structure is a hypothesis pending buyer discovery.</p>
  </div>;
}
