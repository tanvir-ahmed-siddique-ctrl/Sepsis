"use client";

import { motion, useReducedMotion } from "motion/react";

/**
 * Soft background motion for the homepage hero — sits behind copy/showcase,
 * never competes with the headline.
 */
export function HeroAmbient() {
  const reduce = useReducedMotion();
  if (reduce) return null;

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
      <motion.span
        className="absolute -left-16 top-8 h-56 w-56 rounded-full bg-[#9FD4B4]/35 blur-3xl sm:h-72 sm:w-72"
        animate={{ x: [0, 28, 0], y: [0, 18, 0], scale: [1, 1.08, 1] }}
        transition={{ duration: 14, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.span
        className="absolute right-[-4rem] top-24 h-64 w-64 rounded-full bg-[#B7E0C8]/40 blur-3xl sm:top-16 sm:h-80 sm:w-80"
        animate={{ x: [0, -22, 0], y: [0, 26, 0], scale: [1.05, 0.95, 1.05] }}
        transition={{ duration: 16, repeat: Infinity, ease: "easeInOut", delay: 0.8 }}
      />
      <motion.span
        className="absolute bottom-8 left-1/3 h-40 w-40 rounded-full bg-[#73C3CF]/20 blur-3xl sm:h-52 sm:w-52"
        animate={{ x: [0, 16, 0], y: [0, -20, 0], opacity: [0.45, 0.75, 0.45] }}
        transition={{ duration: 11, repeat: Infinity, ease: "easeInOut", delay: 1.4 }}
      />
      <motion.span
        className="absolute left-[18%] top-[42%] h-2 w-2 rounded-full bg-[#2F8A63]/45"
        animate={{ y: [0, -14, 0], opacity: [0.25, 0.8, 0.25] }}
        transition={{ duration: 4.5, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.span
        className="absolute right-[28%] top-[28%] h-1.5 w-1.5 rounded-full bg-[#287A88]/40"
        animate={{ y: [0, 12, 0], opacity: [0.2, 0.7, 0.2] }}
        transition={{ duration: 5.2, repeat: Infinity, ease: "easeInOut", delay: 0.6 }}
      />
      <motion.span
        className="absolute bottom-[22%] right-[18%] h-2 w-2 rounded-full bg-[#2F8A63]/35"
        animate={{ y: [0, -10, 0], x: [0, 8, 0], opacity: [0.2, 0.65, 0.2] }}
        transition={{ duration: 6, repeat: Infinity, ease: "easeInOut", delay: 1.1 }}
      />
    </div>
  );
}
