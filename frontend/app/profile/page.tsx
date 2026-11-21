"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { ApiError, EmptyState, FileDrop, KeyValue, PageHeader, Panel, Pill, Skeleton, Tabs } from "@/components/ui";
import { Icon } from "@/components/ui/Icon";
import { api } from "@/lib/api";
import { humanize } from "@/lib/pilot";
import { useSession } from "@/lib/session";
import { usePoll } from "@/lib/usePoll";

type Profile = {
  user_id: string;
  display_name: string;
  avatar_data_url?: string | null;
  role: string;
  units: string[] | null;
  preferences: {
    alert_notifications: boolean;
    sound: boolean;
    quiet_when_off_shift: boolean;
    escalation_minutes: number;
  };
  devices: {
    device_id: string;
    label: string;
    kind: string;
    notification_permission: string;
    enrolled_at: string;
  }[];
  current_shift: { shift: { label: string; start: string; end: string } | null; staff: { user_id: string }[] };
  delivery_history: { event: string; alert_id: string | null; patient_id: string | null; at: string | null; reason: string | null }[];
  delivery_capability: { browser_notifications: boolean; closed_app_web_push: boolean; note: string };
};

type Workspaces = { site_id: string; workspaces: { id: string; label: string; path: string; scope: string }[]; default_path: string | null };

type TabId = "overview" | "personal" | "access" | "security" | "preferences" | "auralis-ai" | "activity";

const TABS: Array<{ id: TabId; label: string; icon: "user" | "doc" | "building" | "shield" | "settings" | "layers" | "clock" }> = [
  { id: "overview", label: "Overview", icon: "user" },
  { id: "personal", label: "Personal information", icon: "doc" },
  { id: "access", label: "Organization & access", icon: "building" },
  { id: "security", label: "Security", icon: "shield" },
  { id: "preferences", label: "Preferences", icon: "settings" },
  { id: "auralis-ai", label: "Auri AI", icon: "layers" },
  { id: "activity", label: "Activity", icon: "clock" },
];

const PIN_ROLES = new Set(["clinician", "nurse", "admin"]);
const AVATAR_MAX_BYTES = 256 * 1024;

type Notice = { tone: "success" | "danger"; text: string } | null;

export default function ProfilePage() {
  const router = useRouter();
  const { me, signOut } = useSession();
  const profile = usePoll(() => api<Profile>("/v1/auth/profile"), 15000);
  const [tab, setTab] = useState<TabId>("overview");
  const [notice, setNotice] = useState<Notice>(null);

  useEffect(() => {
    const fromHash = window.location.hash.replace("#", "") as TabId;
    if (TABS.some((item) => item.id === fromHash)) setTab(fromHash);
  }, []);

  function changeTab(id: TabId) {
    setTab(id);
    setNotice(null);
    window.history.replaceState(null, "", `#${id}`);
  }

  async function act(action: () => Promise<unknown>, success: string) {
    setNotice(null);
    try {
      await action();
      setNotice({ tone: "success", text: success });
      await profile.refresh();
      return true;
    } catch (cause) {
      setNotice({ tone: "danger", text: cause instanceof Error ? cause.message : String(cause) });
      return false;
    }
  }

  function signOutToSignIn() {
    signOut();
    router.push("/signin");
    router.refresh();
  }

  const data = profile.data;

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader eyebrow="Account" title="Profile and security" description="Your identity, access, sign-in security and alert preferences for this hospital site." />

      {profile.error && <ApiError error={profile.error} />}

      {!data && !profile.error && (
        <div className="space-y-4">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      )}

      {data && (
        <>
          <div className="mb-6 flex flex-wrap items-center gap-4">
            <Avatar profile={data} size="lg" />
            <div className="min-w-0">
              <p className="text-lg font-semibold text-ink">{data.display_name}</p>
              <p className="text-sm text-muted">
                <span className="font-mono">{data.user_id}</span> · {humanize(data.role)}
              </p>
            </div>
            <div className="ml-auto flex flex-wrap gap-2">
              <Pill tone={me?.totp_enabled ? "success" : "neutral"}>
                <Icon name="shield" size={12} />
                {me?.totp_enabled ? "Two-factor on" : "Two-factor off"}
              </Pill>
              <ShiftPill profile={data} />
            </div>
          </div>

          <Tabs tabs={TABS} value={tab} onChange={changeTab} label="Profile sections" />

          {notice && (
            <div
              role={notice.tone === "danger" ? "alert" : "status"}
              className={`mt-5 flex items-center gap-2 rounded-lg border px-3.5 py-2.5 text-sm ${
                notice.tone === "success" ? "border-risk-stable/25 bg-risk-stable/[0.05] text-risk-stable" : "border-risk-high/25 bg-risk-high/[0.05] text-risk-high"
              }`}
            >
              <Icon name={notice.tone === "success" ? "check" : "alert"} size={16} />
              {notice.text}
            </div>
          )}

          <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} className="mt-6 space-y-5">
            {tab === "overview" && <OverviewTab profile={data} totp={Boolean(me?.totp_enabled)} authMode={me?.auth_mode} go={changeTab} />}
            {tab === "personal" && <PersonalTab profile={data} act={act} />}
            {tab === "access" && <AccessTab profile={data} />}
            {tab === "security" && (
              <SecurityTab
                role={data.role}
                authMode={me?.auth_mode ?? ""}
                totpEnabled={Boolean(me?.totp_enabled)}
                act={act}
                onCredentialChanged={signOutToSignIn}
              />
            )}
            {tab === "preferences" && <PreferencesTab profile={data} act={act} setNotice={setNotice} />}
            {tab === "auralis-ai" && <AuralisAiTab role={data.role} />}
            {tab === "activity" && <ActivityTab profile={data} />}
          </div>
        </>
      )}
    </div>
  );
}

