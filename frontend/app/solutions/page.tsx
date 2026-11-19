import type { Metadata } from "next";
import Link from "next/link";
import { FeatureGrid, MarketingCta, MarketingHero, MarketingSection } from "@/components/marketing/MarketingPage";
import { Icon } from "@/components/ui/Icon";

export const metadata: Metadata = {
  title: "Solutions | Auralis",
  description: "ICU sepsis early warning, ward NEWS2 surveillance, HL7/FHIR integration, and hospital technology enablement.",
};

export default function SolutionsPage() {
  return (
    <div className="bg-white">
      <MarketingHero
        eyebrow="Solutions"
        title={
          <>
            Clinical intelligence &{" "}
            <span className="text-teal">hospital engineering.</span>
          </>
        }
        description="Start with infrastructure readiness, HL7/FHIR integration, or a silent ICU evaluation — scoped cleanly to what your hospital needs."
      />

      <MarketingSection eyebrow="Core Solutions" title="Four modular tracks." tone="muted">
        <FeatureGrid
          items={[
            {
              tag: "Adult ICU",
              title: "6-Hour Sepsis Early Warning",
              body: "Real-time risk trends, physiological driver explanations, SLA alert timers, and shift handoff.",
            },
            {
              tag: "General Wards",
              title: "Deterministic NEWS2 Surveillance",
              body: "Structured vital-sign scoring and deterioration visibility outside the ICU.",
            },
            {
              tag: "Integration",
              title: "Forward Deployed HL7 & FHIR Engineering",
              body: "On-site connector buildout, unit alignment, and quarantine protection for hospital IT.",
            },
            {
              tag: "Enablement",
              title: "Servers, Networking & Device Readiness",
              body: "Hardware planning, monitor compatibility checks, and staff onboarding for growing hospitals.",
            },
          ]}
        />
        <div className="mt-8 flex flex-wrap gap-5 text-sm font-semibold text-teal">
          <Link href="/signin" className="auralis-link">Open live ICU board<Icon name="arrow-right" size={16} /></Link>
          <Link href="/deployment-integration" className="auralis-link">Integration Details<Icon name="arrow-right" size={16} /></Link>
        </div>
      </MarketingSection>

      <MarketingCta />
    </div>
  );
}
