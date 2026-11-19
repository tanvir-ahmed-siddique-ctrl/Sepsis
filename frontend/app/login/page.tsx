"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, type ReactNode } from "react";
import { BrandMark } from "@/components/ui/BrandMark";
import { Icon, type IconName } from "@/components/ui/Icon";
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

const VENDOR_DEMO = { user_id: "vendor@auralis.demo", label: "Vendor control plane", password: "auralis-demo-2026", default_path: "/platform/accounts" };

const ROLE_META: Record<string, { icon: IconName; detail: string }> = {
  clinician: { icon: "grid", detail: "ICU board, alerts, handoff" },
  nurse: { icon: "clipboard", detail: "Charting and ward NEWS2" },
  admin: { icon: "building", detail: "Staff, unit settings, evaluation" },
  clinical_it: { icon: "server", detail: "Connectors and feed health" },
  operator: { icon: "gauge", detail: "Fleet health overview" },
  vendor: { icon: "layers", detail: "Tenants, licences, documents" },
};

const WORKSPACES = [
  { title: "Judge tour", detail: "Congress walkthrough: pitch → evidence → ICU", href: "/judge", icon: "shield" as IconName },
  { title: "180s presentation", detail: "Timed pitch replay for panels", href: "/presentation", icon: "activity" as IconName },
  { title: "ICU board", detail: "Live risk board, alerts and handoff", href: "/app/icu", icon: "grid" as IconName },
  { title: "Bedside charting", detail: "Flowsheet vitals and ward NEWS2", href: "/app/chart", icon: "clipboard" as IconName },
  { title: "Hospital administration", detail: "Staff access, unit settings, evaluation", href: "/app/admin/overview", icon: "building" as IconName },
  { title: "Deployment console", detail: "Connectors, quarantine, commissioning", href: "/deploy", icon: "server" as IconName },
  { title: "Vendor control plane", detail: "Tenants, licences, FDE projects", href: "/platform/accounts", icon: "layers" as IconName },
];

function safeNext(raw: string | null): string | null {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//")) return null;
  if (raw.startsWith("/signin") || raw.startsWith("/login")) return null;
  return raw;
}

