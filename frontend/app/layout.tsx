import type { Metadata, Viewport } from "next";
import "@fontsource/instrument-serif/400.css";
import "@fontsource/instrument-serif/400-italic.css";
import "@fontsource/manrope/500.css";
import "@fontsource/manrope/600.css";
import "@fontsource/manrope/700.css";
import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "@fontsource/inter/700.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/600.css";
import "@fontsource/noto-sans-bengali/400.css";
import "@fontsource/noto-sans-bengali/600.css";
import "./globals.css";
import { SurfaceFrame } from "@/components/shells/SurfaceFrame";
import { LocaleProvider } from "@/lib/locale";
import { SessionProvider } from "@/lib/session";

export const metadata: Metadata = {
  title: "Auralis",
  description: "Auralis hospital-local ICU sepsis-risk review with accountable clinician oversight",
  manifest: "/manifest.webmanifest",
  icons: { icon: "/app-icon.svg", apple: "/app-icon.svg" },
};

export const viewport: Viewport = {
  themeColor: "#087E83",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-canvas text-ink font-sans antialiased">
        <LocaleProvider>
          <SessionProvider>
            <SurfaceFrame>{children}</SurfaceFrame>
          </SessionProvider>
        </LocaleProvider>
      </body>
    </html>
  );
}
