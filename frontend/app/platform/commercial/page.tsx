import Link from "next/link";
import { VendorCommercial } from "@/components/VendorCommercial";

export const metadata = { title: "Commercial operations | Auralis", robots: { index: false, follow: false } };

export default function VendorCommercialPage() {
  return (
    <div className="mx-auto max-w-6xl py-10">
      <div className="mb-7 flex flex-wrap gap-4 text-sm font-semibold text-forest">
        <Link href="/platform/accounts" className="underline underline-offset-2">Organization registry</Link>
        <Link href="/platform/partnership" className="underline underline-offset-2">Partnership & FDE</Link>
      </div>
      <VendorCommercial />
    </div>
  );
}
