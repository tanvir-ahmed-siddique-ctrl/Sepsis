import { requireAccountWorkspace } from "@/lib/server-account-workspace";

export default async function VendorServiceLayout({ children }: { children: React.ReactNode }) {
  await requireAccountWorkspace("vendor", ["root_admin", "platform_admin", "deployment_engineer", "support_engineer", "security_compliance"]);
  return children;
}
