"use client";

/**
 * Primary homepage brand lines — one clean pair, no stacked/rotating duplicates.
 */
export function HeroHeadline() {
  return (
    <h1 className="max-w-xl min-w-0 font-display">
      <span className="block text-[1.75rem] font-semibold leading-[1.12] tracking-[-0.035em] text-navy sm:text-[2.9rem] sm:leading-[1.05] sm:tracking-[-0.04em] lg:text-[3.4rem] lg:leading-[1.02]">
        Earlier signal.
      </span>
      <span className="mt-0.5 block text-[1.75rem] font-semibold leading-[1.12] tracking-[-0.035em] text-[#2F8A63] sm:mt-1 sm:text-[2.9rem] sm:leading-[1.05] sm:tracking-[-0.04em] lg:text-[3.4rem] lg:leading-[1.02]">
        Risk you can explain.
      </span>
    </h1>
  );
}
