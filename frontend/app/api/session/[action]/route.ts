import { NextRequest, NextResponse } from "next/server";
import { hospitalApiUrl, sameOriginWrite, SESSION_COOKIE } from "@/lib/server-session";
import { accountApiUrl, ACCOUNT_SESSION_COOKIE } from "@/lib/server-account";

type Context = { params: Promise<{ action: string }> };

export async function POST(request: NextRequest, context: Context) {
  if (!sameOriginWrite(request)) return NextResponse.json({ detail: "Same-origin request required" }, { status: 403 });
  const { action } = await context.params;
  const existing = request.cookies.get(SESSION_COOKIE)?.value;
  const accountToken = request.cookies.get(ACCOUNT_SESSION_COOKIE)?.value;
  if (action === "evaluation-clinical" || action === "evaluation-account") {
    if (process.env.EVALUATION_RUNTIME !== "true" || !accountToken) return NextResponse.json({ detail: "Evaluation access unavailable" }, { status: 403 });
    const identityUrl = accountApiUrl("v1/auth/me");
    if (!identityUrl) return NextResponse.json({ detail: "Evaluation account service unavailable" }, { status: 503 });
    const checked = await fetch(identityUrl, { headers: { Authorization: `Bearer ${accountToken}` }, cache: "no-store" });
    if (!checked.ok || !(await checked.json()).evaluation) return NextResponse.json({ detail: "Evaluation account required" }, { status: 403 });
    if (action === "evaluation-account") {
      if (existing) await fetch(hospitalApiUrl("v1/auth/logout"), { method: "POST", headers: { Authorization: `Bearer ${existing}` }, cache: "no-store" }).catch(() => undefined);
      const response = NextResponse.json({ destination: "/platform/accounts" });
      response.cookies.delete(SESSION_COOKIE);
      return response;
    }
    const password = process.env.EVALUATION_HOSPITAL_PASSWORD;
    if (!password) return NextResponse.json({ detail: "Evaluation clinical credentials unavailable" }, { status: 503 });
    const login = await fetch(hospitalApiUrl("v1/auth/login"), {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: "eval-admin", password }), cache: "no-store",
    });
    const result = await login.json().catch(() => ({}));
    if (!login.ok || !result.access_token) return NextResponse.json({ detail: "Evaluation clinical sign-in failed" }, { status: 503 });
    const response = NextResponse.json({ destination: "/app/icu" });
    response.cookies.set(SESSION_COOKIE, result.access_token, {
      httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "strict", path: "/",
      maxAge: Math.min(Number(result.expires_in_seconds) || 900, 3600),
    });
    return response;
  }
  if (action === "logout") {
    if (existing) await fetch(hospitalApiUrl("v1/auth/logout"), { method: "POST", headers: { Authorization: `Bearer ${existing}` }, cache: "no-store" }).catch(() => undefined);
    const accountLogout = accountApiUrl("v1/auth/logout");
    if (accountToken && accountLogout) await fetch(accountLogout, { method: "POST", headers: { Authorization: `Bearer ${accountToken}` }, cache: "no-store" }).catch(() => undefined);
    const response = NextResponse.json({ logged_out: true });
    response.cookies.delete(SESSION_COOKIE);
    response.cookies.delete(ACCOUNT_SESSION_COOKIE);
    return response;
  }
  if (!["login", "pin", "exchange"].includes(action)) return NextResponse.json({ detail: "Not found" }, { status: 404 });
  let token: string;
  let mustChange = false;
  let maxAge = 15 * 60;
  if (action === "exchange") {
    const body = await request.json().catch(() => null);
    token = typeof body?.token === "string" ? body.token.trim() : "";
    if (!token) return NextResponse.json({ detail: "Token required" }, { status: 422 });
  } else {
    const body = await request.json().catch(() => null);
    if (!body || typeof body.user_id !== "string") return NextResponse.json({ detail: "Invalid sign-in request" }, { status: 422 });
    if (action === "login" && body.user_id.includes("@")) {
      const loginUrl = accountApiUrl("v1/auth/login");
      const identityUrl = accountApiUrl("v1/auth/me");
      if (!loginUrl || !identityUrl) return NextResponse.json({ detail: "Organization account service is not configured" }, { status: 503 });
      const accountLogin = await fetch(loginUrl, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: body.user_id, password: body.password, totp_code: body.totp_code || null }), cache: "no-store",
      });
      const accountResult = await accountLogin.json().catch(() => ({}));
      if (!accountLogin.ok) return NextResponse.json({ detail: accountResult.detail || "Sign-in failed" }, { status: accountLogin.status });
      const accountIdentity = await fetch(identityUrl, { headers: { Authorization: `Bearer ${accountResult.access_token}` }, cache: "no-store" });
      if (!accountIdentity.ok) return NextResponse.json({ detail: "Identity validation failed" }, { status: 401 });
      const identity = await accountIdentity.json() as { workspaces?: Array<{ path: string }> };
      const destination = identity.workspaces?.[0]?.path;
      if (!destination || !["/portal", "/platform/accounts"].includes(destination)) return NextResponse.json({ detail: "No account workspace assigned" }, { status: 403 });
      const response = NextResponse.json({ signed_in: true, must_change_password: Boolean(accountResult.must_change_password), destination });
      response.cookies.set(ACCOUNT_SESSION_COOKIE, accountResult.access_token, {
        httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "strict", path: "/",
        maxAge: Math.min(Number(accountResult.expires_in_seconds) || 900, 8 * 3600),
      });
      response.cookies.delete(SESSION_COOKIE);
      return response;
    }
    const upstream = await fetch(hospitalApiUrl(action === "pin" ? "v1/auth/pin-login" : "v1/auth/login"), {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), cache: "no-store",
    });
    const result = await upstream.json().catch(() => ({}));
    if (!upstream.ok) return NextResponse.json({ detail: result.detail || "Sign-in failed" }, { status: upstream.status });
    token = result.access_token;
    mustChange = Boolean(result.must_change_password);
    maxAge = Math.min(Number(result.expires_in_seconds) || 15 * 60, 60 * 60);
  }
  const identity = await fetch(hospitalApiUrl("v1/auth/me"), { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" });
  if (!identity.ok) return NextResponse.json({ detail: "Identity validation failed" }, { status: 401 });
  const response = NextResponse.json({ signed_in: true, must_change_password: mustChange, destination: null });
  response.cookies.set(SESSION_COOKIE, token, { httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "strict", path: "/", maxAge });
  response.cookies.delete(ACCOUNT_SESSION_COOKIE);
  return response;
}
