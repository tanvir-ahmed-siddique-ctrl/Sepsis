"use client";

import { useState } from "react";
import { GatesPanel, LocalProtocols, SiteControls, type Readiness } from "@/components/pilot/PilotGovernance";
import { PilotMetrics, type PilotMetricsData } from "@/components/pilot/PilotMetrics";
import { ApiError, Panel, SiteModeBanner } from "@/components/ui";
import { api, isStatus } from "@/lib/api";
import { humanize } from "@/lib/pilot";
import { usePoll } from "@/lib/usePoll";

type Outcome = { outcome_id: string; encounter_key: string; adjudication: string; onset_time: string | null; criteria: string; adjudicator: string; recorded_at: string };
type ExportLog = { export_id: string; created_at: string; created_by: string; sha256: string; counts: Record<string, number>; reason: string };
type Monitoring = { status: string; patient_hours: number; scope: string; findings: Array<{ code: string; severity: string; observed: string | number; action: string }> };

export default function PilotPage() {
  const [unit, setUnit] = useState("");
  const [pilotOnly, setPilotOnly] = useState(false);
  const [thresholds, setThresholds] = useState("");
  const [exportReason, setExportReason] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const readiness = usePoll(() => api<Readiness>("/v1/site/readiness"), 15000);
  const units = usePoll(() => api<{ units: string[] }>("/v1/units"), 30000);
  const query = new URLSearchParams();
  if (unit) query.set("unit_id", unit);
  if (pilotOnly) query.set("pilot_only", "true");
  if (thresholds.trim()) query.set("thresholds", thresholds.trim());
  const metrics = usePoll(() => api<PilotMetricsData>(`/v1/pilot/metrics?${query}`), 15000, [query.toString()]);
  const monitoring = usePoll(() => api<Monitoring>("/v1/pilot/monitoring"), 15000);
  const outcomes = usePoll(() => api<{ outcomes: Outcome[] }>("/v1/pilot/outcomes"), 15000);
  const exports = usePoll(() => api<{ exports: ExportLog[] }>("/v1/pilot/exports"), 30000);
  const feedback = usePoll(
    () =>
      api<{
        feedback: {
          feedback_id: string;
          encounter_key: string;
          alert_id: string | null;
          user_id: string;
          role: string;
          usefulness: string;
          workflow: string[];
          comment: string | null;
          recorded_at: string;
        }[];
      }>("/v1/pilot/feedback"),
    15000,
  );

  if (readiness.error && isStatus(readiness.error, 403)) {
    return <ApiError error="The silent-pilot workspace is restricted to pilot administrators. Sign in with an admin role." />;
  }

  async function createExport() {
    if (exportReason.trim().length < 5) {
      setMessage("Exports need a reason of at least 5 characters (it is written to the audit log).");
      return;
    }
    try {
      const params = new URLSearchParams({ reason: exportReason.trim() });
      if (unit) params.set("unit_id", unit);
      const body = await api<{ export_id: string; sha256: string; export: unknown }>(`/v1/pilot/export?${params}`, { method: "POST" });
      const blob = new Blob([JSON.stringify(body.export, null, 2)], { type: "application/json" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `${body.export_id}.json`;
      link.click();
      URL.revokeObjectURL(link.href);
      setMessage(`Export ${body.export_id} created · SHA-256 ${body.sha256.slice(0, 16)}…`);
      await exports.refresh();
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : String(cause));
    }
  }

  async function applyRetention() {
    if (!window.confirm("Delete pilot rows older than the configured retention period? This is audited and cannot be undone.")) return;
    try {
      const body = await api<{ deleted: Record<string, number> }>("/v1/pilot/retention/apply", { method: "POST" });
      setMessage(`Retention applied: ${Object.entries(body.deleted).map(([table, count]) => `${humanize(table)} ${count}`).join(", ")}.`);
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : String(cause));
    }
  }

  const refreshAll = async () => {
    await Promise.all([readiness.refresh(), metrics.refresh()]);
  };

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-display text-3xl">Silent pilot</h1>
        <p className="mt-1 text-sm text-ink/60">
          Local evidence for this hospital: what the frozen model would have flagged, how reliable the feeds were, and
          whether every gate for live use has passed. Nothing here changes the model or its thresholds.
        </p>
      </div>
      {readiness.data && <SiteModeBanner mode={readiness.data.site.effective_mode} />}
      {readiness.error && <ApiError error={readiness.error} />}
      {message && <p className="border border-accent/30 bg-accent/5 px-3 py-2 text-sm">{message}</p>}

      {readiness.data && (
        <div className="grid gap-4 lg:grid-cols-2">
          <GatesPanel gates={readiness.data.gates} policy={readiness.data.policy} />
          <SiteControls readiness={readiness.data} onChange={refreshAll} />
        </div>
      )}

      <Panel title="Metric scope">
        <div className="flex flex-wrap items-end gap-3 text-sm">
          <label>
            <span className="block text-xs text-ink/55">Unit</span>
            <select value={unit} onChange={(e) => setUnit(e.target.value)} className="border border-ink/20 bg-white px-2 py-1">
              <option value="">All units</option>
              {units.data?.units.map((value) => <option key={value} value={value}>{value}</option>)}
            </select>
          </label>
          <label className="flex items-center gap-1.5">
            <input type="checkbox" checked={pilotOnly} onChange={(e) => setPilotOnly(e.target.checked)} />
            Real-time pilot rows only (excludes demo & backfill)
          </label>
          <label>
            <span className="block text-xs text-ink/55">Simulate thresholds (comma-separated, 0–1)</span>
            <input value={thresholds} onChange={(e) => setThresholds(e.target.value)} placeholder="0.04,0.06,0.12" className="border border-ink/20 bg-white px-2 py-1" />
          </label>
        </div>
      </Panel>
      {metrics.error && <ApiError error={metrics.error} />}
      {monitoring.error && <ApiError error={monitoring.error} />}
      {monitoring.data && (
        <Panel title="Local monitoring actions">
          <p className="mb-2 text-xs text-ink/55">{monitoring.data.scope}</p>
          <p className="mb-2 text-sm font-medium">{humanize(monitoring.data.status)} · {monitoring.data.patient_hours} real-time pilot patient-hours</p>
          {monitoring.data.findings.length === 0 ? (
            <p className="text-sm text-ink/60">No operational trigger crossed. This is not a clinical validation result.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {monitoring.data.findings.map((item) => (
                <li key={item.code} className="border-t border-ink/10 pt-2">
                  <strong className={item.severity === "critical" ? "text-risk-high" : "text-ink"}>{humanize(item.code)}</strong>
                  <span className="ml-2 text-ink/55">Observed: {item.observed}</span>
                  <p className="text-ink/70">{item.action}</p>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      )}
      {metrics.data && <PilotMetrics metrics={metrics.data} />}

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title={`Adjudicated outcomes (${outcomes.data?.outcomes.length ?? 0})`}>
          <p className="-mt-2 mb-2 text-xs text-ink/55">
            Record adjudications from the patient page. Later entries supersede earlier ones; all are kept for audit.
          </p>
          <ul className="max-h-72 space-y-1 overflow-auto text-xs">
            {outcomes.data?.outcomes.map((item) => (
              <li key={item.outcome_id} className="border-b border-ink/5 pb-1">
                {item.encounter_key} · <strong>{humanize(item.adjudication)}</strong>
                {item.onset_time ? ` · onset ${item.onset_time.replace("T", " ").slice(0, 16)}` : ""} · {item.criteria} · {item.adjudicator}
              </li>
            ))}
          </ul>
        </Panel>
        <Panel title={`Clinician feedback inbox (${feedback.data?.feedback.length ?? 0})`}>
          <p className="-mt-2 mb-2 text-xs text-ink/55">
            Submitted from the patient bedside workflow (“Was this score useful?”). Stored in{" "}
            <code>feedback_records</code>, counted in pilot metrics, and included in pseudonymised exports — used to
            judge alert burden and usefulness before live mode.
          </p>
          {feedback.error && <ApiError error={feedback.error} />}
          <ul className="max-h-72 space-y-1 overflow-auto text-xs">
            {(feedback.data?.feedback.length ?? 0) === 0 && <li className="text-ink/55">No feedback yet — submit from a patient chart.</li>}
            {feedback.data?.feedback.map((item) => (
              <li key={item.feedback_id} className="border-b border-ink/5 pb-1">
                {new Date(item.recorded_at).toLocaleString()} · {item.encounter_key} ·{" "}
                <strong>{humanize(item.usefulness)}</strong>
                {item.workflow?.length ? ` · ${item.workflow.join(", ")}` : ""} · {item.user_id} ({item.role})
                {item.comment ? <span className="mt-0.5 block text-ink/60">{item.comment}</span> : null}
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Export & retention">
          <p className="-mt-2 mb-2 text-xs text-ink/55">
            Exports are pseudonymised (HMAC with the site salt), exclude free-text notes and comments, and are logged with a
            SHA-256 digest.
          </p>
          <div className="flex gap-2">
            <input value={exportReason} onChange={(e) => setExportReason(e.target.value)} placeholder="Reason, e.g. monthly governance review" className="flex-1 border border-ink/20 bg-white px-2 py-1.5 text-sm" />
            <button type="button" onClick={() => void createExport()} className="border border-accent bg-accent px-3 py-1.5 text-sm text-white">Export JSON</button>
          </div>
          <ul className="mt-3 space-y-1 text-xs">
            {exports.data?.exports.map((item) => (
              <li key={item.export_id} className="border-b border-ink/5 pb-1">
                {new Date(item.created_at).toLocaleString()} · {item.created_by} · {item.counts.predictions} predictions ·{" "}
                <code>{item.sha256.slice(0, 12)}…</code> · {item.reason}
              </li>
            ))}
          </ul>
          <button type="button" onClick={() => void applyRetention()} className="mt-3 border border-risk-high/30 px-3 py-1.5 text-sm text-risk-high">
            Apply retention policy
          </button>
        </Panel>
      </div>

      <LocalProtocols />
    </div>
  );
}
