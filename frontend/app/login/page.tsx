"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { BrandMark } from "@/components/ui/BrandMark";
import { Panel } from "@/components/ui";
import { api } from "@/lib/api";
import { accountApi } from "@/lib/account-api";
import { useSession } from "@/lib/session";

type DemoAccount = {
  user_id: string;
  label: string;
  role: string;
  default_path: string;
  password: string;
};

const QUICK_FALLBACK: DemoAccount[] = [
  { user_id: "demo-clinician", label: "ICU Consultant", role: "clinician", default_path: "/app/icu", password: "auralis-demo-2026" },
  { user_id: "demo-nurse", label: "Bedside ICU Nurse", role: "nurse", default_path: "/app/chart", password: "auralis-demo-2026" },
  { user_id: "demo-admin", label: "Hospital Admin", role: "admin", default_path: "/app/admin/overview", password: "auralis-demo-2026" },
  { user_id: "demo-it", label: "Clinical IT & Deployment", role: "clinical_it", default_path: "/deploy", password: "auralis-demo-2026" },
  { user_id: "demo-operator", label: "Fleet Operator", role: "operator", default_path: "/platform/overview", password: "auralis-demo-2026" },
];

const WORKSPACES = [
  { title: "Hospital ICU Dashboard", detail: "Live ICU board, sepsis trajectories, alerts & handoff", href: "/app/icu", demoUser: "demo-clinician" },
  { title: "Bedside Charting & Ward", detail: "Flowsheet vitals, NEWS2 ward surveillance & shifts", href: "/app/chart", demoUser: "demo-nurse" },
  { title: "Hospital Administration", detail: "Unit settings, staff access, readiness & silent pilot", href: "/app/admin/overview", demoUser: "demo-admin" },
  { title: "Deployment Console", detail: "HL7 / FHIR connectors, quarantine & commissioning", href: "/deploy", demoUser: "demo-it" },
  { title: "Vendor Control Plane", detail: "Tenants, CRM, FDE projects, licences & fleet", href: "/platform/accounts", demoEmail: "vendor@auralis.demo" },
];

function safeNext(raw: string | null): string | null {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//")) return null;
  if (raw.startsWith("/signin") || raw.startsWith("/login")) return null;
  return raw;
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="auralis-container py-16 text-sm text-muted">Loading sign-in…</div>}>
      <LoginPageContent />
    </Suspense>
  );
}

function LoginPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextPath = safeNext(searchParams.get("next"));
  const { me, account, signInLocal, signInPin, signInWithToken, signOut } = useSession();

  const [demoEnabled, setDemoEnabled] = useState(true);
  const [demoAccounts, setDemoAccounts] = useState<DemoAccount[]>(QUICK_FALLBACK);
  const [userId, setUserId] = useState("demo-clinician");
  const [password, setPassword] = useState("auralis-demo-2026");
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
  const [quickBusyId, setQuickBusyId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetch("/api/demo-accounts", { cache: "no-store" })
      .then((res) => res.json())
      .then((data: { enabled?: boolean; accounts?: DemoAccount[] }) => {
        if (!active) return;
        if (data.enabled === false) {
          setDemoEnabled(false);
          setUserId("");
          setPassword("");
        } else if (Array.isArray(data.accounts) && data.accounts.length > 0) {
          setDemoEnabled(true);
          setDemoAccounts(data.accounts);
        }
      })
      .catch(() => {
        // Keep helpful fallback presets visible if API is still warming up.
      });
    return () => {
      active = false;
    };
  }, []);

  async function destinationForIdentity() {
    if (nextPath) return nextPath;
    const result = await api<{ default_path: string | null }>("/v1/auth/workspaces");
    return result.default_path || "/app/icu";
  }

  async function run(action: () => Promise<string | void>) {
    setBusy(true);
    setError(null);
    try {
      const destination = await action();
      router.push(destination || nextPath || "/app/icu");
      router.refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
      setQuickBusyId(null);
    }
  }

  async function instantRoleLogin(uid: string, pwd: string, targetPath: string) {
    setUserId(uid);
    setPassword(pwd);
    setQuickBusyId(uid);
    await run(async () => {
      const result = await signInLocal(uid, pwd);
      if (result.must_change_password) return "/signin";
      return nextPath || result.destination || targetPath;
    });
  }

  return (
    <div className="min-h-screen bg-[#FAFBFA] py-10 lg:py-16">
      <div className="auralis-container-public">
        {/* Top return bar */}
        <div className="mb-8 flex items-center justify-between">
          <BrandMark href="/" />
          <Link href="/" className="text-sm font-medium text-muted hover:text-ink">
            ← Back to website
          </Link>
        </div>

        <div className="grid gap-8 lg:grid-cols-[1.08fr_0.92fr] lg:items-start">
          {/* LEFT: Instant 1-Click Role Access + Clean Sign-in Card */}
          <div className="space-y-6">
            {demoEnabled && !me && !account && (
              <section className="rounded-2xl border border-teal/25 bg-white p-6 shadow-sm sm:p-7">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="inline-flex items-center gap-2 rounded-full bg-teal/10 px-3 py-1 text-xs font-semibold text-teal">
                    <span className="h-2 w-2 rounded-full bg-teal" />
                    Instant Demo Access · 1-Click Sign In
                  </span>
                  <span className="text-xs text-muted">Password: <code className="rounded bg-muted-surface px-1.5 py-0.5 font-mono text-ink">auralis-demo-2026</code></span>
                </div>
                <h2 className="mt-3 font-display text-xl font-semibold text-ink">
                  Open a live workspace in one click
                </h2>
                <p className="mt-1 text-sm text-muted">
                  Click any role below to sign in automatically and open that dashboard right away.
                </p>

                <div className="mt-5 grid gap-2.5 sm:grid-cols-2">
                  {demoAccounts.map((acct) => {
                    const isLaunching = quickBusyId === acct.user_id;
                    return (
                      <button
                        key={acct.user_id}
                        type="button"
                        disabled={busy}
                        onClick={() => void instantRoleLogin(acct.user_id, acct.password, acct.default_path)}
                        className="group flex items-center justify-between rounded-xl border border-border bg-[#FAFBFA] px-4 py-3.5 text-left transition-all hover:border-teal hover:bg-white hover:shadow-sm disabled:opacity-50"
                      >
                        <div>
                          <p className="font-display text-sm font-semibold text-ink group-hover:text-teal">
                            {acct.label}
                          </p>
                          <p className="mt-0.5 font-mono text-[11px] text-muted">{acct.user_id}</p>
                        </div>
                        <span className="text-xs font-semibold text-teal">
                          {isLaunching ? "Opening…" : "Enter →"}
                        </span>
                      </button>
                    );
                  })}

                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void instantRoleLogin("vendor@auralis.demo", "auralis-demo-2026", "/platform/accounts")}
                    className="group flex items-center justify-between rounded-xl border border-border bg-[#FAFBFA] px-4 py-3.5 text-left transition-all hover:border-teal hover:bg-white hover:shadow-sm disabled:opacity-50"
                  >
                    <div>
                      <p className="font-display text-sm font-semibold text-ink group-hover:text-teal">
                        Vendor CRM & FDE Admin
                      </p>
                      <p className="mt-0.5 font-mono text-[11px] text-muted">vendor@auralis.demo</p>
                    </div>
                    <span className="text-xs font-semibold text-teal">
                      {quickBusyId === "vendor@auralis.demo" ? "Opening…" : "Enter →"}
                    </span>
                  </button>
                </div>
              </section>
            )}

            <section className="rounded-2xl border border-border bg-white p-6 shadow-sm sm:p-8">
              <h1 className="font-display text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
                Sign in with credentials
              </h1>
              <p className="mt-2 text-sm text-muted">
                Enter a hospital username (for clinical & deployment views) or an organization email (for Vendor & Customer Portal).
              </p>

              {account && (
                <Panel className="mt-6 rounded-xl">
                  <p className="text-sm">
                    Signed in as <strong>{account.display_name}</strong> ({account.email}).
                  </p>
                  {account.must_change_password ? (
                    <form
                      className="mt-4 grid gap-3 text-sm"
                      onSubmit={(event) => {
                        event.preventDefault();
                        void run(async () => {
                          await accountApi("/v1/auth/change-password", {
                            method: "POST",
                            body: JSON.stringify({ current_password: accountCurrent, new_password: accountNew }),
                          });
                          setAccountCurrent("");
                          setAccountNew("");
                          setAccountNotice("Password changed. Sign in again.");
                          signOut();
                          return "/signin";
                        });
                      }}
                    >
                      <p>Change your temporary password before continuing.</p>
                      <label className="auralis-label">
                        Current password
                        <input type="password" value={accountCurrent} onChange={(e) => setAccountCurrent(e.target.value)} required className="auralis-input" />
                      </label>
                      <label className="auralis-label">
                        New password
                        <input type="password" minLength={12} value={accountNew} onChange={(e) => setAccountNew(e.target.value)} required className="auralis-input" />
                      </label>
                      <button type="submit" className="auralis-btn-primary justify-self-start rounded-lg">
                        Update password
                      </button>
                    </form>
                  ) : (
                    <div className="mt-4 flex flex-wrap items-center gap-3">
                      <Link href={account.vendor ? "/platform/accounts" : "/portal"} className="auralis-btn-primary rounded-lg">
                        Open workspace →
                      </Link>
                      <button type="button" onClick={signOut} className="auralis-btn-secondary rounded-lg">
                        Sign out
                      </button>
                    </div>
                  )}
                </Panel>
              )}
              {accountNotice && <p role="status" className="mt-3 text-sm text-teal">{accountNotice}</p>}

              {me && (
                <>
                  <Panel className="mt-6 rounded-xl border-teal/30 bg-teal/5">
                    <p className="text-sm">
                      Signed in as <strong>{me.display_name || me.user_id}</strong> ({me.role})
                    </p>
                    <div className="mt-4 flex flex-wrap gap-3">
                      <Link href={nextPath || "/app/icu"} className="auralis-btn-primary rounded-lg">
                        Open ICU Dashboard →
                      </Link>
                      <button type="button" onClick={signOut} className="auralis-btn-secondary rounded-lg">
                        Sign out
                      </button>
                    </div>
                  </Panel>
                  {["password", "pin"].includes(me.auth_mode) && (
                    <div className="mt-4">
                      <AccountSecurity onDone={signOut} mustChange={me.must_change_password} />
                    </div>
                  )}
                </>
              )}

              {!me && !account && (
                <form
                  className="mt-6 grid gap-4"
                  onSubmit={(event) => {
                    event.preventDefault();
                    void run(async () => {
                      const result = await signInLocal(userId.trim(), password, totp || undefined);
                      if (remember) {
                        // Browser autofill hint only
                      }
                      return result.must_change_password ? "/signin" : result.destination || destinationForIdentity();
                    });
                  }}
                >
                  <label className="block text-xs font-semibold uppercase tracking-wide text-muted">
                    Username or Email
                    <input
                      value={userId}
                      onChange={(e) => setUserId(e.target.value)}
                      required
                      className="mt-1.5 block w-full rounded-lg border border-border bg-white px-3.5 py-2.5 text-sm text-ink focus:border-teal focus:outline-none"
                      autoComplete="username"
                      placeholder="e.g. demo-clinician"
                    />
                  </label>
                  <div>
                    <label htmlFor="auralis-password" className="block text-xs font-semibold uppercase tracking-wide text-muted">
                      Password
                    </label>
                    <div className="mt-1.5 flex items-center rounded-lg border border-border bg-white focus-within:border-teal">
                      <input
                        id="auralis-password"
                        type={showPassword ? "text" : "password"}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        className="min-w-0 flex-1 rounded-l-lg px-3.5 py-2.5 text-sm outline-none"
                        autoComplete="current-password"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword((v) => !v)}
                        className="px-3.5 py-2.5 text-xs font-medium text-muted hover:text-ink"
                      >
                        {showPassword ? "Hide" : "Show"}
                      </button>
                    </div>
                  </div>
                  <label className="block text-xs font-semibold uppercase tracking-wide text-muted">
                    2FA Code (optional unless enabled)
                    <input
                      inputMode="numeric"
                      value={totp}
                      onChange={(e) => setTotp(e.target.value.replace(/\D/g, "").slice(0, 6))}
                      className="mt-1.5 block w-full rounded-lg border border-border bg-white px-3.5 py-2.5 text-sm text-ink focus:border-teal focus:outline-none"
                      placeholder="6-digit code"
                    />
                  </label>
                  <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-muted">
                    <label className="inline-flex items-center gap-2">
                      <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
                      Remember me
                    </label>
                    <span>Hospital IT manages local password resets</span>
                  </div>
                  <button
                    type="submit"
                    disabled={busy}
                    className="auralis-btn-primary mt-1 w-full rounded-lg py-3 text-sm font-semibold disabled:opacity-50"
                  >
                    {busy ? "Signing in…" : "Sign In"}
                  </button>
                  {error && (
                    <p role="alert" className="rounded-lg border border-risk-high/30 bg-risk-high/5 px-3.5 py-2.5 text-sm text-risk-high">
                      {error}
                    </p>
                  )}
                </form>
              )}

              {!me && !account && (
                <div className="mt-6 space-y-2.5 border-t border-border pt-5">
                  <details className="group">
                    <summary className="cursor-pointer text-xs font-medium text-muted hover:text-ink">
                      Ward tablet PIN unlock
                    </summary>
                    <form
                      className="mt-3 grid gap-3 text-sm"
                      onSubmit={(event) => {
                        event.preventDefault();
                        void run(async () => {
                          await signInPin(userId.trim(), pin, totp || undefined);
                          return destinationForIdentity();
                        });
                      }}
                    >
                      <input
                        type="password"
                        inputMode="numeric"
                        value={pin}
                        onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 6))}
                        required
                        className="auralis-input rounded-lg"
                        placeholder="4–6 digit PIN"
                      />
                      <button type="submit" disabled={busy} className="auralis-btn-secondary justify-self-start rounded-lg">
                        Unlock for 15 minutes
                      </button>
                    </form>
                  </details>
                  <details className="group">
                    <summary className="cursor-pointer text-xs font-medium text-muted hover:text-ink">
                      Hospital SSO / OIDC token exchange
                    </summary>
                    <form
                      className="mt-3 grid gap-3 text-sm"
                      onSubmit={(event) => {
                        event.preventDefault();
                        void run(async () => {
                          await signInWithToken(token);
                          return destinationForIdentity();
                        });
                      }}
                    >
                      <textarea
                        value={token}
                        onChange={(e) => setToken(e.target.value)}
                        rows={2}
                        required
                        className="auralis-input rounded-lg font-mono text-xs"
                        placeholder="Paste validated OIDC access token"
                      />
                      <button type="submit" disabled={busy} className="auralis-btn-secondary justify-self-start rounded-lg">
                        Validate token
                      </button>
                    </form>
                  </details>
                </div>
              )}
            </section>
          </div>

          {/* RIGHT: Clean White Workspace Launcher (clicking signs in automatically in demo mode!) */}
          <aside className="rounded-2xl border border-border bg-white p-6 shadow-sm sm:p-8">
            <p className="text-xs font-semibold uppercase tracking-wider text-teal">All Workspaces</p>
            <h2 className="mt-2 font-display text-2xl font-semibold tracking-tight text-ink">
              Jump directly to a surface
            </h2>
            <p className="mt-1.5 text-sm text-muted">
              {me || account
                ? "Your session is active. Select a workspace to open it."
                : demoEnabled
                ? "In demo mode, clicking Go signs you in with the matching role automatically."
                : "Select a destination and sign in with your assigned credentials."}
            </p>

            <div className="mt-6 space-y-3">
              {WORKSPACES.map((item) => (
                <button
                  key={item.href}
                  type="button"
                  disabled={busy}
                  onClick={() => {
                    if (me || account) {
                      router.push(item.href);
                      return;
                    }
                    if (demoEnabled) {
                      const uid = item.demoEmail || item.demoUser || "demo-clinician";
                      void instantRoleLogin(uid, "auralis-demo-2026", item.href);
                      return;
                    }
                    router.push(`/signin?next=${encodeURIComponent(item.href)}`);
                  }}
                  className="group flex w-full items-center justify-between gap-4 rounded-xl border border-border bg-[#FAFBFA] p-4 text-left transition-all hover:border-teal hover:bg-white hover:shadow-sm disabled:opacity-50"
                >
                  <div>
                    <p className="font-display text-base font-semibold text-ink group-hover:text-teal">
                      {item.title}
                    </p>
                    <p className="mt-0.5 text-xs text-muted">{item.detail}</p>
                  </div>
                  <span className="shrink-0 rounded-full bg-teal/10 px-3 py-1 text-xs font-semibold text-teal group-hover:bg-teal group-hover:text-white">
                    Go →
                  </span>
                </button>
              ))}
            </div>
          </aside>
        </div>
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
        <form
          className="space-y-2 text-sm"
          onSubmit={(event) => {
            event.preventDefault();
            void run(
              () => api("/v1/auth/password", { method: "POST", body: JSON.stringify({ current_password: current, new_password: next }) }),
              "Password changed. Sign in again.",
              true,
            );
          }}
        >
          <input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} placeholder="Current password" className="auralis-input" required />
          <input type="password" value={next} onChange={(e) => setNext(e.target.value)} placeholder="New password (12+ chars)" className="auralis-input" required minLength={12} />
          <button className="auralis-btn-secondary">Change</button>
        </form>
      </Panel>
      {!mustChange && (
        <Panel title="Ward PIN">
          <form
            className="space-y-2 text-sm"
            onSubmit={(event) => {
              event.preventDefault();
              void run(() => api("/v1/auth/pin", { method: "POST", body: JSON.stringify({ pin }) }), "PIN changed. Sign in again.", true);
            }}
          >
            <input type="password" inputMode="numeric" value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="4–6 digits" className="auralis-input" required />
            <button className="auralis-btn-secondary">Set PIN</button>
          </form>
        </Panel>
      )}
      {!mustChange && (
        <Panel title="Two-factor auth">
          {!secret ? (
            <button
              type="button"
              className="auralis-btn-secondary text-sm"
              onClick={() =>
                void run(async () => {
                  const result = await api<{ secret: string }>("/v1/auth/totp/begin", { method: "POST" });
                  setSecret(result.secret);
                }, "Enter this secret in an authenticator, then confirm a code.")
              }
            >
              Begin setup
            </button>
          ) : (
            <form
              className="space-y-2 text-sm"
              onSubmit={(event) => {
                event.preventDefault();
                void run(() => api("/v1/auth/totp/confirm", { method: "POST", body: JSON.stringify({ code }) }), "Two-factor authentication enabled.");
              }}
            >
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
