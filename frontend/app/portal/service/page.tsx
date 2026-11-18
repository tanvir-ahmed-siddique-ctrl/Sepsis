import Link from "next/link";
import { ServiceWorkspace } from "@/components/ServiceWorkspace";

export const metadata = { title: "Deployment & service | Auralis", robots: { index: false, follow: false } };

export default function CustomerServicePage() {
  return <div className="mx-auto max-w-6xl py-10"><Link href="/portal" className="mb-7 inline-block text-sm font-semibold text-forest underline underline-offset-2">← Organization workspace</Link><ServiceWorkspace vendor={false} /></div>;
}
