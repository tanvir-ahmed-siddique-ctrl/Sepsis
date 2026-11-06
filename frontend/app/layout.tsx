import type { Metadata, Viewport } from "next";
import "./globals.css";
import { AppNav } from "@/components/AppNav";
import { AlertNotifier } from "@/components/AlertNotifier";
import { AttentionBanner } from "@/components/AttentionBanner";
import { OfflineSync } from "@/components/OfflineSync";
import { EvaluatorHud } from "@/components/EvaluatorHud";
import { LocaleProvider } from "@/lib/locale";
import { SessionProvider } from "@/lib/session";

export const metadata: Metadata = {
  title: "PredictRx Sentinel",
  description: "ICU sepsis early-warning decision support — research prototype",
  manifest: "/manifest.webmanifest",
  icons: { icon: "/app-icon.svg", apple: "/app-icon.svg" },
};

export const viewport: Viewport = {
  themeColor: "#0b6e69",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-mist text-ink font-sans antialiased">
        <LocaleProvider>
          <SessionProvider>
            <AppNav />
            <AttentionBanner />
            <OfflineSync />
            <AlertNotifier />
            <EvaluatorHud />
            <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">{children}</main>
          </SessionProvider>
        </LocaleProvider>
      </body>
    </html>
  );
}
