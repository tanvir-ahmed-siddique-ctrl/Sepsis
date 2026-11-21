import type { Metadata } from "next";
import Link from "next/link";
import { FeatureGrid, MarketingCta, MarketingHero, MarketingSection } from "@/components/marketing/MarketingPage";
import { Reveal } from "@/components/marketing/MotionPrimitives";
import { Icon } from "@/components/ui/Icon";

export const metadata: Metadata = {
  title: "Auri AI | Auralis",
  description: "Local co-pilot for mapping and bounded clinical assist — never overrides the frozen sepsis score.",
};

export default function AuriePage() {
  return (
    <div className="bg-white">
      <MarketingHero
        eyebrow="Auri AI"
        title={
          <>
            Clinical context that{" "}
            <span className="text-teal">never overrides the doctor.</span>
          </>
        }
        description="Auri AI is the site-local co-pilot: mapping, explainers, and gated drafts. Local Qwen by default; optional licence-bundled cloud LLM. It never modifies the frozen sepsis probability and never writes orders."
        specs={[
          { label: "Risk Engine", value: "Frozen Run-4 Classifier" },
          { label: "Context Layer", value: "Cited guideline retrieval" },
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
              Track 2 · Auri AI co-pilot
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

      <MarketingSection eyebrow="Status" title="What you can see today vs what is next." tone="muted">
        <div className="grid gap-6 lg:grid-cols-2">
          <Reveal className="rounded-2xl border border-teal/30 bg-white p-7">
            <span className="rounded-full bg-teal/10 px-3 py-1 text-xs font-semibold text-teal">Shipped · visible now</span>
            <ul className="mt-4 space-y-2 text-sm leading-6 text-ink">
              <li>Header <strong>Language</strong> dropdown — English / বাংলা (medical terms stay English)</li>
              <li>Local Qwen + hybrid RAG mapping co-pilot</li>
              <li>Profile → <strong>Auri AI</strong> capabilities & privacy rules</li>
              <li>Hospital setup → encrypted cloud API key on the <strong>local server</strong> only</li>
              <li>Never writes the Frozen Run 4 sepsis score</li>
            </ul>
          </Reveal>
          <Reveal delayMs={80} className="rounded-2xl border border-border bg-white p-7">
            <span className="rounded-full bg-muted-surface px-3 py-1 text-xs font-semibold text-muted">Coming · roadmap</span>
            <ul className="mt-4 space-y-2 text-sm leading-6 text-muted">
              <li>Gated handoff / shift-note drafts from on-screen fields</li>
              <li>Richer TrustGate & protocol explain chat</li>
              <li>Vendor licence entitlement for bundled cloud assist</li>
            </ul>
            <p className="mt-4 text-xs text-muted">Roadmap is labelled honestly — not a live hospital outcome claim.</p>
          </Reveal>
        </div>
      </MarketingSection>

      <MarketingSection eyebrow="Principles" title="Designed for high-trust ICU care.">
        <FeatureGrid
          items={[
            { title: "Clinician Sign-Off", body: "Every acknowledgement, escalation or snooze requires a named clinician." },
            { title: "No Silent Drift", body: "Models never self-modify online; updates require hospital governance approval." },
            { title: "Source Citations", body: "Every Vital or guideline line links straight back to its raw timestamp." },
            { title: "Local Privacy", body: "Runs inside your hospital's clinical boundary. API keys never live in the browser." },
          ]}
        />
        <div className="mt-8 flex flex-wrap gap-5 text-sm font-semibold text-teal">
          <Link href="/signin?next=/app/profile#auralis-ai" className="auralis-link">
            Open Auri AI in Profile
            <Icon name="arrow-right" size={16} />
          </Link>
          <Link href="/signin?next=/app/icu" className="auralis-link">
            See ICU board
            <Icon name="arrow-right" size={16} />
          </Link>
          <Link href="/model" className="auralis-link">
            Model transparency
            <Icon name="arrow-right" size={16} />
          </Link>
          <Link href="/evidence" className="auralis-link">
            Validation summary
            <Icon name="arrow-right" size={16} />
          </Link>
          <Link href="/judge" className="auralis-link">
            Judge tour
            <Icon name="arrow-right" size={16} />
          </Link>
        </div>
      </MarketingSection>

      <MarketingCta />
    </div>
  );
}
