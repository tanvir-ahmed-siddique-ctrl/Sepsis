"use client";

import { useEffect } from "react";
import { api } from "@/lib/api";
import { flushOutbox } from "@/lib/outbox";

export function OfflineSync() {
  useEffect(() => {
    if ("serviceWorker" in navigator) void navigator.serviceWorker.register("/sw.js");
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
