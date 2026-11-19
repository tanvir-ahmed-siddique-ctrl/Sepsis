import { VendorPartnership } from "@/components/VendorPartnership";
import { BackLink } from "@/components/ui";

export const metadata = { title: "Hospital partnership | Auralis", robots: { index: false, follow: false } };

export default function VendorPartnershipPage() {
  return (
    <div className="mx-auto max-w-6xl py-10">
      <BackLink href="/platform/accounts" label="Organization registry" className="mb-6" />
      <VendorPartnership />
    </div>
  );
}
