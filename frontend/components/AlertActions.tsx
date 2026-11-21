"use client";

import { useState } from "react";
import { api } from "@/lib/api";

type Action = "acknowledged" | "dismissed" | "escalated" | "snoozed";

export function AlertActions({
  alertId,
  onDone,
}: {
  alertId: string;
  onDone?: (message: string) => void;
}) {
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState<Action | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(action: Action) {
    const note = reason.trim();
    if (action === "dismissed" && !note) {
      setError("A dismissal reason is required.");
      return;
    }
    setBusy(action);
    try {
      await api(`/v1/alerts/${alertId}/acknowledge`, {
        method: "POST",
        body: JSON.stringify({
          action,
          reason: note || null,
        }),
      });
      setError(null);
      onDone?.(`Alert ${action}.`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-3 rounded-xl border border-[#D5DDE3] bg-muted-surface/50 p-3 shadow-soft">
      <label className="auralis-label !mb-0" htmlFor={`reason-${alertId}`}>
        Review note <span className="font-normal text-muted">(required to dismiss)</span>
      </label>
      <textarea
        id={`reason-${alertId}`}
        value={reason}
        onChange={(event) => setReason(event.target.value)}
        rows={2}
        maxLength={500}
        placeholder="Clinical review note"
        className="auralis-input"
      />
      <div className="flex flex-wrap gap-2">
        <button type="button" disabled={busy !== null} onClick={() => void submit("acknowledged")} className="auralis-btn-primary auralis-btn-sm">
          {busy === "acknowledged" ? "Recording…" : "Seen (ack)"}
        </button>
        <button
          type="button"
          disabled={busy !== null}
          className="auralis-btn-secondary auralis-btn-sm"
          onClick={() => {
            setBusy("snoozed");
            void api(`/v1/alerts/${alertId}/acknowledge`, {
              method: "POST",
              body: JSON.stringify({
                action: "snoozed",
                reason: reason.trim() || "Quiet while treating — bedside",
                quiet_minutes: 60,
              }),
            })
              .then(() => {
                setError(null);
                onDone?.("Alert quiet for 60 minutes.");
              })
              .catch((cause) => setError(cause instanceof Error ? cause.message : String(cause)))
              .finally(() => setBusy(null));
          }}
        >
          {busy === "snoozed" ? "Recording…" : "Quiet 1h"}
        </button>
        <button type="button" disabled={busy !== null} onClick={() => void submit("escalated")} className="auralis-btn-secondary auralis-btn-sm">
          {busy === "escalated" ? "Recording…" : "Escalate"}
        </button>
        <button type="button" disabled={busy !== null} onClick={() => void submit("dismissed")} className="auralis-btn-danger auralis-btn-sm">
          {busy === "dismissed" ? "Recording…" : "Dismiss"}
        </button>
      </div>
      <p className="text-[11px] leading-5 text-muted">
        Tip: use <strong className="text-ink">Seen</strong> or <strong className="text-ink">Quiet 1h</strong> from the ICU board
        without leaving the patient.
      </p>
      {error && (
        <p role="alert" className="text-xs font-medium text-risk-high">
          {error}
        </p>
      )}
    </div>
  );
}
