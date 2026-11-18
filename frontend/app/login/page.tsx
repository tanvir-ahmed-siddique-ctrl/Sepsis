"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { BrandMark } from "@/components/ui/BrandMark";
import { Panel } from "@/components/ui";
import { api } from "@/lib/api";
import { accountApi } from "@/lib/account-api";
import { useSession } from "@/lib/session";

const WORKSPACES = [
  { title: "Hospital System", detail: "Clinical and hospital-admin workspace", href: "/app/icu", requires: "hospital" as const },
  { title: "Vendor System", detail: "Vendor control plane for tenants and commercial ops", href: "/platform/overview", requires: "vendor" as const },
  { title: "Deployment System", detail: "Site commissioning, interfaces and readiness", href: "/deploy", requires: "hospital" as const },
  { title: "Customer Portal", detail: "Organization contracts, licences and support", href: "/portal", requires: "customer" as const },
  { title: "Evaluation Environment", detail: "Isolated synthetic / replay evaluation", href: "/system-check", requires: "any" as const },
];

export default function LoginPage() {
  const router = useRouter();
  const { me, account, signInLocal, signInPin, signInWithToken, signOut } = useSession();
  const [userId, setUserId] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [remember, setRemember] = useState(true);
  const [totp, setTotp] = useState("");
  const [pin, setPin] = useState("");
  const [token, setToken] = useState("");
  const [accountCurrent, setAccountCurrent] = useState("");
  const [accountNew, setAccountNew] = useState("");
  const [accountNotice, setAccountNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run(action: () => Promise<string | void>) {
    setBusy(true);
    try {
      const destination = await action();
      setError(null);
      router.push(destination || "/app/icu");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  }

  async function destinationForIdentity() {
    const result = await api<{ default_path: string | null }>("/v1/auth/workspaces");
    if (!result.default_path) throw new Error("This identity has no interactive workspace assigned.");
    return result.default_path;
  }

  function workspaceHref(item: (typeof WORKSPACES)[number]) {
    if (item.requires === "any") return item.href;
    if (item.requires === "vendor") return account?.vendor ? item.href : `/signin?next=${encodeURIComponent(item.href)}`;
    if (item.requires === "customer") return account && !account.vendor ? item.href : `/signin?next=${encodeURIComponent(item.href)}`;
    return me ? item.href : `/signin?next=${encodeURIComponent(item.href)}`;
  }

  return (
    <div className="min-h-screen bg-canvas">
      <div className="auralis-container grid gap-10 py-10 lg:grid-cols-[1.05fr_0.95fr] lg:py-16">
        <section className="auralis-panel max-w-xl self-start p-6 sm:p-8">
          <BrandMark href="/" />
          <h1 className="mt-8 font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl">Sign in to Auralis</h1>
          <p className="mt-3 text-sm leading-6 text-muted">Use your hospital identity or organization work email. Production authentication is always required for protected workspaces.</p>

          {account && (
            <Panel className="mt-6">
              <p className="text-sm">Signed in as <strong>{account.display_name}</strong>.</p>
              {account.must_change_password ? (
                <form className="mt-4 grid gap-3 text-sm" onSubmit={(event) => {
                  event.preventDefault();
                  void run(async () => {
                    await accountApi("/v1/auth/change-password", { method: "POST", body: JSON.stringify({ current_password: accountCurrent, new_password: accountNew }) });
                    setAccountCurrent(""); setAccountNew(""); setAccountNotice("Password changed. Sign in again."); signOut(); return "/signin";
                  });
                }}>
                  <p>Change the temporary password before using the account workspace.</p>
                  <label className="auralis-label">Current password<input type="password" value={accountCurrent} onChange={(event) => setAccountCurrent(event.target.value)} required className="auralis-input" /></label>
                  <label className="auralis-label">New password<input type="password" minLength={12} value={accountNew} onChange={(event) => setAccountNew(event.target.value)} required className="auralis-input" /></label>
                  <button type="submit" className="auralis-btn-primary justify-self-start">Change password</button>
                </form>
              ) : (
                <Link href={account.vendor ? "/platform/accounts" : "/portal"} className="mt-3 inline-block text-sm font-semibold text-teal">Open your workspace →</Link>
              )}
              <button type="button" onClick={signOut} className="ml-4 text-sm text-muted underline">Sign out</button>
            </Panel>
          )}
          {accountNotice && <p role="status" className="mt-3 text-sm text-teal">{accountNotice}</p>}

          {me && (
            <>
              <Panel className="mt-6 border-teal/30 bg-teal/5">
                <p className="text-sm">Signed in as <strong>{me.display_name || me.user_id}</strong> ({me.role}, {me.auth_mode})</p>
                {me.must_change_password && <p className="mt-1 text-sm font-medium text-risk-high">Change the temporary password before routine use.</p>}
                <button type="button" onClick={signOut} className="auralis-btn-secondary mt-3">Sign out</button>
              </Panel>
              {["password", "pin"].includes(me.auth_mode) && <div className="mt-4"><AccountSecurity onDone={signOut} mustChange={me.must_change_password} /></div>}
            </>
          )}

          {!me && !account && (
            <form className="mt-8 grid gap-4" onSubmit={(event) => {
              event.preventDefault();
              void run(async () => {
                const result = await signInLocal(userId.trim(), password, totp || undefined);
                if (remember) {
                  // Remember-me is advisory for browser autofill only; sessions remain server-managed.
                }
                return result.must_change_password ? "/signin" : result.destination || destinationForIdentity();
              });
            }}>
              <label className="auralis-label">Username / email
                <input value={userId} onChange={(e) => setUserId(e.target.value)} required className="auralis-input" autoComplete="username" />
              </label>
              <div>
                <label htmlFor="auralis-password" className="auralis-label">Password</label>
                <div className="mt-1 flex items-center border border-border bg-white focus-within:border-teal">
                  <input id="auralis-password" type={showPassword ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} required className="min-w-0 flex-1 px-3 py-2 text-sm outline-none" autoComplete="current-password" />
                  <button type="button" onClick={() => setShowPassword((value) => !value)} className="px-3 py-2 text-xs text-muted" aria-label={showPassword ? "Hide password" : "Show password"}>{showPassword ? "Hide" : "Show"}</button>
                </div>
              </div>
              <label className="auralis-label">Authenticator code (if enabled)
                <input inputMode="numeric" value={totp} onChange={(e) => setTotp(e.target.value.replace(/\D/g, "").slice(0, 6))} className="auralis-input" />
              </label>
              <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
                <label className="inline-flex items-center gap-2 text-muted"><input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} /> Remember me on this device</label>
                <span className="text-muted">Forgot password? Contact your administrator.</span>
              </div>
              <button type="submit" disabled={busy} className="auralis-btn-primary disabled:opacity-50">{busy ? "Signing in…" : "Sign In"}</button>
              {error && <p role="alert" className="text-sm text-risk-high">{error}</p>}
            </form>
          )}

          {!me && !account && (
            <div className="mt-6 space-y-3 border-t border-border pt-5">
              <details>
                <summary className="cursor-pointer text-sm font-medium text-muted">Ward tablet quick unlock</summary>
                <form className="mt-3 grid gap-3 text-sm" onSubmit={(event) => {
                  event.preventDefault();
                  void run(async () => { await signInPin(userId.trim(), pin, totp || undefined); return destinationForIdentity(); });
                }}>
                  <p className="text-xs text-muted">Use your own user ID and 4–6 digit PIN. Never share one ward account.</p>
                  <input type="password" inputMode="numeric" value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 6))} required className="auralis-input" placeholder="PIN" />
                  <button type="submit" disabled={busy} className="auralis-btn-secondary justify-self-start">Unlock for 15 minutes</button>
                </form>
              </details>
              <details>
                <summary className="cursor-pointer text-sm font-medium text-muted">Hospital identity provider</summary>
                <form className="mt-3 grid gap-3 text-sm" onSubmit={(event) => {
                  event.preventDefault();
                  void run(async () => { await signInWithToken(token); return destinationForIdentity(); });
                }}>
                  <p className="text-xs text-muted">For configured identity providers only. Paste a validated hospital access token.</p>
                  <textarea value={token} onChange={(event) => setToken(event.target.value)} rows={3} required className="auralis-input font-mono text-xs" autoComplete="off" />
                  <button type="submit" disabled={busy} className="auralis-btn-secondary justify-self-start">Validate hospital identity</button>
                </form>
              </details>
            </div>
          )}
        </section>

        <aside className="self-start">
          <h2 className="font-display text-2xl font-semibold tracking-tight text-ink">Choose Your Workspace</h2>
          <p className="mt-2 text-sm text-muted">These are real destinations. Protected workspaces still require an authorized session.</p>
          <div className="mt-6 grid gap-3">
            {WORKSPACES.map((item) => (
              <Link key={item.href} href={workspaceHref(item)} className="auralis-panel transition-colors hover:border-teal">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-ink">{item.title}</p>
                    <p className="mt-1 text-sm text-muted">{item.detail}</p>
                  </div>
                  <span className="text-sm font-semibold text-teal">Go →</span>
                </div>
              </Link>
            ))}
          </div>
          <p className="mt-6 text-xs leading-5 text-muted">Evaluation Environment uses pre-provisioned synthetic accounts only when a separate evaluation runtime is configured. No production passwords are embedded in this interface.</p>
        </aside>
      </div>
    </div>
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
          void run(() => api("/v1/auth/password", { method: "POST", body: JSON.stringify({ current_password: current, new_password: next }) }), "Password changed. Sign in again.", true);
        }}>
          <input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} placeholder="Current password" className="auralis-input" required />
          <input type="password" value={next} onChange={(e) => setNext(e.target.value)} placeholder="New password (12+ characters)" className="auralis-input" required minLength={12} />
          <button className="auralis-btn-secondary">Change</button>
        </form>
      </Panel>
      {!mustChange && (
        <Panel title="Ward PIN">
          <form className="space-y-2 text-sm" onSubmit={(event) => {
            event.preventDefault();
            void run(() => api("/v1/auth/pin", { method: "POST", body: JSON.stringify({ pin }) }), "PIN changed. Sign in again.", true);
          }}>
            <input type="password" inputMode="numeric" value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="4–6 digits" className="auralis-input" required />
            <button className="auralis-btn-secondary">Set PIN</button>
          </form>
        </Panel>
      )}
      {!mustChange && (
        <Panel title="Two-factor authentication">
          {!secret ? (
            <button type="button" className="auralis-btn-secondary text-sm" onClick={() => void run(async () => {
              const result = await api<{ secret: string }>("/v1/auth/totp/begin", { method: "POST" });
              setSecret(result.secret);
            }, "Enter this secret in an authenticator, then confirm a code.")}>Begin setup</button>
          ) : (
            <form className="space-y-2 text-sm" onSubmit={(event) => {
              event.preventDefault();
              void run(() => api("/v1/auth/totp/confirm", { method: "POST", body: JSON.stringify({ code }) }), "Two-factor authentication enabled.");
            }}>
              <code className="block break-all bg-muted-surface p-2 text-xs">{secret}</code>
              <input inputMode="numeric" value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="6-digit code" className="auralis-input" required />
              <button className="auralis-btn-secondary">Confirm</button>
            </form>
          )}
        </Panel>
      )}
      {message && <p className="text-sm md:col-span-3">{message}</p>}
    </div>
  );
}
