import { LocalLicencePanel } from "@/components/LocalLicencePanel";
import { requireSiteWorkspace } from "@/lib/server-workspace";

export default async function LocalLicencePage() {
  await requireSiteWorkspace(["hospital-admin"]);
  return <LocalLicencePanel />;
}
