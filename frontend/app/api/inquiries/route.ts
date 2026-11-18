import { NextRequest, NextResponse } from "next/server";
import { accountApiUrl } from "@/lib/server-account";
import { sameOriginWrite } from "@/lib/server-session";

export async function POST(request: NextRequest) {
  if (!sameOriginWrite(request)) return NextResponse.json({ detail: "Same-origin request required" }, { status: 403 });
  const url = accountApiUrl("v1/public/inquiries");
  if (!url) return NextResponse.json({ detail: "Contact intake is not configured" }, { status: 503 });
  const body = await request.text();
  if (body.length > 2048) return NextResponse.json({ detail: "Request too large" }, { status: 413 });
  const upstream = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body, cache: "no-store" }).catch(() => null);
  if (!upstream) return NextResponse.json({ detail: "Contact intake is unavailable" }, { status: 503 });
  const result = await upstream.json().catch(() => ({ detail: "Contact intake failed" }));
  return NextResponse.json(result, { status: upstream.status, headers: { "Cache-Control": "no-store" } });
}
