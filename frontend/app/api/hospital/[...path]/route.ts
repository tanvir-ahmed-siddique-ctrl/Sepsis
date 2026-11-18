import { NextRequest, NextResponse } from "next/server";
import { hospitalApiUrl, sameOriginWrite, SESSION_COOKIE } from "@/lib/server-session";

type Context = { params: Promise<{ path: string[] }> };

async function forward(request: NextRequest, context: Context) {
  const token = request.cookies.get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ detail: "Sign in required" }, { status: 401 });
  const { path } = await context.params;
  if (!path.length || path[0] !== "v1" || path.some((part) => part === "." || part === "..")) return NextResponse.json({ detail: "Not found" }, { status: 404 });
  if (request.method !== "GET" && !sameOriginWrite(request)) return NextResponse.json({ detail: "Same-origin request required" }, { status: 403 });
  const url = hospitalApiUrl(path.map(encodeURIComponent).join("/")) + request.nextUrl.search;
  const headers = new Headers({ Authorization: `Bearer ${token}` });
  for (const name of ["accept", "content-type"]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  const upstream = await fetch(url, { method: request.method, headers, body: request.method === "GET" ? undefined : await request.arrayBuffer(), cache: "no-store", redirect: "manual" });
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
