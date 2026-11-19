"use client";

import { useEffect, useState } from "react";
import { Icon } from "@/components/ui/Icon";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

/**
 * Hospital workspace install control. Captures the browser install prompt when
 * available; otherwise points clinicians to the browser/OS install menu.
 */
export function InstallAppControl({ compact = false }: { compact?: boolean }) {
  const [installEvent, setInstallEvent] = useState<BeforeInstallPromptEvent | null>(null);
  const [installed, setInstalled] = useState(false);
  const [hint, setHint] = useState<string | null>(null);

  useEffect(() => {
    const standalone =
      window.matchMedia("(display-mode: standalone)").matches ||
      ("standalone" in navigator && Boolean((navigator as Navigator & { standalone?: boolean }).standalone));
    if (standalone) setInstalled(true);

    const capture = (event: Event) => {
      event.preventDefault();
      setInstallEvent(event as BeforeInstallPromptEvent);
    };
    const onInstalled = () => {
      setInstalled(true);
      setInstallEvent(null);
    };
    window.addEventListener("beforeinstallprompt", capture);
    window.addEventListener("appinstalled", onInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", capture);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  if (installed) return null;

  async function install() {
    if (!installEvent) {
      setHint("Use the browser menu: Install app or Add to Home Screen.");
      window.setTimeout(() => setHint(null), 4500);
      return;
    }
    await installEvent.prompt();
    const choice = await installEvent.userChoice;
    if (choice.outcome === "accepted") setInstalled(true);
    setInstallEvent(null);
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => void install()}
        className={
          compact
            ? "auralis-icon-btn h-10 w-10"
            : "auralis-btn-secondary auralis-btn-sm hidden sm:inline-flex"
        }
        aria-label="Install Auralis app"
        title="Install app on this device"
      >
        <Icon name="download" size={16} />
        {!compact && <span>Install app</span>}
      </button>
      {hint && (
        <p
          role="status"
          className="auralis-fade-up absolute right-0 top-full z-50 mt-2 w-64 rounded-lg border border-border bg-white px-3 py-2 text-xs leading-5 text-muted shadow-lift"
        >
          {hint}
        </p>
      )}
    </div>
  );
}
