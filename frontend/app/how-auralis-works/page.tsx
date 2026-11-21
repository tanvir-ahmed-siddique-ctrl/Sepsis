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
        description="Auralis is hospital-facing technology partnership: site assessment, integration engineering, local deployment, training and ongoing support. Auri AI is the assistive co-pilot inside that workflow — not an autonomous treatment system and not the sepsis scorer."
      />
      <MarketingSection eyebrow="Operating model" title="What happens in practice.">
        <FeatureGrid items={[
          { title: "Assess before proposing", body: "Inventory data sources, devices, network, staffing and governance. Clinical AI is not assumed for every site." },
          { title: "Hospital-local by design", body: "Clinical processing stays under hospital-approved control. Auri AI keys, when used, sit on the local server — not in the browser." },
          { title: "Auri AI co-pilot", body: "Shipped: Language dropdown, local Qwen mapping, Profile + admin panels. Coming: handoff drafts and licence-bundled cloud assist entitlement." },
          { title: "FDE implementation", body: "Auralis engineers work with hospital IT during mapping, validation, installation and handover." },
          { title: "Clinician in the loop", body: "Risk scores support review. They are not diagnoses or autonomous treatment recommendations." },
          { title: "Evidence before alerts", body: "Silent evaluation and institutional gates precede interruptive clinical alerts." },
        ]} />
      </MarketingSection>
      <MarketingCta />
    </div>
  );
}
