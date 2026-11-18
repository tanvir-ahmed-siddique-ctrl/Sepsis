import { NextRequest } from "next/server";

export const SESSION_COOKIE = "auralis_session";

export function hospitalApiUrl(path: string): string {
  const base = process.env.API_PROXY_TARGET || process.env.HOSPITAL_API_INTERNAL_URL || "http://127.0.0.1:8000";
  return `${base.replace(/\/$/, "")}/${path.replace(/^\//, "")}`;
}

export function sameOriginWrite(request: NextRequest): boolean {
  const origin = request.headers.get("origin");
  const marker = request.headers.get("x-auralis-request");
  if (marker !== "1" || !origin) return false;
  try {
    return new URL(origin).host === request.nextUrl.host;
  } catch {
    return false;
  }
}
