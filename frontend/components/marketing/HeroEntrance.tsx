"use client";

import { useEffect, useState, type ReactNode } from "react";

/**
 * First-paint hero choreography: soft veil lifts, then copy / CTAs / board
 * rise into place so landing on the domain feels composed — not already there.
 * SSR / no-JS stays fully visible; motion only arms after hydration.
 */
export function HeroEntrance({
  copy,
  showcase,
}: {
  copy: ReactNode;
  showcase: ReactNode;
}) {
  const [ready, setReady] = useState(false);
  const [armed, setArmed] = useState(false);
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    setReduced(prefersReduced);
    setReady(true);
    if (prefersReduced) {
      setArmed(true);
      return;
    }
    // One frame hidden, then lift — creates a deliberate domain entrance.
    const frame = window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => setArmed(true));
    });
    return () => window.cancelAnimationFrame(frame);
  }, []);

  return (
    <div
      className="auralis-hero-stage relative"
      data-hero-ready={ready ? "true" : "false"}
      data-hero-armed={armed ? "true" : "false"}
      data-hero-reduced={reduced ? "true" : "false"}
    >
      <div className="auralis-hero-veil" aria-hidden="true" />
      <div className="auralis-container-public relative grid items-center gap-10 pb-16 pt-10 sm:gap-12 sm:pb-20 sm:pt-14 lg:min-h-[calc(100svh-3.5rem)] lg:grid-cols-[0.95fr_1.05fr] lg:gap-16 lg:pb-24 lg:pt-10">
        <div className="auralis-hero-copy lg:pt-8 xl:pt-12">{copy}</div>
        <div className="auralis-hero-board w-full lg:self-center">{showcase}</div>
      </div>
    </div>
  );
}
