"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Panel } from "@/components/ui";
import { api, ROLE_LABELS, type UserRole } from "@/lib/api";
import { useSession } from "@/lib/session";

export default function LoginPage() {
  const router = useRouter();
  const { me, signInDemo, signInLocal, signInPin, signInWithToken, signOut } = useSession();
  const [userId, setUserId] = useState("dr.demo");
  const [password, setPassword] = useState("");
  const [totp, setTotp] = useState("");
  const [pin, setPin] = useState("");
  const [role, setRole] = useState<UserRole>("clinician");
  const [units, setUnits] = useState("");
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run(action: () => Promise<string | void>) {
    setBusy(true);
    try {
      const destination = await action();
      setError(null);
      router.push(destination || "/icu");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[minmax(280px,.8fr)_minmax(0,1.2fr)]">
      <aside className="bg-[#080C14] p-8 text-slate-50 lg:min-h-[650px] lg:p-10">
        <p className="text-xs font-semibold uppercase tracking-[.22em] text-cyan-400">PredictRx / Hospital edge</p>
        <h2 className="mt-10 font-display text-4xl leading-tight">Clinical intelligence stays close to the bedside.</h2>
        <p className="mt-5 text-sm leading-7 text-slate-300">The hospital owns its identity, observation feeds and clinical decisions. The vendor receives a signed, patient-free operational heartbeat when configured.</p>
        <div className="mt-12 space-y-5 border-t border-slate-700 pt-6 text-sm">
          <p><span className="font-mono text-cyan-400">01</span> · Local scoring and data-quality checks</p>
          <p><span className="font-mono text-cyan-400">02</span> · Named users, unit scope and audit</p>
          <p><span className="font-mono text-cyan-400">03</span> · Silent evaluation before live alerts</p>
        </div>
        <p className="mt-16 text-xs leading-5 text-slate-400">Connection status appears after a hospital configures and validates its own feed. This page does not represent a live hospital deployment.</p>
      </aside>
      <div className="space-y-5 py-4">
      <div>
        <h1 className="font-display text-3xl">Sign in</h1>
        <p className="mt-1 text-sm text-ink/60">
          Hospital sites can use local accounts or their identity provider. A short PIN unlocks a shared ward tablet
          for 15 minutes; use a password for administration.
        </p>
      </div>
      <div className="grid gap-4 bg-ink p-6 text-white md:grid-cols-[1fr_auto] md:items-center"><div><p className="text-xs uppercase tracking-widest text-cyan-300">AI Builders Congress 2026 / evaluator access</p><h2 className="mt-2 font-display text-2xl">Explore the hospital workflows by role</h2><p className="mt-2 text-sm text-white/65">Simulation access is separate from hospital account sign-in.</p></div><Link href="/evaluator" className="bg-white px-5 py-3 text-sm font-semibold text-ink">Launch role matrix →</Link></div>
      {me && (
        <>
          <Panel className="border-accent/30 bg-accent/5">
            <p className="text-sm">
              Signed in as <strong>{me.display_name || me.user_id}</strong> ({me.role}, {me.auth_mode}) · units{" "}
              {me.units ? me.units.join(", ") : "all"}
            </p>
            {me.must_change_password && <p className="mt-1 text-sm font-medium text-risk-high">Change the temporary password before routine use.</p>}
            <button type="button" onClick={signOut} className="mt-2 border border-ink/20 px-3 py-1 text-sm">
              Sign out
            </button>
          </Panel>
          {["password", "pin"].includes(me.auth_mode) && (
            <AccountSecurity onDone={signOut} mustChange={me.must_change_password} />
          )}
        </>
      )}
      {!me && (
        <div className="grid gap-4 md:grid-cols-2">
          <Panel title="Hospital account">
            <form className="space-y-3 text-sm" onSubmit={(event) => {
              event.preventDefault();
              void run(async () => {
                const result = await signInLocal(userId.trim(), password, totp || undefined);
                return result.must_change_password ? "/login" : "/icu";
              });
            }}>
              <Field label="User ID">
                <input value={userId} onChange={(e) => setUserId(e.target.value)} required className={INPUT} autoComplete="username" />
              </Field>
              <Field label="Password">
                <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required className={INPUT} autoComplete="current-password" />
              </Field>
              <Field label="Authenticator code (if enabled)">
                <input inputMode="numeric" value={totp} onChange={(e) => setTotp(e.target.value.replace(/\D/g, "").slice(0, 6))} className={INPUT} />
              </Field>
              <button type="submit" disabled={busy} className="border border-accent bg-accent px-3 py-1.5 font-medium text-white disabled:opacity-50">
                Sign in
              </button>
            </form>
          </Panel>
          <Panel title="Ward tablet quick unlock">
            <form className="space-y-3 text-sm" onSubmit={(event) => {
              event.preventDefault();
              void run(() => signInPin(userId.trim(), pin, totp || undefined));
            }}>
              <p className="text-xs text-ink/55">Use your own user ID and 4–6 digit PIN. Never share one ward account.</p>
              <Field label="User ID">
                <input value={userId} onChange={(e) => setUserId(e.target.value)} required className={INPUT} autoComplete="username" />
              </Field>
              <Field label="PIN">
                <input type="password" inputMode="numeric" value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 6))} required className={INPUT} />
              </Field>
              <Field label="Authenticator code (if enabled)">
                <input inputMode="numeric" value={totp} onChange={(e) => setTotp(e.target.value.replace(/\D/g, "").slice(0, 6))} className={INPUT} />
              </Field>
              <button type="submit" disabled={busy} className="border border-ink/20 px-3 py-1.5 font-medium disabled:opacity-50">
                Unlock for 15 minutes
              </button>
            </form>
          </Panel>
        </div>
      )}
      <details className="border-t border-ink/10 pt-4">
        <summary className="cursor-pointer text-sm font-medium text-ink/65">Judge access · simulated roles</summary>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
        <Panel title="Demo sign-in">
          <form
            className="space-y-3 text-sm"
            onSubmit={(event) => {
              event.preventDefault();
              void run(() => signInDemo(userId.trim(), role, units));
            }}
          >
            <Field label="User ID">
              <input value={userId} onChange={(e) => setUserId(e.target.value)} required maxLength={128} className={INPUT} />
            </Field>
            <fieldset>
              <legend className="mb-2 text-xs font-medium uppercase tracking-wide text-ink/50">Choose a judge walkthrough</legend>
              <div className="grid grid-cols-2 gap-2">
                {(Object.keys(ROLE_LABELS) as UserRole[]).map((value) => (
                  <button key={value} type="button" role="radio" aria-checked={role === value} onClick={() => setRole(value)}
                    className={`min-h-11 px-3 py-2 text-left text-sm transition ${role === value ? "bg-accent text-white" : "bg-mist text-ink hover:bg-accent/10"}`}>
                    {ROLE_LABELS[value]}
                  </button>
                ))}
              </div>
            </fieldset>
            <p className="text-xs text-ink/55">Simulated role walkthrough only. Hospital users sign in above with their assigned account.</p>
            <Field label="Unit scope (optional, comma-separated)">
              <input value={units} onChange={(e) => setUnits(e.target.value)} placeholder="icu-demo-1" className={INPUT} />
            </Field>
            <button type="submit" disabled={busy} className="border border-accent bg-accent px-3 py-1.5 font-medium text-white disabled:opacity-50">
              Get demo session
            </button>
          </form>
        </Panel>
        <Panel title="Hospital identity provider token">
          <form
            className="space-y-3 text-sm"
            onSubmit={(event) => {
              event.preventDefault();
              void run(() => signInWithToken(token));
            }}
          >
            <p className="text-xs text-ink/55">
              For pilot testing, paste an access token issued by the hospital IdP. The backend validates issuer,
              audience, signature (JWKS) and role/unit claims. Tokens stay in this browser tab only.
            </p>
            <Field label="Bearer token">
              <textarea value={token} onChange={(e) => setToken(e.target.value)} rows={4} required className={`${INPUT} font-mono text-xs`} />
            </Field>
            <button type="submit" disabled={busy} className="border border-ink/20 px-3 py-1.5 font-medium disabled:opacity-50">
              Use token
            </button>
          </form>
        </Panel>
      </div>
      </details>
      {error && <p role="alert" className="text-sm text-risk-high">{error}</p>}
      </div>
    </div>
  );
}

