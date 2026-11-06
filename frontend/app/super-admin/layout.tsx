import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "PredictRx Sentinel | Fleet command",
  description: "Vendor operator access to site metadata and commercial controls.",
  openGraph: { title: "PredictRx Sentinel | Fleet command", description: "Vendor operator access to site metadata and commercial controls." },
};

export default function RouteLayout({ children }: { children: React.ReactNode }) {
  return children;
}
