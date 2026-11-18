import { requireAccountWorkspace } from "@/lib/server-account-workspace";

export default async function VendorCommercialLayout({ children }: { children: React.ReactNode }) {
  await requireAccountWorkspace("vendor", ["root_admin", "platform_admin", "finance_legal"]);
  return children;
}
