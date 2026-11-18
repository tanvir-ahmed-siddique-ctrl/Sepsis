import type { Metadata } from "next";
import { FeatureGrid, MarketingCta, MarketingHero, MarketingSection } from "@/components/marketing/MarketingPage";

export const metadata: Metadata = {
  title: "Clinical Evaluation & Governance | Auralis",
  description: "Retrospective evidence, silent evaluation and institutional governance gates before clinical commissioning.",
};

export default function ClinicalEvaluationGovernancePage() {
  return (
    <div>
      <MarketingHero
        eyebrow="Clinical evaluation & governance"
        title="Technical install is not clinical commissioning."
        description="A risk score is not a diagnosis or autonomous treatment recommendation. Local retrospective evaluation, silent/shadow periods and hospital sign-off are separate gates."
      />
      <MarketingSection eyebrow="Evidence boundary" title="What is distinguished.">
        <FeatureGrid items={[
          { title: "Retrospective public-data evidence", body: "Research baseline — not Bangladesh hospital validation by default." },
          { title: "Hospital-authorized retrospective evaluation", body: "Requires local permissions, protocol and owners." },
          { title: "Silent / shadow evaluation", body: "Measures feed quality, latency, alert burden and clinician feedback without interruptive alerts." },
          { title: "Governed production", body: "Only after technical, clinical, security and institutional approvals." },
          { title: "Model changes", body: "Clinician-reviewed change control with versioning and rollback — no automatic online learning." },
          { title: "Patient data control", body: "Hospital-controlled processing arrangements; partnership does not grant unrestricted reuse." },
        ]} />
      </MarketingSection>
      <MarketingCta />
    </div>
  );
}
