import type { Metadata } from "next";
import { FeatureGrid, MarketingCta, MarketingHero, MarketingSection } from "@/components/marketing/MarketingPage";

export const metadata: Metadata = { title: "Solutions | Auralis", description: "ICU, ward and governance solution map." };

export default function SolutionsPage() {
  return (
    <div>
      <MarketingHero eyebrow="Solutions" title="Solutions shaped around hospital reality." description="Start with one ICU, expand to ward surveillance and governance workflows only after local readiness is demonstrated." />
      <MarketingSection eyebrow="Solution map" title="Where Auralis fits.">
        <FeatureGrid items={[
          { title: "ICU early warning", body: "Six-hour sepsis-risk review for authorized ICU teams." },
          { title: "Ward surveillance", body: "NEWS2 observation and escalation context outside the ICU." },
          { title: "Integration readiness", body: "Mapping, quarantine and connectivity diagnostics before live mode." },
          { title: "Silent evaluation", body: "Shadow scoring and burden measurement without interruptive alerts." },
          { title: "Commercial governance", body: "Contracts, licences and support records in a separate account plane." },
          { title: "Quality operations", body: "CAPA, document retention and support SLA clocks for vendor operations." },
        ]} />
      </MarketingSection>
      <MarketingCta />
    </div>
  );
}
