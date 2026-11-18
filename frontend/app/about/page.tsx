import type { Metadata } from "next";
import { FeatureGrid, MarketingCta, MarketingHero, MarketingSection } from "@/components/marketing/MarketingPage";

export const metadata: Metadata = { title: "About | Auralis", description: "About Auralis and the product mission." };

export default function AboutPage() {
  return (
    <div>
      <MarketingHero eyebrow="About" title="Auralis builds hospital-owned clinical intelligence." description="The product focuses on early warning, data quality and accountable review. It is not a claim of regulatory clearance or completed hospital clinical validation." />
      <MarketingSection eyebrow="Principles" title="How we work.">
        <FeatureGrid items={[
          { title: "Honesty in evidence", body: "Retrospective results, synthetic evaluation and live hospital validation are kept distinct." },
          { title: "Local by default", body: "Clinical scoring and patient data belong with the hospital." },
          { title: "Separation of planes", body: "Vendor commercial systems do not become a chart viewer." },
          { title: "Clinician authority", body: "Software informs review; clinicians decide." },
        ]} />
      </MarketingSection>
      <MarketingCta />
    </div>
  );
}
