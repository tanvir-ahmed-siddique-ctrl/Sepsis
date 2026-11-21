import type { Alert, ConnectorHealth, Gate, SiteMode } from "@/lib/api";

export type Tone = "neutral" | "info" | "warning" | "danger" | "success";

export const TONE_CLASS: Record<Tone, string> = {
  neutral: "border-transparent bg-muted-surface text-ink",
  info: "border-transparent bg-teal-soft/70 text-teal-dark",
  warning: "border-transparent bg-risk-watch/[0.1] text-[#7A4505]",
  danger: "border-transparent bg-risk-high/[0.08] text-risk-high",
  success: "border-transparent bg-risk-stable/[0.1] text-risk-stable",
};

export function humanize(value: string): string {
  return value.replaceAll("_", " ").replaceAll("-", " ");
}

export function siteModeBanner(mode: SiteMode): { tone: Tone; title: string; body: string } | null {
  switch (mode) {
    case "demo":
      // Clinical boards present the workspace without a loud evaluation disclaimer.
      return null;
    case "silent":
      return {
        tone: "warning",
        title: "Silent pilot",
        body: "Feeds are scored and recorded. Bedside staff are blinded and alerts are shadow-only.",
      };
    case "live-disabled":
      return {
        tone: "danger",
        title: "Live requested — disabled",
        body: "Readiness gates have not all passed, so the site behaves as a silent pilot. No interruptive alerts.",
      };
    case "live":
      return {
        tone: "success",
        title: "Live decision support",
        body: "Every readiness gate passed. Alerts reach clinicians; every decision stays with the clinical team.",
      };
  }
}

export function gateProgress(gates: Gate[]): { passed: number; total: number; blocking: string[]; eligible: boolean } {
  const blocking = gates.filter((gate) => !gate.passed).map((gate) => gate.gate);
  return { passed: gates.length - blocking.length, total: gates.length, blocking, eligible: gates.length > 0 && blocking.length === 0 };
}

export function formatGateValue(value: unknown): string {
  if (value == null) return "—";
  if (typeof value === "boolean") return value ? "yes" : "no";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(3);
  if (Array.isArray(value)) return value.length ? value.join(", ") : "none";
  if (typeof value === "object") return Object.keys(value as object).length ? "recorded" : "—";
  return String(value);
}

export function reviewClock(alert: Pick<Alert, "status" | "review_minutes" | "review_sla_minutes" | "overdue">): {
  label: string;
  tone: Tone;
} {
  if (alert.review_minutes == null) return { label: "No wall-clock time (replay)", tone: "neutral" };
  if (alert.status !== "open") return { label: `First action after ${alert.review_minutes} min`, tone: "neutral" };
  if (alert.overdue) {
    return { label: `Overdue by ${alert.review_minutes - alert.review_sla_minutes} min`, tone: "danger" };
  }
  return { label: `Open ${alert.review_minutes} of ${alert.review_sla_minutes} min`, tone: alert.review_minutes >= alert.review_sla_minutes * 0.66 ? "warning" : "info" };
}

/** Only TrustGate-covered open alerts are allowed to demand attention; watch / verify / abstain never interrupt. */
export function attentionAlerts(alerts: Alert[], seen: ReadonlySet<string>): Alert[] {
  return alerts.filter((alert) => alert.status === "open" && alert.trustgate.state === "alert" && !seen.has(alert.alert_id));
}

export function connectorTone(state: ConnectorHealth["state"]): Tone {
  return {
    never_connected: "neutral",
    healthy: "success",
    degraded: "warning",
    stale: "danger",
    circuit_open: "danger",
  }[state] as Tone;
}

export function minutesLabel(minutes: number | null | undefined): string {
  if (minutes == null) return "—";
  if (minutes < 60) return `${Math.round(minutes)} min`;
  if (minutes < 60 * 48) return `${(minutes / 60).toFixed(1)} h`;
  return `${(minutes / 1440).toFixed(1)} d`;
}
