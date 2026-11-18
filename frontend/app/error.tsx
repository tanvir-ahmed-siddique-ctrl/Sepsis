"use client";

export default function WorkspaceError({ reset }: { error: Error; reset: () => void }) {
  return <section role="alert" className="mx-auto max-w-2xl border-l-2 border-risk-watch bg-white p-7">
    <p className="text-xs font-semibold uppercase tracking-widest text-risk-watch">Auralis</p>
    <h1 className="mt-3 font-display text-3xl">This view could not load</h1>
    <p className="mt-3 text-sm leading-7 text-slate">The local service did not return a current view. No observation or score should be assumed current. Check the connection, then retry.</p>
    <button type="button" onClick={reset} className="mt-5 bg-forest px-4 py-2 text-sm font-semibold text-white">Retry</button>
  </section>;
}
