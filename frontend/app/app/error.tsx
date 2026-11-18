"use client";

export default function HospitalWorkspaceError({ reset }: { error: Error; reset: () => void }) {
  return <section role="alert" className="mx-auto max-w-2xl border-l-2 border-risk-watch bg-white p-7">
    <p className="text-xs font-semibold uppercase tracking-widest text-risk-watch">Hospital workspace</p>
    <h1 className="mt-3 font-display text-3xl">Local service unavailable</h1>
    <p className="mt-3 text-sm leading-7 text-slate">The hospital identity or clinical service did not respond. This screen cannot confirm current observations or scores. Check the local connection and try again.</p>
    <button type="button" onClick={reset} className="mt-5 bg-forest px-4 py-2 text-sm font-semibold text-white">Retry connection</button>
  </section>;
}
