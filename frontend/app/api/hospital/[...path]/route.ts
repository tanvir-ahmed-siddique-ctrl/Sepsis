import { NextRequest, NextResponse } from "next/server";
import { hospitalApiUrl, sameOriginWrite, SESSION_COOKIE } from "@/lib/server-session";

type Context = { params: Promise<{ path: string[] }> };

async function forward(request: NextRequest, context: Context) {
  const { path } = await context.params;
  if (!path.length || path.some((part) => part === "." || part === "..")) {
    return NextResponse.json({ detail: "Not found" }, { status: 404 });
  }
  // Public liveness/readiness (FastAPI /health, /ready) — used by /docs and site setup.
  // Everything else stays under /v1 and requires a session cookie.
  const publicProbe =
    request.method === "GET" && path.length === 1 && ["ready", "health"].includes(path[0]);
  if (path[0] !== "v1" && !publicProbe) {
    return NextResponse.json({ detail: "Not found" }, { status: 404 });
  }
  const token = request.cookies.get(SESSION_COOKIE)?.value;
  if (!token && !publicProbe) {
    return NextResponse.json({ detail: "Sign in required" }, { status: 401 });
  }
  if (request.method !== "GET" && !sameOriginWrite(request)) {
    return NextResponse.json({ detail: "Same-origin request required" }, { status: 403 });
  }
  const url = hospitalApiUrl(path.map(encodeURIComponent).join("/")) + request.nextUrl.search;
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  for (const name of ["accept", "content-type"]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  const upstream = await fetch(url, {
    method: request.method,
    headers,
    body: request.method === "GET" ? undefined : await request.arrayBuffer(),
    cache: "no-store",
    redirect: "manual",
  });
  const responseHeaders = new Headers();
  for (const name of ["content-type", "content-disposition"]) {
    const value = upstream.headers.get(name);
    if (value) responseHeaders.set(name, value);
  }
  return new NextResponse(upstream.body, { status: upstream.status, headers: responseHeaders });
}

export const GET = forward;
export const POST = forward;
export const PUT = forward;
export const PATCH = forward;
export const DELETE = forward;
