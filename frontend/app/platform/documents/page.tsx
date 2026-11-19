import { DocumentWorkspace } from "@/components/DocumentWorkspace";
import { BackLink } from "@/components/ui";

export const metadata = { title: "Document centre | Auralis", robots: { index: false, follow: false } };

export default function VendorDocuments() {
  return <div className="mx-auto max-w-6xl py-10"><BackLink href="/platform/accounts" label="Organization registry" className="mb-6" /><DocumentWorkspace vendor /></div>;
}
