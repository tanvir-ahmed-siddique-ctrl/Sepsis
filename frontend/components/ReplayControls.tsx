"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const AUTO_HINT_SECONDS = Number(process.env.NEXT_PUBLIC_REPLAY_AUTO_SECONDS || "20");

export function ReplayControls({ onChange }: { onChange?: () => void | Promise<void> }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [locked, setLocked] = useState(false);
  const publicJudgeDemo = process.env.NEXT_PUBLIC_JUDGE_DEMO === "true";

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        await api("/v1/demo/replay/status");
        if (!cancelled) setLocked(false);
      } catch {
        /* status itself should work when signed in */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function run(path: string) {
    if (busy) return;
    setBusy(true);
    try {
      await api(path, { method: "POST" });
      await onChange?.();
      setError(null);
      setLocked(false);
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : String(cause);
      setError(message);
      if (/403|401|locked|prepared replay/i.test(message)) setLocked(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-border bg-white p-3 shadow-soft sm:flex-row sm:flex-wrap sm:items-center">
      <p className="text-xs leading-5 text-muted sm:mr-auto sm:max-w-md">
        {publicJudgeDemo || locked
          ? `ICU demo board auto-advances one replay hour every ~${AUTO_HINT_SECONDS}s (same as Advance 1 hour). UI refreshes every 3s.`
          : `Advance the PhysioNet replay timeline, or leave auto-advance on (~${AUTO_HINT_SECONDS}s) in the demo image.`}
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          disabled={busy || locked}
          onClick={() => void run("/v1/demo/replay/step?hours=1")}
          className="border border-accent bg-accent px-3 py-1.5 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          Advance 1 hour
        </button>
        <button
          type="button"
          disabled={busy || locked}
          onClick={() => void run("/v1/demo/replay/step?hours=6")}
          className="border border-ink/20 bg-white px-3 py-1.5 text-sm font-medium text-ink disabled:cursor-not-allowed disabled:opacity-50"
        >
          Advance 6 hours
        </button>
        <button
          type="button"
          disabled={busy || locked}
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
