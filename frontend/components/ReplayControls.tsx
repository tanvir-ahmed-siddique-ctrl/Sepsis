"use client";

import { useState } from "react";
import { flash } from "@/components/FlashToast";
import { api } from "@/lib/api";

const AUTO_HINT_SECONDS = Number(process.env.NEXT_PUBLIC_REPLAY_AUTO_SECONDS || "30");

export function ReplayControls({
  onChange,
  siteMode = null,
  onRefresh,
}: {
  onChange?: () => void | Promise<void>;
  siteMode?: string | null;
  /** Optional board refresh (poll now) — separate from timeline advance. */
  onRefresh?: () => void | Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const modeBlocked = Boolean(siteMode && siteMode !== "demo");

  async function run(path: string, label: string) {
    if (busy || modeBlocked) return;
    setBusy(true);
    try {
      await api(path, { method: "POST" });
      await onChange?.();
      setError(null);
      flash(label);
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : String(cause);
      setError(message);
      flash(message, "err");
    } finally {
      setBusy(false);
    }
  }

  async function refreshBoard() {
    if (busy || !onRefresh) return;
    setBusy(true);
    try {
      await onRefresh();
      flash("Board refreshed");
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : String(cause);
      flash(message, "err");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-[#D5DDE3] bg-[#F8FAFB] px-3 py-3 sm:flex-row sm:flex-wrap sm:items-center sm:gap-4 sm:px-4">
      <p className="text-xs leading-5 text-muted sm:mr-auto sm:max-w-md">
        {modeBlocked
          ? `Site mode is ${siteMode}. Switch back to demo operating mode to advance the Main ICU timeline.`
          : `Main ICU timeline · auto ~${
              Number.isFinite(AUTO_HINT_SECONDS) && AUTO_HINT_SECONDS > 0 ? AUTO_HINT_SECONDS : 90
            }s (few beds/tick) · board polls every 3s`}
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          disabled={busy || modeBlocked}
          onClick={() => void run("/v1/demo/replay/step?hours=1", "Advanced 1 hour")}
          className="auralis-btn-primary auralis-btn-sm"
        >
          Advance 1h
        </button>
        <button
          type="button"
          disabled={busy || modeBlocked}
          onClick={() => void run("/v1/demo/replay/step?hours=3", "Advanced 3 hours")}
          className="auralis-btn-secondary auralis-btn-sm"
        >
          Advance 3h
        </button>
        <button
          type="button"
          disabled={busy || modeBlocked}
          onClick={() => void run("/v1/demo/replay/step?hours=6", "Advanced 6 hours")}
          className="auralis-btn-secondary auralis-btn-sm"
        >
          Advance 6h
        </button>
        <button
          type="button"
          disabled={busy || modeBlocked}
          onClick={() => void run("/v1/demo/replay/reset", "Timeline reset")}
          className="auralis-btn-ghost auralis-btn-sm"
        >
          Reset timeline
        </button>
        {onRefresh && (
          <button type="button" disabled={busy} onClick={() => void refreshBoard()} className="auralis-btn-secondary auralis-btn-sm">
            Refresh board
          </button>
        )}
      </div>
      {error && <span role="alert" className="basis-full text-xs text-risk-high">{error}</span>}
    </div>
  );
}
