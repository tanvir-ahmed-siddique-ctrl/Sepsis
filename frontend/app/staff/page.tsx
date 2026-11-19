"use client";

import { useState } from "react";
import { ApiError, FileDrop, PageHeader, Panel, Pill } from "@/components/ui";
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
  const shiftById = new Map((data?.shifts ?? []).map((shift) => [shift.id, shift]));
  const currentWindow = data?.current.shift;

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <PageHeader
        eyebrow="Current team"
        title="Who is on this shift?"
        description="Clinical responsibility and handoff visibility, not payroll attendance. The list changes automatically at the configured shift boundary."
      />
      {roster.error && <ApiError error={roster.error} />}
      {message && <p role="status" className="rounded-lg border border-teal/25 bg-teal-soft/40 px-3.5 py-2.5 text-sm text-ink">{message}</p>}

      <Panel
        title={
          currentWindow
            ? `Now · ${currentWindow.label} · ${currentWindow.start}–${currentWindow.end}`
            : "Now · loading shift window"
        }
      >
        {currentWindow && (
          <p className="mb-4 text-sm text-muted">
            Shift window <span className="font-semibold tabular-nums text-ink">{currentWindow.start}</span>
            {" → "}
            <span className="font-semibold tabular-nums text-ink">{currentWindow.end}</span>
          </p>
        )}
        {(data?.current.staff.length ?? 0) === 0 ? (
          <p className="text-sm text-ink/60">No one is assigned to the current shift yet. An admin can add people below.</p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {data?.current.staff.map((person) => {
              const shift = shiftById.get(person.shift_id) ?? currentWindow;
              return (
                <article key={person.id} className="flex items-start justify-between gap-3 rounded-xl border border-border bg-white p-4">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-ink">{person.display_name}</p>
                    <p className="text-xs capitalize text-muted">{person.role} · {person.unit_id ?? "all units"}</p>
                    <p className="mt-1 text-xs font-medium tabular-nums text-teal-dark">
                      {shift ? `${shift.start}–${shift.end}` : "Time not set"}
                    </p>
                  </div>
                  <Pill tone="success">On shift</Pill>
                </article>
              );
            })}
          </div>
        )}
      </Panel>

      <Panel title="Full schedule">
        <div className="auralis-table-scroll">
          <table className="auralis-table min-w-[42rem]">
            <thead>
              <tr>
                <th>Name</th>
                <th>Role</th>
                <th>Shift</th>
                <th>Time</th>
                <th>Unit</th>
                <th>Status</th>
                {isAdmin && <th />}
              </tr>
            </thead>
            <tbody>
              {data?.assignments.map((row) => {
                const shift = shiftById.get(row.shift_id);
                return (
                  <tr key={row.id}>
                    <td>
                      <span className="font-medium text-ink">{row.display_name}</span>
                      <span className="block font-mono text-xs text-muted">{row.user_id}</span>
                    </td>
                    <td className="capitalize">{row.role}</td>
                    <td>{shift?.label ?? row.shift_id}</td>
                    <td className="tabular-nums text-ink">{shift ? `${shift.start}–${shift.end}` : "—"}</td>
                    <td>{row.unit_id ?? "all"}</td>
                    <td>
                      <Pill tone={row.active ? "success" : "neutral"}>{row.active ? "Active" : "Inactive"}</Pill>
                    </td>
                    {isAdmin && (
                      <td className="whitespace-nowrap text-right">
                        <button type="button" className="auralis-btn-ghost auralis-btn-sm" onClick={() => beginEdit(row)}>
                          Edit
                        </button>
                        <button
                          type="button"
                          className="auralis-btn-ghost auralis-btn-sm text-risk-high hover:text-risk-high"
                          onClick={() => void remove(row.id)}
                        >
                          Delete
                        </button>
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Panel>

      {isAdmin && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Panel title={editingId ? "Edit assignment" : "Add assignment"}>
            <div className="grid gap-3 text-sm">
              <input aria-label="User ID" className="auralis-input" placeholder="User ID" value={form.user_id} onChange={(e) => setForm({ ...form, user_id: e.target.value })} />
              <input aria-label="Display name" className="auralis-input" placeholder="Display name" value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} />
              <select aria-label="Role" className="auralis-input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                <option value="clinician">doctor / clinician</option><option value="nurse">nurse</option>
                <option value="operator">operator</option><option value="admin">admin</option>
              </select>
              <select aria-label="Shift" className="auralis-input" value={form.shift_id} onChange={(e) => setForm({ ...form, shift_id: e.target.value })}>
                {data?.shifts.map((s) => <option key={s.id} value={s.id}>{s.label} · {s.start}–{s.end}</option>)}
              </select>
              <input aria-label="Unit ID" className="auralis-input" placeholder="Unit ID (optional)" value={form.unit_id} onChange={(e) => setForm({ ...form, unit_id: e.target.value })} />
              <label className="flex items-center gap-2"><input type="checkbox" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} />Active</label>
              <div className="flex gap-2">
                <button type="button" className="auralis-btn-primary" onClick={() => void saveAssignment()}>{editingId ? "Save changes" : "Add to schedule"}</button>
                {editingId && (
                  <button type="button" className="auralis-btn-ghost" onClick={() => { setEditingId(null); setForm(EMPTY); }}>Cancel</button>
                )}
              </div>
            </div>
          </Panel>
          <Panel title="CSV import" description="Columns: user_id, display_name, role, shift_id, unit_id, active">
            {data?.csv_template && <pre className="mb-4 overflow-auto rounded-lg border border-border bg-canvas p-3 font-mono text-[11px] text-ink">{data.csv_template}</pre>}
            <FileDrop label="Roster file" accept=".csv,text/csv" acceptLabel="CSV" maxBytes={12 * 1024 * 1024} file={csvFile} onFile={setCsvFile} compact />
            <label className="mt-3 flex items-center gap-2 text-sm"><input type="checkbox" checked={replace} onChange={(e) => setReplace(e.target.checked)} />Replace the existing schedule</label>
            <button type="button" disabled={!csvFile} className="auralis-btn-primary mt-4" onClick={() => void importCsv()}>Import CSV</button>
          </Panel>
        </div>
      )}
    </div>
  );
}
