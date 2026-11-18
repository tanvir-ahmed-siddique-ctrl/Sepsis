import type { Metadata } from "next";
import { FeatureGrid, MarketingCta, MarketingHero, MarketingSection } from "@/components/marketing/MarketingPage";

export const metadata: Metadata = { title: "Security & Governance | Auralis", description: "Security posture and governance boundaries for Auralis." };

export default function SecurityPage() {
  return (
    <div>
      <MarketingHero eyebrow="Security & Governance" title="Security that respects hospital boundaries." description="Hospital clinical data and vendor commercial metadata are separated by design. Access is role-scoped, audited and never granted by UI convenience." />
      <MarketingSection eyebrow="Controls" title="What is implemented in the product.">
        <FeatureGrid items={[
          { title: "Role-based access", body: "Hospital and vendor permission matrices enforce least privilege." },
          { title: "Tenant isolation", body: "Customer and hospital records stay scoped to authorized organizations." },
          { title: "Document vault", body: "Encrypted commercial PDFs with malware scanning and retention lifecycle." },
          { title: "Licence entitlements", body: "Signed offline packages can be revoked without interrupting a running bedside session." },
          { title: "Audit trails", body: "Account and operational actions are recorded for review." },
          { title: "Evaluation isolation", body: "Synthetic evaluation runtimes stay separate from hospital operations." },
        ]} />
      </MarketingSection>
      <MarketingCta />
    </div>
  );
}
