import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "PredictRx Sentinel | ICU command",
  description: "Review hospital-local ICU risk, telemetry and clinical workflow.",
  openGraph: { title: "PredictRx Sentinel | ICU command", description: "Review hospital-local ICU risk, telemetry and clinical workflow." },
};

export default function RouteLayout({ children }: { children: React.ReactNode }) {
  return children;
}
