import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "PredictRx Sentinel | Enterprise sign in",
  description: "Sign in with a hospital-issued account or open the labelled evaluator gateway.",
  openGraph: { title: "PredictRx Sentinel | Enterprise sign in", description: "Sign in with a hospital-issued account or open the labelled evaluator gateway." },
};

export default function RouteLayout({ children }: { children: React.ReactNode }) {
  return children;
}
