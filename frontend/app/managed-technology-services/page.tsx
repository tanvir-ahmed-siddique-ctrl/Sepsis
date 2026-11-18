import type { Metadata } from "next";
import { FeatureGrid, MarketingCta, MarketingHero, MarketingSection } from "@/components/marketing/MarketingPage";

export const metadata: Metadata = {
  title: "Managed Technology Services | Auralis",
  description: "Contracted hospital technical support, maintenance, monitoring and equipment lifecycle coordination.",
};

export default function ManagedTechnologyServicesPage() {
  return (
    <div>
      <MarketingHero
        eyebrow="Managed technology services"
        title="Support scoped to the contract — not unlimited claims."
        description="Where capability and agreements support it, Auralis can provide technical support plans, maintenance, monitoring, incident response, backup verification and upgrade planning."
      />
      <MarketingSection eyebrow="Covered themes" title="Typical managed-service elements.">
        <FeatureGrid items={[
          { title: "Technical support plans", body: "Agreed hours, contacts and escalation paths." },
          { title: "System maintenance", body: "Updates and release governance within licensed scope." },
          { title: "Infrastructure monitoring", body: "Feed and edge health where contracted." },
          { title: "Incident response", body: "Ticketed operational issues with SLA targets where defined." },
          { title: "Backup / restore verification", body: "Scheduled checks — not assumed continuous DR." },
          { title: "Equipment lifecycle coordination", body: "Warranty and refresh planning with qualified partners where applicable." },
        ]} />
        <p className="mt-6 text-sm leading-7 text-slate">We do not advertise 24/7 unlimited managed IT unless formally staffed and contractually supported.</p>
      </MarketingSection>
      <MarketingCta />
    </div>
  );
}
