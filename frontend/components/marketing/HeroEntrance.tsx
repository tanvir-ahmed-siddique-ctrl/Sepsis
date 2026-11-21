"use client";

import { useEffect, useState, type ReactNode } from "react";

/**
 * Hero choreography — stays hidden until BrandSplash finishes, then rises in.
 * Arms only on `auralis:splash-done` (every homepage refresh).
 */
export function HeroEntrance({
  copy,
  showcase,
}: {
  copy: ReactNode;
  showcase: ReactNode;
}) {
  const [armed, setArmed] = useState(false);
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    setReduced(prefersReduced);

    const arm = () => {
      if (prefersReduced) {
        setArmed(true);
        return;
      }
      window.requestAnimationFrame(() => {
        window.requestAnimationFrame(() => setArmed(true));
      });
    };

    const onSplash = () => arm();
    window.addEventListener("auralis:splash-done", onSplash);
    const fallback = window.setTimeout(arm, 3200);
    return () => {
      window.removeEventListener("auralis:splash-done", onSplash);
      window.clearTimeout(fallback);
    };
  }, []);

  return (
    <div
      className="auralis-hero-stage relative min-w-0 overflow-x-clip"
      data-hero-ready="true"
      data-hero-armed={armed ? "true" : "false"}
      data-hero-reduced={reduced ? "true" : "false"}
    >
      <div className="auralis-hero-veil" aria-hidden="true" />
      <div className="auralis-container-public relative grid min-w-0 items-start gap-8 pb-10 pt-8 sm:gap-12 sm:pb-20 sm:pt-14 lg:min-h-[calc(100svh-3.5rem)] lg:grid-cols-[0.95fr_1.05fr] lg:items-center lg:gap-16 lg:pb-24 lg:pt-10">
        <div className="auralis-hero-copy min-w-0 lg:pt-8 xl:pt-12">{copy}</div>
        <div className="auralis-hero-board w-full min-w-0 max-w-full lg:self-center">{showcase}</div>
      </div>
    </div>
  );
}