const INPUT = "w-full border border-ink/20 bg-white px-2 py-1.5 outline-none focus:border-accent";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium uppercase tracking-wide text-ink/50">{label}</span>
      {children}
    </label>
  );
}

function AccountSecurity({ onDone, mustChange }: { onDone: () => void; mustChange: boolean }) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [pin, setPin] = useState("");
  const [secret, setSecret] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  async function run(action: () => Promise<unknown>, done: string, logout = false) {
    try {
      await action();
      setMessage(done);
      if (logout) onDone();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    }
  }
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <Panel title="Change password">
        <form className="space-y-2 text-sm" onSubmit={(event) => {
          event.preventDefault();
          void run(() => api("/v1/auth/password", {
            method: "POST", body: JSON.stringify({ current_password: current, new_password: next }),
          }), "Password changed. Sign in again.", true);
        }}>
          <input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} placeholder="Current password" className={INPUT} required />
          <input type="password" value={next} onChange={(e) => setNext(e.target.value)} placeholder="New password (12+ characters)" className={INPUT} required minLength={12} />
          <button className="border border-ink/20 px-3 py-1.5">Change</button>
        </form>
      </Panel>
      {!mustChange && <Panel title="Ward PIN">
        <form className="space-y-2 text-sm" onSubmit={(event) => {
          event.preventDefault();
          void run(() => api("/v1/auth/pin", { method: "POST", body: JSON.stringify({ pin }) }), "PIN changed. Sign in again.", true);
        }}>
          <input type="password" inputMode="numeric" value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="4–6 digits" className={INPUT} required />
          <button className="border border-ink/20 px-3 py-1.5">Set PIN</button>
        </form>
      </Panel>}
      {!mustChange && <Panel title="Two-factor authentication">
        {!secret ? (
          <button type="button" className="border border-ink/20 px-3 py-1.5 text-sm" onClick={() => void run(async () => {
            const result = await api<{ secret: string }>("/v1/auth/totp/begin", { method: "POST" });
            setSecret(result.secret);
          }, "Enter this secret in an authenticator, then confirm a code.")}>Begin setup</button>
        ) : (
          <form className="space-y-2 text-sm" onSubmit={(event) => {
            event.preventDefault();
            void run(() => api("/v1/auth/totp/confirm", { method: "POST", body: JSON.stringify({ code }) }), "Two-factor authentication enabled.");
          }}>
            <code className="block break-all bg-mist p-2 text-xs">{secret}</code>
            <input inputMode="numeric" value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="6-digit code" className={INPUT} required />
            <button className="border border-ink/20 px-3 py-1.5">Confirm</button>
          </form>
        )}
      </Panel>}
      {message && <p className="text-sm md:col-span-3">{message}</p>}
    </div>
  );
}
