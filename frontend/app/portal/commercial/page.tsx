import Link from "next/link";
import { CustomerCommercial } from "@/components/CustomerCommercial";

export const metadata = { title: "Contracts & finance | Auralis", robots: { index: false, follow: false } };

export default function CustomerCommercialPage() {
  return <div className="mx-auto max-w-6xl py-10"><Link href="/portal" className="mb-7 inline-block text-sm font-semibold text-forest underline underline-offset-2">← Organization workspace</Link><CustomerCommercial /></div>;
}
