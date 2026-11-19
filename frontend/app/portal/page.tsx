import type { Metadata } from "next";
import { CustomerWorkspace } from "@/components/CustomerWorkspace";

export const metadata: Metadata = {
  title: "Customer Portal | Auralis",
  description: "Organization-scoped account and operational support access for Auralis customers.",
  robots: { index: false, follow: false },
};

export default function PortalPage() {
  return <div className="mx-auto max-w-6xl py-10"><CustomerWorkspace /></div>;
}
