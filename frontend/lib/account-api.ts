export class AccountRequestError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

export async function accountApi<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.method && init.method.toUpperCase() !== "GET") headers.set("X-Auralis-Request", "1");
  if (init?.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const response = await fetch(`/api/account${path}`, { ...init, headers, credentials: "same-origin", cache: "no-store" });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new AccountRequestError(String(result.detail || "Account request failed"), response.status);
  return result as T;
}
