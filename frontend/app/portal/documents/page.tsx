import { DocumentWorkspace } from "@/components/DocumentWorkspace";
import { BackLink } from "@/components/ui";

export const metadata = { title: "Documents | Auralis", robots: { index: false, follow: false } };

export default function CustomerDocuments() {
  return <div className="mx-auto max-w-6xl py-10"><BackLink href="/portal" label="Organization workspace" className="mb-6" /><DocumentWorkspace vendor={false} /></div>;
}
