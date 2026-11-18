import Link from "next/link";

const groups = [
  ["Clinical workflow", "Units, admitted encounters, observation charting, bedside ownership, alerts and handoff."],
  ["Interoperability", "FHIR R4 bundles and NDJSON, HL7 v2 ORU and ADT, laboratory CSV, mapping registry, quarantine and replay spool."],
  ["Governance", "Readiness gates, silent-pilot feedback, adjudicated outcomes, exports, retention and local protocols."],
  ["Operations", "Health, Prometheus metrics, audit-chain verification and a signed patient-free fleet heartbeat."],
];

export default function ApiReferencePage() {
  return (
    <main className="mx-auto max-w-5xl space-y-6 px-4 py-8 sm:px-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">Hospital integration surface</p>
        <h1 className="mt-2 font-display text-3xl text-ink">API & integration reference</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-ink/65">
          These are the interfaces a hospital IT team uses to connect existing systems. The public link exposes only
          synthetic and de-identified evaluation data.
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {groups.map(([title, detail]) => (
          <section key={title} className="border border-ink/10 bg-white p-5">
            <h2 className="font-display text-xl">{title}</h2>
            <p className="mt-2 text-sm leading-6 text-ink/65">{detail}</p>
          </section>
        ))}
      </div>
      <section className="border border-accent/25 bg-accent/5 p-5">
        <h2 className="font-display text-xl">Try the machine-readable reference</h2>
        <p className="mt-2 text-sm text-ink/65">
          OpenAPI lists request schemas, role requirements and example responses. Use the Integration Hub for the
          guided workflow and safe synthetic FHIR sample.
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <a href="/api/docs" className="border border-accent bg-accent px-3 py-2 text-sm font-medium text-white">Open API documentation</a>
          <Link href="/integration" className="border border-ink/20 bg-white px-3 py-2 text-sm font-medium">Open Integration Hub</Link>
        </div>
      </section>
    </main>
  );
}
