import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sign in | Auralis",
  description: "Sign in to Auralis with a hospital-issued identity.",
  openGraph: { title: "Sign in | Auralis", description: "Sign in with a hospital-issued identity." },
};

export default function SigninLayout({ children }: { children: React.ReactNode }) {
  return children;
}
