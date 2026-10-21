"use client";

import { useState } from "react";
import { ApiError, Panel } from "@/components/ui";
import { api } from "@/lib/api";
import { humanize } from "@/lib/pilot";
import { useSession } from "@/lib/session";
import { usePoll } from "@/lib/usePoll";

const WORKFLOW_TAGS = ["already_aware", "prompted_review", "data_issue", "alarm_fatigue", "wrong_patient_context", "other"];
const INPUT = "w-full border border-ink/20 bg-white px-2 py-1.5 text-sm outline-none focus:border-accent";

type Note = { note_id: string; user_id: string; note: string; recorded_at: string };

export function WorkflowPanel({
  patientId,
  owner,
  latestAlertId,
}: {
  patientId: string;
  owner: string | null;
  latestAlertId: string | null;
}) {
  const id = encodeURIComponent(patientId);
  const { me, isAdmin } = useSession();
  const notes = usePoll(() => api<{ notes: Note[] }>(`/v1/patients/${id}/handoff-notes?limit=10`), 15000, [id]);
  const [note, setNote] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [usefulness, setUsefulness] = useState("helpful");
  const [tags, setTags] = useState<string[]>([]);
  const [comment, setComment] = useState("");
  const [adjudication, setAdjudication] = useState("no_sepsis");
  const [onset, setOnset] = useState("");
  const [criteria, setCriteria] = useState("sepsis-3");
  const [outcomeNotes, setOutcomeNotes] = useState("");

  async function run(action: () => Promise<unknown>, done: string) {
    try {
      await action();
      setStatus(done);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    }
  }

  const mine = owner != null && owner === me?.user_id;

  return (
    <Panel title="Bedside workflow">
      <div className="grid gap-5 lg:grid-cols-3">
        <section className="space-y-2">
          <h3 className="text-xs font-medium uppercase tracking-wide text-ink/50">Ownership & handoff notes</h3>
          <p className="text-sm">
            Owner: <strong>{owner ?? "unassigned"}</strong>{" "}
            <button
              type="button"
              className="ml-2 border border-ink/20 px-2 py-0.5 text-xs"
              onClick={() =>
                void run(
                  () => api(`/v1/patients/${id}/ownership`, { method: mine ? "DELETE" : "POST", body: mine ? undefined : JSON.stringify({}) }),
                  mine ? "Bed released." : "Bed claimed.",
                )
              }
            >
              {mine ? "Release" : "Claim"}
            </button>
          </p>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              if (!note.trim()) return;
              void run(async () => {
                await api(`/v1/patients/${id}/handoff-notes`, { method: "POST", body: JSON.stringify({ note: note.trim() }) });
                setNote("");
                await notes.refresh();
              }, "Handoff note saved.");
            }}
            className="space-y-1"
          >
            <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2} maxLength={1000} placeholder="Handoff note (no identifiers beyond the chart)" className={INPUT} />
            <button type="submit" className="border border-ink/20 px-2 py-1 text-xs">Add note</button>
          </form>
          {notes.error && <ApiError error={notes.error} />}
          <ul className="space-y-1 text-xs">
            {notes.data?.notes.map((item) => (
              <li key={item.note_id} className="border-b border-ink/5 pb-1">
                <span className="text-ink/50">{new Date(item.recorded_at).toLocaleString()} · {item.user_id}:</span> {item.note}
              </li>
            ))}
          </ul>
        </section>

        <section className="space-y-2">
          <h3 className="text-xs font-medium uppercase tracking-wide text-ink/50">Was this score useful?</h3>
          <form
            className="space-y-2"
            onSubmit={(event) => {
              event.preventDefault();
              void run(
                () =>
                  api("/v1/pilot/feedback", {
                    method: "POST",
                    body: JSON.stringify({ patient_id: patientId, alert_id: latestAlertId, usefulness, workflow: tags, comment: comment.trim() || null }),
                  }),
                "Feedback recorded for the pilot evaluation.",
              );
            }}
          >
            <div className="flex gap-3 text-sm">
              {["helpful", "not_helpful", "unsure"].map((value) => (
                <label key={value} className="flex items-center gap-1">
                  <input type="radio" name="usefulness" value={value} checked={usefulness === value} onChange={() => setUsefulness(value)} />
                  {humanize(value)}
                </label>
              ))}
            </div>
            <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs">
              {WORKFLOW_TAGS.map((tag) => (
                <label key={tag} className="flex items-center gap-1">
                  <input
                    type="checkbox"
                    checked={tags.includes(tag)}
                    onChange={(event) => setTags((current) => (event.target.checked ? [...current, tag] : current.filter((t) => t !== tag)))}
                  />
                  {humanize(tag)}
                </label>
              ))}
            </div>
            <textarea value={comment} onChange={(e) => setComment(e.target.value)} rows={2} maxLength={500} placeholder="Optional comment (excluded from exports)" className={INPUT} />
            <button type="submit" className="border border-ink/20 px-2 py-1 text-xs">Send feedback</button>
          </form>
        </section>

        <section className="space-y-2">
          <h3 className="text-xs font-medium uppercase tracking-wide text-ink/50">Outcome adjudication</h3>
          {!isAdmin ? (
            <p className="text-sm text-ink/60">Chart-review adjudication is recorded by the pilot review team.</p>
          ) : (
            <form
              className="space-y-2"
              onSubmit={(event) => {
                event.preventDefault();
                void run(
                  () =>
                    api("/v1/pilot/outcomes", {
                      method: "POST",
                      body: JSON.stringify({
                        patient_id: patientId,
                        adjudication,
                        onset_time: adjudication === "sepsis" && onset ? new Date(onset).toISOString() : null,
                        criteria,
                        notes: outcomeNotes.trim() || null,
                      }),
                    }),
                  "Adjudication recorded (previous entries are kept and superseded).",
                );
              }}
            >
              <select value={adjudication} onChange={(e) => setAdjudication(e.target.value)} className={INPUT} aria-label="Adjudication">
                <option value="no_sepsis">No sepsis</option>
                <option value="sepsis">Sepsis</option>
                <option value="indeterminate">Indeterminate</option>
              </select>
              {adjudication === "sepsis" && (
                <label className="block text-xs text-ink/60">
                  Onset (local time, converted to UTC)
                  <input type="datetime-local" value={onset} onChange={(e) => setOnset(e.target.value)} required className={INPUT} />
                </label>
              )}
              <input value={criteria} onChange={(e) => setCriteria(e.target.value)} maxLength={64} aria-label="Criteria" className={INPUT} />
              <textarea value={outcomeNotes} onChange={(e) => setOutcomeNotes(e.target.value)} rows={2} maxLength={1000} placeholder="Reviewer notes (excluded from exports)" className={INPUT} />
              <button type="submit" className="border border-ink/20 px-2 py-1 text-xs">Record adjudication</button>
            </form>
          )}
        </section>
      </div>
      {status && <p className="mt-3 text-sm text-accent">{status}</p>}
      {error && <p role="alert" className="mt-3 text-sm text-risk-high">{error}</p>}
    </Panel>
  );
}
