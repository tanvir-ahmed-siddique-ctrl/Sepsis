"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

/**
 * Progressive-enhancement scroll reveal:
 * - Content renders visible by default (SSR & no-JS safe).
 * - When mounted on a client that allows motion and is below the fold, it arms a smooth entrance.
 * - Immediately reveals when intersecting or when reduced-motion is preferred.
 */
export function Reveal({
  children,
  className = "",
  delayMs = 0,
  as: Tag = "div",
}: {
  children: ReactNode;
  className?: string;
  delayMs?: number;
  as?: "div" | "section" | "article" | "header" | "aside";
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);
  const [revealed, setRevealed] = useState(true);

  useEffect(() => {
    const node = ref.current;
    if (!node || typeof window === "undefined") return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setRevealed(true);
      return;
    }
    const rect = node.getBoundingClientRect();
    const inInitialView = rect.top < window.innerHeight * 0.92;
    if (inInitialView) {
      setReady(true);
      setRevealed(true);
      return;
    }
    setReady(true);
    setRevealed(false);

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setRevealed(true);
            observer.disconnect();
            break;
          }
        }
      },
      { threshold: 0.14, rootMargin: "0px 0px -48px 0px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <Tag
      ref={ref as never}
      data-reveal-ready={ready ? "true" : "false"}
      data-revealed={revealed ? "true" : "false"}
      style={delayMs ? { transitionDelay: `${delayMs}ms` } : undefined}
      className={`auralis-reveal ${className}`}
    >
      {children}
    </Tag>
  );
}

/**
 * Controlled subtle vertical parallax wrapper for architectural diagrams & specimen callouts.
 * Respects prefers-reduced-motion and caps offset to keep clinical typography crisp.
 */
export function ParallaxFrame({
  children,
  speed = 0.08,
  className = "",
}: {
  children: ReactNode;
  speed?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    let raf = 0;
    const update = () => {
      raf = 0;
      const node = ref.current;
      if (!node) return;
      const rect = node.getBoundingClientRect();
      const centerDelta = rect.top + rect.height / 2 - window.innerHeight / 2;
      const clamped = Math.max(-28, Math.min(28, -centerDelta * speed));
      setOffset(clamped);
    };

    const onScroll = () => {
      if (!raf) raf = window.requestAnimationFrame(update);
    };

    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      if (raf) window.cancelAnimationFrame(raf);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, [speed]);

  return (
    <div
      ref={ref}
      style={{ transform: `translate3d(0, ${offset.toFixed(1)}px, 0)` }}
      className={`transition-transform duration-150 ease-out will-change-transform ${className}`}
    >
      {children}
    </div>
  );
}
