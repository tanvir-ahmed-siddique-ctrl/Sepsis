import { requireSiteWorkspace } from "@/lib/server-workspace";

export default async function HospitalLayout({ children }: { children: React.ReactNode }) {
  await requireSiteWorkspace(["clinical", "hospital-admin", "hospital-integration"]);
  return children;
}