function Avatar({ profile, size = "md" }: { profile: Profile; size?: "md" | "lg" }) {
  const dims = size === "lg" ? "h-14 w-14 text-lg" : "h-10 w-10 text-sm";
  if (profile.avatar_data_url) {
    return (
      <div
        role="img"
        aria-label={`${profile.display_name} profile photo`}
        style={{ backgroundImage: `url(${profile.avatar_data_url})` }}
        className={`${dims} shrink-0 rounded-full bg-cover bg-center ring-1 ring-border`}
      />
    );
  }
  return (
    <div aria-hidden="true" className={`${dims} flex shrink-0 items-center justify-center rounded-full bg-navy font-semibold text-white`}>
      {profile.display_name.slice(0, 1).toUpperCase()}
    </div>
  );
}

function ShiftPill({ profile }: { profile: Profile }) {
  const onShift = profile.current_shift.staff.some((person) => person.user_id === profile.user_id);
  return (
    <Pill tone={onShift ? "success" : "neutral"}>
      <Icon name="clock" size={12} />
      {profile.current_shift.shift ? `${profile.current_shift.shift.label}${onShift ? " · on shift" : ""}` : "No active shift"}
    </Pill>
  );
}

function OverviewTab({ profile, totp, authMode, go }: { profile: Profile; totp: boolean; authMode?: string; go: (id: TabId) => void }) {
  const cards: Array<{ title: string; value: string; detail: string; target: TabId }> = [
    { title: "Access", value: humanize(profile.role), detail: profile.units?.length ? `Units ${profile.units.join(", ")}` : "All assigned units", target: "access" },
    { title: "Sign-in security", value: totp ? "Two-factor enabled" : "Password only", detail: authMode ? `Session via ${humanize(authMode)}` : "Hospital identity", target: "security" },
    { title: "Alert delivery", value: profile.preferences.alert_notifications ? "Notifications on" : "Notifications off", detail: `${profile.devices.length} enrolled device${profile.devices.length === 1 ? "" : "s"}`, target: "preferences" },
    { title: "Recent activity", value: `${profile.delivery_history.length} alert action${profile.delivery_history.length === 1 ? "" : "s"}`, detail: "Acknowledge, snooze, escalate", target: "activity" },
  ];
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {cards.map((card) => (
        <button key={card.title} type="button" onClick={() => go(card.target)} className="auralis-btn-reset group rounded-xl border border-border bg-white p-5 text-left shadow-soft transition-all hover:-translate-y-px hover:shadow-card">
          <span className="flex items-center justify-between text-xs font-medium text-muted">
            {card.title}
            <Icon name="chevron-right" size={16} className="transition-transform group-hover:translate-x-0.5" />
          </span>
          <span className="mt-2 block text-lg font-semibold text-ink">{card.value}</span>
          <span className="mt-0.5 block text-sm text-muted">{card.detail}</span>
        </button>
      ))}
    </div>
  );
}

