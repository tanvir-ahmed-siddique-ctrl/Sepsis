import type { Metadata } from "next";
import { FeatureGrid, MarketingCta, MarketingHero, MarketingSection } from "@/components/marketing/MarketingPage";

export const metadata: Metadata = {
  title: "About | Auralis",
  description: "Auralis builds hospital-owned clinical intelligence and long-term healthcare technology partnerships.",
};

export default function AboutPage() {
  return (
    <div className="bg-white">
      <MarketingHero
        eyebrow="About Auralis"
        title={
          <>
            Durable,{" "}
            <span className="font-serif italic font-normal text-teal">hospital-owned</span> clinical intelligence.
          </>
        }
        description="Critical-care software should strengthen a hospital's own clinical and IT teams — not lock patient data inside an opaque cloud black box."
        specs={[
          { label: "Mission", value: "Earlier Signal, Safer Care" },
          { label: "Intelligence", value: "Aurie AI (Bounded Context)" },
          { label: "Delivery", value: "Forward Deployed Engineers" },
          { label: "Standard", value: "Verified Evidence Only" },
        ]}
      />

      <MarketingSection
        eyebrow="Our Principles"
        title="How we build and partner with hospitals."
        tone="muted"
      >
        <FeatureGrid
          items={[
            {
              title: "Honesty in Evidence",
              body: "We keep public holdout benchmarks, synthetic demos, and local hospital clinical validation strictly distinct — with zero exaggerated claims.",
            },
            {
              title: "Local by Default",
              body: "Patient data and real-time sepsis scoring belong inside the hospital's own infrastructure.",
            },
            {
              title: "Engineers at Your Side",
              body: "We help solve real-world monitor, network, and HL7/FHIR challenges before commissioning clinical software.",
            },
            {
              title: "Doctors Hold Authority",
              body: "Every risk score is explainable, TrustGate-checked, and reviewed by an accountable clinician.",
            },
          ]}
        />
      </MarketingSection>

      <MarketingCta />
    </div>
  );
}
