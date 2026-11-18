import type { Metadata } from "next";
import { VendorAccounts } from "@/components/VendorAccounts";

export const metadata: Metadata = { title: "Organization registry | Auralis", robots: { index: false, follow: false } };

export default function VendorAccountsPage() {
  return <div className="mx-auto max-w-6xl py-10"><VendorAccounts /></div>;
}
