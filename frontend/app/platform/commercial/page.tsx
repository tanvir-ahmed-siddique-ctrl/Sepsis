import { VendorCommercial } from "@/components/VendorCommercial";
import { BackLink } from "@/components/ui";

export const metadata = { title: "Commercial operations | Auralis", robots: { index: false, follow: false } };

export default function VendorCommercialPage() {
  return (
    <div className="mx-auto max-w-6xl py-10">
      <BackLink href="/platform/accounts" label="Organization registry" className="mb-6" />
      <VendorCommercial />
    </div>
  );
}
