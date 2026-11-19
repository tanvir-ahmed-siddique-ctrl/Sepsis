import type { Metadata } from "next";
import Link from "next/link";
import { FeatureGrid, MarketingCta, MarketingHero, MarketingSection } from "@/components/marketing/MarketingPage";
import { Icon } from "@/components/ui/Icon";

export const metadata: Metadata = {
  title: "For Hospitals | Auralis",
  description: "How hospitals adopt Auralis: readiness assessment, on-site integration, silent pilot, and governed live care.",
};

const STEPS = [
  ["01", "Initial Consultation", "Align on clinical goals, units, and hospital stakeholders."],
  ["02", "Infrastructure Audit", "Review servers, network, monitors, and IT staffing."],
  ["03", "Readiness Passport", "Complete our 16-point evidence checklist."],
  ["04", "Connector Engineering", "Map HL7v2, FHIR R4, or CSV feeds and test unit rules."],
  ["05", "Silent Pilot", "Measure feed lag and alert burden with zero bedside interruption."],
  ["06", "Governed Go-Live", "Enable live ICU alerts only after clinical & IT sign-off, backed by ongoing support."],
];

export default function ForHospitalsPage() {
  return (
    <div className="bg-white">
      <MarketingHero
        eyebrow="For Hospitals"
        title={
          <>
            Getting a model into your ICU is a{" "}
            <span className="text-teal">deployment problem.</span>
          </>
        }
        description="You get a holdout-proven six-hour sepsis model — and a safe path to use it: infrastructure readiness, real feed integration, silent evaluation, then live alerts only after IT and clinical sign-off."
        specs={[
          { label: "Hospital Sizes", value: "Small, Tertiary & Multi-Site" },
          { label: "Readiness Tiers", value: "Foundation · Connected · Advanced" },
          { label: "Engineering", value: "On-Site & Remote FDE" },
          { label: "Go-Live Rule", value: "Hospital Governance Sign-Off" },
        ]}
      />

      <MarketingSection
        eyebrow="Adoption Path"
        title="Six stages that treat deployment as the product."
        tone="muted"
      >
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {STEPS.map(([num, title, body]) => (
            <div key={num} className="rounded-2xl border border-border bg-white p-6">
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-teal/10 font-display text-xs font-bold text-teal">
                {num}
              </span>
              <h3 className="mt-4 font-display text-lg font-semibold text-ink">{title}</h3>
              <p className="mt-1.5 text-sm leading-6 text-muted">{body}</p>
            </div>
          ))}
        </div>
      </MarketingSection>

      <MarketingSection eyebrow="Readiness Tiers" title="Tailored to your digital maturity.">
        <FeatureGrid
          items={[
            {
              tag: "Foundation Tier",
              title: "Infrastructure & Device Enablement",
              body: "Server/network planning, monitor compatibility review, and staff training before introducing clinical AI.",
            },
            {
              tag: "Connected Tier",
              title: "HL7 / FHIR Integration & Mapping",
              body: "Connector buildout, unit alignment, and TrustGate quarantine validation on your hospital LAN.",
            },
            {
              tag: "Advanced Tier",
              title: "Silent Evaluation & Live ICU Rollout",
              body: "Shadow-mode validation, clinical governance review, and multi-unit enterprise support.",
            },
            {
              tag: "Long-Term Partnership",
              title: "Training, Upgrades & Managed SLA",
              body: "Role-based onboarding for doctors, nurses, and IT with transparent annual service schedules.",
            },
          ]}
        />
        <div className="mt-8 flex flex-wrap gap-5 text-sm font-semibold text-teal">
          <Link href="/forward-deployed-engineering" className="auralis-link">Forward Deployed Engineering<Icon name="arrow-right" size={16} /></Link>
          <Link href="/technology-enablement" className="auralis-link">Technology Enablement<Icon name="arrow-right" size={16} /></Link>
          <Link href="/site-readiness" className="auralis-link">Site Readiness Checklist<Icon name="arrow-right" size={16} /></Link>
        </div>
      </MarketingSection>

      <MarketingCta />
    </div>
  );
}
