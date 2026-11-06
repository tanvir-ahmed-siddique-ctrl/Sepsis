import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "PredictRx Sentinel | Evaluator gateway",
  description: "Explore five simulated hospital and platform workflows for the AI Builders Congress.",
  openGraph: { title: "PredictRx Sentinel | Evaluator gateway", description: "Explore five simulated hospital and platform workflows for the AI Builders Congress." },
};

export default function RouteLayout({ children }: { children: React.ReactNode }) {
  return children;
}
