import { ServiceWorkspace } from "@/components/ServiceWorkspace";
import { BackLink } from "@/components/ui";

export const metadata = { title: "Deployment & service | Auralis", robots: { index: false, follow: false } };

export default function CustomerServicePage() {
  return <div className="mx-auto max-w-6xl py-10"><BackLink href="/portal" label="Organization workspace" className="mb-6" /><ServiceWorkspace vendor={false} /></div>;
}
