import type { Metadata } from "next";
import Link from "next/link";
import { FeatureGrid, MarketingCta, MarketingHero, MarketingSection } from "@/components/marketing/MarketingPage";

export const metadata: Metadata = {
  title: "HL7 & FHIR Integration | Auralis",
  description: "Connect bedside monitors, LIS labs, and hospital systems safely inside your LAN.",
};

export default function DeploymentIntegrationPage() {
  return (
    <div className="bg-white">
      <MarketingHero
        eyebrow="Deployment & Integration"
        title={
          <>
            Connect the systems your hospital{" "}
            <span className="font-serif italic font-normal text-teal">actually runs.</span>
          </>
        }
        description="From CSV flowsheets and HL7v2 MLLP feeds to FHIR R4 APIs — every connector is tested in a sandbox with unit and staleness protection."
        specs={[
          { label: "Standards", value: "HL7v2 · FHIR R4 · CSV" },
          { label: "Protection", value: "Unit & Staleness Quarantine" },
          { label: "Hosting", value: "On-Prem VM / Appliance" },
          { label: "Egress", value: "Zero Cloud Patient Data" },
        ]}
      />

      <MarketingSection eyebrow="Connection Ladder" title="Three practical integration paths." tone="muted">
        <FeatureGrid
          items={[
            {
              tag: "Level 0 · Structured Capture",
              title: "Approved Batch CSV & Bedside Flowsheet",
              body: "Get started safely during early readiness or retrospective review before live broker interfaces are wired.",
            },
            {
              tag: "Level 1 · HL7v2 Gateway",
              title: "Monitor & Laboratory ORU_R01 Streams",
              body: "Parses live HL7v2 messages, reconciles µmol/L vs mg/dL units, and holds malformed segments in quarantine.",
            },
            {
              tag: "Level 2 · FHIR R4 API",
              title: "Observation, Patient & Encounter Bundles",
              body: "Version-controlled LOINC mappings, feed silence detection, and circuit-breaker monitoring.",
            },
            {
              tag: "Commissioning Console",
              title: "Built-In Readiness & Backup Gates",
              body: "Hospital IT inspects feed lag, quarantine counts, and backup status directly in the Deployment Console.",
            },
          ]}
        />
        <div className="mt-8 flex flex-wrap gap-5 text-sm font-semibold text-teal">
          <Link href="/signin?next=/deploy" className="hover:underline">Open Deployment Console →</Link>
          <Link href="/api-reference" className="hover:underline">API & FHIR Reference →</Link>
        </div>
      </MarketingSection>

      <MarketingCta />
    </div>
  );
}
