import type { ReactNode } from "react";
import type { RiskBand, SiteMode } from "@/lib/api";
import { siteModeBanner, TONE_CLASS, type Tone } from "@/lib/pilot";

export const BAND_COLOR: Record<RiskBand, string> = {
  insufficient_data: "#667085",
  stable: "#1f7a4d",
  watch: "#b7791f",
  high_risk: "#b42318",
};

export function Panel({
  title,
  className = "",
  children,
}: {
  title?: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section className={`border border-ink/10 bg-white/90 p-4 sm:p-5 ${className}`}>
      {title && <h2 className="mb-3 font-display text-xl text-ink">{title}</h2>}
      {children}
    </section>
  );
}

export function ApiError({ error }: { error: Error | string }) {
  const message = error instanceof Error ? error.message : error;
  return (
    <div role="alert" className="border border-risk-high/30 bg-risk-high/5 px-4 py-3 text-sm text-risk-high">
      <p className="font-semibold">Unable to load this view</p>
      <p className="mt-1">{message}</p>
    </div>
  );
}

export function Pill({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return <span className={`inline-block border px-2 py-0.5 text-xs font-medium ${TONE_CLASS[tone]}`}>{children}</span>;
}

export function SiteModeBanner({ mode, detail }: { mode: SiteMode; detail?: ReactNode }) {
  const banner = siteModeBanner(mode);
  return (
    <div role="status" className={`border px-4 py-2 text-sm ${TONE_CLASS[banner.tone]}`}>
      <strong>{banner.title}.</strong> {banner.body}
      {detail && <span className="ml-1 text-ink/60">{detail}</span>}
    </div>
  );
}

export function Stat({ label, value, color = "text-ink" }: { label: string; value: ReactNode; color?: string }) {
  return (
    <div className="min-w-[5.5rem] border border-ink/10 bg-white/70 px-3 py-2 text-center">
      <p className={`text-2xl font-semibold tabular-nums ${color}`}>{value}</p>
      <p className="text-xs uppercase tracking-wide text-ink/50">{label}</p>
    </div>
  );
}

export function KeyValue({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex justify-between gap-3 border-b border-ink/5 py-1 text-sm">
      <dt className="text-ink/55">{label}</dt>
      <dd className="text-right tabular-nums">{value}</dd>
    </div>
  );
}

export function Sparkline({
  values,
  color,
}: {
  values: Array<number | null>;
  color: string;
}) {
  const observed = values
    .map((value, index) => ({ value, index }))
    .filter((point): point is { value: number; index: number } => point.value != null && Number.isFinite(point.value));
  if (observed.length < 2) {
    return <div className="h-8 border-b border-ink/10" aria-label="Not enough risk history for a trend" />;
  }
  const width = 112;
  const height = 32;
  const max = Math.max(...observed.map((point) => point.value), 0.01);
  const min = Math.min(...observed.map((point) => point.value), 0);
  const span = Math.max(max - min, 0.01);
  const denominator = Math.max(values.length - 1, 1);
  const points = observed
    .map(({ value, index }) => {
      const x = (index / denominator) * width;
      const y = height - ((value - min) / span) * (height - 3) - 1.5;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Recent sepsis-risk trend" className="h-8 w-full">
      <polyline points={points} fill="none" stroke={color} strokeWidth="2" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}
