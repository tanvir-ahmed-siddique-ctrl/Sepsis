import Link from "next/link";
import { DocumentWorkspace } from "@/components/DocumentWorkspace";

export const metadata = { title: "Document centre | Auralis", robots: { index: false, follow: false } };

export default function VendorDocuments() {
  return <div className="mx-auto max-w-6xl py-10"><Link href="/platform/accounts" className="mb-7 inline-block text-sm font-semibold text-forest underline underline-offset-2">← Organization registry</Link><DocumentWorkspace vendor /></div>;
}
