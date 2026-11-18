"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type LicenceState = { status: string; activation_eligible: boolean; licence_id?: string; expires_on?: string; modules?: string[]; clinical_approval_separate?: boolean; required_for_new_live_request?: boolean };

export function LocalLicencePanel() {
  const [state, setState] = useState<LicenceState | null>(null);
  const [document, setDocument] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { void api<LicenceState>("/v1/site/licence").then(setState).catch((cause) => setError(cause instanceof Error ? cause.message : "Licence status unavailable")); }, []);

  async function importPackage(event: React.FormEvent) {
    event.preventDefault(); setError(null); setBusy(true);
    try {
      const parsed: unknown = JSON.parse(document);
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("Paste a JSON licence package");
      const result = await api<LicenceState>("/v1/site/licence", { method: "PUT", body: JSON.stringify(parsed) });
      setState(result); setDocument("");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Licence import failed"); }
    finally { setBusy(false); }
  }

  return <main className="mx-auto max-w-4xl px-4 py-10 text-ink sm:px-6">
    <p className="text-xs font-semibold uppercase tracking-widest text-forest">Hospital administration / Local entitlement</p>
    <h1 className="mt-3 font-display text-4xl">Site licence</h1>
    <p className="mt-4 max-w-2xl text-sm leading-6 text-slate">Import the signed package issued for this hospital site. Verification uses a locally configured public key and works without an internet connection. The vendor signing key never belongs on this server.</p>
    <section className="mt-8 border-y border-[#D6DCD8] py-5 text-sm" aria-live="polite">
      <h2 className="font-semibold">Local verification</h2>
      <p className="mt-2">Status: <strong>{state?.status ?? "Loading"}</strong>{state?.licence_id ? ` · ${state.licence_id}` : ""}</p>
      {state?.expires_on && <p>Expiry: {state.expires_on}</p>}
      {state?.modules && <p>Modules: {state.modules.join(", ")}</p>}
      <p className="mt-2 text-slate">{state?.activation_eligible ? "Commercial entitlement verified for a new live-mode request." : "A new live-mode request cannot use this entitlement."} Clinical governance, feed readiness, and local validation remain separate requirements. An already running clinical workflow is not stopped by this screen.</p>
    </section>
    <form onSubmit={(event) => void importPackage(event)} className="mt-8 space-y-4">
      <label className="block text-sm font-semibold" htmlFor="licence-package">Signed licence JSON package</label>
      <textarea id="licence-package" value={document} onChange={(event) => setDocument(event.target.value)} required maxLength={16384} rows={8} spellCheck={false} className="w-full border border-[#B8C2BD] bg-white p-3 font-mono text-xs" />
      <button disabled={busy} className="bg-forest px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{busy ? "Verifying…" : "Verify and import"}</button>
      {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    </form>
  </main>;
}
