"use client";

import { useState } from "react";
import { api } from "@/lib/api";

type Action = "acknowledged" | "dismissed" | "escalated";

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
    <div className="space-y-2">
      <label className="block text-xs font-medium uppercase tracking-wide text-ink/50" htmlFor={`reason-${alertId}`}>
        Review note <span className="normal-case tracking-normal">(required to dismiss)</span>
      </label>
      <textarea
        id={`reason-${alertId}`}
        value={reason}
        onChange={(event) => setReason(event.target.value)}
        rows={2}
        maxLength={500}
        placeholder="Clinical review note"
        className="w-full border border-ink/20 bg-white px-2 py-1.5 text-sm outline-none focus:border-accent"
      />
      <div className="flex flex-wrap gap-2">
        <ActionButton disabled={busy !== null} onClick={() => void submit("acknowledged")}>
          {busy === "acknowledged" ? "Recording…" : "Acknowledge"}
        </ActionButton>
        <ActionButton disabled={busy !== null} onClick={() => void submit("escalated")}>
          {busy === "escalated" ? "Recording…" : "Escalate"}
        </ActionButton>
        <ActionButton danger disabled={busy !== null} onClick={() => void submit("dismissed")}>
          {busy === "dismissed" ? "Recording…" : "Dismiss"}
        </ActionButton>
      </div>
      {error && <p role="alert" className="text-xs text-risk-high">{error}</p>}
    </div>
  );
}

function ActionButton({
  children,
  disabled,
  danger = false,
  onClick,
}: {
  children: React.ReactNode;
  disabled: boolean;
  danger?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={`border px-3 py-1.5 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50 ${
        danger ? "border-risk-high/30 text-risk-high" : "border-ink/20 text-ink"
      }`}
    >
      {children}
    </button>
  );
}
