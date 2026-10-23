"use client";

import { useEffect } from "react";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";

type Alert = {
  alert_id: string;
  display_name?: string;
  patient_id: string;
  probability: number | null;
  reason: string;
};

export function AlertNotifier() {
  const { me } = useSession();
  useEffect(() => {
    if (!me || !("serviceWorker" in navigator)) return;
    let stopped = false;
    const check = async () => {
      if (stopped || !("Notification" in window) || Notification.permission !== "granted") return;
      try {
        const [alerts, profile] = await Promise.all([
          api<{ alerts: Alert[] }>("/v1/alerts?status=open"),
          api<{
            preferences: { alert_notifications: boolean; quiet_when_off_shift: boolean };
            current_shift: { staff: { user_id: string }[] };
          }>("/v1/auth/profile"),
        ]);
        const onShift = profile.current_shift.staff.some((person) => person.user_id === me.user_id);
        if (!profile.preferences.alert_notifications || (profile.preferences.quiet_when_off_shift && !onShift)) return;
        const seenKey = "predictrx-notified-alerts";
        const seen = new Set<string>(JSON.parse(window.localStorage.getItem(seenKey) || "[]"));
        const registration = await navigator.serviceWorker.ready;
        for (const alert of alerts.alerts) {
          if (seen.has(alert.alert_id)) continue;
          registration.active?.postMessage({
            type: "SHOW_ALERT",
            alertId: alert.alert_id,
            title: `PredictRx · ${alert.display_name || alert.patient_id}`,
            body: alert.reason,
            url: `/alerts?alert=${encodeURIComponent(alert.alert_id)}`,
          });
          seen.add(alert.alert_id);
        }
        window.localStorage.setItem(seenKey, JSON.stringify([...seen].slice(-100)));
      } catch {
        // Network/auth errors are already surfaced by the main app. Notification
        // delivery must never break bedside rendering.
      }
    };
    void check();
    const timer = window.setInterval(() => void check(), 15000);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [me]);
  return null;
}
