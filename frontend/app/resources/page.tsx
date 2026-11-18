import type { Metadata } from "next";
import Link from "next/link";
import { MarketingCta, MarketingHero, MarketingSection } from "@/components/marketing/MarketingPage";

export const metadata: Metadata = {
  title: "Resources | Auralis",
  description: "Clinical evidence, model transparency, API reference, and operations documentation.",
};

const LINKS = [
  { href: "/evidence", tag: "Validation", title: "Clinical Evidence & Safety Boundaries", body: "Holdout benchmark performance, calibration, and local hospital validation requirements." },
  { href: "/model", tag: "Transparency", title: "Frozen Model Card & Features", body: "Input vitals/labs, 6-hour horizon, and TrustGate abstention rules." },
  { href: "/api-reference", tag: "Interoperability", title: "HL7 & FHIR API Reference", body: "Schemas, unit rules, and quarantine response codes for hospital IT." },
  { href: "/workflows", tag: "Bedside Care", title: "ICU & Ward Clinical Workflows", body: "How doctors, nurses, and IT collaborate across alerts and shift handoff." },
  { href: "/docs", tag: "Operations", title: "System & Deployment Guide", body: "Local server architecture, backups, and commissioning steps." },
  { href: "/business", tag: "Commercial", title: "Institutional Partnership Model", body: "Transparent engagement scoping for readiness, FDE, and site licensing." },
];

export default function ResourcesPage() {
  return (
    <div className="bg-white">
      <MarketingHero
        eyebrow="Resources"
        title={
          <>
            Clear technical &{" "}
            <span className="font-serif italic font-normal text-teal">clinical documentation.</span>
          </>
        }
        description="Explore our model card, HL7/FHIR schemas, clinical workflows, and validation evidence."
      />

      <MarketingSection eyebrow="Library" title="Browse documentation." tone="muted">
        <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {LINKS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="group flex flex-col justify-between rounded-2xl border border-border bg-white p-6 transition-all hover:border-teal hover:shadow-sm"
            >
              <div>
                <span className="text-xs font-semibold text-teal">{item.tag}</span>
                <h3 className="mt-2 font-display text-lg font-semibold text-ink group-hover:text-teal">
                  {item.title}
                </h3>
                <p className="mt-2 text-sm leading-6 text-muted">{item.body}</p>
              </div>
              <span className="mt-5 text-xs font-semibold text-teal">Read guide →</span>
            </Link>
          ))}
        </div>
      </MarketingSection>

      <MarketingCta />
    </div>
  );
}
