import { requireAccountWorkspace } from "@/lib/server-account-workspace";

export default async function CustomerPortalLayout({ children }: { children: React.ReactNode }) {
  await requireAccountWorkspace("customer");
  return children;
}
