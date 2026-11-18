import type { Metadata } from "next";
import Link from "next/link";
import { FeatureGrid, MarketingCta, MarketingHero, MarketingSection } from "@/components/marketing/MarketingPage";
import { Reveal } from "@/components/marketing/MotionPrimitives";

export const metadata: Metadata = {
  title: "Aurie AI | Auralis",
  description: "Bounded clinical context and guideline checklists beside each ICU risk review.",
};

export default function AuriePage() {
  return (
    <div className="bg-white">
      <MarketingHero
        eyebrow="Aurie AI"
        title={
          <>
            Clinical context that{" "}
            <span className="font-serif italic font-normal text-teal">never overrides the doctor.</span>
          </>
        }
        description="Aurie summarizes recent vital changes and surfaces hospital sepsis checklists beside an alert — without ever modifying the mathematical risk score."
        specs={[
          { label: "Risk Engine", value: "Frozen Run-4 Classifier" },
          { label: "Context Layer", value: "Protocol & Trend Summary" },
          { label: "Safety Rule", value: "Text Never Changes Score" },
          { label: "Autonomy", value: "Zero Automated Orders" },
        ]}
      />

      <MarketingSection
        eyebrow="Two-Track Safety"
        title="Why scoring and clinical text stay separated."
        tone="muted"
      >
        <div className="grid gap-6 lg:grid-cols-2">
          <Reveal className="rounded-2xl border border-border bg-white p-7">
            <span className="rounded-full bg-teal/10 px-3 py-1 text-xs font-semibold text-teal">
              Track 1 · Deterministic Scoring
            </span>
            <h3 className="mt-4 font-display text-xl font-semibold text-ink">
              Frozen 6-hour sepsis-risk model
            </h3>
            <p className="mt-2 text-sm leading-6 text-muted">
              Computes sepsis risk strictly from verified vitals and laboratory slopes. Identical inputs always produce the exact same inspectable probability.
            </p>
          </Reveal>

          <Reveal delayMs={80} className="rounded-2xl border border-teal/25 bg-white p-7">
            <span className="rounded-full bg-teal/10 px-3 py-1 text-xs font-semibold text-teal">
              Track 2 · Aurie Bedside Context
            </span>
            <h3 className="mt-4 font-display text-xl font-semibold text-ink">
              Readable shift & guideline summary
            </h3>
            <p className="mt-2 text-sm leading-6 text-muted">
              Highlights what changed over the last 6 hours and cites your hospital&apos;s approved sepsis bundle so clinicians review faster with full source links.
            </p>
          </Reveal>
        </div>
      </MarketingSection>

      <MarketingSection eyebrow="Principles" title="Designed for high-trust ICU care.">
        <FeatureGrid
          items={[
            { title: "Clinician Sign-Off", body: "Every acknowledgement, escalation or snooze requires a named clinician." },
            { title: "No Silent Drift", body: "Models never self-modify online; updates require hospital governance approval." },
            { title: "Source Citations", body: "Every Vital or guideline line links straight back to its raw timestamp." },
            { title: "Local Privacy", body: "Runs inside your hospital's clinical boundary." },
          ]}
        />
        <div className="mt-8 flex flex-wrap gap-5 text-sm font-semibold text-teal">
          <Link href="/model" className="hover:underline">Model transparency →</Link>
          <Link href="/evidence" className="hover:underline">Validation summary →</Link>
        </div>
      </MarketingSection>

      <MarketingCta />
    </div>
  );
}
