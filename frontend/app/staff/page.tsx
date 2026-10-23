"use client";

import { useState } from "react";
import { ApiError, Panel, Pill } from "@/components/ui";
import { api, isStatus } from "@/lib/api";
import { usePoll } from "@/lib/usePoll";
import { useSession } from "@/lib/session";

type Assignment = {
  id: string;
  user_id: string;
  display_name: string;
  role: string;
  shift_id: string;
  unit_id: string | null;
  active: boolean;
};

type Roster = {
  shifts: { id: string; label: string; start: string; end: string }[];
  assignments: Assignment[];
  current: { shift: { label: string; start: string; end: string } | null; staff: Assignment[] };
  csv_template: string;
  note?: string;
};

const EMPTY = { user_id: "", display_name: "", role: "clinician", shift_id: "morning", unit_id: "", active: true };

export default function StaffPage() {
  const { me, isAdmin, loading } = useSession();
  const roster = usePoll(() => api<Roster>("/v1/site/shift-roster"), 15000);
  const [form, setForm] = useState(EMPTY);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [replace, setReplace] = useState(false);

  if (!loading && !me) {
    return (
      <ApiError error="Sign in first. The current-shift roster is hospital staff information, so it is not shown anonymously." />
    );
  }
  if (roster.error && isStatus(roster.error, 403)) {
    return <ApiError error="Your session cannot view this unit’s roster. Sign in with a clinical, operator, or admin role." />;
  }

  async function saveAssignment() {
    try {
      await api("/v1/site/shift-roster/assignments", {
        method: "PUT",
        body: JSON.stringify({ ...form, id: editingId, unit_id: form.unit_id || null }),
      });
      setMessage(`${editingId ? "Updated" : "Added"} ${form.display_name}.`);
      setForm(EMPTY);
      setEditingId(null);
      await roster.refresh();
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : String(cause));
    }
  }

  function beginEdit(row: Assignment) {
    setEditingId(row.id);
    setForm({
      user_id: row.user_id,
      display_name: row.display_name,
      role: row.role,
      shift_id: row.shift_id,
      unit_id: row.unit_id ?? "",
      active: row.active,
    });
  }

  async function remove(id: string) {
    await api(`/v1/site/shift-roster/assignments/${encodeURIComponent(id)}`, { method: "DELETE" });
    setMessage("Shift assignment deleted.");
    await roster.refresh();
  }

  async function importCsv() {
    if (!csvFile) return;
    await api(`/v1/site/shift-roster/csv?replace=${replace}`, {
      method: "POST",
      headers: { "Content-Type": "text/csv; charset=utf-8" },
      body: await csvFile.text(),
    });
    setMessage(`Imported ${csvFile.name}.`);
    await roster.refresh();
  }

  const data = roster.data;
  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">Current team</p>
        <h1 className="font-display text-3xl">Who is on this shift?</h1>
        <p className="mt-1 text-sm text-ink/60">
          Clinical responsibility and handoff visibility—not payroll attendance. The list changes automatically at
          the configured shift boundary.
        </p>
      </header>
      {roster.error && <ApiError error={roster.error} />}
      {message && <p className="border border-accent/30 bg-accent/5 px-3 py-2 text-sm">{message}</p>}

      <Panel
        title={`Now · ${data?.current.shift?.label ?? "loading"} ${
          data?.current.shift ? `(${data.current.shift.start}–${data.current.shift.end})` : ""
        }`}
      >
        {(data?.current.staff.length ?? 0) === 0 ? (
          <p className="text-sm text-ink/60">No one is assigned to the current shift yet. An admin can add people below.</p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {data?.current.staff.map((person) => (
              <article key={person.id} className="border border-ink/10 bg-white p-3">
                <p className="font-medium">{person.display_name}</p>
                <p className="text-xs text-ink/55">{person.role} · {person.unit_id ?? "all units"}</p>
                <Pill tone="success">On shift</Pill>
              </article>
            ))}
          </div>
        )}
      </Panel>

      <Panel title="Full schedule">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-ink/50">
              <tr><th>Name</th><th>Role</th><th>Shift</th><th>Unit</th><th>Status</th>{isAdmin && <th />}</tr>
            </thead>
            <tbody>
              {data?.assignments.map((row) => (
                <tr key={row.id} className="border-t border-ink/5">
                  <td className="py-2">{row.display_name}<span className="block text-xs text-ink/45">{row.user_id}</span></td>
                  <td>{row.role}</td><td>{row.shift_id}</td><td>{row.unit_id ?? "all"}</td>
                  <td>{row.active ? "active" : "inactive"}</td>
                  {isAdmin && (
                    <td className="space-x-2 text-right">
                      <button className="text-accent underline" onClick={() => beginEdit(row)}>Edit</button>
                      <button className="text-risk-high underline" onClick={() => void remove(row.id)}>Delete</button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {isAdmin && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Panel title={editingId ? "Edit assignment" : "Add assignment"}>
            <div className="grid gap-2 text-sm">
              <input className="border border-ink/20 px-2 py-1.5" placeholder="User ID" value={form.user_id} onChange={(e) => setForm({ ...form, user_id: e.target.value })} />
              <input className="border border-ink/20 px-2 py-1.5" placeholder="Display name" value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} />
              <select className="border border-ink/20 px-2 py-1.5" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                <option value="clinician">doctor / clinician</option><option value="nurse">nurse</option>
                <option value="operator">operator</option><option value="admin">admin</option>
              </select>
              <select className="border border-ink/20 px-2 py-1.5" value={form.shift_id} onChange={(e) => setForm({ ...form, shift_id: e.target.value })}>
                {data?.shifts.map((s) => <option key={s.id} value={s.id}>{s.label} · {s.start}–{s.end}</option>)}
              </select>
              <input className="border border-ink/20 px-2 py-1.5" placeholder="Unit ID (optional)" value={form.unit_id} onChange={(e) => setForm({ ...form, unit_id: e.target.value })} />
              <label className="flex gap-2"><input type="checkbox" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} />Active</label>
              <button className="bg-accent px-3 py-2 text-white" onClick={() => void saveAssignment()}>{editingId ? "Save edit" : "Add to schedule"}</button>
            </div>
          </Panel>
          <Panel title="CSV import">
            <p className="mb-2 text-xs text-ink/55">Format: <code>user_id,display_name,role,shift_id,unit_id,active</code></p>
            <pre className="mb-3 overflow-auto bg-mist/50 p-2 text-[11px]">{data?.csv_template}</pre>
            <input type="file" accept=".csv,text/csv" onChange={(e) => setCsvFile(e.target.files?.[0] ?? null)} />
            <label className="mt-2 flex gap-2 text-sm"><input type="checkbox" checked={replace} onChange={(e) => setReplace(e.target.checked)} />Replace existing schedule</label>
            <button disabled={!csvFile} className="mt-2 border border-ink/20 px-3 py-2 disabled:opacity-40" onClick={() => void importCsv()}>Import CSV</button>
          </Panel>
        </div>
      )}
    </div>
  );
}
