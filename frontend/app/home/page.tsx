import Link from "next/link";

const steps = [
  ["01", "Hospital systems", "ADT, FHIR, HL7, CSV or structured bedside charting enter through a site-approved interface."],
  ["02", "Local edge", "Identifiers, timestamps, codes and units are reconciled on the hospital network. Unusable observations are quarantined."],
  ["03", "Clinical review", "The frozen model scores when inputs are sufficient; TrustGate, alert ownership and audit keep review human-led."],
  ["04", "Vendor fleet", "Signed operational heartbeats report technical health without sending patient charts to the vendor."],
];

export default function HomePage() {
  return <div className="mx-auto max-w-7xl space-y-12 bg-[#080C14] px-5 pb-16 text-slate-50 sm:px-8">
    <header className="grid gap-8 py-10 lg:grid-cols-[1.2fr_.8fr] lg:items-end">
      <div><p className="text-xs font-semibold uppercase tracking-[.22em] text-cyan-400">PredictRx Sentinel / Hospital intelligence</p>
        <h1 className="mt-4 max-w-3xl font-display text-5xl leading-tight">An ICU early warning workflow built around the hospital.</h1>
        <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-300">Connect local data, inspect its quality, review a six-hour sepsis risk score, and keep clinical decisions with the care team.</p>
        <div className="mt-7 flex flex-wrap gap-3"><Link href="/login" className="bg-cyan-500 px-5 py-3 text-sm font-semibold text-slate-950">Enterprise sign in</Link><Link href="/evaluator" className="bg-slate-800 px-5 py-3 text-sm font-semibold text-slate-50">Jury & evaluator access</Link></div>
      </div>
      <div className="bg-[#0F172A] p-7 text-slate-50"><p className="text-xs uppercase tracking-widest text-slate-400">Deployment principle</p><p className="mt-4 font-display text-3xl">Patient data stays at the site.</p><p className="mt-3 text-sm leading-7 text-slate-300">Hospital-local scoring and a separate metadata-only fleet path. A connection or clinical benefit is assessed at each site; neither is assumed.</p></div>
    </header>
    <section><h2 className="font-display text-3xl">System path</h2><div className="mt-5 grid gap-3 md:grid-cols-4">{steps.map(([number,title,detail])=><article key={number} className="bg-[#0F172A] p-5"><p className="font-mono text-xs text-cyan-400">{number}</p><h3 className="mt-3 font-semibold">{title}</h3><p className="mt-2 text-sm leading-6 text-slate-300">{detail}</p></article>)}</div></section>
    <section className="grid gap-5 lg:grid-cols-2"><Link href="/business" className="bg-[#0F172A] p-7"><h2 className="font-display text-2xl">Adoption & licensing</h2><p className="mt-3 text-sm leading-6 text-slate-300">Readiness assessment, silent evaluation, implementation, annual site licence and support.</p><span className="mt-4 inline-block text-sm font-semibold text-cyan-400">Explore the offer →</span></Link><Link href="/connection" className="bg-[#0F172A] p-7"><h2 className="font-display text-2xl">Integration without replacing the HIS</h2><p className="mt-3 text-sm leading-6 text-slate-300">A staged connection ladder with mapping review, quarantine and manual entry where required.</p><span className="mt-4 inline-block text-sm font-semibold text-cyan-400">See the architecture →</span></Link></section>
    <p className="text-xs leading-6 text-slate-400">Prototype status: retrospective public-data model evidence; no live hospital integration, Bangladesh clinical validation or demonstrated patient-outcome benefit.</p>
  </div>;
}
