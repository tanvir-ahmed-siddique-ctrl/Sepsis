import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Auralis | ICU command centre",
  description: "Hospital-local ICU risk board, telemetry freshness and bedside ownership.",
  openGraph: {
    title: "Auralis | ICU command centre",
    description: "Hospital-local ICU risk board, telemetry freshness and bedside ownership.",
  },
};

export default function RouteLayout({ children }: { children: React.ReactNode }) {
  return children;
}
