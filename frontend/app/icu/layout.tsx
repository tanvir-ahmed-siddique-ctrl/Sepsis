import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Auralis | ICU command",
  description: "Review hospital-local ICU risk, telemetry and clinical workflow.",
  openGraph: { title: "Auralis | ICU command", description: "Review hospital-local ICU risk, telemetry and clinical workflow." },
};

export default function RouteLayout({ children }: { children: React.ReactNode }) {
  return children;
}
