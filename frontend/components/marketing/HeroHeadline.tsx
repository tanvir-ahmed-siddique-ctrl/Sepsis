"use client";

import { useEffect, useRef, useState } from "react";

const LINES: Array<[string, string]> = [
  ["Earlier signal.", "Risk you can explain."],
  ["Connect the feeds.", "Earn the right to alert."],
  ["Strong holdout model.", "Pipes that reach the bed."],
  ["Six-hour sepsis risk.", "TrustGate before interrupt."],
];

/**
 * Dual-layer crossfade headline — outgoing and incoming overlap so words
 * never blank out or jump during the swap.
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
      clearOut = window.setTimeout(() => setOutgoing(null), 780);
    }, 5200);

    return () => {
      window.clearInterval(tick);
      if (clearOut) window.clearTimeout(clearOut);
    };
  }, []);

  const [line1, line2] = LINES[current];

  return (
    <h1 className="relative max-w-xl">
      <span className="sr-only">
        {line1} {line2}
      </span>
      <span className="relative block min-h-[5.4rem] sm:min-h-[6.6rem] lg:min-h-[7.4rem]" aria-hidden="true">
        {outgoing != null && (
          <span className="auralis-hero-line is-out absolute inset-x-0 top-0">
            <LinePair pair={LINES[outgoing]} />
          </span>
        )}
        <span className={`auralis-hero-line absolute inset-x-0 top-0 ${outgoing != null ? "is-in" : ""}`}>
          <LinePair pair={LINES[current]} />
        </span>
      </span>
    </h1>
  );
}

function LinePair({ pair }: { pair: [string, string] }) {
  return (
    <>
      <span className="block text-[2.35rem] font-semibold leading-[1.05] tracking-[-0.04em] text-navy sm:text-[2.9rem] lg:text-[3.4rem] lg:leading-[1.02]">
        {pair[0]}
      </span>
      <span className="mt-1 block text-[2.35rem] font-semibold leading-[1.05] tracking-[-0.04em] text-teal sm:text-[2.9rem] lg:text-[3.4rem] lg:leading-[1.02]">
        {pair[1]}
      </span>
    </>
  );
}
