import { requireAccountWorkspace } from "@/lib/server-account-workspace";

export default async function VendorAccountsLayout({ children }: { children: React.ReactNode }) {
  await requireAccountWorkspace("vendor");
  return children;
}
