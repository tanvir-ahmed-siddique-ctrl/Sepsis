import Link from "next/link";
import { DocumentWorkspace } from "@/components/DocumentWorkspace";

export const metadata = { title: "Documents | Auralis", robots: { index: false, follow: false } };

export default function CustomerDocuments() {
  return <div className="mx-auto max-w-6xl py-10"><Link href="/portal" className="mb-7 inline-block text-sm font-semibold text-forest underline underline-offset-2">← Organization workspace</Link><DocumentWorkspace vendor={false} /></div>;
}
