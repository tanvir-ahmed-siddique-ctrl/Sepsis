import { NextRequest } from "next/server";

export const SESSION_COOKIE = "auralis_session";

export function hospitalApiUrl(path: string): string {
  const base = process.env.API_PROXY_TARGET || process.env.HOSPITAL_API_INTERNAL_URL || "http://127.0.0.1:8000";
  return `${base.replace(/\/$/, "")}/${path.replace(/^\//, "")}`;
}

function normalizeHost(raw: string): string {
  return raw.trim().toLowerCase().replace(/\.$/, "");
}

/** Public hosts the reverse proxy may present (Render/Caddy rewrite nextUrl.host). */
export function requestPublicHosts(request: NextRequest): Set<string> {
  const hosts = new Set<string>();
  const add = (value: string | null) => {
    if (!value) return;
    for (const part of value.split(",")) {
      const host = normalizeHost(part);
      if (host) hosts.add(host);
    }
  };
  add(request.headers.get("x-forwarded-host"));
  add(request.headers.get("host"));
  try {
    hosts.add(normalizeHost(request.nextUrl.host));
  } catch {
    // ignore malformed nextUrl
  }
  return hosts;
}

export function sameOriginWrite(request: NextRequest): boolean {
  const origin = request.headers.get("origin");
  const marker = request.headers.get("x-auralis-request");
  if (marker !== "1" || !origin) return false;
  try {
    const originHost = normalizeHost(new URL(origin).host);
    return requestPublicHosts(request).has(originHost);
  } catch {
    return false;
  }
}
