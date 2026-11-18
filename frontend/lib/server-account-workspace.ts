import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { accountApiUrl, ACCOUNT_SESSION_COOKIE } from "@/lib/server-account";

export async function requireAccountWorkspace(required: "vendor" | "customer", allowedRoles?: string[]) {
  const token = (await cookies()).get(ACCOUNT_SESSION_COOKIE)?.value;
  if (!token) redirect("/signin");
  const url = accountApiUrl("v1/auth/me");
  if (!url) throw new Error("Account service is not configured");
  const response = await fetch(url, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" }).catch(() => null);
  if (!response) throw new Error("Account service unavailable");
  if (response.status === 401 || response.status === 403) redirect("/signin");
  if (!response.ok) throw new Error("Account identity resolution failed");
  const identity = await response.json() as { vendor?: boolean; role?: string; evaluation?: boolean; must_change_password?: boolean; organization_ids?: string[] };
  if (identity.must_change_password) redirect("/signin");
  if (required === "vendor" ? !identity.vendor : (identity.vendor && !identity.evaluation) || !identity.organization_ids?.length) redirect("/signin");
  if (allowedRoles && !identity.evaluation && !allowedRoles.includes(identity.role || "")) redirect("/signin");
}
