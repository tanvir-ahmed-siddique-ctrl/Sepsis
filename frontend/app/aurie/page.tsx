import type { Metadata } from "next";
import { FeatureGrid, MarketingCta, MarketingHero, MarketingSection } from "@/components/marketing/MarketingPage";

export const metadata: Metadata = { title: "Aurie AI | Auralis", description: "Aurie assists with clinical context without changing model probability." };

export default function AuriePage() {
  return (
    <div>
      <MarketingHero eyebrow="Aurie AI" title="Assistance that never overrides the clinician." description="Aurie provides structured context and guideline retrieval around a risk review. Retrieved text does not change the sepsis-risk probability." />
      <MarketingSection eyebrow="Design principles" title="Bounded intelligence for clinical work.">
        <FeatureGrid items={[
          { title: "Human oversight", body: "Every actionable path remains a named clinician decision." },
          { title: "Separated from scoring", body: "Assistive text is distinct from the frozen model output." },
          { title: "Auditable use", body: "Review history and acknowledgements remain part of the clinical record path." },
          { title: "No autonomous orders", body: "Aurie does not place orders, diagnoses or treatment plans." },
        ]} />
      </MarketingSection>
      <MarketingCta />
    </div>
  );
}
