import Link from "next/link";

const steps = [
  ["1", "Start the story", "Open Presentation for the three-minute evidence-led walkthrough."],
  ["2", "See the clinical workflow", "Use the ICU board, a patient chart, alerts, handoff and ward NEWS2 as Nurse or Doctor."],
  ["3", "See how a hospital onboards", "Choose Hospital admin to inspect integration health, mapping review, users, readiness gates and silent-pilot evidence."],
  ["4", "See the founder view", "Open Fleet Console to see the vendor's cross-site health view. It receives signed metadata only, never a patient record."],
];

const proof = [
  ["Innovation", "TrustGate makes the system verify data, watch, or abstain instead of forcing every score into an alert."],
  ["Technical execution", "FHIR, HL7, CSV, monitor relay and bedside charting converge into one audited observation contract before a frozen, hash-verified model runs."],
  ["Business & scale", "Hospitals start with readiness, integration and silent evaluation; Docker packaging and standards-based connectors make each site repeatable."],
  ["Impact & ethics", "No hospital data is on this link. Production alerts remain off until local validation, governance and eight other readiness gates pass."],
];

export default function JudgeGuidePage() {
  const publicDemo = process.env.NEXT_PUBLIC_JUDGE_DEMO === "true";
  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <header className="space-y-3">
        <p className="text-xs uppercase tracking-[0.2em] text-accent">PredictRx Sentinel · Judge guide</p>
        <h1 className="font-display text-4xl">One link, two real product perspectives.</h1>
        <p className="max-w-3xl text-lg text-ink/65">
          This is a public simulation of one hospital installation and the vendor&apos;s separate control plane. It is designed
          to show the workflow without claiming that a real hospital is already deployed.
        </p>
      </header>

      {publicDemo && (
        <section className="border-l-4 border-accent bg-white p-4 text-sm text-ink/70">
          <strong className="text-ink">Public demo boundary.</strong> This host uses nine de-identified public PhysioNet
          replay cases and synthetic integration messages. Its operating mode is locked to replay so visitors cannot stop
          the shared experience. A hospital installation uses named accounts and permits audited mode changes locally.
        </section>
      )}

      <section className="grid gap-3 sm:grid-cols-2">
        {steps.map(([number, title, detail]) => (
          <article key={number} className="border border-ink/10 bg-white/85 p-5">
            <p className="text-xs font-semibold tracking-widest text-accent">{number}</p>
            <h2 className="mt-1 font-display text-2xl">{title}</h2>
            <p className="mt-2 text-sm text-ink/65">{detail}</p>
          </article>
        ))}
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-2xl">Use these paths</h2>
        <div className="flex flex-wrap gap-2 text-sm">
          {[
            ["/presentation", "Presentation"], ["/", "ICU board"], ["/integration", "Integration hub"],
            ["/readiness", "Readiness passport"], ["/docs", "Technical whitepaper"], ["/fleet", "Fleet Console"],
          ].map(([href, label]) => (
            <Link key={href} href={href} className="border border-ink/20 bg-white px-3 py-2 hover:border-accent hover:text-accent">{label}</Link>
          ))}
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-2">
        <article className="border border-ink/10 bg-white/85 p-5">
          <h2 className="font-display text-2xl">Who is the admin here?</h2>
          <p className="mt-2 text-sm text-ink/65">
            The public role picker is an exploration tool, not a real identity system. In production, hospital IT creates
            the first named administrator during installation. That administrator controls staff accounts, unit scope,
            integrations and audited site-mode changes.
          </p>
        </article>
        <article className="border border-ink/10 bg-white/85 p-5">
          <h2 className="font-display text-2xl">What is the founder&apos;s access?</h2>
          <p className="mt-2 text-sm text-ink/65">
            The founder operates a separate fleet console and can be granted an <code>operator</code> account by a
            hospital. Both expose deployment health and readiness only; patient pages remain unavailable to that role.
          </p>
        </article>
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-2xl">What judges can verify</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {proof.map(([title, detail]) => (
            <article key={title} className="border-l-2 border-accent pl-4">
              <h3 className="font-medium">{title}</h3>
              <p className="mt-1 text-sm text-ink/65">{detail}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
