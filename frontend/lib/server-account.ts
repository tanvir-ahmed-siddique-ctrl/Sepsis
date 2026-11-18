export const ACCOUNT_SESSION_COOKIE = "auralis_account_session";

export function accountApiUrl(path: string): string | null {
  const base = process.env.ACCOUNT_API_INTERNAL_URL;
  if (!base) return null;
  return `${base.replace(/\/$/, "")}/${path.replace(/^\//, "")}`;
}
