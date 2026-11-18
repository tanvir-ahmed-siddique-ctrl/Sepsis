import type { Metadata } from "next";
import { FeatureGrid, MarketingCta, MarketingHero, MarketingSection } from "@/components/marketing/MarketingPage";

export const metadata: Metadata = {
  title: "How Auralis Works | Auralis",
  description: "Hospital-local clinical intelligence with Forward Deployed Engineering, readiness assessment and governed commissioning.",
};

export default function HowAuralisWorksPage() {
  return (
    <div>
      <MarketingHero
        eyebrow="How Auralis works"
        title="Local software, hospital ownership, measured rollout."
        description="Auralis is hospital-facing technology partnership: site assessment, integration engineering, local deployment, training and ongoing support. Aurie AI is the assistive intelligence component inside that governed workflow — not an autonomous treatment system."
      />
      <MarketingSection eyebrow="Operating model" title="What happens in practice.">
        <FeatureGrid items={[
          { title: "Assess before proposing", body: "Inventory data sources, devices, network, staffing and governance. Clinical AI is not assumed for every site." },
          { title: "Hospital-local by design", body: "Clinical processing is intended to remain under hospital-approved control and deployment architecture." },
          { title: "FDE implementation", body: "Auralis engineers work with hospital IT during mapping, validation, installation and handover." },
          { title: "Clinician in the loop", body: "Risk scores support review. They are not diagnoses or autonomous treatment recommendations." },
          { title: "Evidence before alerts", body: "Silent evaluation and institutional gates precede interruptive clinical alerts." },
          { title: "Contracted support", body: "Maintenance, training refresh and releases follow the approved service scope — not unlimited claims." },
        ]} />
      </MarketingSection>
      <MarketingCta />
    </div>
  );
}
