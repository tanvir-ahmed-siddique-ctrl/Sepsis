import type { Metadata } from "next";
import { FeatureGrid, MarketingCta, MarketingHero, MarketingSection } from "@/components/marketing/MarketingPage";

export const metadata: Metadata = {
  title: "Site Readiness | Auralis",
  description: "Evidence-backed hospital site readiness assessment for infrastructure, data sources, devices and governance.",
};

export default function SiteReadinessPage() {
  return (
    <div>
      <MarketingHero
        eyebrow="Site readiness"
        title="Readiness is evidenced, not assumed."
        description="Auralis tracks network, compute, data sources, device interfaces, identity, privacy review, clinical governance owners and staffing capacity with explicit checklist states."
      />
      <MarketingSection eyebrow="Checklist themes" title="What the readiness passport covers.">
        <FeatureGrid items={[
          { title: "Infrastructure", body: "Network, servers, workstations, storage, backup and local VM readiness." },
          { title: "Data & interfaces", body: "HIS/LIS/monitor ownership, interface types, timestamp/unit consistency, sandbox availability." },
          { title: "Devices", body: "Medical equipment inventory and connectivity feasibility." },
          { title: "Governance", body: "Privacy/security review, clinical owners, procurement permissions." },
          { title: "People", body: "Technical staffing and support capacity for sustained operation." },
          { title: "States", body: "Not started → in progress → requires evidence → blocked → submitted → approved / rejected." },
        ]} />
      </MarketingSection>
      <MarketingCta />
    </div>
  );
}
