import { NextResponse } from "next/server";
import { hospitalApiUrl } from "@/lib/server-session";

export async function GET() {
  try {
    const upstream = await fetch(hospitalApiUrl("v1/auth/demo-accounts"), { cache: "no-store" });
    if (!upstream.ok) {
      // Soft-fail: keep client fallback roles visible while hospital API is down.
      return NextResponse.json(
        { enabled: true, accounts: [] },
        { headers: { "Cache-Control": "no-store" } },
      );
    }
    const data = await upstream.json();
    return NextResponse.json(data, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json(
      { enabled: true, accounts: [] },
      { headers: { "Cache-Control": "no-store" } },
    );
  }
}