function friendlyError(raw: string): string {
  const text = raw.toLowerCase();
  if (text.includes("failed to fetch") || text.includes("networkerror") || text.includes("load failed")) {
    return "Can't reach the sign-in service. Check your connection and try again.";
  }
  if (text.includes("429") || text.includes("too many") || text.includes("rate")) {
    return "Too many sign-in attempts. Wait a moment before trying again.";
  }
  if (text.includes("503") || text.includes("502") || text.includes("unavailable")) {
    return "The sign-in service is starting up or temporarily unavailable. Try again shortly.";
  }
  if (text.includes("totp") || text.includes("two-factor") || text.includes("2fa")) {
    return "That two-factor code wasn't accepted. Enter the current 6-digit code from your authenticator.";
  }
  if (text.includes("locked")) return "This account is temporarily locked. Contact hospital IT.";
  if (text.includes("invalid") || text.includes("incorrect") || text.includes("401") || text.includes("credentials")) {
    return "Username or password is incorrect.";
  }
  return raw;
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center text-sm text-muted">Loading sign-in…</div>}>
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
  const [userId, setUserId] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
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
        } else if (Array.isArray(data.accounts) && data.accounts.length > 0) {
          setDemoEnabled(true);
          setDemoAccounts(data.accounts);
        }
      })
      .catch(() => {
        // Keep fallback presets visible while the API warms up.
      });
    return () => {
      active = false;
    };
  }, []);

  function destinationForRole(role?: string | null) {
    if (nextPath) return nextPath;
    switch (role) {
      case "nurse":
        return "/app/chart";
      case "admin":
        return "/app/admin/overview";
      case "clinical_it":
        return "/deploy";
      case "operator":
        return "/platform/overview";
      default:
        return "/app/icu";
    }
  }

  function workspaceLabel(role?: string | null) {
    switch (role) {
      case "operator":
        return "Open fleet overview";
      case "clinical_it":
        return "Open deployment console";
      case "admin":
        return "Open hospital overview";
      case "nurse":
        return "Open charting";
      default:
        return "Open ICU board";
    }
  }

  async function destinationForIdentity() {
    if (nextPath) return nextPath;
    try {
      const result = await api<{ default_path: string | null }>("/v1/auth/workspaces");
      return result.default_path || destinationForRole(me?.role);
    } catch {
      return destinationForRole(me?.role);
    }
  }

  async function run(action: () => Promise<string | void>) {
    setBusy(true);
    setError(null);
    try {
      const destination = await action();
      router.push(destination || nextPath || "/app/icu");
      router.refresh();
    } catch (cause) {
      setError(friendlyError(cause instanceof Error ? cause.message : String(cause)));
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

  function signOutHere() {
    signOut();
    router.push("/signin");
    router.refresh();
  }

  const signedIn = Boolean(me || account);

  return (
    <div className="grid min-h-screen bg-white lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
      {/* Brand panel */}
      <aside className="relative hidden overflow-hidden bg-navy text-white lg:flex lg:flex-col lg:justify-between lg:p-12 xl:p-16">
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.35] [background-image:radial-gradient(rgba(115,195,207,0.25)_1px,transparent_1px)] [background-size:24px_24px] [mask-image:linear-gradient(160deg,#000_10%,transparent_65%)]"
          aria-hidden="true"
        />
        <div className="relative">
          <BrandMark href="/" tone="dark" />
        </div>
        <div className="relative max-w-md">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#73C3CF]">Clinical intelligence platform</p>
          <h2 className="mt-4 text-4xl font-semibold leading-[1.1] tracking-[-0.03em] text-white">
            Earlier sepsis signals, with the reasons attached.
          </h2>
          <ul className="mt-10 space-y-5 text-sm">
            {[
              ["activity", "Six-hour risk with trend and drivers for every scored bed."],
              ["shield", "TrustGate abstains when inputs are stale or invalid."],
              ["lock", "Role-based workspaces with separate clinical and vendor identities."],
            ].map(([icon, text]) => (
              <li key={text} className="flex items-start gap-3.5 text-white/75">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/5 text-[#73C3CF]">
                  <Icon name={icon as IconName} size={16} />
                </span>
                <span className="pt-1.5">{text}</span>
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-white/45">
          Assistive decision support. Clinical decisions remain with licensed clinicians.
        </p>
      </aside>

      {/* Form column */}
      <main className="flex min-w-0 flex-col">
        <div className="flex items-center justify-between gap-3 px-4 py-5 sm:px-10">
          <span className="min-w-0 lg:invisible">
            <BrandMark href="/" compact />
          </span>
          <Link href="/" className="group inline-flex shrink-0 items-center gap-1.5 text-sm font-medium text-muted hover:text-ink">
            <Icon name="arrow-left" size={16} className="transition-transform group-hover:-translate-x-0.5" />
            <span className="hidden sm:inline">Back to website</span>
            <span className="sm:hidden">Back</span>
          </Link>
        </div>

        <div className="flex flex-1 items-start justify-center px-4 pb-16 pt-4 sm:px-10 lg:items-center lg:pt-0">
          <div className="w-full max-w-[30rem] min-w-0">
            {!signedIn && (
              <>
                <h1 className="text-[1.75rem] font-semibold tracking-[-0.025em] text-ink">Sign in</h1>
                <p className="mt-1.5 text-sm text-muted">
                  Use your hospital username, or your organisation email for the vendor and customer portals.
                </p>
                {nextPath && (
                  <p className="mt-4 flex items-center gap-2 rounded-lg border border-border bg-canvas px-3 py-2 text-xs text-muted">
                    <Icon name="info" size={14} />
                    You&apos;ll continue to <span className="font-mono text-ink">{nextPath}</span> after signing in.
                  </p>
                )}
              </>
            )}

            {error && (
              <div role="alert" className="mt-6 flex gap-2.5 rounded-lg border border-risk-high/25 bg-risk-high/[0.05] px-3.5 py-3 text-sm text-risk-high">
                <Icon name="alert" size={17} className="mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            {/* Vendor / customer account session */}
            {account && (
              <SignedInCard name={account.display_name} detail={account.email}>
                {account.must_change_password ? (
                  <form
                    className="mt-5 grid gap-4"
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
                    <p className="text-sm text-muted">Change your temporary password before continuing.</p>
                    <Field label="Current password" htmlFor="acct-current">
                      <input id="acct-current" type="password" value={accountCurrent} onChange={(e) => setAccountCurrent(e.target.value)} required className="auralis-input" autoComplete="current-password" />
                    </Field>
                    <Field label="New password" htmlFor="acct-new" help="At least 12 characters.">
                      <input id="acct-new" type="password" minLength={12} value={accountNew} onChange={(e) => setAccountNew(e.target.value)} required className="auralis-input" autoComplete="new-password" />
                    </Field>
                    <button type="submit" disabled={busy} className="auralis-btn-primary">
                      {busy ? "Updating…" : "Update password"}
                    </button>
                  </form>
                ) : (
                  <div className="mt-5 flex flex-wrap gap-2.5">
                    <Link href={account.vendor ? "/platform/accounts" : "/portal"} className="group auralis-btn-primary">
                      Open workspace
                      <Icon name="arrow-right" size={16} className="transition-transform group-hover:translate-x-0.5" />
                    </Link>
                    <button type="button" onClick={signOut} className="auralis-btn-secondary">
                      Sign out
                    </button>
                  </div>
                )}
              </SignedInCard>
            )}
            {accountNotice && <p role="status" className="mt-3 text-sm text-teal">{accountNotice}</p>}

            {/* Hospital session */}
            {me && (
              <>
                <SignedInCard name={me.display_name || me.user_id} detail={me.role.replace(/_/g, " ")}>
                  <div className="mt-5 flex flex-wrap gap-2.5">
                    <Link href={destinationForRole(me.role)} className="group auralis-btn-primary">
                      {workspaceLabel(me.role)}
                      <Icon name="arrow-right" size={16} className="transition-transform group-hover:translate-x-0.5" />
                    </Link>
                    <button type="button" onClick={signOutHere} className="auralis-btn-secondary">
                      Sign out
                    </button>
                  </div>
                  {me.role === "operator" && (
                    <p className="mt-4 text-xs leading-5 text-muted">
                      Fleet overview uses the hospital operator session. For tenants, CRM and documents, sign out and use{" "}
                      <code className="rounded bg-muted-surface px-1 font-mono">vendor@auralis.demo</code>.
                    </p>
                  )}
                </SignedInCard>
                {["password", "pin"].includes(me.auth_mode) && (
                  <div className="mt-6">
                    <AccountSecurity onDone={signOutHere} mustChange={me.must_change_password} />
                  </div>
                )}
              </>
            )}

            {signedIn && (
              <section className="mt-8">
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted">Workspaces</p>
                <div className="mt-3 divide-y divide-border overflow-hidden rounded-xl border border-border">
                  {WORKSPACES.map((item) => (
                    <Link key={item.href} href={item.href} className="group flex items-center gap-3.5 bg-white px-4 py-3 transition-colors hover:bg-canvas">
                      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted-surface text-navy">
                        <Icon name={item.icon} size={16} />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block text-sm font-medium text-ink">{item.title}</span>
                        <span className="block text-xs text-muted">{item.detail}</span>
                      </span>
                      <Icon name="chevron-right" size={16} className="text-muted transition-transform group-hover:translate-x-0.5" />
                    </Link>
                  ))}
                </div>
                <p className="mt-2 text-xs text-muted">Workspaces outside your role will ask you to sign in with a different account.</p>
              </section>
            )}

            {/* Credentials form */}
            {!signedIn && (
              <form
                className="mt-7 grid gap-4"
                onSubmit={(event) => {
                  event.preventDefault();
                  void run(async () => {
                    const result = await signInLocal(userId.trim(), password, totp || undefined);
                    return result.must_change_password ? "/signin" : result.destination || destinationForIdentity();
                  });
                }}
              >
                <Field label="Username or email" htmlFor="auralis-user">
                  <input
                    id="auralis-user"
                    value={userId}
                    onChange={(e) => setUserId(e.target.value)}
                    required
                    className="auralis-input"
                    autoComplete="username"
                    placeholder="e.g. demo-clinician"
                    autoFocus
                  />
                </Field>
                <Field label="Password" htmlFor="auralis-password">
                  <div className="relative">
                    <input
                      id="auralis-password"
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      className="auralis-input pr-11"
                      autoComplete="current-password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((v) => !v)}
                      className="absolute inset-y-0 right-0 flex w-11 items-center justify-center text-muted hover:text-ink"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                      aria-pressed={showPassword}
                    >
                      <Icon name={showPassword ? "eye-off" : "eye"} size={17} />
                    </button>
                  </div>
                </Field>
                <Field label="Two-factor code" htmlFor="auralis-totp" help="Only required if two-factor authentication is enabled on your account.">
                  <input
                    id="auralis-totp"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    value={totp}
                    onChange={(e) => setTotp(e.target.value.replace(/\D/g, "").slice(0, 6))}
                    className="auralis-input font-mono tracking-[0.3em] placeholder:font-sans placeholder:tracking-normal"
                    placeholder="6-digit code"
                  />
                </Field>
                <button type="submit" disabled={busy} className="auralis-btn-primary mt-1 h-12 w-full">
                  {busy && !quickBusyId ? <Spinner /> : null}
                  {busy && !quickBusyId ? "Signing in…" : "Sign in"}
                </button>
                <p className="text-center text-xs text-muted">Forgotten passwords are reset by your hospital IT administrator.</p>
              </form>
            )}

            {/* Quick role access */}
            {!signedIn && demoEnabled && (
              <section className="mt-8" aria-labelledby="role-access-heading">
                <div className="flex items-center gap-3">
                  <span className="h-px flex-1 bg-border" />
                  <h2 id="role-access-heading" className="text-xs font-medium text-muted">
                    Quick role access
                  </h2>
                  <span className="h-px flex-1 bg-border" />
                </div>
                <div className="mt-4 grid gap-2 sm:grid-cols-2">
                  {[...demoAccounts.map((acct) => ({ ...acct, key: acct.role })), { ...VENDOR_DEMO, role: "vendor", key: "vendor" }].map((acct) => {
                    const meta = ROLE_META[acct.key] ?? ROLE_META.clinician;
                    const launching = quickBusyId === acct.user_id;
                    return (
                      <button
                        key={acct.user_id}
                        type="button"
                        disabled={busy}
                        onClick={() => void instantRoleLogin(acct.user_id, acct.password, acct.default_path)}
                        className="group flex items-center gap-3 rounded-xl border border-border bg-white px-3 py-2.5 text-left transition-all hover:border-[#C3CDD3] hover:shadow-card disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted-surface text-navy transition-colors group-hover:bg-teal-soft group-hover:text-teal-dark">
                          {launching ? <Spinner /> : <Icon name={meta.icon} size={16} />}
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-[13px] font-semibold text-ink">{acct.label}</span>
                          <span className="block truncate text-xs text-muted">{launching ? "Signing in…" : meta.detail}</span>
                        </span>
                      </button>
                    );
                  })}
                </div>
                <p className="mt-3 text-center text-xs text-muted">
                  Synthetic patients only. Shared password{" "}
                  <code className="rounded border border-border bg-canvas px-1.5 py-0.5 font-mono text-ink">auralis-demo-2026</code>
                </p>
              </section>
            )}

            {/* Alternative hospital sign-in methods */}
            {!signedIn && (
              <div className="mt-8 divide-y divide-border rounded-xl border border-border">
                <details className="group">
                  <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-3 text-sm font-medium text-ink [&::-webkit-details-marker]:hidden">
                    <span className="flex items-center gap-2.5">
                      <Icon name="key" size={16} className="text-muted" />
                      Ward tablet PIN unlock
                    </span>
                    <Icon name="chevron-down" size={16} className="text-muted transition-transform group-open:rotate-180" />
                  </summary>
                  <form
                    className="grid gap-3 px-4 pb-4"
                    onSubmit={(event) => {
                      event.preventDefault();
                      void run(async () => {
                        await signInPin(userId.trim(), pin, totp || undefined);
                        return destinationForIdentity();
                      });
                    }}
                  >
                    <p className="text-xs text-muted">Uses the username entered above. Unlocks a 15-minute session.</p>
                    <input
                      type="password"
                      inputMode="numeric"
                      aria-label="Ward PIN"
                      value={pin}
                      onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 6))}
                      required
                      className="auralis-input"
                      placeholder="4–6 digit PIN"
                    />
                    <button type="submit" disabled={busy || !userId.trim()} className="auralis-btn-secondary justify-self-start">
                      Unlock
                    </button>
                  </form>
                </details>
                <details className="group">
                  <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-3 text-sm font-medium text-ink [&::-webkit-details-marker]:hidden">
                    <span className="flex items-center gap-2.5">
                      <Icon name="building" size={16} className="text-muted" />
                      Hospital SSO token exchange
                    </span>
                    <Icon name="chevron-down" size={16} className="text-muted transition-transform group-open:rotate-180" />
                  </summary>
                  <form
                    className="grid gap-3 px-4 pb-4"
                    onSubmit={(event) => {
                      event.preventDefault();
                      void run(async () => {
                        await signInWithToken(token);
                        return destinationForIdentity();
                      });
                    }}
                  >
                    <p className="text-xs text-muted">Paste an access token issued by your hospital&apos;s OIDC provider. It is validated server-side.</p>
                    <textarea
                      value={token}
                      onChange={(e) => setToken(e.target.value)}
                      rows={3}
                      required
                      aria-label="OIDC access token"
                      className="auralis-input font-mono text-xs"
                      placeholder="eyJhbGciOi…"
                    />
                    <button type="submit" disabled={busy} className="auralis-btn-secondary justify-self-start">
                      Validate token
                    </button>
                  </form>
                </details>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function Spinner() {
  return <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-r-transparent" aria-hidden="true" />;
}

function Field({ label, htmlFor, help, children }: { label: string; htmlFor: string; help?: string; children: ReactNode }) {
  return (
    <div>
      <label htmlFor={htmlFor} className="auralis-label">
        {label}
      </label>
      {children}
      {help && <p className="auralis-help">{help}</p>}
    </div>
  );
}

function SignedInCard({ name, detail, children }: { name: string; detail: string; children: ReactNode }) {
  return (
    <section className="mt-6 rounded-xl border border-border bg-canvas p-5">
      <div className="flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-full bg-navy text-sm font-semibold text-white">
          {name.slice(0, 1).toUpperCase()}
        </span>
        <div className="min-w-0">
          <p className="text-xs text-muted">Signed in as</p>
          <p className="truncate text-[15px] font-semibold text-ink">
            {name} <span className="font-normal capitalize text-muted">· {detail}</span>
          </p>
        </div>
      </div>
      {children}
    </section>
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
    <div className="grid gap-4">
      {mustChange && <p className="text-sm font-medium text-ink">Change your temporary password to continue.</p>}
      <Panel title="Change password">
        <form
          className="grid gap-2.5 text-sm"
          onSubmit={(event) => {
            event.preventDefault();
            void run(
              () => api("/v1/auth/password", { method: "POST", body: JSON.stringify({ current_password: current, new_password: next }) }),
              "Password changed. Sign in again.",
              true,
            );
          }}
        >
          <input type="password" aria-label="Current password" value={current} onChange={(e) => setCurrent(e.target.value)} placeholder="Current password" className="auralis-input" required autoComplete="current-password" />
          <input type="password" aria-label="New password" value={next} onChange={(e) => setNext(e.target.value)} placeholder="New password (12+ characters)" className="auralis-input" required minLength={12} autoComplete="new-password" />
          <button className="auralis-btn-secondary justify-self-start">Change password</button>
        </form>
      </Panel>
      {!mustChange && (
        <div className="grid gap-4 sm:grid-cols-2">
          <Panel title="Ward PIN">
            <form
              className="grid gap-2.5 text-sm"
              onSubmit={(event) => {
                event.preventDefault();
                void run(() => api("/v1/auth/pin", { method: "POST", body: JSON.stringify({ pin }) }), "PIN changed. Sign in again.", true);
              }}
            >
              <input type="password" inputMode="numeric" aria-label="New PIN" value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="4–6 digits" className="auralis-input" required />
              <button className="auralis-btn-secondary justify-self-start">Set PIN</button>
            </form>
          </Panel>
          <Panel title="Two-factor authentication">
            {!secret ? (
              <button
                type="button"
                className="auralis-btn-secondary"
                onClick={() =>
                  void run(async () => {
                    const result = await api<{ secret: string }>("/v1/auth/totp/begin", { method: "POST" });
                    setSecret(result.secret);
                  }, "Add this secret to an authenticator app, then confirm a code.")
                }
              >
                Begin setup
              </button>
            ) : (
              <form
                className="grid gap-2.5 text-sm"
                onSubmit={(event) => {
                  event.preventDefault();
                  void run(() => api("/v1/auth/totp/confirm", { method: "POST", body: JSON.stringify({ code }) }), "Two-factor authentication enabled.");
                }}
              >
                <code className="block break-all rounded-md bg-muted-surface p-2 text-xs">{secret}</code>
                <input inputMode="numeric" aria-label="Authenticator code" value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="6-digit code" className="auralis-input" required />
                <button className="auralis-btn-secondary justify-self-start">Confirm</button>
              </form>
            )}
          </Panel>
        </div>
      )}
      {message && <p role="status" className="text-sm text-muted">{message}</p>}
    </div>
  );
}
