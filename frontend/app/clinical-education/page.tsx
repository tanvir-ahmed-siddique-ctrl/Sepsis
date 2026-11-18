import type { Metadata } from "next";
import { FeatureGrid, MarketingCta, MarketingHero, MarketingSection } from "@/components/marketing/MarketingPage";

export const metadata: Metadata = {
  title: "Clinical Education & Training | Auralis",
  description: "Evidence-based staff onboarding, workflow education and technical workshops without purchase pressure.",
};

export default function ClinicalEducationPage() {
  return (
    <div>
      <MarketingHero
        eyebrow="Clinical education & training"
        title="Capability building without purchase pressure."
        description="Education supports responsible technology adoption. It must remain evidence-based and must not pressure clinicians to purchase, prescribe, adopt or endorse Auralis."
      />
      <MarketingSection eyebrow="Programme themes" title="Potential activities.">
        <FeatureGrid items={[
          { title: "Staff onboarding", body: "Scoped complimentary training where staffing and budget allow — not unlimited free seminars." },
          { title: "Clinical workflow education", body: "Doctor and nurse technology training with attendance records." },
          { title: "Data-quality workshops", body: "ICU observation quality, timestamps and interface literacy." },
          { title: "IT & interoperability workshops", body: "Hospital technical staff knowledge transfer." },
          { title: "Seminars & collaborations", body: "Hospital-hosted or institutional events — affiliations and CME only when genuinely granted." },
          { title: "Disclosures", body: "Speaker disclosures and sponsor transparency; no gifts linked to purchasing decisions." },
        ]} />
      </MarketingSection>
      <MarketingCta />
    </div>
  );
}