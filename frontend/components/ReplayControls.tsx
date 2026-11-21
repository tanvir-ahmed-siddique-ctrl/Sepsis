"use client";

import { useState } from "react";
import { api } from "@/lib/api";

const AUTO_HINT_SECONDS = Number(process.env.NEXT_PUBLIC_REPLAY_AUTO_SECONDS || "20");

export function ReplayControls({ onChange }: { onChange?: () => void | Promise<void> }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(path: string) {
    if (busy) return;
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
      <p className="text-xs leading-5 text-muted sm:mr-auto sm:max-w-md">
        Advance the ICU replay timeline anytime. The board also auto-advances one hour every ~
        {Number.isFinite(AUTO_HINT_SECONDS) && AUTO_HINT_SECONDS > 0 ? AUTO_HINT_SECONDS : 20}s; UI
        refreshes every 3s.
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={() => void run("/v1/demo/replay/step?hours=1")}
          className="border border-accent bg-accent px-3 py-1.5 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          Advance 1 hour
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => void run("/v1/demo/replay/step?hours=6")}
          className="border border-ink/20 bg-white px-3 py-1.5 text-sm font-medium text-ink disabled:cursor-not-allowed disabled:opacity-50"
        >
          Advance 6 hours
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => void run("/v1/demo/replay/reset")}
          className="px-3 py-1.5 text-sm text-ink/60 hover:text-ink disabled:cursor-not-allowed disabled:opacity-50"
        >
          Reset replay
        </button>
      </div>
      {error && <span role="alert" className="basis-full text-xs text-risk-high">{error}</span>}
    </div>
  );
}
