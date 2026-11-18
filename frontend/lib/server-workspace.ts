import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { hospitalApiUrl, SESSION_COOKIE } from "@/lib/server-session";

export async function requireSiteWorkspace(allowed: string[]) {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) redirect("/signin");
  const response = await fetch(hospitalApiUrl("v1/auth/workspaces"), {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  }).catch(() => null);
  if (!response) throw new Error("Hospital identity service is unavailable");
  if (response.status === 401 || response.status === 403) redirect("/signin");
  if (!response.ok) throw new Error("Hospital workspace resolution failed");
  const result = await response.json() as { workspaces?: Array<{ id: string }> };
  if (!result.workspaces?.some((workspace) => allowed.includes(workspace.id))) redirect("/signin");
}
