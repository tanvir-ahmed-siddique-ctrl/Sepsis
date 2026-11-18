"use client";

import Link from "next/link";
import { useState } from "react";

export default function ActivatePage() {
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  async function activate(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setStatus("");
    try {
      const response = await fetch("/api/account-invitation", {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-Auralis-Request": "1" },
        body: JSON.stringify({ token: token.trim(), password }),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(String(result.detail || "Activation failed"));
      setToken(""); setPassword(""); setStatus("Account activated. Sign in to open your authorized workspace.");
    } catch (error) { setStatus(error instanceof Error ? error.message : "Activation failed"); }
    finally { setBusy(false); }
  }

  return <main className="mx-auto max-w-lg px-6 py-16">
    <p className="text-xs font-semibold uppercase tracking-widest text-forest">Auralis / institutional access</p>
    <h1 className="mt-4 font-display text-4xl">Activate your account</h1>
    <p className="mt-4 text-sm leading-6 text-slate">Use the one-time invitation token supplied by your authorized institution contact. It expires after 48 hours.</p>
    <form onSubmit={(event) => void activate(event)} className="mt-8 grid gap-4 text-sm">
      <label>Invitation token<input value={token} onChange={(event) => setToken(event.target.value)} required minLength={32} autoComplete="off" className="mt-1 block w-full border bg-white p-3" /></label>
      <label>New password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={12} autoComplete="new-password" className="mt-1 block w-full border bg-white p-3" /></label>
      <button disabled={busy} className="justify-self-start bg-forest px-5 py-3 font-semibold text-white disabled:opacity-50">Activate account</button>
    </form>
    {status && <p role="status" className="mt-5 border-l-2 border-forest bg-warm p-3 text-sm">{status}</p>}
    <Link href="/signin" className="mt-6 inline-block text-sm font-semibold text-forest underline">Go to sign-in</Link>
  </main>;
}
