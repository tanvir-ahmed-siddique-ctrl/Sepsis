import type { Metadata } from "next";
import "./globals.css";
import { AppNav } from "@/components/AppNav";
import { AttentionBanner } from "@/components/AttentionBanner";
import { OfflineSync } from "@/components/OfflineSync";
import { LocaleProvider } from "@/lib/locale";
import { SessionProvider } from "@/lib/session";

export const metadata: Metadata = {
  title: "PredictRx Sentinel",
  description: "ICU sepsis early-warning decision support — research prototype",
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
            <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">{children}</main>
          </SessionProvider>
        </LocaleProvider>
      </body>
    </html>
  );
}
