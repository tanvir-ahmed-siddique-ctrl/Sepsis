"use client";

import { useEffect, useState } from "react";
import { BrandGlyph, BrandWordmark } from "@/components/ui/BrandMark";

const STORAGE_KEY = "auralis.domain-splash";

export function markSplashDone() {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(STORAGE_KEY, "1");
  } catch {
    /* private mode */
  }
  window.dispatchEvent(new Event("auralis:splash-done"));
}

export function splashAlreadySeen(): boolean {
  if (typeof window === "undefined") return true;
  try {
    return window.sessionStorage.getItem(STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

/**
 * Full-viewport domain entry: Auralis glyph + wordmark side by side,
 * then a soft cloud dissolve into the homepage.
 * Once per browser tab session.
 */
export function BrandSplash() {
  const [phase, setPhase] = useState<"boot" | "hold" | "out" | "gone">("boot");

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      markSplashDone();
      setPhase("gone");
      return;
    }
    if (splashAlreadySeen()) {
      markSplashDone();
      setPhase("gone");
      return;
    }

    setPhase("hold");
    const toOut = window.setTimeout(() => setPhase("out"), 1200);
    const toGone = window.setTimeout(() => {
      markSplashDone();
      setPhase("gone");
    }, 2400);

    return () => {
      window.clearTimeout(toOut);
      window.clearTimeout(toGone);
    };
  }, []);

  if (phase === "boot" || phase === "gone") return null;

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
        <BrandGlyph size={58} className="auralis-splash-glyph shadow-soft" title="Auralis" />
        <BrandWordmark tone="light" height={38} className="auralis-splash-word" />
      </div>
    </div>
  );
}
