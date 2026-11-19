"use client";

import { useEffect, useRef, useState } from "react";

const SOURCES = [
  { id: "monitors", label: "Monitors", sub: "ORU / vitals" },
  { id: "lis", label: "LIS", sub: "Labs" },
  { id: "adt", label: "ADT", sub: "Beds / ID" },
  { id: "fhir", label: "FHIR", sub: "Observations" },
] as const;

const PIPE = [
  { id: "map", label: "Map", detail: "Units & codes" },
  { id: "gate", label: "TrustGate", detail: "Abstain if unsafe" },
  { id: "model", label: "Model", detail: "6 h sepsis risk" },
  { id: "board", label: "ICU board", detail: "Clinician review" },
] as const;

/**
 * Wide, flat scroll-lit connection story — no CSS 3D tilt.
 * Progress lights sources → LAN spine → pipe stages as the section scrolls through view.
 */
export function IntegrationOrbit() {
  const root = useRef<HTMLDivElement>(null);
  const [progress, setProgress] = useState(0);
  const reduced = useRef(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    reduced.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced.current) {
      setProgress(1);
      return;
    }

    let raf = 0;
    const tick = () => {
      raf = 0;
      const node = root.current;
      if (!node) return;
      const rect = node.getBoundingClientRect();
      const view = window.innerHeight || 1;
      // Smooth 0→1 while the section travels through the viewport
      const start = view * 0.92;
      const end = view * 0.18 - rect.height * 0.15;
      const raw = (start - rect.top) / (start - end);
      setProgress(Math.max(0, Math.min(1, raw)));
    };
    const onScroll = () => {
      if (!raf) raf = window.requestAnimationFrame(tick);
    };
    tick();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      if (raf) window.cancelAnimationFrame(raf);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, []);

  const sourceLit = Math.min(SOURCES.length, Math.floor(progress * (SOURCES.length + 0.35)));
  const spine = Math.max(0, Math.min(1, (progress - 0.18) / 0.55));
  const pipeLit = Math.min(PIPE.length, Math.floor(Math.max(0, progress - 0.28) * (PIPE.length + 0.8)));
  const stage =
    progress < 0.22 ? 0 : progress < 0.45 ? 1 : progress < 0.72 ? 2 : 3;

  return (
    <div ref={root} className="auralis-flow" style={{ ["--flow-progress" as string]: String(spine) }}>
      <div className="auralis-flow-grid">
        {/* Sources */}
        <div className="auralis-flow-sources">
          <p className="auralis-flow-eyebrow">Hospital sources</p>
          <ul>
            {SOURCES.map((src, idx) => {
              const lit = idx < sourceLit;
              return (
                <li key={src.id} className={lit ? "is-lit" : ""} style={{ transitionDelay: `${idx * 50}ms` }}>
                  <span className="auralis-flow-dot" />
                  <span>
                    <strong>{src.label}</strong>
                    <small>{src.sub}</small>
                  </span>
                </li>
              );
            })}
          </ul>
        </div>

        {/* Spine */}
        <div className="auralis-flow-spine" aria-hidden="true">
          <div className="auralis-flow-spine-track">
            <div className="auralis-flow-spine-fill" />
          </div>
          <span className="auralis-flow-spine-label">Hospital LAN</span>
        </div>

        {/* Pipe stages */}
        <div className="auralis-flow-pipe">
          <p className="auralis-flow-eyebrow">On-prem pipe</p>
          <ol>
            {PIPE.map((step, idx) => {
              const active = idx < pipeLit;
              return (
                <li key={step.id} className={active ? "is-active" : ""} style={{ transitionDelay: `${idx * 60}ms` }}>
                  <span className="auralis-flow-step">{idx + 1}</span>
                  <span>
                    <strong>{step.label}</strong>
                    <small>{step.detail}</small>
                  </span>
                </li>
              );
            })}
          </ol>
        </div>
      </div>

      <p className="auralis-flow-caption" aria-live="polite">
        {stage === 0 && "Sources wake as you scroll…"}
        {stage === 1 && "Feeds enter the hospital LAN…"}
        {stage === 2 && "TrustGate qualifies — then the model scores…"}
        {stage === 3 && "Risk reaches the ICU board for a clinician."}
      </p>
    </div>
  );
}
