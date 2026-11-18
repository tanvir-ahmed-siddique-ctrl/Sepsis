"use client";

import { useState } from "react";
import { ApiError, KeyValue, Panel, Pill } from "@/components/ui";
import { api, type Gate, type SiteMode } from "@/lib/api";
import { formatGateValue, gateProgress, humanize } from "@/lib/pilot";
import { usePoll } from "@/lib/usePoll";

export type Readiness = {
  site: {
    site_id: string;
    effective_mode: SiteMode;
    requested_mode: string;
    governance_signoff: Record<string, string> | null;
    guideline_approval: Record<string, string> | null;
    updated_at: string | null;
    updated_by: string | null;
  };
  gates: Gate[];
  live_eligible: boolean;
  policy: string;
};

type Protocol = {
  entry_id: string;
  status: "pending_approval" | "approved" | "retired";
  submitted_by: string;
  approved_by: string | null;
  payload: { title: string; section: string; text: string; topic: string; version: string; document_ref: string; review_due: string };
};

const INPUT = "w-full border border-ink/20 bg-white px-2 py-1.5 text-sm outline-none focus:border-accent";

export function GatesPanel({ gates, policy }: { gates: Gate[]; policy: string }) {
  const progress = gateProgress(gates);
  return (
    <Panel title={`Readiness gates — ${progress.passed}/${progress.total} passed`}>
      <ul className="space-y-1.5">
        {gates.map((gate) => (
          <li key={gate.gate} className="grid grid-cols-[1.5rem_1fr_auto] items-start gap-2 border-b border-ink/5 pb-1.5 text-sm">
            <span aria-label={gate.passed ? "passed" : "not passed"} className={gate.passed ? "text-risk-stable" : "text-risk-high"}>
              {gate.passed ? "✓" : "✗"}
            </span>
            <span>
              <span className="font-medium">{humanize(gate.gate)}</span>
              <span className="block text-xs text-ink/55">{gate.detail}</span>
            </span>
            <span className="text-right text-xs tabular-nums text-ink/70">
              {formatGateValue(gate.value)} <span className="text-ink/40">/ {formatGateValue(gate.target)}</span>
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-2 text-xs text-ink/55">{policy}</p>
    </Panel>
  );
}

export function SiteControls({ readiness, onChange }: { readiness: Readiness; onChange: () => Promise<void> }) {
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [signoff, setSignoff] = useState({ committee: "", reference: "", approver: "" });
  const { site } = readiness;

  async function run(action: () => Promise<unknown>, done: string) {
    try {
      await action();
      setMessage(done);
      await onChange();
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : String(cause));
    }
  }

  function setMode(mode: "demo" | "silent" | "live") {
    if (reason.trim().length < 3) {
      setMessage("Record a reason (at least 3 characters) before changing the site mode.");
      return;
    }
    void run(
      () => api("/v1/site/mode", { method: "PUT", body: JSON.stringify({ mode, reason: reason.trim() }) }),
      mode === "live" && !readiness.live_eligible
        ? "Live requested: gates not passed, so the site stays live-disabled (silent behaviour)."
        : `Site mode set to ${mode}.`,
    );
  }

  return (
    <Panel title="Site operating mode & governance">
      <dl className="mb-3">
        <KeyValue label="Site" value={site.site_id} />
        <KeyValue label="Effective / requested" value={`${site.effective_mode} / ${site.requested_mode}`} />
        <KeyValue label="Last change" value={site.updated_at ? `${new Date(site.updated_at).toLocaleString()} by ${site.updated_by}` : "—"} />
      </dl>
      <label className="block text-xs font-medium uppercase tracking-wide text-ink/50" htmlFor="mode-reason">Reason (audited)</label>
      <input id="mode-reason" value={reason} onChange={(e) => setReason(e.target.value)} maxLength={500} className={INPUT} placeholder="e.g. Ethics approval HEC-2026-041, start silent pilot" />
      <div className="mt-2 flex flex-wrap gap-2">
        {(["demo", "silent", "live"] as const).map((mode) => (
          <button
            key={mode}
            type="button"
            onClick={() => setMode(mode)}
            className={`border px-3 py-1.5 text-sm ${site.requested_mode === mode ? "border-accent bg-accent text-white" : "border-ink/20"}`}
          >
            {mode === "live" ? "Request live" : mode === "demo" ? "Evaluation replay" : humanize(mode)}
          </button>
        ))}
      </div>

      <div className="mt-4 border-t border-ink/5 pt-3">
        <p className="text-xs font-medium uppercase tracking-wide text-ink/50">Clinical governance sign-off</p>
        {site.governance_signoff ? (
          <p className="text-sm">
            {site.governance_signoff.committee} · {site.governance_signoff.reference} · approved by {site.governance_signoff.approver}
          </p>
        ) : (
          <form
            className="mt-1 grid gap-2 sm:grid-cols-3"
            onSubmit={(event) => {
              event.preventDefault();
              void run(() => api("/v1/site/governance-signoff", { method: "POST", body: JSON.stringify(signoff) }), "Governance sign-off recorded.");
            }}
          >
            {(["committee", "reference", "approver"] as const).map((field) => (
              <input
                key={field}
                required
                minLength={2}
                value={signoff[field]}
                onChange={(e) => setSignoff((current) => ({ ...current, [field]: e.target.value }))}
                placeholder={humanize(field)}
                className={INPUT}
              />
            ))}
            <button type="submit" className="border border-ink/20 px-3 py-1.5 text-sm sm:col-span-3">Record sign-off</button>
          </form>
        )}
      </div>

      <div className="mt-4 border-t border-ink/5 pt-3">
        <p className="text-xs font-medium uppercase tracking-wide text-ink/50">Guideline registry approval</p>
        {site.guideline_approval ? (
          <p className="text-sm">
            v{site.guideline_approval.registry_version} approved by {site.guideline_approval.approved_by} — {site.guideline_approval.reason}
          </p>
        ) : (
          <button
            type="button"
            className="mt-1 border border-ink/20 px-3 py-1.5 text-sm"
            onClick={() => {
              if (reason.trim().length < 3) {
                setMessage("Record a reason before approving the guideline registry.");
                return;
              }
              void run(
                () => api(`/v1/evidence/guidelines/approve?reason=${encodeURIComponent(reason.trim())}`, { method: "POST" }),
                "Guideline registry version approved for this site.",
              );
            }}
          >
            Approve current guideline registry
          </button>
        )}
      </div>
      {message && <p className="mt-3 text-sm text-accent">{message}</p>}
    </Panel>
  );
}

export function LocalProtocols() {
  const list = usePoll(() => api<{ protocols: Protocol[] }>("/v1/evidence/local-protocols"), 30000);
  const [form, setForm] = useState({ title: "", section: "", text: "", topic: "escalation", version: "", document_ref: "", review_due: "" });
  const [message, setMessage] = useState<string | null>(null);

  async function run(action: () => Promise<unknown>, done: string) {
    try {
      await action();
      setMessage(done);
      await list.refresh();
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : String(cause));
    }
  }

  return (
    <Panel title="Local protocols (two-person approval)">
      <p className="-mt-2 mb-3 text-xs text-ink/55">
        Excerpts from the hospital&apos;s approved sepsis protocol shown beside guideline citations. Doses are rejected;
        the submitter cannot approve their own entry.
      </p>
      <form
        className="grid gap-2 sm:grid-cols-2"
        onSubmit={(event) => {
          event.preventDefault();
          void run(
            () => api("/v1/evidence/local-protocols", { method: "POST", body: JSON.stringify({ ...form, concepts: ["*"] }) }),
            "Submitted — a second administrator must approve it.",
          );
        }}
      >
        <input required minLength={3} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="Title" className={INPUT} />
        <input required value={form.section} onChange={(e) => setForm({ ...form, section: e.target.value })} placeholder="Section" className={INPUT} />
        <textarea required minLength={10} value={form.text} onChange={(e) => setForm({ ...form, text: e.target.value })} placeholder="Verbatim excerpt (no doses)" rows={3} className={`${INPUT} sm:col-span-2`} />
        <select value={form.topic} onChange={(e) => setForm({ ...form, topic: e.target.value })} className={INPUT} aria-label="Topic">
          {["screening", "assessment", "escalation", "monitoring", "governance"].map((topic) => (
            <option key={topic} value={topic}>{topic}</option>
          ))}
        </select>
        <input required value={form.version} onChange={(e) => setForm({ ...form, version: e.target.value })} placeholder="Document version" className={INPUT} />
        <input required value={form.document_ref} onChange={(e) => setForm({ ...form, document_ref: e.target.value })} placeholder="Document reference" className={INPUT} />
        <input required type="date" value={form.review_due} onChange={(e) => setForm({ ...form, review_due: e.target.value })} aria-label="Review due" className={INPUT} />
        <button type="submit" className="border border-ink/20 px-3 py-1.5 text-sm sm:col-span-2">Submit for approval</button>
      </form>
      {message && <p className="mt-2 text-sm text-accent">{message}</p>}
      {list.error && <ApiError error={list.error} />}
      <ul className="mt-3 space-y-2 text-sm">
        {list.data?.protocols.map((protocol) => (
          <li key={protocol.entry_id} className="border-b border-ink/5 pb-2">
            <div className="flex flex-wrap items-center gap-2">
              <strong className="font-medium">{protocol.payload.title}</strong>
              <Pill tone={protocol.status === "approved" ? "success" : protocol.status === "retired" ? "neutral" : "warning"}>
                {humanize(protocol.status)}
              </Pill>
              <span className="text-xs text-ink/50">
                {protocol.payload.document_ref} v{protocol.payload.version} · by {protocol.submitted_by}
                {protocol.approved_by ? ` · approved by ${protocol.approved_by}` : ""}
              </span>
            </div>
            <p className="mt-1 text-xs">{protocol.payload.text}</p>
            <div className="mt-1 flex gap-2">
              {protocol.status === "pending_approval" && (
                <button type="button" className="border border-ink/20 px-2 py-0.5 text-xs" onClick={() => void run(() => api(`/v1/evidence/local-protocols/${protocol.entry_id}/approve`, { method: "POST" }), "Protocol approved.")}>
                  Approve
                </button>
              )}
              {protocol.status !== "retired" && (
                <button type="button" className="border border-ink/20 px-2 py-0.5 text-xs" onClick={() => void run(() => api(`/v1/evidence/local-protocols/${protocol.entry_id}/retire`, { method: "POST" }), "Protocol retired.")}>
                  Retire
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </Panel>
  );
}
