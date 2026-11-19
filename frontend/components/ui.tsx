"use client";

import Link from "next/link";
import { useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import type { RiskBand, SiteMode } from "@/lib/api";
import { siteModeBanner, TONE_CLASS, type Tone } from "@/lib/pilot";
import { Icon, type IconName } from "@/components/ui/Icon";

export const BAND_COLOR: Record<RiskBand, string> = {
  insufficient_data: "#667085",
  stable: "#1f7a4d",
  watch: "#a15c07",
  high_risk: "#b42318",
};

export function Panel({
  title,
  description,
  actions,
  className = "",
  children,
}: {
  title?: string;
  description?: ReactNode;
  actions?: ReactNode;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section className={`auralis-panel ${className}`}>
      {(title || actions) && (
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            {title && <h2 className="text-base font-semibold tracking-tight text-ink">{title}</h2>}
            {description && <p className="mt-1 text-sm text-muted">{description}</p>}
          </div>
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

export function ApiError({ error, title = "Unable to load this view" }: { error: Error | string; title?: string }) {
  const message = error instanceof Error ? error.message : error;
  return (
    <div role="alert" className="flex gap-3 rounded-xl border border-risk-high/25 bg-risk-high/[0.04] px-4 py-3 text-sm">
      <Icon name="alert" size={18} className="mt-0.5 text-risk-high" />
      <div className="min-w-0">
        <p className="font-semibold text-risk-high">{title}</p>
        <p className="mt-0.5 break-words text-ink/80">{message}</p>
      </div>
    </div>
  );
}

export function Pill({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-medium ${TONE_CLASS[tone]}`}>
      {children}
    </span>
  );
}

export function StatusDot({ tone = "neutral", pulse = false }: { tone?: Tone; pulse?: boolean }) {
  const color = {
    neutral: "bg-muted",
    info: "bg-teal",
    warning: "bg-risk-watch",
    danger: "bg-risk-high",
    success: "bg-risk-stable",
  }[tone];
  return (
    <span className="relative inline-flex h-2 w-2" aria-hidden="true">
      {pulse && <span className={`auralis-pulse-dot absolute inset-0 rounded-full ${color}`} />}
      <span className={`relative h-2 w-2 rounded-full ${color}`} />
    </span>
  );
}

export function SiteModeBanner({ mode, detail }: { mode: SiteMode; detail?: ReactNode }) {
  const banner = siteModeBanner(mode);
  if (!banner) return null;
  return (
    <div role="status" className={`flex flex-wrap items-center gap-x-2 gap-y-1 rounded-xl border px-4 py-2.5 text-sm ${TONE_CLASS[banner.tone]}`}>
      <StatusDot tone={banner.tone} />
      <strong className="font-semibold">{banner.title}.</strong>
      <span className="text-ink/80">{banner.body}</span>
      {detail && <span className="text-muted">{detail}</span>}
    </div>
  );
}

export function Stat({ label, value, color = "text-ink", hint }: { label: string; value: ReactNode; color?: string; hint?: ReactNode }) {
  return (
    <div className="min-w-0 flex-1 basis-[7rem] rounded-xl border border-border bg-white px-3 py-3 shadow-soft sm:min-w-[7rem] sm:flex-none sm:px-4">
      <p className="truncate text-xs font-medium text-muted">{label}</p>
      <p className={`mt-1 text-2xl font-semibold tabular-nums tracking-tight ${color}`}>{value}</p>
      {hint && <p className="mt-0.5 text-xs text-muted">{hint}</p>}
    </div>
  );
}

export function KeyValue({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex justify-between gap-3 border-b border-border/70 py-2 text-sm last:border-b-0">
      <dt className="text-muted">{label}</dt>
      <dd className="text-right tabular-nums text-ink">{value}</dd>
    </div>
  );
}

export function EmptyState({ title, body, action, icon = "layers" }: { title: string; body: string; action?: ReactNode; icon?: IconName }) {
  return (
    <div className="flex flex-col items-center rounded-xl border border-dashed border-border bg-white px-6 py-10 text-center text-sm">
      <span className="flex h-10 w-10 items-center justify-center rounded-full bg-muted-surface text-muted">
        <Icon name={icon} size={18} />
      </span>
      <h2 className="mt-3 text-base font-semibold text-ink">{title}</h2>
      <p className="mt-1 max-w-md text-muted">{body}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function Skeleton({ className = "h-4 w-full" }: { className?: string }) {
  return <div className={`auralis-skeleton ${className}`} aria-hidden="true" />;
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  back,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
  back?: { href: string; label: string };
}) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4 border-b border-border pb-5">
      <div className="min-w-0">
        {back && <BackLink href={back.href} label={back.label} className="mb-3" />}
        {eyebrow && <p className="auralis-eyebrow">{eyebrow}</p>}
        <h1 className="mt-1.5 auralis-page-title">{title}</h1>
        {description && <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  );
}

export function BackLink({ href, label, className = "" }: { href: string; label: string; className?: string }) {
  return (
    <Link href={href} className={`group inline-flex items-center gap-1.5 text-sm font-medium text-muted transition-colors hover:text-ink ${className}`}>
      <Icon name="arrow-left" size={16} className="transition-transform group-hover:-translate-x-0.5" />
      {label}
    </Link>
  );
}

export function ArrowLink({ href, children, className = "", external = false }: { href: string; children: ReactNode; className?: string; external?: boolean }) {
  if (external) {
    return (
      <a href={href} target="_blank" rel="noreferrer" className={`auralis-link ${className}`}>
        {children}
        <Icon name="external" size={15} />
      </a>
    );
  }
  return (
    <Link href={href} className={`auralis-link ${className}`}>
      {children}
      <Icon name="arrow-right" size={16} />
    </Link>
  );
}

export function Tabs<T extends string>({
  tabs,
  value,
  onChange,
  label,
}: {
  tabs: Array<{ id: T; label: string; icon?: IconName }>;
  value: T;
  onChange: (id: T) => void;
  label: string;
}) {
  const refs = useRef<Array<HTMLButtonElement | null>>([]);
  function onKey(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let next = -1;
    if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
    if (event.key === "ArrowLeft") next = (index - 1 + tabs.length) % tabs.length;
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = tabs.length - 1;
    if (next < 0) return;
    event.preventDefault();
    onChange(tabs[next].id);
    refs.current[next]?.focus();
  }
  return (
    <div role="tablist" aria-label={label} className="flex gap-1 overflow-x-auto overflow-y-hidden border-b border-border [scrollbar-width:none]">
      {tabs.map((tab, index) => {
        const active = tab.id === value;
        return (
          <button
            key={tab.id}
            ref={(node) => {
              refs.current[index] = node;
            }}
            role="tab"
            type="button"
            id={`tab-${tab.id}`}
            aria-selected={active}
            aria-controls={`panel-${tab.id}`}
            tabIndex={active ? 0 : -1}
            onClick={() => onChange(tab.id)}
            onKeyDown={(event) => onKey(event, index)}
            className={`inline-flex shrink-0 items-center gap-2 rounded-none border-b-2 px-3 py-2.5 text-sm font-medium transition-colors ${
              active ? "border-navy text-ink" : "border-transparent text-muted hover:border-border hover:text-ink"
            }`}
          >
            {tab.icon && <Icon name={tab.icon} size={16} />}
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Number((bytes / 1024).toFixed(bytes < 10 * 1024 ? 1 : 0))} KB`;
  return `${Number((bytes / (1024 * 1024)).toFixed(1))} MB`;
}

/**
 * Drag-and-drop file control. Client checks mirror server limits only for UX;
 * the server remains the authority on type, size and content validation.
 */
export function FileDrop({
  label,
  accept,
  acceptLabel,
  maxBytes,
  limitLabel,
  file,
  onFile,
  disabled = false,
  compact = false,
  name,
  required = false,
}: {
  label: string;
  accept: string;
  acceptLabel: string;
  maxBytes?: number;
  limitLabel?: string;
  file: File | null;
  onFile: (file: File | null) => void;
  disabled?: boolean;
  compact?: boolean;
  name?: string;
  required?: boolean;
}) {
  const inputId = useId();
  const hintId = `${inputId}-hint`;
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  function accepts(candidate: File): boolean {
    const rules = accept.split(",").map((rule) => rule.trim().toLowerCase()).filter(Boolean);
    if (!rules.length) return true;
    const fileName = candidate.name.toLowerCase();
    const type = (candidate.type || "").toLowerCase();
    return rules.some((rule) => {
      if (rule.startsWith(".")) return fileName.endsWith(rule);
      if (rule.endsWith("/*")) return type.startsWith(rule.slice(0, -1));
      return type === rule;
    });
  }

  function choose(candidate: File | null | undefined) {
    if (!candidate) return;
    if (!accepts(candidate)) {
      setProblem(`Unsupported file type. Accepted: ${acceptLabel}.`);
      return;
    }
    if (maxBytes && candidate.size > maxBytes) {
      setProblem(`File is ${formatBytes(candidate.size)}. The limit is ${limitLabel ?? formatBytes(maxBytes)}.`);
      return;
    }
    if (candidate.size === 0) {
      setProblem("File is empty.");
      return;
    }
    setProblem(null);
    onFile(candidate);
  }

  function clear() {
    setProblem(null);
    onFile(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  const limit = maxBytes ? ` · up to ${limitLabel ?? formatBytes(maxBytes)}` : "";

  return (
    <div>
      <span className="auralis-label" id={`${inputId}-label`}>
        {label}
        {required && <span className="text-risk-high"> *</span>}
      </span>
      <input
        ref={inputRef}
        id={inputId}
        name={name}
        type="file"
        accept={accept}
        disabled={disabled}
        className="sr-only"
        aria-labelledby={`${inputId}-label`}
        aria-describedby={hintId}
        onChange={(event) => choose(event.target.files?.[0])}
      />
      {file ? (
        <div className="flex items-center gap-3 rounded-xl border border-border bg-white px-3.5 py-3 shadow-soft">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-teal-soft/60 text-teal-dark">
            <Icon name="file" size={18} />
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-ink">{file.name}</p>
            <p className="text-xs text-muted">{formatBytes(file.size)}</p>
          </div>
          <button type="button" onClick={() => inputRef.current?.click()} disabled={disabled} className="auralis-btn-ghost auralis-btn-sm">
            Replace
          </button>
          <button type="button" onClick={clear} disabled={disabled} className="auralis-icon-btn h-9 w-9" aria-label={`Remove ${file.name}`}>
            <Icon name="close" size={16} />
          </button>
        </div>
      ) : (
        <label
          htmlFor={inputId}
          onDragOver={(event) => {
            event.preventDefault();
            if (!disabled) setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            if (!disabled) choose(event.dataTransfer.files?.[0]);
          }}
          className={`flex cursor-pointer items-center gap-3 rounded-xl border border-dashed px-4 transition-colors ${compact ? "py-3" : "flex-col justify-center py-7 text-center"} ${
            disabled
              ? "cursor-not-allowed border-border bg-muted-surface opacity-60"
              : dragging
                ? "border-teal bg-teal-soft/40"
                : "border-[#CBD4DA] bg-white hover:border-teal/60 hover:bg-[#FAFCFC]"
          }`}
        >
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-muted-surface text-ink">
            <Icon name="upload" size={17} />
          </span>
          <span className={compact ? "text-left" : ""}>
            <span className="block text-sm text-ink">
              <span className="font-semibold text-teal">Choose a file</span> or drag it here
            </span>
            <span id={hintId} className="block text-xs text-muted">
              {acceptLabel}
              {limit}
            </span>
          </span>
        </label>
      )}
      {problem && (
        <p role="alert" className="mt-2 flex items-center gap-1.5 text-xs font-medium text-risk-high">
          <Icon name="alert" size={14} />
          {problem}
        </p>
      )}
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
    return <div className="h-8 border-b border-dashed border-border" aria-label="Not enough risk history for a trend" />;
  }
  const width = 112;
  const height = 32;
  const max = Math.max(...observed.map((point) => point.value), 0.01);
  const min = Math.min(...observed.map((point) => point.value), 0);
  const span = Math.max(max - min, 0.01);
  const denominator = Math.max(values.length - 1, 1);
  const coords = observed.map(({ value, index }) => {
    const x = (index / denominator) * width;
    const y = height - ((value - min) / span) * (height - 3) - 1.5;
    return [x, y] as const;
  });
  const points = coords.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const area = `${coords[0][0].toFixed(1)},${height} ${points} ${coords[coords.length - 1][0].toFixed(1)},${height}`;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Recent sepsis-risk trend" className="h-8 w-full" preserveAspectRatio="none">
      <polygon points={area} fill={color} opacity="0.08" />
      <polyline points={points} fill="none" stroke={color} strokeWidth="1.75" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}
