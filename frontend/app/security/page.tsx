import type { Metadata } from "next";
import { FeatureGrid, MarketingCta, MarketingHero, MarketingSection } from "@/components/marketing/MarketingPage";
import { Reveal } from "@/components/marketing/MotionPrimitives";

export const metadata: Metadata = {
  title: "Security & Privacy | Auralis",
  description: "Hospital-local patient data, strict dual-plane isolation, RBAC, and cryptographic offline licensing.",
};

export default function SecurityPage() {
  return (
    <div className="bg-white">
      <MarketingHero
        eyebrow="Security & Privacy"
        title={
          <>
            Engineered around{" "}
            <span className="text-teal">hospital data sovereignty.</span>
          </>
        }
        description="Patient identifiers and clinical observations stay inside your hospital's local server. Vendor billing and support run on a completely separate metadata plane."
        specs={[
          { label: "Data Boundary", value: "Zero PHI in Vendor Cloud" },
          { label: "Access Control", value: "61 Role Permissions" },
          { label: "Document Vault", value: "Encrypted + Malware Scanned" },
          { label: "Site Licensing", value: "Offline Ed25519 Signed" },
        ]}
      />

      <MarketingSection eyebrow="Dual-Plane Architecture" title="Two isolated systems by design." tone="muted">
        <div className="grid gap-6 lg:grid-cols-2">
          <Reveal className="rounded-2xl border border-border bg-white p-7">
            <span className="rounded-full bg-teal/10 px-3 py-1 text-xs font-semibold text-teal">
              Plane 1 · Hospital Clinical Server
            </span>
            <h3 className="mt-4 font-display text-xl font-semibold text-ink">
              Patient vitals, risk scoring & bedside charts
            </h3>
            <p className="mt-2 text-sm leading-6 text-muted">
              Runs inside your hospital network with local RBAC (Consultant, Nurse, Admin, Clinical IT, Viewer) and a tamper-evident audit chain.
            </p>
          </Reveal>

          <Reveal delayMs={80} className="rounded-2xl border border-border bg-white p-7">
            <span className="rounded-full bg-teal/10 px-3 py-1 text-xs font-semibold text-teal">
              Plane 2 · Vendor & Customer Portal
            </span>
            <h3 className="mt-4 font-display text-xl font-semibold text-ink">
              Contracts, readiness checklists & support tickets
            </h3>
            <p className="mt-2 text-sm leading-6 text-muted">
              Contains zero patient tables or clinical observations. Vendor staff manage licences and SLAs without ever seeing patient charts.
            </p>
          </Reveal>
        </div>
      </MarketingSection>

      <MarketingSection eyebrow="Core Controls" title="Built-in institutional safeguards.">
        <FeatureGrid
          items={[
            { title: "Strict Tenant Isolation", body: "Every hospital organization and site is isolated at the API and database query layer." },
            { title: "Safe Offline Licensing", body: "Licence expiry or revocation never interrupts an active bedside clinical session." },
            { title: "Encrypted Document Vault", body: "Commercial PDFs are scanned and Fernet-encrypted at rest with retention controls." },
            { title: "No Cross-Hospital Data Pooling", body: "Auralis never pools patient records across hospitals or runs unapproved online retraining." },
          ]}
        />
      </MarketingSection>

      <MarketingCta />
    </div>
  );
}
