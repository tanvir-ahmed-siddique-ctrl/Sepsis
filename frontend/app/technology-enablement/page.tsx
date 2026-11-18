import type { Metadata } from "next";
import { FeatureGrid, MarketingCta, MarketingHero, MarketingSection } from "@/components/marketing/MarketingPage";

export const metadata: Metadata = {
  title: "Hospital Technology Enablement | Auralis",
  description: "Infrastructure planning, equipment compatibility coordination, integration and managed technical services for hospitals at different readiness levels.",
};

export default function TechnologyEnablementPage() {
  return (
    <div>
      <MarketingHero
        eyebrow="Technology enablement"
        title="Improve the environment before, or alongside, clinical software."
        description="Hospitals may begin with infrastructure, networking, device connectivity, readiness and training. Clinical intelligence is considered only when eligibility conditions are met."
      />
      <MarketingSection eyebrow="Service categories" title="What we can help plan and coordinate.">
        <FeatureGrid items={[
          { title: "IT infrastructure", body: "Network, workstations, local servers, storage, backup planning, power resilience and identity basics." },
          { title: "Medical equipment enablement", body: "Compatibility review, requirements assessment, supplier coordination and connectivity planning. Biomedical certification remains with qualified partners." },
          { title: "Hospital-specific integration", body: "Supported interfaces only, with mapping, validation and quarantine behaviour documented." },
          { title: "Local deployment", body: "Hospital-local installation, TLS, smoke tests, backup/restore verification and technical acceptance." },
          { title: "Training & knowledge transfer", body: "Role-based onboarding for clinicians, administrators and technical staff with completion records." },
          { title: "Managed technical support", body: "Where contracted: maintenance, monitoring, incident response and upgrade planning within agreed hours." },
        ]} />
      </MarketingSection>
      <MarketingSection eyebrow="Delivery models" title="Equipment ownership stays explicit.">
        <FeatureGrid items={[
          { title: "Hospital-owned procurement", body: "Hospital purchases; Auralis coordinates requirements, compatibility, integration and implementation." },
          { title: "Supplier / OEM provided", body: "Qualified supplier provides equipment; Auralis coordinates integration and supporting services." },
          { title: "Partner-managed lease", body: "Only where a legitimate financing or supplier partner and contract model exist — not assumed by default." },
        ]} />
        <p className="mt-6 text-sm leading-7 text-slate">Available vs partner-delivered vs future services are distinguished in proposals. We do not claim nationwide equipment stock, universal managed IT or manufacturer-authorized biomedical repair without the corresponding capability and authorization.</p>
      </MarketingSection>
      <MarketingCta />
    </div>
  );
}
