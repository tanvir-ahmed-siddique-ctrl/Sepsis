"use client";

import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Icon } from "@/components/ui/Icon";

type FlashDetail = { message: string; tone?: "ok" | "err" };

const EVENT = "auralis:flash";

/** Fire a short success/error toast anywhere in the workspace. */
export function flash(message: string, tone: "ok" | "err" = "ok") {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent<FlashDetail>(EVENT, { detail: { message, tone } }));
}

export function FlashHost() {
  const reduceMotion = useReducedMotion();
  const [mounted, setMounted] = useState(false);
  const [item, setItem] = useState<(FlashDetail & { id: number }) | null>(null);

  useEffect(() => {
    setMounted(true);
    let hideTimer = 0;
    function onFlash(event: Event) {
      const detail = (event as CustomEvent<FlashDetail>).detail;
      if (!detail?.message) return;
      setItem({ ...detail, id: Date.now() });
      window.clearTimeout(hideTimer);
      hideTimer = window.setTimeout(() => setItem(null), 3200);
    }
    window.addEventListener(EVENT, onFlash);
    return () => {
      window.removeEventListener(EVENT, onFlash);
      window.clearTimeout(hideTimer);
    };
  }, []);

  if (!mounted) return null;

  const ok = item?.tone !== "err";

  return createPortal(
    <AnimatePresence>
      {item ? (
        <motion.div
          key={item.id}
          role="status"
          aria-live="polite"
          initial={reduceMotion ? false : { opacity: 0, y: 16, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={reduceMotion ? undefined : { opacity: 0, y: 10, scale: 0.98 }}
          transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
          className={`pointer-events-none fixed bottom-6 right-6 z-[200] flex max-w-sm items-start gap-3 rounded-xl px-4 py-3.5 text-sm shadow-lift ring-1 ${
            ok
              ? "bg-[#ECF8F1] text-[#145A38] ring-[#1F7A4D]/35"
              : "bg-[#FDECEC] text-[#8B1A14] ring-[#B42318]/35"
          }`}
        >
          <span
            className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${
              ok ? "bg-[#1F7A4D] text-white" : "bg-[#B42318] text-white"
            }`}
          >
            <Icon name={ok ? "check" : "alert"} size={14} />
          </span>
          <span className="leading-5 font-medium">{item.message}</span>
        </motion.div>
      ) : null}
    </AnimatePresence>,
    document.body,
  );
}
