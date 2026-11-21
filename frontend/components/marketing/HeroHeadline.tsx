"use client";

import { useEffect, useRef, useState } from "react";

/** Headline pairs — never repeat the static subtitle below. */
const LINES: Array<[string, string]> = [
  ["Earlier signal.", "Risk you can explain."],
  ["Connect the feeds.", "Earn the right to alert."],
  ["Strong holdout model.", "Pipes that reach the bed."],
  ["Govern every score.", "TrustGate before interrupt."],
];

/**
 * Dual-layer crossfade headline — clipped to a fixed box so swaps never
 * paint over the subtitle beneath.
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
    // Offset from carousel (~7.8s) so left/right never flip together.
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
    <h1 className="relative max-w-xl min-w-0">
      <span className="sr-only">
        {line1} {line2}
      </span>
      {/* Mobile: natural height so long lines wrap cleanly. Desktop: clipped stage for crossfade. */}
      <span
        className="relative block min-h-[4.75rem] overflow-hidden sm:h-[6.8rem] sm:min-h-0 lg:h-[7.6rem]"
        aria-hidden="true"
      >
        {outgoing != null && (
          <span className="auralis-hero-line is-out absolute inset-x-0 top-0">
            <LinePair pair={LINES[outgoing]} />
          </span>
        )}
        <span className={`auralis-hero-line absolute inset-x-0 top-0 ${outgoing != null ? "is-in" : "is-steady"}`}>
          <LinePair pair={LINES[current]} />
        </span>
        {/* Invisible steady pair reserves mobile height while absolute layers animate */}
        <span className="invisible block sm:hidden">
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
