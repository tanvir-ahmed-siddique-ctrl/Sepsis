"use client";

import { useEffect } from "react";
import { api } from "@/lib/api";
import { flushOutbox } from "@/lib/outbox";

export function OfflineSync() {
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      void navigator.serviceWorker.register("/sw.js").then((registration) => {
        // Force the notify-only worker so old auralis-shell-v* page caches die.
        void registration.update();
      });
      // One-shot wipe of stale shell caches left by earlier demo builds.
      if ("caches" in window) {
        void caches.keys().then((keys) =>
          Promise.all(keys.filter((key) => key.startsWith("auralis-shell-")).map((key) => caches.delete(key))),
        );
      }
    }
    const sync = () => {
      void flushOutbox(async (item) => {
        await api(item.path, { method: "POST", body: JSON.stringify(item.body) });
      });
    };
    window.addEventListener("online", sync);
    if (navigator.onLine) sync();
    return () => window.removeEventListener("online", sync);
  }, []);
  return null;
}
