import Link from "next/link";

const destinations = [
  {
    href: "/judge-guide",
    title: "Judge guide",
    detail: "A short explanation of the simulated hospital, role-based walkthrough and separate metadata-only fleet console.",
  },
  {
    href: "/presentation",
    title: "Three-minute replay",
    detail: "The timed, evidence-led competition walkthrough of one held-out replay case.",
  },
  {
    href: "/docs",
    title: "Technical dossier",
    detail: "Architecture, model governance, responsible-AI controls, implementation pathway and business case.",
  },
];

export default function JudgeDeskPage() {
  return (
    <main className="mx-auto max-w-4xl space-y-8 px-4 py-10 sm:px-6">
      <div className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">Competition materials</p>
        <h1 className="font-display text-4xl text-ink">PredictRx Sentinel review desk</h1>
        <p className="max-w-2xl text-ink/70">
          These materials explain and demonstrate the product. They are kept outside the hospital workspace so the clinical and administration flows stay focused on daily operation.
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {destinations.map((destination) => (
          <Link
            key={destination.href}
            href={destination.href}
            className="border border-ink/10 bg-white p-5 transition hover:border-accent hover:shadow-sm"
          >
            <h2 className="font-display text-xl text-ink">{destination.title}</h2>
            <p className="mt-3 text-sm leading-6 text-ink/70">{destination.detail}</p>
            <span className="mt-5 inline-block text-sm font-semibold text-accent">Open →</span>
          </Link>
        ))}
      </div>
      <p className="text-sm text-ink/60">
        For the product itself, sign in as a clinician for the ICU workflow or as Hospital admin for onboarding, integration, readiness and operations.
      </p>
    </main>
  );
}
