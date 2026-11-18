import { NextResponse } from "next/server";
import { hospitalApiUrl } from "@/lib/server-session";

export async function GET() {
  try {
    const upstream = await fetch(hospitalApiUrl("v1/auth/demo-accounts"), { cache: "no-store" });
    if (!upstream.ok) return NextResponse.json({ enabled: false, accounts: [] });
    const data = await upstream.json();
    return NextResponse.json(data, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ enabled: false, accounts: [] });
  }
}
