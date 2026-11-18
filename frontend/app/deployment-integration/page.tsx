import type { Metadata } from "next";
import { FeatureGrid, MarketingCta, MarketingHero, MarketingSection } from "@/components/marketing/MarketingPage";

export const metadata: Metadata = { title: "Deployment & Integration | Auralis", description: "How Auralis connects to hospital systems without inventing unsupported integrations." };

export default function DeploymentIntegrationPage() {
  return (
    <div>
      <MarketingHero eyebrow="Deployment & Integration" title="Connect only what the site can support." description="HL7, FHIR, CSV and approved adapters are commissioned against the hospital's real interfaces. Unsupported integrations are never shown as live." />
      <MarketingSection eyebrow="Deployment console" title="Commissioning tools for technical teams.">
        <FeatureGrid items={[
          { title: "Interface health", body: "Connector status, quarantine and mapping diagnostics." },
          { title: "Connectivity ladder", body: "Stepwise validation from network reachability to payload trust." },
          { title: "Readiness gates", body: "Silent-to-live controls that refuse unsafe activation." },
          { title: "Backup visibility", body: "Operational checks remain hospital-owned and evidence-backed." },
        ]} />
      </MarketingSection>
      <MarketingCta />
    </div>
  );
}
