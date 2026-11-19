import type { Metadata } from "next";
import Link from "next/link";
import { FeatureGrid, MarketingCta, MarketingHero, MarketingSection } from "@/components/marketing/MarketingPage";
import { ModelMark } from "@/components/ui/ModelMark";
import { Icon } from "@/components/ui/Icon";

export const metadata: Metadata = {
  title: "About & partnership | Auralis",
  description:
    "How Auralis partners with hospitals: trained sepsis risk model, on-site integration, what we offer, and how to book a consultation.",
};

const OFFERS = [
  {
    title: "ICU sepsis risk workspace",
    body: "Holdout-proven six-hour probability with SHAP drivers, TrustGate-checked alerts, charting, ward NEWS2 and shift handoff — on hospital infrastructure.",
  },
  {
    title: "Forward deployed engineering",
    body: "On-site engineers connect HL7/FHIR feeds, map units and codes, and commission monitors, networks and servers before go-live.",
  },
  {
    title: "Silent evaluation to live",
    body: "Shadow-mode scoring first. Interruptive alerts only after hospital readiness gates and clinical sign-off.",
  },
  {
    title: "Managed technology services",
    body: "Ongoing feed health, backups, licence operations and support SLA after commissioning.",
  },
];

const HOW_WE_WORK = [
  {
    step: "01",
    title: "Discover",
    body: "Site assessment of rooms, networks, servers and bedside devices. Scope the clinical units and integration path.",
  },
  {
    step: "02",
    title: "Connect",
    body: "Build and verify connectors. Quarantine bad messages. Align local coding so scores are trustworthy.",
  },
  {
    step: "03",
    title: "Prove",
    body: "Silent evaluation on hospital feeds. Joint review of alert burden, data quality and governance gates.",
  },
  {
    step: "04",
    title: "Operate",
    body: "Supervised live decision support with hospital-owned data, local scoring and accountable clinician review.",
  },
];

export default function AboutPage() {
  return (
    <div className="bg-white">
      <MarketingHero
        eyebrow="About & partnership"
        title={
          <>
            How we partner with{" "}
            <span className="text-teal">hospitals</span>.
          </>
        }
        description="A holdout-validated six-hour sepsis model — plus the on-site engineering that gets it onto ICU boards. Strong model, hospital-owned runtime, clinician still in command."
        specs={[
          { label: "Mission", value: "Earlier signal. Risk you can explain." },
          { label: "Model", value: "Frozen holdout-proven ML" },
          { label: "Delivery", value: "Forward deployed engineers" },
          { label: "Authority", value: "Clinician holds the decision" },
        ]}
      />

      <section className="border-b border-border bg-canvas py-10">
        <div className="auralis-container-public flex flex-wrap items-center justify-between gap-4">
          <ModelMark label="Holdout-proven ML · hospital deployment engineering" />
          <div className="flex flex-wrap gap-4">
            <Link href="/deployment-integration" className="inline-flex items-center gap-1.5 text-sm font-semibold text-teal hover:text-teal-dark">
              Why deployment matters
              <Icon name="arrow-right" size={14} />
            </Link>
            <Link href="/model" className="inline-flex items-center gap-1.5 text-sm font-semibold text-teal hover:text-teal-dark">
              Model transparency
              <Icon name="arrow-right" size={14} />
            </Link>
          </div>
        </div>
      </section>

      <MarketingSection eyebrow="What we offer" title="Clear packages hospitals can book against.">
        <FeatureGrid items={OFFERS} />
        <div className="mt-10 flex flex-wrap gap-3">
          <Link href="/contact" className="auralis-btn-primary h-11 px-6">
            Book a consultation
          </Link>
          <Link href="/business" className="auralis-btn-secondary h-11 px-6">
            Commercial approach
          </Link>
          <Link href="/for-hospitals" className="auralis-btn-ghost h-11 px-6">
            Adoption journey
          </Link>
        </div>
      </MarketingSection>

      <MarketingSection eyebrow="How engagement works" title="Four stages from assessment to live care." tone="muted">
        <ol className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {HOW_WE_WORK.map((item) => (
            <li key={item.step} className="rounded-2xl border border-border bg-white p-5 shadow-soft">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-teal">{item.step}</p>
              <h3 className="mt-2 text-lg font-semibold text-ink">{item.title}</h3>
              <p className="mt-2 text-sm leading-6 text-muted">{item.body}</p>
            </li>
          ))}
        </ol>
      </MarketingSection>

      <MarketingSection eyebrow="Principles" title="How we build with hospitals.">
        <FeatureGrid
          items={[
            {
              title: "Honesty in evidence",
              body: "Holdout benchmarks, commissioning data and local clinical validation stay distinct — no inflated claims.",
            },
            {
              title: "Local by default",
              body: "Patient data and real-time scoring stay inside the hospital’s own infrastructure.",
            },
            {
              title: "Engineers at your side",
              body: "We solve monitor, network and HL7/FHIR problems before commissioning clinical software.",
            },
            {
              title: "Doctors hold authority",
              body: "Every risk score is explainable, TrustGate-checked and reviewed by an accountable clinician.",
            },
          ]}
        />
      </MarketingSection>

      <section className="border-t border-border bg-gradient-to-br from-[#F3FAFB] via-white to-[#EEF4F8] py-16 lg:py-20">
        <div className="auralis-container-public grid gap-8 lg:grid-cols-[1.2fr_0.8fr] lg:items-center">
          <div>
            <span className="auralis-eyebrow">Book</span>
            <h2 className="mt-3 text-3xl font-semibold tracking-[-0.025em] text-navy sm:text-4xl">
              Ready to scope a site?
            </h2>
            <p className="mt-4 max-w-xl text-base leading-7 text-muted">
              Tell us your ICU footprint, integration stack and timeline. We reply with a concrete assessment plan — not a generic sales deck.
            </p>
          </div>
          <div className="flex flex-wrap gap-3 lg:justify-end">
            <Link href="/contact" className="auralis-btn-primary h-12 px-6">
              Book a consultation
              <Icon name="arrow-right" size={16} />
            </Link>
            <Link href="/signin?next=/app/icu" className="auralis-btn-secondary h-12 px-6">
              Open ICU workspace
            </Link>
          </div>
        </div>
      </section>

      <MarketingCta />
    </div>
  );
}
