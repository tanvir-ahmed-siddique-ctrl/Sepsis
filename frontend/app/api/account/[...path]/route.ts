import { NextRequest, NextResponse } from "next/server";
import { accountApiUrl, ACCOUNT_SESSION_COOKIE } from "@/lib/server-account";
import { sameOriginWrite } from "@/lib/server-session";

type Context = { params: Promise<{ path: string[] }> };

async function forward(request: NextRequest, context: Context) {
  const token = request.cookies.get(ACCOUNT_SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ detail: "Organization sign-in required" }, { status: 401 });
  const { path } = await context.params;
  if (path[0] !== "v1" || path.some((part) => part === "." || part === "..")) return NextResponse.json({ detail: "Not found" }, { status: 404 });
  if (request.method !== "GET" && !sameOriginWrite(request)) return NextResponse.json({ detail: "Same-origin request required" }, { status: 403 });
  const url = accountApiUrl(path.map(encodeURIComponent).join("/"));
  if (!url) return NextResponse.json({ detail: "Account service unavailable" }, { status: 503 });
  const headers = new Headers({ Authorization: `Bearer ${token}` });
  for (const name of ["accept", "content-type"]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  const upstream = await fetch(url + request.nextUrl.search, {
    method: request.method, headers,
    body: request.method === "GET" ? undefined : await request.arrayBuffer(),
    cache: "no-store", redirect: "manual",
  });
  const responseHeaders = new Headers({ "Cache-Control": "no-store" });
  const contentType = upstream.headers.get("content-type");
  if (contentType) responseHeaders.set("content-type", contentType);
  const disposition = upstream.headers.get("content-disposition");
  if (disposition && contentType === "application/pdf") responseHeaders.set("content-disposition", disposition);
  return new NextResponse(upstream.body, { status: upstream.status, headers: responseHeaders });
}

export const GET = forward;
export const POST = forward;
export const PATCH = forward;
export const DELETE = forward;
