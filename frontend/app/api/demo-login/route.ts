import { NextRequest, NextResponse } from "next/server";
import { hospitalApiUrl, SESSION_COOKIE } from "@/lib/server-session";
import { accountApiUrl, ACCOUNT_SESSION_COOKIE } from "@/lib/server-account";

const DEMO_PASSWORD = "auralis-demo-2026";

const HOSPITAL_DEMOS: Record<string, string> = {
  "demo-clinician": "/app/icu",
  "demo-nurse": "/app/chart",
  "demo-admin": "/app/admin/overview",
  "demo-it": "/deploy",
  "demo-operator": "/platform/overview",
};

const VENDOR_DEMO = "vendor@auralis.demo";

function safeNext(raw: string | null): string | null {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//")) return null;
  if (raw.startsWith("/signin") || raw.startsWith("/login") || raw.startsWith("/api/")) return null;
  return raw;
}

function redirectTo(request: NextRequest, path: string) {
  const host = request.headers.get("x-forwarded-host") || request.headers.get("host");
  const protoHeader = request.headers.get("x-forwarded-proto");
  const proto = protoHeader || (request.nextUrl.protocol === "https:" ? "https" : "http");
  if (host) {
    return NextResponse.redirect(`${proto}://${host}${path}`, 303);
  }
  const url = request.nextUrl.clone();
  url.pathname = path;
  url.search = "";
  url.hash = "";
  return NextResponse.redirect(url, 303);
}

/**
 * Form-friendly demo sign-in. Works without client hydration — quick-role
 * buttons can POST here and get a normal redirect + session cookie.
 */
export async function POST(request: NextRequest) {
  const form = await request.formData().catch(() => null);
  const userId = String(form?.get("user_id") || "").trim();
  const next = safeNext(String(form?.get("next") || "") || null);

  if (!userId) {
    return redirectTo(request, "/signin");
  }

  if (userId === VENDOR_DEMO) {
    const loginUrl = accountApiUrl("v1/auth/login");
    const identityUrl = accountApiUrl("v1/auth/me");
    if (!loginUrl || !identityUrl) {
      const url = request.nextUrl.clone();
      url.pathname = "/signin";
      url.search = "error=accounts";
      return NextResponse.redirect(url, 303);
    }
    const accountLogin = await fetch(loginUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: userId, password: DEMO_PASSWORD }),
      cache: "no-store",
    });
    const accountResult = await accountLogin.json().catch(() => ({}));
    if (!accountLogin.ok || !accountResult.access_token) {
      const url = request.nextUrl.clone();
      url.pathname = "/signin";
      url.search = "error=vendor";
      return NextResponse.redirect(url, 303);
    }
    const identity = await fetch(identityUrl, {
      headers: { Authorization: `Bearer ${accountResult.access_token}` },
      cache: "no-store",
    });
    if (!identity.ok) {
      const url = request.nextUrl.clone();
      url.pathname = "/signin";
      url.search = "error=vendor";
      return NextResponse.redirect(url, 303);
    }
    const me = (await identity.json()) as { workspaces?: Array<{ path: string }> };
    const destination = next || me.workspaces?.[0]?.path || "/platform/accounts";
    const response = redirectTo(request, destination);
    response.cookies.set(ACCOUNT_SESSION_COOKIE, accountResult.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: Math.min(Number(accountResult.expires_in_seconds) || 900, 8 * 3600),
    });
    response.cookies.delete(SESSION_COOKIE);
    return response;
  }

  const fallbackPath = HOSPITAL_DEMOS[userId];
  if (!fallbackPath) {
    const url = request.nextUrl.clone();
    url.pathname = "/signin";
    url.search = "error=unknown";
    return NextResponse.redirect(url, 303);
  }

  const upstream = await fetch(hospitalApiUrl("v1/auth/login"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, password: DEMO_PASSWORD }),
    cache: "no-store",
  });
  const result = await upstream.json().catch(() => ({}));
  if (!upstream.ok || !result.access_token) {
    const url = request.nextUrl.clone();
    url.pathname = "/signin";
    url.search = "error=hospital";
    return NextResponse.redirect(url, 303);
  }

  const identity = await fetch(hospitalApiUrl("v1/auth/me"), {
    headers: { Authorization: `Bearer ${result.access_token}` },
    cache: "no-store",
  });
  if (!identity.ok) {
    const url = request.nextUrl.clone();
    url.pathname = "/signin";
    url.search = "error=hospital";
    return NextResponse.redirect(url, 303);
  }
  const me = (await identity.json().catch(() => ({}))) as { role?: string; default_path?: string };
  const destination =
    next ||
    (me.role === "operator" || me.default_path?.startsWith("/platform")
      ? me.default_path || "/platform/overview"
      : fallbackPath);

  const response = redirectTo(request, destination);
  response.cookies.set(SESSION_COOKIE, result.access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: Math.min(Number(result.expires_in_seconds) || 15 * 60, 60 * 60),
  });
  response.cookies.delete(ACCOUNT_SESSION_COOKIE);
  return response;
}
