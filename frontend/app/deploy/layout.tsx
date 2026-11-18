import type { ReactNode } from "react";
import { requireSiteWorkspace } from "@/lib/server-workspace";

export default async function DeployLayout({ children }: { children: ReactNode }) {
  await requireSiteWorkspace(["clinical", "hospital-admin", "hospital-integration", "platform"]);
  return children;
}
