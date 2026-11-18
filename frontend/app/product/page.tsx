import type { Metadata } from "next";
import { FeatureGrid, MarketingCta, MarketingHero, MarketingSection } from "@/components/marketing/MarketingPage";

export const metadata: Metadata = {
  title: "Product | Auralis",
  description: "Hospital-local ICU risk review: intended use, TrustGate, clinician-in-the-loop operation and evidence boundary.",
};

export default function ProductPage() {
  return (
    <div>
      <MarketingHero
        eyebrow="Product"
        title="ICU risk review that stays inspectable."
        description="Auralis combines observation quality checks, a frozen six-hour sepsis-risk model and clinician acknowledgement into a hospital-local workflow. A risk score is not a diagnosis or autonomous treatment recommendation."
      />
      <MarketingSection eyebrow="Capabilities" title="What the product delivers today.">
        <FeatureGrid items={[
          { title: "ICU board", body: "Unit-level risk overview with provenance, freshness and review status." },
          { title: "Patient chart", body: "Trends, drivers and observation context for authorized clinicians." },
          { title: "Alert review", body: "SLA-aware acknowledgement with accountable clinical ownership." },
          { title: "Handoff", body: "Shift-ready summaries without replacing clinical judgment." },
          { title: "Ward NEWS2", body: "Deterministic ward scoring for non-ICU surveillance contexts." },
          { title: "TrustGate", body: "Abstain and quarantine when required data quality is missing." },
        ]} />
      </MarketingSection>
      <MarketingSection eyebrow="Intended use & limits" title="Clinical and technical boundary.">
        <FeatureGrid items={[
          { title: "Intended use", body: "Assistive early-warning / risk review for adult ICU sepsis-risk workflows within licensed scope." },
          { title: "Care setting", body: "Hospital units under institutional governance — not consumer or autonomous ICU control." },
          { title: "Clinician in the loop", body: "Clinicians retain decision authority for every patient action." },
          { title: "Evidence status", body: "Retrospective public-data evidence is distinct from local hospital validation and prospective evaluation." },
          { title: "Patient-data boundary", body: "Clinical data remains under hospital-approved control in a site deployment." },
          { title: "Interoperability", body: "Supported connectors only; FHIR availability does not guarantee every hospital integration." },
        ]} />
      </MarketingSection>
      <MarketingCta />
    </div>
  );
}
