"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { useSession } from "@/lib/session";

export function EvaluationSwitcher() {
  const router = useRouter();
  const { account, refresh } = useSession();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (!account?.evaluation) return null;

  async function switchTo(target: "clinical" | "customer" | "vendor") {
    setBusy(true);
    try {
      const action = target === "clinical" ? "evaluation-clinical" : "evaluation-account";
      const response = await fetch(`/api/session/${action}`, {
        method: "POST", credentials: "same-origin", cache: "no-store",
        headers: { "Content-Type": "application/json", "X-Auralis-Request": "1" }, body: "{}",
      });
      if (!response.ok) throw new Error("Workspace switch failed");
      await refresh();
      setError(null);
      router.push(target === "clinical" ? "/app/icu" : target === "customer" ? "/portal" : "/platform/accounts");
    } catch { setError("Could not switch workspace. Retry or sign in again."); }
    finally { setBusy(false); }
  }

  return <nav aria-label="Synthetic evaluation workspaces" className="fixed bottom-4 right-4 z-50 flex max-w-[calc(100vw-2rem)] flex-wrap gap-1 border border-[#C6CECA] bg-[#FCFBF8] p-2 shadow-lg">
    {error && <span role="alert" className="basis-full px-2 text-xs text-risk-high">{error}</span>}
    <span className="self-center px-2 text-xs font-semibold text-forest">Synthetic evaluation</span>
    <button type="button" disabled={busy} onClick={() => void switchTo("clinical")} className="px-2 py-1 text-xs hover:bg-[#E9ECEA] disabled:opacity-50">Clinical</button>
    <button type="button" disabled={busy} onClick={() => void switchTo("customer")} className="px-2 py-1 text-xs hover:bg-[#E9ECEA] disabled:opacity-50">Customer</button>
    <button type="button" disabled={busy} onClick={() => void switchTo("vendor")} className="px-2 py-1 text-xs hover:bg-[#E9ECEA] disabled:opacity-50">Vendor</button>
  </nav>;
}
