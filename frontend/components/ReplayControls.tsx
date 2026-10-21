"use client";

import { useState } from "react";
import { api } from "@/lib/api";

export function ReplayControls({ onChange }: { onChange?: () => void | Promise<void> }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const publicJudgeDemo = process.env.NEXT_PUBLIC_JUDGE_DEMO === "true";

  if (publicJudgeDemo) {
    return (
      <p className="border border-ink/10 bg-white/70 px-3 py-2 text-xs text-ink/60">
        Public replay state is prepared and locked for a consistent judge walkthrough.
      </p>
    );
  }

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
      {error && <span role="alert" className="text-xs text-risk-high">{error}</span>}
    </div>
  );
}
