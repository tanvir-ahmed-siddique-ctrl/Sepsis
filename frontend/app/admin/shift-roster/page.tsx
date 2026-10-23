"use client";

import { useState } from "react";
import { ApiError, Panel, Pill } from "@/components/ui";
import { api, isStatus } from "@/lib/api";
import { usePoll } from "@/lib/usePoll";

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
  current: { shift: { label: string } | null; staff: Assignment[]; note?: string };
  csv_template: string;
  note?: string;
};

const EMPTY = { user_id: "", display_name: "", role: "clinician", shift_id: "morning", unit_id: "", active: true };

export default function ShiftRosterPage() {
  const roster = usePoll(() => api<Roster>("/v1/site/shift-roster"), 15000);
  const [form, setForm] = useState(EMPTY);
  const [message, setMessage] = useState<string | null>(null);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [replace, setReplace] = useState(false);

  if (roster.error && isStatus(roster.error, 403)) {
    return <ApiError error="Shift roster is visible to clinical roles; edits need admin." />;
  }

  async function saveAssignment() {
    try {
      await api("/v1/site/shift-roster/assignments", {
        method: "PUT",
        body: JSON.stringify({
          ...form,
          unit_id: form.unit_id || null,
        }),
      });
      setMessage(`Saved ${form.display_name} on ${form.shift_id}.`);
      setForm(EMPTY);
      await roster.refresh();
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : String(cause));
    }
  }

  async function remove(id: string) {
    try {
      await api(`/v1/site/shift-roster/assignments/${encodeURIComponent(id)}`, { method: "DELETE" });
      setMessage("Assignment removed.");
      await roster.refresh();
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : String(cause));
    }
  }

  async function importCsv() {
    if (!csvFile) return;
    try {
      await api(`/v1/site/shift-roster/csv?replace=${replace}`, {
        method: "POST",
        headers: { "Content-Type": "text/csv; charset=utf-8" },
        body: await csvFile.text(),
      });
      setMessage(`Imported ${csvFile.name}.`);
      await roster.refresh();
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : String(cause));
    }
  }

  const data = roster.data;

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <div>
        <h1 className="font-display text-3xl">Shift roster</h1>
        <p className="mt-1 text-sm text-ink/60">
          Who is expected on this ICU shift for handoff and open-alert ownership. This is{" "}
          <strong>not</strong> payroll attendance — the hospital already records that elsewhere.
        </p>
      </div>
      {roster.error && <ApiError error={roster.error} />}
      {message && <p className="border border-accent/30 bg-accent/5 px-3 py-2 text-sm">{message}</p>}

      {data && (
        <Panel title={`Current shift — ${data.current.shift?.label ?? "—"}`}>
          <p className="mb-2 text-xs text-ink/55">{data.note}</p>
          {data.current.staff.length === 0 ? (
            <p className="text-sm text-ink/60">Nobody listed for the current window. Add below or import CSV.</p>
          ) : (
            <ul className="flex flex-wrap gap-2">
              {data.current.staff.map((p) => (
                <li key={p.id}>
                  <Pill tone="success">
                    {p.display_name} · {p.role}
                  </Pill>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Add / edit person">
          <div className="grid gap-2 text-sm">
            <input className="border border-ink/20 px-2 py-1.5" placeholder="User id (login id)" value={form.user_id} onChange={(e) => setForm({ ...form, user_id: e.target.value })} />
            <input className="border border-ink/20 px-2 py-1.5" placeholder="Display name" value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} />
            <select className="border border-ink/20 px-2 py-1.5" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
              <option value="clinician">clinician</option>
              <option value="nurse">nurse</option>
              <option value="admin">admin</option>
              <option value="operator">operator</option>
            </select>
            <select className="border border-ink/20 px-2 py-1.5" value={form.shift_id} onChange={(e) => setForm({ ...form, shift_id: e.target.value })}>
              {(data?.shifts ?? []).map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label} ({s.start}–{s.end})
                </option>
              ))}
            </select>
            <input className="border border-ink/20 px-2 py-1.5" placeholder="Unit id (optional)" value={form.unit_id} onChange={(e) => setForm({ ...form, unit_id: e.target.value })} />
            <button type="button" className="border border-accent bg-accent px-3 py-1.5 text-white" onClick={() => void saveAssignment()}>
              Save assignment
            </button>
          </div>
        </Panel>
        <Panel title="CSV import">
          <p className="mb-2 text-xs text-ink/55">
            Columns: <code>user_id,display_name,role,shift_id,unit_id,active</code>
          </p>
          <pre className="mb-3 max-h-40 overflow-auto bg-mist/50 p-2 text-[11px]">{data?.csv_template}</pre>
          <div className="space-y-2 text-sm">
            <input type="file" accept=".csv,text/csv" onChange={(e) => setCsvFile(e.target.files?.[0] ?? null)} />
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={replace} onChange={(e) => setReplace(e.target.checked)} />
              Replace all existing assignments
            </label>
            <button type="button" disabled={!csvFile} className="border border-ink/20 px-3 py-1.5 disabled:opacity-40" onClick={() => void importCsv()}>
              Import CSV
            </button>
          </div>
        </Panel>
      </div>

      <Panel title="All assignments">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-ink/50">
              <tr>
                <th className="py-1">Name</th>
                <th className="py-1">Role</th>
                <th className="py-1">Shift</th>
                <th className="py-1">Unit</th>
                <th className="py-1">Active</th>
                <th className="py-1" />
              </tr>
            </thead>
            <tbody>
              {(data?.assignments ?? []).map((row) => (
                <tr key={row.id} className="border-t border-ink/5">
                  <td className="py-1.5">
                    {row.display_name}
                    <span className="block text-xs text-ink/45">{row.user_id}</span>
                  </td>
                  <td className="py-1.5">{row.role}</td>
                  <td className="py-1.5">{row.shift_id}</td>
                  <td className="py-1.5">{row.unit_id ?? "—"}</td>
                  <td className="py-1.5">{row.active ? "yes" : "no"}</td>
                  <td className="py-1.5">
                    <button type="button" className="text-xs text-risk-high underline" onClick={() => void remove(row.id)}>
                      Delete
                    </button>
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
