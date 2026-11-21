import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Hospital services | Auralis",
  description: "Site assessment, integration, managed edge support and governed evaluation for hospital-local ICU intelligence.",
};

const engagements = [
  ["Discover", "Any site", "Data, workflow, device and infrastructure assessment; a scoped deployment proposal.", "Hospital access to clinical and technical owners"],
  ["Bridge Start", "Basic digitization", "Structured capture or approved batch import, mapping and data-quality checks.", "Approved source data and identifiers"],
  ["Bridge Connect", "Connected site", "Commission an approved HL7, FHIR, API or vendor feed with a local gateway.", "Interface permission and site-specific validation"],
  ["Managed Edge", "Limited local IT capacity", "Agreed appliance, backup, updates, feed monitoring, helpdesk and support scope.", "Institutional contact, clinical owner and agreed service hours"],
  ["Validated Evaluation", "Evidence-ready site", "Approved local retrospective review, silent evaluation and reporting.", "Governance, data access and clinical review approvals"],
  ["Clinical Workflow Licence", "Approved clinical rollout", "Licensed modules and support under a site-specific agreement.", "Required evidence, regulatory review and hospital sign-off"],
];

export default function ServicesPage() {
  return <div className="mx-auto max-w-6xl space-y-12 py-10 sm:py-16">
    <header className="grid gap-8 border-b border-[#D6DCD8] pb-12 lg:grid-cols-[1fr_1.3fr]">
      <div><p className="text-xs font-semibold uppercase tracking-[.18em] text-forest">Auralis / hospital services</p><h1 className="mt-5 font-display text-5xl leading-tight">A deployment shaped by the hospital.</h1></div>
      <div className="self-end"><p className="text-lg leading-8 text-slate">We assess data, devices, workflow and infrastructure before proposing software or support. Every engagement is scoped individually after a site-readiness assessment.</p><p className="mt-5 text-sm leading-6 text-slate">The flagship clinical system focuses on adult ICU sepsis-risk review (Frozen LightGBM Run 4). Auri AI is the separate local co-pilot for mapping and bounded assist — not the sepsis model.</p></div>
    </header>
    <section aria-labelledby="engagements"><div className="flex flex-wrap items-end justify-between gap-4"><h2 id="engagements" className="text-2xl font-semibold">Engagement models</h2><span className="text-sm text-slate">No public price list · institutional proposal</span></div><div className="mt-6 divide-y divide-[#D6DCD8] border-y border-[#D6DCD8]">{engagements.map(([name,fit,scope,prerequisite],index)=><article key={name} className="grid gap-3 py-6 md:grid-cols-[3rem_12rem_1fr_1fr]"><span className="font-mono text-xs text-forest">0{index+1}</span><div><h3 className="font-semibold">{name}</h3><p className="mt-1 text-xs text-slate">{fit}</p></div><p className="text-sm leading-6">{scope}</p><p className="text-sm leading-6 text-slate"><strong className="text-ink">Requires:</strong> {prerequisite}</p></article>)}</div></section>
    <section className="grid gap-8 bg-warm p-7 lg:grid-cols-2"><div><h2 className="text-2xl font-semibold">Managed IT & Edge Services</h2><p className="mt-4 text-sm leading-7 text-slate">For a hospital with limited IT capacity, a contract can cover an approved local server or appliance, storage, backup checks, connector monitoring, updates, helpdesk and scheduled visits. Device sourcing and servicing require qualified suppliers and agreed warranty responsibilities.</p></div><div><h2 className="text-2xl font-semibold">Governed operations</h2><p className="mt-4 text-sm leading-7 text-slate">The hospital appoints an institutional contact and clinical owner. Support hours, response targets, covered assets and exclusions are written into the agreement. Regulatory coordination supports documentation and review; qualified counsel supplies legal advice.</p></div></section>
    <section aria-labelledby="journey" className="space-y-5"><h2 id="journey" className="text-2xl font-semibold">From first contact to local operation</h2><div className="grid gap-5 border-t border-[#D6DCD8] pt-6 md:grid-cols-4">{[
      ["01", "Assess", "Inventory available observations, timestamps, device exports, clinical ownership and local infrastructure."],
      ["02", "Scope", "Agree on interfaces, hardware, training, support hours, exclusions and an institutional proposal."],
      ["03", "Commission", "Test mappings, data quality, access, backups and downtime procedures on the hospital network."],
      ["04", "Evaluate", "Run approved silent evaluation. Clinical alerts require evidence, governance review and readiness gates."],
    ].map(([number,title,detail])=><article key={number}><span className="font-mono text-xs text-forest">{number}</span><h3 className="mt-3 font-semibold">{title}</h3><p className="mt-2 text-sm leading-6 text-slate">{detail}</p></article>)}</div></section>
    <section className="grid gap-8 border-t border-[#D6DCD8] pt-7 lg:grid-cols-2"><div><h2 className="text-xl font-semibold">Hardware & continuity</h2><p className="mt-3 text-sm leading-7 text-slate">Monitor and gateway compatibility must be checked by vendor, model and firmware. Procurement, lease, installation, maintenance and warranty responsibilities are agreed with qualified suppliers. The site plans power continuity, backups and restore checks for its local deployment.</p></div><div><h2 className="text-xl font-semibold">Training & regulatory coordination</h2><p className="mt-3 text-sm leading-7 text-slate">Role-based onboarding and refresher training need completion records. We can coordinate intended-use, privacy, security, pilot and change-control documents. Legal opinions and country-specific sign-off come from qualified external counsel.</p></div></section>
    <p className="border-l-2 border-forest pl-5 text-sm leading-7">Every hospital has a different clinical, data and infrastructure environment. Engagements are scoped individually following a site-readiness assessment. Contact our team through an established institutional channel for a tailored proposal.</p>
    <Link href="/" className="inline-block text-sm font-semibold text-forest underline underline-offset-4">Return to Auralis overview</Link>
  </div>;
}
