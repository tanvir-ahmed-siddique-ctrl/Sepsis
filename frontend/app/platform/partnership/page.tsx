import Link from "next/link";
import { VendorPartnership } from "@/components/VendorPartnership";

export const metadata = { title: "Hospital partnership | Auralis", robots: { index: false, follow: false } };

export default function VendorPartnershipPage() {
  return (
    <div className="mx-auto max-w-6xl py-10">
      <div className="mb-7 flex flex-wrap gap-4 text-sm font-semibold text-forest">
        <Link href="/platform/commercial" className="underline underline-offset-2">Commercial</Link>
        <Link href="/platform/accounts" className="underline underline-offset-2">Accounts</Link>
        <Link href="/platform/service" className="underline underline-offset-2">Service</Link>
      </div>
      <VendorPartnership />
    </div>
  );
}
