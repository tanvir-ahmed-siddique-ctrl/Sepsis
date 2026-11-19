import type { Metadata } from "next";
import Link from "next/link";
import { FeatureGrid, MarketingCta, MarketingHero, MarketingSection } from "@/components/marketing/MarketingPage";
import { ProductShowcaseCarousel } from "@/components/marketing/ProductShowcaseCarousel";
import { Icon } from "@/components/ui/Icon";

export const metadata: Metadata = {
  title: "Platform | Auralis",
  description: "Hospital-local ICU sepsis risk board, bedside charting, TrustGate safety, and shift handoff.",
};

export default function ProductPage() {
  return (
    <div className="bg-white">
      <MarketingHero
        eyebrow="Clinical Platform"
        title={
          <>
            ICU early warning that stays{" "}
            <span className="text-teal">clear at the bedside.</span>
          </>
        }
        description="Auralis brings vitals freshness, 6-hour sepsis risk trends, and accountable alert review into one clean hospital-local workspace."
        specs={[
          { label: "Care Setting", value: "Adult ICU & General Wards" },
          { label: "Prediction Horizon", value: "6-Hour Sepsis Window" },
          { label: "Data Safety", value: "TrustGate Auto-Hold" },
          { label: "Hosting", value: "100% Hospital-Local" },
        ]}
      />

      <MarketingSection
        eyebrow="Interactive Walkthrough"
        title="See every screen your ICU team uses."
        description="Switch through the live board, patient trajectory chart, TrustGate checks, and shift handoff."
        tone="muted"
      >
        <ProductShowcaseCarousel />
      </MarketingSection>

      <MarketingSection
        eyebrow="Intended Use & Boundaries"
        title="Built for clinical safety and transparency."
      >
        <FeatureGrid
          items={[
            {
              title: "Assistive Decision Support",
              tag: "Intended Use",
              body: "Supports early clinical review for adult ICU patients. A risk score is never an autonomous diagnosis or treatment order.",
            },
            {
              title: "Ward NEWS2 Surveillance",
              tag: "Step-Down & General Wards",
              body: "Uses deterministic NEWS2 scoring on general wards rather than misapplying ICU-trained sepsis models.",
            },
            {
              title: "TrustGate Input Protection",
              tag: "Zero Guessed Scores",
              body: "Automatically abstains when required labs are stale and quarantines mismatched units before scoring.",
            },
            {
              title: "Hospital Data Ownership",
              tag: "Local Processing",
              body: "Patient identifiers and observations remain inside your hospital's own network.",
            },
          ]}
        />
        <div className="mt-8 flex flex-wrap gap-5 text-sm font-semibold text-teal">
          <Link href="/signin?next=/app/icu" className="auralis-link">
            Open the live ICU board
            <Icon name="arrow-right" size={16} />
          </Link>
          <Link href="/model" className="auralis-link">
            Read the model card
            <Icon name="arrow-right" size={16} />
          </Link>
        </div>
      </MarketingSection>

      <MarketingCta />
    </div>
  );
}
