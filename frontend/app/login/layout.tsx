import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Auralis | Enterprise sign in",
  description: "Sign in with a hospital-issued account or open the labelled evaluator gateway.",
  openGraph: { title: "Auralis | Enterprise sign in", description: "Sign in with a hospital-issued account or open the labelled evaluator gateway." },
};

export default function RouteLayout({ children }: { children: React.ReactNode }) {
  return children;
}
