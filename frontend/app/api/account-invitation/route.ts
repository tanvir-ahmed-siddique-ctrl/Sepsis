import { NextRequest, NextResponse } from "next/server";
import { accountApiUrl } from "@/lib/server-account";
import { sameOriginWrite } from "@/lib/server-session";

export async function POST(request: NextRequest) {
  if (!sameOriginWrite(request)) return NextResponse.json({ detail: "Same-origin request required" }, { status: 403 });
  const url = accountApiUrl("v1/auth/accept-invitation");
  if (!url) return NextResponse.json({ detail: "Account service unavailable" }, { status: 503 });
  const body = await request.text();
  if (body.length > 2048) return NextResponse.json({ detail: "Request too large" }, { status: 413 });
  const upstream = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    cache: "no-store",
    redirect: "manual",
  }).catch(() => null);
  if (!upstream) return NextResponse.json({ detail: "Account service unavailable" }, { status: 503 });
  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: { "Content-Type": upstream.headers.get("content-type") || "application/json", "Cache-Control": "no-store" },
  });
}
