"use client";

import { useEffect, useState } from "react";
import { Icon } from "@/components/ui/Icon";

type FlashDetail = { message: string; tone?: "ok" | "err" };

const EVENT = "auralis:flash";

/** Fire a short success/error toast anywhere in the workspace. */
export function flash(message: string, tone: "ok" | "err" = "ok") {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent<FlashDetail>(EVENT, { detail: { message, tone } }));
}

export function FlashHost() {
  const [item, setItem] = useState<(FlashDetail & { id: number }) | null>(null);

  useEffect(() => {
    let hideTimer = 0;
    function onFlash(event: Event) {
      const detail = (event as CustomEvent<FlashDetail>).detail;
      if (!detail?.message) return;
      setItem({ ...detail, id: Date.now() });
      window.clearTimeout(hideTimer);
      hideTimer = window.setTimeout(() => setItem(null), 2800);
    }
    window.addEventListener(EVENT, onFlash);
    return () => {
      window.removeEventListener(EVENT, onFlash);
      window.clearTimeout(hideTimer);
    };
  }, []);

  if (!item) return null;

  const ok = item.tone !== "err";
  return (
    <div
      role="status"
      aria-live="polite"
      className={`pointer-events-none fixed bottom-5 right-5 z-[60] flex max-w-sm items-start gap-2.5 rounded-xl border px-4 py-3 text-sm shadow-lift ${
        ok
          ? "border-risk-stable/30 bg-white text-ink"
          : "border-risk-high/30 bg-white text-ink"
      }`}
    >
      <Icon
        name={ok ? "check" : "alert"}
        size={16}
        className={`mt-0.5 shrink-0 ${ok ? "text-risk-stable" : "text-risk-high"}`}
      />
      <span className="leading-5">{item.message}</span>
    </div>
  );
}
