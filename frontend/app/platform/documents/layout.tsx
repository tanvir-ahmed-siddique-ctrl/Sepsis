import { requireAccountWorkspace } from "@/lib/server-account-workspace";

export default async function VendorDocumentLayout({ children }: { children: React.ReactNode }) {
  await requireAccountWorkspace("vendor", ["root_admin", "finance_legal", "platform_admin", "security_compliance"]);
  return children;
}
