import { requireSiteWorkspace } from "@/lib/server-workspace";

export default async function PlatformLayout({ children }: { children: React.ReactNode }) {
  await requireSiteWorkspace(["platform"]);
  return children;
}