function PersonalTab({ profile, act }: { profile: Profile; act: (action: () => Promise<unknown>, success: string) => Promise<boolean> }) {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);

  async function upload() {
    if (!file) return;
    setBusy(true);
    const ok = await act(async () => {
      const dataUrl = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onerror = () => reject(new Error("Could not read that image."));
        reader.onload = () => (typeof reader.result === "string" ? resolve(reader.result) : reject(new Error("Invalid image.")));
        reader.readAsDataURL(file);
      });
      await api("/v1/auth/profile/avatar", { method: "PUT", body: JSON.stringify({ data_url: dataUrl }) });
    }, "Profile photo saved.");
    if (ok) setFile(null);
    setBusy(false);
  }

  return (
    <>
      <Panel title="Profile photo" description="Shown to colleagues in rosters and handoff. Stored on this hospital's server.">
        <div className="grid gap-5 sm:grid-cols-[auto_1fr] sm:items-start">
          <Avatar profile={profile} size="lg" />
          <div className="space-y-3">
            <FileDrop label="Upload a new photo" accept="image/png,image/jpeg,image/webp" acceptLabel="PNG, JPEG or WebP" maxBytes={AVATAR_MAX_BYTES} file={file} onFile={setFile} disabled={busy} compact />
            <div className="flex flex-wrap gap-2">
              <button type="button" className="auralis-btn-primary auralis-btn-sm" disabled={!file || busy} onClick={() => void upload()}>
                {busy ? "Saving…" : "Save photo"}
              </button>
              {profile.avatar_data_url && (
                <button
                  type="button"
                  className="auralis-btn-danger auralis-btn-sm"
                  disabled={busy}
                  onClick={() => void act(() => api("/v1/auth/profile/avatar", { method: "DELETE" }), "Profile photo removed.")}
                >
                  Remove photo
                </button>
              )}
            </div>
          </div>
        </div>
      </Panel>
      <Panel title="Identity" description="Your name, username and role come from the hospital identity record and can only be changed by a hospital administrator.">
        <dl>
          <KeyValue label="Display name" value={profile.display_name} />
          <KeyValue label="Username" value={<span className="font-mono">{profile.user_id}</span>} />
          <KeyValue label="Role" value={humanize(profile.role)} />
        </dl>
      </Panel>
    </>
  );
}

function AccessTab({ profile }: { profile: Profile }) {
  const { me } = useSession();
  const workspaces = usePoll(() => api<Workspaces>("/v1/auth/workspaces"), 60000);
  return (
    <>
      <Panel title="Role and scope">
        <dl>
          <KeyValue label="Primary role" value={humanize(profile.role)} />
          <KeyValue label="All roles" value={me?.roles?.length ? me.roles.map(humanize).join(", ") : humanize(profile.role)} />
          <KeyValue label="Units" value={profile.units?.length ? profile.units.join(", ") : "All assigned units"} />
          {workspaces.data && <KeyValue label="Site" value={<span className="font-mono">{workspaces.data.site_id}</span>} />}
          {me && <KeyValue label="Site mode" value={humanize(me.site_mode)} />}
        </dl>
      </Panel>
      <Panel title="Workspaces you can open" description="Resolved by the server from your role. Other workspaces are not available to this account.">
        {workspaces.error && <ApiError error={workspaces.error} />}
        {!workspaces.data && !workspaces.error && <Skeleton className="h-12 w-full" />}
        {workspaces.data && workspaces.data.workspaces.length === 0 && <p className="text-sm text-muted">No workspaces are assigned to this role.</p>}
        <ul className="divide-y divide-border">
          {workspaces.data?.workspaces.map((ws) => (
            <li key={ws.id}>
              <a href={ws.path} className="group flex items-center justify-between gap-3 py-3 text-sm">
                <span>
                  <span className="block font-medium text-ink">{ws.label}</span>
                  <span className="block font-mono text-xs text-muted">{ws.path}</span>
                </span>
                <span className="flex items-center gap-2">
                  {workspaces.data?.default_path === ws.path && <Pill tone="info">Default</Pill>}
                  <Icon name="chevron-right" size={16} className="text-muted transition-transform group-hover:translate-x-0.5" />
                </span>
              </a>
            </li>
          ))}
        </ul>
      </Panel>
    </>
  );
}

