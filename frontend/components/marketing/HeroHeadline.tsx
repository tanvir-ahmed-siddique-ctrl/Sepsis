"use client";

import { useEffect, useRef, useState } from "react";

/** Headline pairs — sepsis/ML first, then operational beats. Never repeat the static subtitle. */
const LINES: Array<[string, string]> = [
  ["Six-hour sepsis risk.", "A model you can audit."],
  ["Frozen LightGBM.", "SHAP drivers on every bed."],
  ["Connect the feeds.", "Earn the right to alert."],
  ["Govern every score.", "TrustGate before interrupt."],
];

/**
 * Dual-layer crossfade headline — height sized to the tallest pair so wraps never clip.
 * Cadence ~6s; carousel starts later (~3.2s) and ticks ~7.8s so left/right never flip together.
 */
export function HeroHeadline() {
  const [current, setCurrent] = useState(0);
  const [outgoing, setOutgoing] = useState<number | null>(null);
  const currentRef = useRef(0);

  useEffect(() => {
    currentRef.current = current;
  }, [current]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    let clearOut: number | undefined;
    const tick = window.setInterval(() => {
      const from = currentRef.current;
      const next = (from + 1) % LINES.length;
      setOutgoing(from);
      setCurrent(next);
      clearOut = window.setTimeout(() => setOutgoing(null), 820);
    }, 6000);

    return () => {
      window.clearInterval(tick);
      if (clearOut) window.clearTimeout(clearOut);
    };
  }, []);

  const [line1, line2] = LINES[current];

  return (
    <h1 className="relative max-w-xl min-w-0 font-display">
      <span className="sr-only">
        {line1} {line2}
      </span>
      {/* Grid stack: invisible copies set height to the tallest wrapped pair */}
      <span className="relative grid overflow-hidden py-1" aria-hidden="true">
        {LINES.map((pair, i) => (
          <span key={i} className="invisible col-start-1 row-start-1">
            <LinePair pair={pair} />
          </span>
        ))}
        {outgoing != null && (
          <span className="auralis-hero-line is-out absolute inset-x-0 top-1">
            <LinePair pair={LINES[outgoing]} />
          </span>
        )}
        <span
          className={`auralis-hero-line absolute inset-x-0 top-1 ${outgoing != null ? "is-in" : "is-steady"}`}
        >
          <LinePair pair={LINES[current]} />
        </span>
      </span>
    </h1>
  );
}

function LinePair({ pair }: { pair: [string, string] }) {
  return (
    <>
      <span className="block text-[1.75rem] font-semibold leading-[1.12] tracking-[-0.035em] text-navy sm:text-[2.9rem] sm:leading-[1.05] sm:tracking-[-0.04em] lg:text-[3.4rem] lg:leading-[1.02]">
        {pair[0]}
      </span>
      <span className="mt-0.5 block text-[1.75rem] font-semibold leading-[1.12] tracking-[-0.035em] text-[#2F8A63] sm:mt-1 sm:text-[2.9rem] sm:leading-[1.05] sm:tracking-[-0.04em] lg:text-[3.4rem] lg:leading-[1.02]">
        {pair[1]}
      </span>
    </>
  );
}
