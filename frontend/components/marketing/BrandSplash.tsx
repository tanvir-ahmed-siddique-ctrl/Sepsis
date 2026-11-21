"use client";

import { useEffect, useState } from "react";

/**
 * Full-viewport homepage entry — every refresh / direct domain hit.
 * Wordmark only (no glyph) so the brand name stays centered and readable.
 */
export function BrandSplash() {
  const [phase, setPhase] = useState<"hold" | "out" | "gone">("hold");

  useEffect(() => {
    if (typeof window === "undefined") return;

    document.documentElement.classList.add("auralis-splash-active");

    const finish = () => {
      document.documentElement.classList.remove("auralis-splash-active");
      window.dispatchEvent(new Event("auralis:splash-done"));
      setPhase("gone");
    };

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      finish();
      return;
    }

    const toOut = window.setTimeout(() => setPhase("out"), 1400);
    const toGone = window.setTimeout(finish, 2700);

    return () => {
      window.clearTimeout(toOut);
      window.clearTimeout(toGone);
      document.documentElement.classList.remove("auralis-splash-active");
    };
  }, []);

  if (phase === "gone") return null;

  return (
    <div
      className={`auralis-splash ${phase === "out" ? "is-out" : ""}`}
      role="presentation"
      aria-hidden="true"
    >
      <div className="auralis-splash-cloud auralis-splash-cloud-a" />
      <div className="auralis-splash-cloud auralis-splash-cloud-b" />
      <div className="auralis-splash-cloud auralis-splash-cloud-c" />
      <div className="auralis-splash-mark">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/wordmark-on-light.png"
          alt="Auralis"
          width={720}
          height={148}
          className="auralis-splash-word"
          decoding="sync"
          fetchPriority="high"
        />
      </div>
    </div>
  );
}

/** Hero / page motion should wait for this; never skip on homepage refresh. */
export function splashAlreadySeen(): boolean {
  return false;
}
