"use client";

import { useState } from "react";
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

  async function run(path: string) {
    if (busy || modeBlocked) return;
    setBusy(true);
    try {
      await api(path, { method: "POST" });
      await onChange?.();
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-border bg-white p-3 shadow-soft sm:flex-row sm:flex-wrap sm:items-center">
      <p className="text-xs leading-5 text-muted sm:mr-auto sm:max-w-lg">
        {modeBlocked
          ? `Site mode is ${siteMode}. Switch back to demo operating mode to advance the Main ICU timeline.`
          : `Main ICU timeline: Advance 1h / 3h / 6h, or Reset. Auto-advance ~${
              Number.isFinite(AUTO_HINT_SECONDS) && AUTO_HINT_SECONDS > 0 ? AUTO_HINT_SECONDS : 30
            }s. Board also auto-refreshes every 3s — use Refresh to pull now.`}
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          disabled={busy || modeBlocked}
          onClick={() => void run("/v1/demo/replay/step?hours=1")}
          className="border border-accent bg-accent px-3 py-1.5 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          Advance 1h
        </button>
        <button
          type="button"
          disabled={busy || modeBlocked}
          onClick={() => void run("/v1/demo/replay/step?hours=3")}
          className="border border-ink/20 bg-white px-3 py-1.5 text-sm font-medium text-ink disabled:cursor-not-allowed disabled:opacity-50"
        >
          Advance 3h
        </button>
        <button
          type="button"
          disabled={busy || modeBlocked}
          onClick={() => void run("/v1/demo/replay/step?hours=6")}
          className="border border-ink/20 bg-white px-3 py-1.5 text-sm font-medium text-ink disabled:cursor-not-allowed disabled:opacity-50"
        >
          Advance 6h
        </button>
        <button
          type="button"
          disabled={busy || modeBlocked}
          onClick={() => void run("/v1/demo/replay/reset")}
          className="px-3 py-1.5 text-sm text-ink/60 hover:text-ink disabled:cursor-not-allowed disabled:opacity-50"
        >
          Reset timeline
        </button>
        {onRefresh && (
          <button
            type="button"
            disabled={busy}
            onClick={() => void onRefresh()}
            className="border border-border bg-white px-3 py-1.5 text-sm font-medium text-ink disabled:cursor-not-allowed disabled:opacity-50"
          >
            Refresh board
          </button>
        )}
      </div>
      {error && <span role="alert" className="basis-full text-xs text-risk-high">{error}</span>}
    </div>
  );
}
