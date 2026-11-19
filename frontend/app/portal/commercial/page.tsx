import { CustomerCommercial } from "@/components/CustomerCommercial";
import { BackLink } from "@/components/ui";

export const metadata = { title: "Contracts & finance | Auralis", robots: { index: false, follow: false } };

export default function CustomerCommercialPage() {
  return <div className="mx-auto max-w-6xl py-10"><BackLink href="/portal" label="Organization workspace" className="mb-6" /><CustomerCommercial /></div>;
}
