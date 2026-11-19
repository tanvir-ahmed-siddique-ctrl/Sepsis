import { ServiceWorkspace } from "@/components/ServiceWorkspace";
import { BackLink } from "@/components/ui";

export const metadata = { title: "Deployment & service operations | Auralis", robots: { index: false, follow: false } };

export default function VendorServicePage() {
  return <div className="mx-auto max-w-6xl py-10"><BackLink href="/platform/accounts" label="Organization registry" className="mb-6" /><ServiceWorkspace vendor /></div>;
}
