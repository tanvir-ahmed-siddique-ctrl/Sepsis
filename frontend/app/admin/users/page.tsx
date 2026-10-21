"use client";

import { useState } from "react";
import { ApiError, Panel, Pill } from "@/components/ui";
import { api, ROLE_LABELS, type CareUnit, type LocalUser, type UserRole } from "@/lib/api";
import { usePoll } from "@/lib/usePoll";

const INPUT = "w-full border border-ink/20 bg-white px-2 py-1.5 text-sm outline-none focus:border-accent";
const ROLE_OPTIONS = (Object.keys(ROLE_LABELS) as UserRole[]).map((role) => (
  <option key={role} value={role}>{ROLE_LABELS[role]}</option>
));

export default function UsersPage() {
  const users = usePoll(() => api<{ users: LocalUser[] }>("/v1/auth/users"), 15000);
  const units = usePoll(() => api<{ units: CareUnit[] }>("/v1/care/units"), 30000);
  const [form, setForm] = useState({ user_id: "", display_name: "", role: "clinician", password: "", units: "" });
  const [editing, setEditing] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({ display_name: "", role: "clinician", units: "" });
  const [unitForm, setUnitForm] = useState({ unit_id: "", label: "", kind: "ward", news2_scale_default: "1" });
  const [message, setMessage] = useState<string | null>(null);

  async function create() {
    try {
      await api("/v1/auth/users", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          units: form.units ? form.units.split(",").map((value) => value.trim()).filter(Boolean) : null,
        }),
      });
      setForm({ user_id: "", display_name: "", role: "clinician", password: "", units: "" });
      setMessage("User created with a temporary password.");
      await users.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    }
  }

  async function toggle(user: LocalUser) {
    try {
      await api(`/v1/auth/users/${encodeURIComponent(user.user_id)}`, {
        method: "PATCH",
        body: JSON.stringify({ disabled: !user.disabled }),
      });
      setMessage(`${user.user_id} ${user.disabled ? "enabled" : "disabled"}; existing sessions were revoked.`);
      await users.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    }
  }

  async function reset(user: LocalUser) {
    const next = window.prompt(`Temporary password for ${user.user_id} (12+ characters)`);
    if (!next) return;
    try {
      await api(`/v1/auth/users/${encodeURIComponent(user.user_id)}/reset-password`, {
        method: "POST",
        body: JSON.stringify({ new_password: next }),
      });
      setMessage(`${user.user_id} must change the temporary password at next sign-in.`);
      await users.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    }
  }

  function beginEdit(user: LocalUser) {
    setEditing(user.user_id);
    setEditForm({
      display_name: user.display_name,
      role: user.role,
      units: user.units?.join(", ") ?? "",
    });
  }

  async function saveEdit(user: LocalUser) {
    try {
      await api(`/v1/auth/users/${encodeURIComponent(user.user_id)}`, {
        method: "PATCH",
        body: JSON.stringify({
          display_name: editForm.display_name,
          role: editForm.role,
          units: editForm.units ? editForm.units.split(",").map((value) => value.trim()).filter(Boolean) : null,
        }),
      });
      setEditing(null);
      setMessage(`${user.user_id} updated; access-changing edits revoke existing sessions.`);
      await users.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    }
  }

  async function resetFactors(user: LocalUser) {
    if (!window.confirm(`Remove the PIN and authenticator app from ${user.user_id}?`)) return;
    try {
      await api(`/v1/auth/users/${encodeURIComponent(user.user_id)}/reset-factors`, { method: "POST" });
      setMessage(`${user.user_id}'s PIN and 2FA were reset; existing sessions were revoked.`);
      await users.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    }
  }

  async function remove(user: LocalUser) {
    const confirmation = window.prompt(`Type ${user.user_id} to permanently remove this login profile. Clinical audit records retain the user ID.`);
    if (confirmation !== user.user_id) return;
    try {
      await api(`/v1/auth/users/${encodeURIComponent(user.user_id)}`, { method: "DELETE" });
      setMessage(`${user.user_id} removed. Historical audit attribution was retained.`);
      await users.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    }
  }

  async function saveUnit() {
    try {
      await api("/v1/care/units", {
        method: "POST",
        body: JSON.stringify({
          ...unitForm,
          news2_scale_default: Number(unitForm.news2_scale_default),
        }),
      });
      setMessage(`Care unit ${unitForm.unit_id} saved.`);
      setUnitForm({ unit_id: "", label: "", kind: "ward", news2_scale_default: "1" });
      await units.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-display text-3xl">Site users</h1>
        <p className="mt-1 text-sm text-ink/60">Individual accounts, role and unit scope. Never create a shared ward account.</p>
      </div>
      {users.data?.users.some((user) => user.user_id.startsWith("sim-")) && (
        <p className="rounded-lg bg-accent/5 px-4 py-3 text-sm text-ink/70">
          Public commissioning roster: these named simulation accounts show role and unit assignment. The role picker
          signs reviewers in separately; a hospital provisions its own staff accounts or identity provider.
        </p>
      )}
      {users.error && <ApiError error={users.error} />}
      <Panel title="Create local user">
        <form className="grid gap-3 md:grid-cols-3" onSubmit={(event) => { event.preventDefault(); void create(); }}>
          <input className={INPUT} value={form.user_id} onChange={(e) => setForm({ ...form, user_id: e.target.value })} placeholder="User ID" required />
          <input className={INPUT} value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} placeholder="Display name" required />
          <select className={INPUT} value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
            {ROLE_OPTIONS}
          </select>
          <input className={INPUT} type="password" minLength={12} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder="Temporary password (12+)" required />
          <input className={INPUT} value={form.units} onChange={(e) => setForm({ ...form, units: e.target.value })} placeholder="Units, comma-separated; blank = all" list="care-units" />
          <datalist id="care-units">{units.data?.units.map((unit) => <option key={unit.unit_id} value={unit.unit_id} />)}</datalist>
          <button className="border border-accent bg-accent px-3 py-1.5 text-sm font-medium text-white">Create user</button>
        </form>
        {message && <p className="mt-3 text-sm">{message}</p>}
      </Panel>
      <Panel title="Hospital units">
        <p className="mb-3 text-sm text-ink/60">
          Create a ward or ICU before assigning staff and admitting patients. Reuse an existing unit ID to update its label or NEWS2 default; IDs remain stable for audit history.
        </p>
        <form className="grid gap-3 md:grid-cols-5" onSubmit={(event) => { event.preventDefault(); void saveUnit(); }}>
          <input className={INPUT} value={unitForm.unit_id} onChange={(e) => setUnitForm({ ...unitForm, unit_id: e.target.value })} placeholder="Unit ID, e.g. medicine-a" required />
          <input className={INPUT} value={unitForm.label} onChange={(e) => setUnitForm({ ...unitForm, label: e.target.value })} placeholder="Display label" required />
          <select className={INPUT} value={unitForm.kind} onChange={(e) => setUnitForm({ ...unitForm, kind: e.target.value })}>
            <option value="ward">Ward</option>
            <option value="icu">ICU</option>
          </select>
          <select className={INPUT} value={unitForm.news2_scale_default} onChange={(e) => setUnitForm({ ...unitForm, news2_scale_default: e.target.value })}>
            <option value="1">NEWS2 SpO₂ scale 1</option>
          </select>
          <button className="border border-accent bg-accent px-3 py-1.5 text-sm font-medium text-white">Save unit</button>
        </form>
        <div className="mt-3 flex flex-wrap gap-2">
          {units.data?.units.map((unit) => (
            <button
              type="button"
              key={unit.unit_id}
              className="border border-ink/15 px-2 py-1 text-left text-xs"
              onClick={() => setUnitForm({
                unit_id: unit.unit_id,
                label: unit.label,
                kind: unit.kind,
                news2_scale_default: String(unit.news2_scale_default),
              })}
            >
              <strong>{unit.label}</strong> · {unit.unit_id} · {unit.kind}
            </button>
          ))}
        </div>
      </Panel>
      <Panel title="Accounts">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-ink/10 text-xs uppercase text-ink/50">
              <tr><th className="p-2">User</th><th>Role / units</th><th>Security</th><th>Last login</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {users.data?.users.map((user) => (
                <tr key={user.user_id} className="border-b border-ink/5">
                  <td className="p-2">
                    {editing === user.user_id
                      ? <input className={INPUT} value={editForm.display_name} onChange={(e) => setEditForm({ ...editForm, display_name: e.target.value })} aria-label={`Display name for ${user.user_id}`} />
                      : <strong>{user.display_name}</strong>}
                    <span className="block text-xs text-ink/50">{user.user_id}</span>
                  </td>
                  <td>
                    {editing === user.user_id ? (
                      <div className="space-y-1 py-1">
                        <select className={INPUT} value={editForm.role} onChange={(e) => setEditForm({ ...editForm, role: e.target.value })} aria-label={`Role for ${user.user_id}`}>
                          {ROLE_OPTIONS}
                        </select>
                        <input className={INPUT} value={editForm.units} onChange={(e) => setEditForm({ ...editForm, units: e.target.value })} placeholder="all units" aria-label={`Units for ${user.user_id}`} />
                      </div>
                    ) : (
                      <>{ROLE_LABELS[user.role] ?? user.role}<span className="block text-xs text-ink/50">{user.units?.join(", ") || "all units"}</span></>
                    )}
                  </td>
                  <td className="space-x-1">
                    {user.disabled && <Pill tone="danger">disabled</Pill>}
                    {user.must_change_password && <Pill tone="warning">change password</Pill>}
                    {user.totp_enabled && <Pill tone="success">2FA</Pill>}
                    {user.pin_set && <Pill>PIN</Pill>}
                  </td>
                  <td>{user.last_login_at ? new Date(user.last_login_at).toLocaleString() : "never"}</td>
                  <td className="space-x-2">
                    <button type="button" className="underline" onClick={() => void toggle(user)}>{user.disabled ? "Enable" : "Disable"}</button>
                    <button type="button" className="underline" onClick={() => void reset(user)}>Reset password</button>
                    <button type="button" className="underline" onClick={() => void resetFactors(user)}>Reset PIN/2FA</button>
                    {editing === user.user_id ? (
                      <>
                        <button type="button" className="underline" onClick={() => void saveEdit(user)}>Save</button>
                        <button type="button" className="underline" onClick={() => setEditing(null)}>Cancel</button>
                      </>
                    ) : (
                      <button type="button" className="underline" onClick={() => beginEdit(user)}>Edit</button>
                    )}
                    <button type="button" className="text-risk-high underline" onClick={() => void remove(user)}>Remove</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
