import type { Metadata } from "next";
import Link from "next/link";
import { FeatureGrid, MarketingCta, MarketingHero, MarketingSection } from "@/components/marketing/MarketingPage";
import { Icon } from "@/components/ui/Icon";

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
            Models fail in hospitals when{" "}
            <span className="text-teal">feeds never arrive clean.</span>
          </>
        }
        description="We ship a holdout-validated six-hour sepsis model — then treat connection, quarantine and commissioning as first-class work, because that is why good models usually never reach a bed."
        specs={[
          { label: "Standards", value: "HL7v2 · FHIR R4 · CSV" },
          { label: "Protection", value: "Unit & Staleness Quarantine" },
          { label: "Hosting", value: "On-Prem VM / Appliance" },
          { label: "Egress", value: "Zero Cloud Patient Data" },
        ]}
      />

      <MarketingSection
        eyebrow="Why this matters"
        title="Good model. Real pipes. Both required."
      >
        <FeatureGrid
          items={[
            {
              title: "Our model earns the bed",
              body: "Frozen LightGBM, preregistered Dataset B holdout (~0.81 AUROC), beat clinical-rule and logistic baselines — with SHAP drivers clinicians can inspect.",
            },
            {
              title: "Hospitals still need pipes",
              body: "ADT, ORU, Observations, bed IDs and local coding must reconcile before that probability is trustworthy at the bedside.",
            },
            {
              title: "We commission on-site",
              body: "Forward deployed engineers build the ladder from CSV to HL7 to FHIR, then prove feed health in your Deployment Console.",
            },
            {
              title: "TrustGate keeps it honest",
              body: "Even a strong model abstains on stale or conflicting inputs — so live scoring stays decision support, not theatre.",
            },
          ]}
        />
      </MarketingSection>

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
          <Link href="/signin?next=/deploy" className="auralis-link">Open Deployment Console<Icon name="arrow-right" size={16} /></Link>
          <Link href="/api-reference" className="auralis-link">API & FHIR Reference<Icon name="arrow-right" size={16} /></Link>
        </div>
      </MarketingSection>

      <MarketingCta />
    </div>
  );
}