function SecurityTab({
  role,
  authMode,
  totpEnabled,
  act,
  onCredentialChanged,
}: {
  role: string;
  authMode: string;
  totpEnabled: boolean;
  act: (action: () => Promise<unknown>, success: string) => Promise<boolean>;
  onCredentialChanged: () => void;
}) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [pin, setPin] = useState("");
  const [secret, setSecret] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const localCredentials = ["password", "pin"].includes(authMode);
  const mismatch = confirm.length > 0 && confirm !== next;

  return (
    <>
      {!localCredentials && (
        <Panel title="Managed sign-in">
          <p className="text-sm text-muted">
            This session uses <strong className="text-ink">{humanize(authMode || "external")}</strong> authentication. Password and PIN are managed by your hospital identity provider.
          </p>
        </Panel>
      )}

      {localCredentials && (
        <Panel title="Change password" description="You'll be signed out on every device after changing it.">
          <form
            className="grid max-w-md gap-4"
            onSubmit={(event) => {
              event.preventDefault();
              if (mismatch) return;
              void act(
                () => api("/v1/auth/password", { method: "POST", body: JSON.stringify({ current_password: current, new_password: next }) }),
                "Password changed. Signing you out…",
              ).then((ok) => ok && onCredentialChanged());
            }}
          >
            <Field label="Current password" id="pw-current">
              <input id="pw-current" type="password" value={current} onChange={(e) => setCurrent(e.target.value)} className="auralis-input" required autoComplete="current-password" />
            </Field>
            <Field label="New password" id="pw-new" help="At least 12 characters.">
              <input id="pw-new" type="password" value={next} onChange={(e) => setNext(e.target.value)} className="auralis-input" required minLength={12} autoComplete="new-password" />
            </Field>
            <Field label="Confirm new password" id="pw-confirm" error={mismatch ? "Passwords don't match." : undefined}>
              <input id="pw-confirm" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} className="auralis-input" required minLength={12} autoComplete="new-password" aria-invalid={mismatch} />
            </Field>
            <button type="submit" className="auralis-btn-primary justify-self-start" disabled={mismatch}>
              Update password
            </button>
          </form>
        </Panel>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        {localCredentials && PIN_ROLES.has(role) && (
          <Panel title="Ward tablet PIN" description="A 4–6 digit PIN for quick 15-minute unlocks on shared ward devices.">
            <form
              className="grid gap-3"
              onSubmit={(event) => {
                event.preventDefault();
                void act(() => api("/v1/auth/pin", { method: "POST", body: JSON.stringify({ pin }) }), "PIN updated. Signing you out…").then((ok) => ok && onCredentialChanged());
              }}
            >
              <Field label="New PIN" id="pin-new">
                <input id="pin-new" type="password" inputMode="numeric" value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 6))} className="auralis-input max-w-[12rem] font-mono tracking-[0.3em]" required minLength={4} />
              </Field>
              <button type="submit" className="auralis-btn-secondary justify-self-start">
                Set PIN
              </button>
            </form>
          </Panel>
        )}

        <Panel title="Two-factor authentication" description="Require a 6-digit authenticator code at sign-in.">
          {totpEnabled ? (
            <p className="flex items-center gap-2 text-sm text-risk-stable">
              <Icon name="check" size={16} />
              Enabled for this account.
            </p>
          ) : !secret ? (
            <button
              type="button"
              className="auralis-btn-secondary"
              onClick={() =>
                void act(async () => {
                  const result = await api<{ secret: string }>("/v1/auth/totp/begin", { method: "POST" });
                  setSecret(result.secret);
                }, "Add this secret to your authenticator app, then confirm with a code.")
              }
            >
              Set up two-factor
            </button>
          ) : (
            <form
              className="grid gap-3"
              onSubmit={(event) => {
                event.preventDefault();
                void act(() => api("/v1/auth/totp/confirm", { method: "POST", body: JSON.stringify({ code }) }), "Two-factor authentication enabled.");
              }}
            >
              <div>
                <p className="auralis-label">Setup secret</p>
                <code className="block break-all rounded-lg border border-border bg-canvas p-3 font-mono text-xs text-ink">{secret}</code>
              </div>
              <Field label="Authenticator code" id="totp-code">
                <input id="totp-code" inputMode="numeric" autoComplete="one-time-code" value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))} className="auralis-input max-w-[12rem] font-mono tracking-[0.3em]" required />
              </Field>
              <button type="submit" className="auralis-btn-primary justify-self-start">
                Confirm and enable
              </button>
            </form>
          )}
        </Panel>
      </div>
    </>
  );
}

