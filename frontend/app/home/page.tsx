import type { Metadata } from "next";
import Link from "next/link";
import { FeatureGrid, MarketingCta, MarketingHero, MarketingSection } from "@/components/marketing/MarketingPage";

export const metadata: Metadata = {
  title: "Auralis | Hospital-local ICU early warning",
  description: "Auralis hospital-local sepsis-risk review with data quality checks, clinician review and a measured path to deployment.",
};

const stages = [
  { title: "Acquire", body: "Commission an approved HL7, FHIR, CSV or bedside entry path. Map identifiers, units and timestamps before scoring." },
  { title: "Qualify", body: "Check freshness and missing observations. Quarantine untrusted inputs and abstain when required context is unavailable." },
  { title: "Score", body: "Run the frozen sepsis model locally. Show probability, provenance, trend and drivers for each reviewable score." },
  { title: "Respond", body: "Route review to an accountable clinician. Capture acknowledgement, context, feedback and a traceable handoff." },
];

export default function HomePage() {
  return (
    <div className="bg-canvas text-ink">
      <MarketingHero
        eyebrow="Hospital-local intelligence"
        title={<>Earlier signal.<br /><span className="text-teal">Clearer decision.</span></>}
        description="Auralis brings hospital observations, six-hour sepsis risk and accountable bedside review into one ICU workflow. In a hospital deployment, clinical data and scoring stay within the site boundary."
      />

      <MarketingSection eyebrow="Architecture" title="A local path from signal to action." description="Each hospital approves its interface, data boundary and operating mode. Vendor fleet heartbeats carry technical metadata only.">
        <FeatureGrid items={stages} />
      </MarketingSection>

      <MarketingSection eyebrow="Product surfaces" title="One product family. Six clear boundaries.">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[
            ["Hospital Workspace", "Role-specific clinical and administrative views for authorized hospital users.", "/signin"],
            ["Vendor Control Plane", "Tenant, commercial, support and document operations without patient charts.", "/signin"],
            ["Deployment Console", "Site commissioning, interfaces, readiness and silent monitoring.", "/signin"],
            ["Customer Portal", "Organization members, contracts, licences, invoices and support tickets.", "/signin"],
            ["Evaluation Environment", "Isolated synthetic and replay workflows for product evaluation.", "/system-check"],
            ["Public website", "Product, security, resources and consultation requests.", "/product"],
          ].map(([title, body, href]) => (
            <article key={title} className="auralis-panel flex flex-col">
              <h3 className="font-display text-lg font-semibold">{title}</h3>
              <p className="mt-3 flex-1 text-sm leading-6 text-muted">{body}</p>
              <Link href={href} className="mt-5 text-sm font-semibold text-teal hover:text-teal-dark">Open →</Link>
            </article>
          ))}
        </div>
      </MarketingSection>

      <MarketingSection eyebrow="Evidence" title="Evidence travels with the decision." description="Score history, signal freshness, provenance, model limitations and audit are visible. Local validation and alert-burden review remain hospital responsibilities.">
        <div className="grid gap-4 lg:grid-cols-3">
          {[
            ["Retrospective evaluation", "Public-data model evaluation is documented in the evidence view."],
            ["Hospital validation pending", "Calibration, subgroup results and outcomes require a clinical partner."],
            ["No claimed mortality reduction", "Unmeasured clinical benefit is never presented as fact."],
          ].map(([title, body]) => (
            <article key={title} className="border-l-2 border-teal bg-white p-5">
              <h3 className="font-semibold text-ink">{title}</h3>
              <p className="mt-2 text-sm leading-6 text-muted">{body}</p>
            </article>
          ))}
        </div>
        <Link href="/evidence" className="mt-6 inline-block text-sm font-semibold text-teal">Review evidence →</Link>
      </MarketingSection>

      <MarketingCta />
    </div>
  );
}
