"use client";

import { useEffect, useState } from "react";
import { ApiError, Panel, Pill } from "@/components/ui";
import { api } from "@/lib/api";
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

export default function ProfilePage() {
  const profile = usePoll(() => api<Profile>("/v1/auth/profile"), 15000);
  const [prefs, setPrefs] = useState<Profile["preferences"] | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [installEvent, setInstallEvent] = useState<Event | null>(null);

  useEffect(() => {
    if (profile.data && !prefs) setPrefs(profile.data.preferences);
  }, [profile.data, prefs]);
  useEffect(() => {
    const capture = (event: Event) => {
      event.preventDefault();
      setInstallEvent(event);
    };
    window.addEventListener("beforeinstallprompt", capture);
    return () => window.removeEventListener("beforeinstallprompt", capture);
  }, []);

  async function savePreferences() {
    if (!prefs) return;
    await api("/v1/auth/profile/preferences", { method: "PUT", body: JSON.stringify(prefs) });
    setMessage("Alert preferences saved.");
    await profile.refresh();
  }

  async function uploadAvatar(file: File | undefined) {
    if (!file) return;
    if (!new Set(["image/png", "image/jpeg", "image/webp"]).has(file.type)) {
      setMessage("Choose a PNG, JPEG or WebP image.");
      return;
    }
    if (file.size > 256 * 1024) {
      setMessage("Profile photos must be 256 KB or smaller.");
      return;
    }
    const dataUrl = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(new Error("Could not read that image."));
      reader.onload = () => typeof reader.result === "string" ? resolve(reader.result) : reject(new Error("Invalid image."));
      reader.readAsDataURL(file);
    });
    try {
      await api("/v1/auth/profile/avatar", { method: "PUT", body: JSON.stringify({ data_url: dataUrl }) });
      setMessage("Profile photo saved.");
      await profile.refresh();
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : String(cause));
    }
  }

  async function removeAvatar() {
    await api("/v1/auth/profile/avatar", { method: "DELETE" });
    setMessage("Profile photo removed.");
    await profile.refresh();
  }

  async function enrollDevice() {
    const permission =
      "Notification" in window ? await Notification.requestPermission() : "unsupported";
    const key = "predictrx-device-id";
    let deviceId = window.localStorage.getItem(key);
    if (!deviceId) {
      deviceId = `browser-${crypto.randomUUID()}`;
      window.localStorage.setItem(key, deviceId);
    }
    await api("/v1/auth/profile/devices", {
      method: "POST",
      body: JSON.stringify({
        device_id: deviceId,
        label: `${navigator.platform || "Hospital device"} browser`,
        user_agent: navigator.userAgent,
        notification_permission: permission,
      }),
    });
    setMessage(
      permission === "granted"
        ? "This browser is enrolled for alerts while the PWA is running/backgrounded."
        : `Device recorded; notification permission is ${permission}.`,
    );
    await profile.refresh();
  }

  async function installPwa() {
    if (!installEvent) {
      setMessage("Use your browser menu → Install app / Add to Home Screen.");
      return;
    }
    const prompt = installEvent as Event & { prompt: () => Promise<void> };
    await prompt.prompt();
    setInstallEvent(null);
  }

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">My hospital app</p>
        <h1 className="font-display text-3xl">{profile.data?.display_name ?? "Staff profile"}</h1>
        <p className="mt-1 text-sm text-ink/60">
          Personal alert inbox settings, shift context, enrolled ward devices, and acknowledgement history.
        </p>
      </header>
      {profile.error && <ApiError error={profile.error} />}
      {message && <p className="border border-accent/30 bg-accent/5 px-3 py-2 text-sm">{message}</p>}

      {profile.data && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Panel title="Identity & shift">
            <div className="mb-4 flex items-center gap-3">
              {profile.data.avatar_data_url
                ? <div role="img" aria-label={`${profile.data.display_name} profile photo`} style={{ backgroundImage: `url(${profile.data.avatar_data_url})` }} className="h-14 w-14 rounded-full bg-cover bg-center" />
                : <div aria-hidden="true" className="flex h-14 w-14 items-center justify-center rounded-full bg-mist text-lg font-semibold text-accent">{profile.data.display_name.slice(0, 1).toUpperCase()}</div>}
              <div><label className="block text-xs font-medium text-ink/60">Profile photo · PNG/JPEG/WebP · max 256 KB<input className="mt-1 block max-w-full text-xs" type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => void uploadAvatar(event.target.files?.[0])} /></label>
                {profile.data.avatar_data_url && <button type="button" className="mt-1 text-xs text-risk-high underline" onClick={() => void removeAvatar()}>Remove photo</button>}</div>
            </div>
            <p className="text-sm"><strong>{profile.data.user_id}</strong> · {profile.data.role}</p>
            <p className="mt-1 text-sm text-ink/60">Units: {profile.data.units?.join(", ") ?? "all assigned units"}</p>
            <p className="mt-3 text-sm">
              Current: <Pill tone={profile.data.current_shift.staff.some((p) => p.user_id === profile.data!.user_id) ? "success" : "info"}>
                {profile.data.current_shift.shift?.label ?? "No active shift"}
              </Pill>
            </p>
          </Panel>
          <Panel title="Install on ward device">
            <p className="text-sm text-ink/65">
              Install this PWA for full-screen bedside access and offline handoff shell. Each clinician still signs in
              with their own hospital identity/PIN.
            </p>
            <div className="mt-3 flex gap-2">
              <button className="bg-accent px-3 py-2 text-sm text-white" onClick={() => void installPwa()}>Install app</button>
              <button className="border border-ink/20 px-3 py-2 text-sm" onClick={() => void enrollDevice()}>Enable alerts on this device</button>
            </div>
            <p className="mt-3 text-xs text-ink/50">{profile.data.delivery_capability.note}</p>
          </Panel>
        </div>
      )}

      {prefs && (
        <Panel title="Alert preferences">
          <div className="grid gap-3 text-sm sm:grid-cols-2">
            <label className="flex gap-2"><input type="checkbox" checked={prefs.alert_notifications} onChange={(e) => setPrefs({ ...prefs, alert_notifications: e.target.checked })} />Browser alert notifications</label>
            <label className="flex gap-2"><input type="checkbox" checked={prefs.sound} onChange={(e) => setPrefs({ ...prefs, sound: e.target.checked })} />Sound when hospital policy permits</label>
            <label className="flex gap-2"><input type="checkbox" checked={prefs.quiet_when_off_shift} onChange={(e) => setPrefs({ ...prefs, quiet_when_off_shift: e.target.checked })} />Quiet when I am off shift</label>
            <label>Escalate after <input type="number" min={5} max={120} value={prefs.escalation_minutes} onChange={(e) => setPrefs({ ...prefs, escalation_minutes: Number(e.target.value) })} className="ml-2 w-20 border border-ink/20 px-2 py-1" /> min</label>
          </div>
          <button className="mt-4 bg-accent px-3 py-2 text-sm text-white" onClick={() => void savePreferences()}>Save preferences</button>
        </Panel>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title={`Enrolled devices (${profile.data?.devices.length ?? 0})`}>
          <ul className="space-y-2 text-sm">
            {profile.data?.devices.map((device) => (
              <li key={device.device_id} className="border-b border-ink/5 pb-2">
                <strong>{device.label}</strong><span className="block text-xs text-ink/50">{device.notification_permission} · enrolled {new Date(device.enrolled_at).toLocaleString()}</span>
              </li>
            ))}
            {!profile.data?.devices.length && <li className="text-ink/55">No ward browser enrolled yet.</li>}
          </ul>
        </Panel>
        <Panel title="My alert action history">
          <ul className="max-h-72 space-y-2 overflow-auto text-xs">
            {profile.data?.delivery_history.map((row, index) => (
              <li key={`${row.alert_id}-${index}`} className="border-b border-ink/5 pb-1">
                {row.at ? new Date(row.at).toLocaleString() : "—"} · <strong>{row.event.replaceAll("_", " ")}</strong> · {row.patient_id ?? "patient"}
                {row.reason ? <span className="block text-ink/55">{row.reason}</span> : null}
              </li>
            ))}
            {!profile.data?.delivery_history.length && <li className="text-ink/55">No alert actions recorded for this user.</li>}
          </ul>
        </Panel>
      </div>
    </div>
  );
}
