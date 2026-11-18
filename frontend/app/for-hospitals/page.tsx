import type { Metadata } from "next";
import Link from "next/link";
import { FeatureGrid, MarketingCta, MarketingHero, MarketingSection } from "@/components/marketing/MarketingPage";

export const metadata: Metadata = {
  title: "For Hospitals | Auralis",
  description: "Hospital technology partnership journey: assessment, enablement, FDE integration and governed clinical intelligence when eligible.",
};

const journey = [
  ["01", "Initial consultation", "Institutional discovery of goals, constraints and stakeholders."],
  ["02", "Workflow & stakeholder discovery", "Clinical, IT, biomedical and procurement owners identified."],
  ["03", "Hospital & infrastructure assessment", "Servers, network, workstations, storage and staffing capacity."],
  ["04", "Site-readiness assessment", "Evidence-backed checklist — not an automatic AI eligibility score."],
  ["05", "Integration architecture & feasibility", "Supported interfaces only; gaps documented plainly."],
  ["06", "Approved test-data & connector validation", "Sandbox or approved test feeds before production mapping."],
  ["07", "Hospital-specific retrospective evaluation", "Only where locally authorized and scoped."],
  ["08", "Silent / shadow evaluation", "Where appropriate — non-interruptive measurement."],
  ["09", "Clinical & institutional governance review", "Hospital owners decide go / no-go."],
  ["10", "Governed commissioning", "Only when technical, clinical, security and institutional gates pass."],
  ["11", "Ongoing support & maintenance", "Contracted support, training refresh and release governance."],
  ["12", "Renewal, improvement & expansion", "Units, sites or services expand only under approved change control."],
];

export default function ForHospitalsPage() {
  return (
    <div>
      <MarketingHero
        eyebrow="For Hospitals"
        title="A hospital technology & clinical intelligence partner."
        description="Auralis works with each hospital’s existing infrastructure, clinical requirements and digital maturity. Clinical intelligence is considered only when intended use, data quality, ownership, validation and governance requirements are satisfied."
      />

      <MarketingSection eyebrow="Adoption journey" title="How hospitals engage with Auralis.">
        <p className="mb-8 max-w-3xl text-sm leading-7 text-slate">
          Auralis engineers work alongside hospital IT and clinical teams during assessment, integration and deployment. Size does not equal readiness — a small hospital may be advanced; a large hospital may need foundational infrastructure work first.
        </p>
        <ol className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {journey.map(([n, title, body]) => (
            <li key={n} className="border-t border-[#D6DCD8] pt-4">
              <span className="font-mono text-xs text-forest">{n}</span>
              <h3 className="mt-2 font-semibold">{title}</h3>
              <p className="mt-2 text-sm leading-6 text-slate">{body}</p>
            </li>
          ))}
        </ol>
        <div className="mt-8 overflow-x-auto border border-[#D6DCD8] bg-warm p-4 text-xs leading-6 text-slate">
          <pre className="font-mono whitespace-pre">{`Consultation → Discovery → Readiness → Integration → Evaluation → Governance → Commissioning → Support
Foundation hospitals may stop at infrastructure & training until gates are met.`}</pre>
        </div>
      </MarketingSection>

      <MarketingSection eyebrow="Readiness tiers" title="Foundation, Connected, Advanced.">
        <FeatureGrid items={[
          { title: "Foundation", body: "Limited IT, fragmented records or connectivity gaps. Focus: assessment, network/server planning, equipment compatibility, foundational training — not automatic clinical AI." },
          { title: "Connected", body: "Some digital systems and structured sources with identifiable gaps. Focus: integration feasibility, mapping, managed IT and readiness for clinical intelligence evaluation." },
          { title: "Advanced", body: "Established infrastructure, owners and governance pathways. Focus: advanced integration, eligible local evaluation, managed operations and multi-unit coordination." },
        ]} />
      </MarketingSection>

      <MarketingSection eyebrow="Related" title="Hospital-facing guides.">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 text-sm">
          {[
            ["/how-auralis-works", "How Auralis works"],
            ["/technology-enablement", "Hospital technology enablement"],
            ["/forward-deployed-engineering", "Forward Deployed Engineering"],
            ["/site-readiness", "Site readiness"],
            ["/clinical-evaluation-governance", "Clinical evaluation & governance"],
            ["/managed-technology-services", "Managed technology services"],
            ["/clinical-education", "Clinical education & training"],
            ["/deployment-integration", "Deployment & integration"],
            ["/security", "Security & data privacy"],
            ["/business", "Commercial approach"],
            ["/contact", "Contact Auralis"],
          ].map(([href, label]) => (
            <Link key={href} href={href} className="border-t border-[#D6DCD8] pt-3 font-semibold text-forest underline underline-offset-2">{label}</Link>
          ))}
        </div>
      </MarketingSection>

      <MarketingCta />
    </div>
  );
}