function AuralisAiTab({ role }: { role: string }) {
  const isIt = role === "admin" || role === "clinical_it" || role === "operator";
  const [status, setStatus] = useState<{
    configured: boolean;
    mode: string;
    model: string | null;
    has_api_key: boolean;
    source: string;
    note: string;
  } | null>(null);

  useEffect(() => {
    void api<{
      configured: boolean;
      mode: string;
      model: string | null;
      has_api_key: boolean;
      source: string;
      note: string;
    }>("/v1/site/auri-ai")
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);

  return (
    <div className="space-y-5">
      <Panel title="Auri AI · medical assistant / co-pilot">
        <p className="max-w-3xl text-sm leading-6 text-muted">
          <strong className="text-ink">Auri AI</strong> is the site-local assistant: local Qwen by default, optional
          vendor-bundled cloud LLM for better drafts — still never writes sepsis risk (Frozen Run 4 + TrustGate only).
        </p>
        {status && (
          <p className="mt-3 text-sm text-ink">
            Status: {status.configured ? "LLM configured" : "Deterministic retrieval"} · {status.mode}
            {status.model ? ` · ${status.model}` : ""} · source {status.source}
            {status.has_api_key ? " · cloud key on server" : ""}
          </p>
        )}
        <ul className="mt-4 space-y-2 text-sm text-ink">
          {[
            "Bangla / local lab → LOINC proposals (human SHA sign-off)",
            "Explain TrustGate, boards, and workflows in EN or বাংলা chrome",
            "Draft handoff / shift notes from fields already on screen (gated)",
            "Optional cloud model (licence-bundled) improves those jobs only",
          ].map((item) => (
            <li key={item} className="flex items-start gap-2">
              <Icon name="check" size={16} className="mt-0.5 shrink-0 text-teal" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
        <p className="mt-4 text-sm text-muted">
          Forbidden: diagnosis, prescriptions, changing Run 4, sending full identifiable charts to a public cloud by
          default. Product page:{" "}
          <a className="text-teal underline" href="/aurie">
            /aurie
          </a>
          .
        </p>
      </Panel>

      <Panel title="Language">
        <p className="text-sm leading-6 text-muted">
          Use the header <strong className="text-ink">Language</strong> dropdown (English / বাংলা) for menus and help.
          Disease names, LOINC, and drug-class labels stay <strong className="text-ink">English</strong> on clinical
          boards.
        </p>
      </Panel>

      <Panel title="Credentials & privacy">
        <p className="text-sm leading-6 text-muted">
          API keys are <strong className="text-ink">not stored in this browser</strong>. When Auralis includes cloud
          assist in a hospital deal, admin installs the key on the <strong className="text-ink">local server</strong>{" "}
          (encrypted). Clinicians only use Auri — they do not paste keys here.
        </p>
        {isIt ? (
          <p className="mt-3 text-sm text-ink">
            Configure under{" "}
            <a className="text-teal underline" href="/app/admin/setup">
              Hospital setup → Auri AI
            </a>
            . Plan: <code className="text-xs">docs/auralis-copilot-byo-llm.md</code>.
          </p>
        ) : (
          <p className="mt-3 text-sm text-muted">Ask clinical IT / admin if your site&apos;s licence includes cloud Auri assist.</p>
        )}
      </Panel>
    </div>
  );
}

function PreferencesTab({
  profile,
  act,
  setNotice,
}: {
  profile: Profile;
  act: (action: () => Promise<unknown>, success: string) => Promise<boolean>;
  setNotice: (notice: Notice) => void;
}) {
  const [prefs, setPrefs] = useState(profile.preferences);
  const [installEvent, setInstallEvent] = useState<Event | null>(null);
  const dirty = JSON.stringify(prefs) !== JSON.stringify(profile.preferences);

  useEffect(() => {
    const capture = (event: Event) => {
      event.preventDefault();
      setInstallEvent(event);
    };
    window.addEventListener("beforeinstallprompt", capture);
    return () => window.removeEventListener("beforeinstallprompt", capture);
  }, []);

  async function enrollDevice() {
    const permission = "Notification" in window ? await Notification.requestPermission() : "unsupported";
    const key = "predictrx-device-id";
    let deviceId = window.localStorage.getItem(key);
    if (!deviceId) {
      deviceId = `browser-${crypto.randomUUID()}`;
      window.localStorage.setItem(key, deviceId);
    }
    await act(
      () =>
        api("/v1/auth/profile/devices", {
          method: "POST",
          body: JSON.stringify({
            device_id: deviceId,
            label: `${navigator.platform || "Hospital device"} browser`,
            user_agent: navigator.userAgent,
            notification_permission: permission,
          }),
        }),
      permission === "granted" ? "This browser is enrolled for alerts while the app is open or in the background." : `Device recorded. Notification permission is ${permission}.`,
    );
  }

  async function installPwa() {
    if (!installEvent) {
      setNotice({ tone: "success", text: "Use your browser menu and choose Install app or Add to Home Screen." });
      return;
    }
    const prompt = installEvent as Event & { prompt: () => Promise<void> };
    await prompt.prompt();
    setInstallEvent(null);
  }

  const toggles: Array<{ key: "alert_notifications" | "sound" | "quiet_when_off_shift"; label: string; detail: string }> = [
    { key: "alert_notifications", label: "Browser alert notifications", detail: "Show a system notification when a new alert is assigned to you." },
    { key: "sound", label: "Sound", detail: "Play a tone with notifications, where hospital policy permits." },
    { key: "quiet_when_off_shift", label: "Quiet when off shift", detail: "Suppress personal notifications outside your rostered shift." },
  ];

  return (
    <>
      <Panel title="Alert notifications">
        <div className="divide-y divide-border">
          {toggles.map((toggle) => (
            <label key={toggle.key} className="flex cursor-pointer items-center justify-between gap-6 py-3.5">
              <span>
                <span className="block text-sm font-medium text-ink">{toggle.label}</span>
                <span className="block text-sm text-muted">{toggle.detail}</span>
              </span>
              <Switch checked={prefs[toggle.key]} onChange={(value) => setPrefs({ ...prefs, [toggle.key]: value })} label={toggle.label} />
            </label>
          ))}
          <div className="flex items-center justify-between gap-6 py-3.5">
            <label htmlFor="escalation" className="block">
              <span className="block text-sm font-medium text-ink">Escalate unacknowledged alerts after</span>
              <span className="block text-sm text-muted">Between 5 and 120 minutes.</span>
            </label>
            <div className="flex items-center gap-2">
              <input
                id="escalation"
                type="number"
                min={5}
                max={120}
                value={prefs.escalation_minutes}
                onChange={(e) => setPrefs({ ...prefs, escalation_minutes: Number(e.target.value) })}
                className="auralis-input h-10 w-20 text-right tabular-nums"
              />
              <span className="text-sm text-muted">min</span>
            </div>
          </div>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <button type="button" className="auralis-btn-primary" disabled={!dirty} onClick={() => void act(() => api("/v1/auth/profile/preferences", { method: "PUT", body: JSON.stringify(prefs) }), "Alert preferences saved.")}>
            Save preferences
          </button>
          {dirty && (
            <button type="button" className="auralis-btn-ghost" onClick={() => setPrefs(profile.preferences)}>
              Discard changes
            </button>
          )}
        </div>
      </Panel>

      <Panel
        title="Devices"
        description={profile.delivery_capability.note}
        actions={
          <div className="flex flex-wrap gap-2">
            <button type="button" className="auralis-btn-secondary auralis-btn-sm" onClick={() => void installPwa()}>
              Install app
            </button>
            <button type="button" className="auralis-btn-primary auralis-btn-sm" onClick={() => void enrollDevice()}>
              Enable alerts on this device
            </button>
          </div>
        }
      >
        {profile.devices.length === 0 ? (
          <p className="text-sm text-muted">No devices enrolled yet.</p>
        ) : (
          <ul className="divide-y divide-border">
            {profile.devices.map((device) => (
              <li key={device.device_id} className="flex items-center gap-3 py-3">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted-surface text-navy">
                  <Icon name="server" size={16} />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-ink">{device.label}</span>
                  <span className="block text-xs text-muted">
                    Notifications {device.notification_permission} · enrolled {new Date(device.enrolled_at).toLocaleString()}
                  </span>
                </span>
                <button
                  type="button"
                  className="auralis-btn-ghost auralis-btn-sm"
                  onClick={() => void act(() => api(`/v1/auth/profile/devices/${encodeURIComponent(device.device_id)}`, { method: "DELETE" }), "Device removed.")}
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </>
  );
}

function ActivityTab({ profile }: { profile: Profile }) {
  if (!profile.delivery_history.length) {
    return <EmptyState icon="clock" title="No alert actions yet" body="Acknowledgements, snoozes, escalations and dismissals you make will appear here." />;
  }
  return (
    <Panel title="Alert actions" description="Your 50 most recent alert actions on this site.">
      <ol className="relative space-y-0 border-l border-border pl-5">
        {profile.delivery_history.map((row, index) => (
          <li key={`${row.alert_id}-${index}`} className="relative pb-4 last:pb-0">
            <span className="absolute -left-[25px] top-1.5 h-2 w-2 rounded-full bg-teal ring-4 ring-white" aria-hidden="true" />
            <p className="text-sm text-ink">
              <span className="font-medium capitalize">{row.event.replaceAll("_", " ")}</span>
              {row.patient_id && <span className="text-muted"> · patient {row.patient_id}</span>}
            </p>
            <p className="text-xs text-muted">{row.at ? new Date(row.at).toLocaleString() : "Time not recorded"}</p>
            {row.reason && <p className="mt-0.5 text-sm text-muted">{row.reason}</p>}
          </li>
        ))}
      </ol>
    </Panel>
  );
}

function Switch({ checked, onChange, label }: { checked: boolean; onChange: (value: boolean) => void; label: string }) {
  return (
    <span className="relative inline-flex shrink-0">
      <input type="checkbox" role="switch" className="peer sr-only" checked={checked} onChange={(e) => onChange(e.target.checked)} aria-label={label} />
      <span className="h-6 w-10 rounded-full bg-[#D5DCE1] transition-colors peer-checked:bg-teal peer-focus-visible:ring-4 peer-focus-visible:ring-teal/20" />
      <span className="absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white shadow-soft transition-transform peer-checked:translate-x-4" />
    </span>
  );
}

function Field({ label, id, help, error, children }: { label: string; id: string; help?: string; error?: string; children: ReactNode }) {
  return (
    <div>
      <label htmlFor={id} className="auralis-label">
        {label}
      </label>
      {children}
      {error ? <p className="mt-1.5 text-xs font-medium text-risk-high">{error}</p> : help ? <p className="auralis-help">{help}</p> : null}
    </div>
  );
}
