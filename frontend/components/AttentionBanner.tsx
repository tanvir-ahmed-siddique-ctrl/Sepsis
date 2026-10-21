"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { api, type Alert } from "@/lib/api";
import { useLocale } from "@/lib/locale";
import { attentionAlerts } from "@/lib/pilot";
import { useSession } from "@/lib/session";

const POLL_MS = 5000;

/**
 * Polls open alerts and surfaces only TrustGate-covered ones. Alerts already open when the page
 * loads are treated as seen so a refresh does not re-announce them.
 */
export function AttentionBanner() {
  const { t } = useLocale();
  const { me } = useSession();
  const seen = useRef<Set<string> | null>(null);
  const [pending, setPending] = useState<Alert[]>([]);

  useEffect(() => {
    if (!me) return;
    let active = true;
    async function poll() {
      try {
        const { alerts } = await api<{ alerts: Alert[] }>("/v1/alerts?status=open");
        if (!active) return;
        if (seen.current === null) {
          seen.current = new Set(alerts.map((alert) => alert.alert_id));
          return;
        }
        const fresh = attentionAlerts(alerts, seen.current);
        fresh.forEach((alert) => seen.current?.add(alert.alert_id));
        const stillOpen = new Set(alerts.map((alert) => alert.alert_id));
        setPending((current) => [...current.filter((alert) => stillOpen.has(alert.alert_id)), ...fresh]);
      } catch {
        // Banner is best effort; the alerts page surfaces errors.
      }
    }
    void poll();
    const timer = window.setInterval(() => void poll(), POLL_MS);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [me]);

  if (pending.length === 0) return null;
  const latest = pending[pending.length - 1];
  return (
    <div role="alert" aria-live="assertive" className="border-b border-risk-high/40 bg-risk-high/10">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-4 py-2 text-sm sm:px-6">
        <strong className="text-risk-high">{t.attention.title}</strong>
        <span>
          {latest.display_name} {t.attention.body}
          {pending.length > 1 ? ` (+${pending.length - 1})` : ""}
        </span>
        <Link href={`/patient/${latest.patient_id}`} className="ml-auto border border-risk-high/40 px-2 py-0.5 font-medium text-risk-high">
          {t.attention.review}
        </Link>
        <button type="button" onClick={() => setPending([])} className="text-xs text-ink/60 underline">
          {t.attention.dismiss}
        </button>
      </div>
    </div>
  );
}
