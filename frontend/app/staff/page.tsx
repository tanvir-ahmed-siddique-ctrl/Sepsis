"use client";

import { useState } from "react";
import { ApiError, FileDrop, PageHeader, Pill } from "@/components/ui";
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
    <div className="space-y-8">
      <PageHeader
        title="Who is on this shift?"
        description="Clinical responsibility and handoff visibility, not payroll attendance. The list changes automatically at the configured shift boundary."
      />
      {roster.error && <ApiError error={roster.error} />}
      {message && <p role="status" className="text-sm text-teal-dark">{message}</p>}

      <section>
        <h2 className="text-base font-semibold tracking-tight text-ink">
          {currentWindow
            ? `Now · ${currentWindow.label} · ${currentWindow.start}–${currentWindow.end}`
            : "Now · loading shift window"}
        </h2>
        {currentWindow && (
          <p className="mt-1 text-sm text-muted">
            Shift window <span className="font-semibold tabular-nums text-ink">{currentWindow.start}</span>
            {" → "}
            <span className="font-semibold tabular-nums text-ink">{currentWindow.end}</span>
          </p>
        )}
        {(data?.current.staff.length ?? 0) === 0 ? (
          <p className="mt-4 text-sm text-ink/60">No one is assigned to the current shift yet. An admin can add people below.</p>
        ) : (
          <ul className="mt-3 divide-y divide-border/70">
            {data?.current.staff.map((person) => {
              const shift = shiftById.get(person.shift_id) ?? currentWindow;
              return (
                <li key={person.id} className="flex items-start justify-between gap-3 py-3.5">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-ink">{person.display_name}</p>
                    <p className="text-xs capitalize text-muted">{person.role} · {person.unit_id ?? "all units"}</p>
                    <p className="mt-1 text-xs font-medium tabular-nums text-muted">
                      {shift ? `${shift.start}–${shift.end}` : "Time not set"}
                    </p>
                  </div>
                  <Pill tone="success">On shift</Pill>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section>
        <h2 className="text-base font-semibold tracking-tight text-ink">Full schedule</h2>
        <div className="auralis-table-scroll mt-3">
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
      </section>

      {isAdmin && (
        <div className="grid gap-8 lg:grid-cols-2">
          <section>
            <h2 className="text-base font-semibold tracking-tight text-ink">{editingId ? "Edit assignment" : "Add assignment"}</h2>
            <div className="mt-3 grid gap-3 text-sm">
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
          </section>
          <section>
            <h2 className="text-base font-semibold tracking-tight text-ink">CSV import</h2>
            <p className="mt-1 text-sm text-muted">Columns: user_id, display_name, role, shift_id, unit_id, active</p>
            {data?.csv_template && <pre className="mt-3 overflow-auto rounded-lg bg-canvas p-3 font-mono text-[11px] text-ink">{data.csv_template}</pre>}
            <div className="mt-3">
              <FileDrop label="Roster file" accept=".csv,text/csv" acceptLabel="CSV" maxBytes={12 * 1024 * 1024} file={csvFile} onFile={setCsvFile} compact />
            </div>
            <label className="mt-3 flex items-center gap-2 text-sm"><input type="checkbox" checked={replace} onChange={(e) => setReplace(e.target.checked)} />Replace the existing schedule</label>
            <button type="button" disabled={!csvFile} className="auralis-btn-primary mt-4" onClick={() => void importCsv()}>Import CSV</button>
          </section>
        </div>
      )}
    </div>
  );
}
