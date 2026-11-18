import type { Metadata } from "next";
import Link from "next/link";
import { MarketingCta, MarketingHero, MarketingSection } from "@/components/marketing/MarketingPage";

export const metadata: Metadata = { title: "Resources | Auralis", description: "Documentation, API reference and evidence resources." };

const resources = [
  { href: "/docs", title: "Documentation", body: "Architecture and operations notes for deployment teams." },
  { href: "/api-reference", title: "Integration API", body: "Connector and FHIR reference for hospital IT." },
  { href: "/evidence", title: "Evidence", body: "Retrospective evaluation summary and limitations." },
  { href: "/model", title: "Model transparency", body: "Frozen model scope, inputs and abstention behavior." },
  { href: "/workflows", title: "Workflows", body: "Clinical review and handoff path overview." },
  { href: "/business", title: "Commercial scope", body: "Engagement bands without invented prices or outcomes." },
];

export default function ResourcesPage() {
  return (
    <div>
      <MarketingHero eyebrow="Resources" title="Technical resources without marketing fiction." description="Use these pages for product understanding, integration planning and evidence review. No fabricated customer case studies." />
      <MarketingSection eyebrow="Library" title="Browse by topic.">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {resources.map((item) => (
            <Link key={item.href} href={item.href} className="auralis-panel transition-colors hover:border-teal">
              <h3 className="font-display text-lg font-semibold text-ink">{item.title}</h3>
              <p className="mt-3 text-sm leading-6 text-muted">{item.body}</p>
            </Link>
          ))}
        </div>
      </MarketingSection>
      <MarketingCta />
    </div>
  );
}
