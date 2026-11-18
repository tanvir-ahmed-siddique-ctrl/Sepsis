// @vitest-environment node
import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { POST as sessionPost } from "@/app/api/session/[action]/route";
import { GET as hospitalGet, POST as hospitalPost } from "@/app/api/hospital/[...path]/route";
import { GET as accountGet } from "@/app/api/account/[...path]/route";

afterEach(() => vi.unstubAllGlobals());

const sessionContext = (action: string) => ({ params: Promise.resolve({ action }) });
const hospitalContext = (path: string[]) => ({ params: Promise.resolve({ path }) });

describe("web session boundary", () => {
  it("keeps the hospital token in an HttpOnly cookie", async () => {
    const upstream = vi.fn().mockResolvedValueOnce(Response.json({ access_token: "private-token", expires_in_seconds: 900, must_change_password: false }))
      .mockResolvedValueOnce(Response.json({ user_id: "clinician", role: "clinician" }));
    vi.stubGlobal("fetch", upstream);
    const request = new NextRequest("http://localhost:3000/api/session/login", {
      method: "POST", headers: { Origin: "http://localhost:3000", "X-Auralis-Request": "1", "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: "clinician", password: "test-secret" }),
    });
    const response = await sessionPost(request, sessionContext("login"));
    expect(response.status).toBe(200);
    expect(response.headers.get("set-cookie")).toContain("HttpOnly");
    expect(response.headers.get("set-cookie")).toContain("SameSite=strict");
    expect(await response.json()).toEqual({ signed_in: true, must_change_password: false, destination: null });
  });

  it("rejects cross-origin session writes before contacting the hospital", async () => {
    const upstream = vi.fn();
    vi.stubGlobal("fetch", upstream);
    const request = new NextRequest("http://localhost:3000/api/session/login", {
      method: "POST", headers: { Origin: "https://other.example", "X-Auralis-Request": "1" }, body: "{}",
    });
    expect((await sessionPost(request, sessionContext("login"))).status).toBe(403);
    expect(upstream).not.toHaveBeenCalled();
  });

  it("accepts same-origin writes when nextUrl is the container bind but Host is public", async () => {
    const upstream = vi.fn()
      .mockResolvedValueOnce(Response.json({ access_token: "private-token", expires_in_seconds: 900, must_change_password: false }))
      .mockResolvedValueOnce(Response.json({ user_id: "clinician", role: "clinician" }));
    vi.stubGlobal("fetch", upstream);
    const request = new NextRequest("http://0.0.0.0:10000/api/session/login", {
      method: "POST",
      headers: {
        Origin: "https://predictrx-sentinel-demo.onrender.com",
        Host: "predictrx-sentinel-demo.onrender.com",
        "X-Forwarded-Host": "predictrx-sentinel-demo.onrender.com",
        "X-Auralis-Request": "1",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ user_id: "clinician", password: "test-secret" }),
    });
    expect((await sessionPost(request, sessionContext("login"))).status).toBe(200);
    expect(upstream).toHaveBeenCalled();
  });

  it("requires a cookie and rejects cross-origin clinical writes", async () => {
    const upstream = vi.fn();
    vi.stubGlobal("fetch", upstream);
    const anonymous = new NextRequest("http://localhost:3000/api/hospital/v1/units");
    expect((await hospitalGet(anonymous, hospitalContext(["v1", "units"]))).status).toBe(401);
    const crossOrigin = new NextRequest("http://localhost:3000/api/hospital/v1/care/units", {
      method: "POST", headers: { Cookie: "auralis_session=private-token", Origin: "https://other.example", "X-Auralis-Request": "1" }, body: "{}",
    });
    expect((await hospitalPost(crossOrigin, hospitalContext(["v1", "care", "units"]))).status).toBe(403);
    expect(upstream).not.toHaveBeenCalled();
  });

  it("forwards an authenticated read with a server-held bearer token", async () => {
    const upstream = vi.fn().mockResolvedValue(Response.json({ units: [] }));
    vi.stubGlobal("fetch", upstream);
    const request = new NextRequest("http://localhost:3000/api/hospital/v1/care/units", {
      headers: { Cookie: "auralis_session=private-token" },
    });
    const response = await hospitalGet(request, hospitalContext(["v1", "care", "units"]));
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ units: [] });
    expect(new Headers(upstream.mock.calls[0][1].headers).get("Authorization")).toBe("Bearer private-token");
  });

  it("routes an organization identity to a separate account authority", async () => {
    const previous = process.env.ACCOUNT_API_INTERNAL_URL;
    process.env.ACCOUNT_API_INTERNAL_URL = "http://accounts.internal:8101";
    try {
      const upstream = vi.fn()
        .mockResolvedValueOnce(Response.json({ access_token: "account-token", expires_in_seconds: 3600, must_change_password: false }))
        .mockResolvedValueOnce(Response.json({ workspaces: [{ id: "customer", path: "/portal" }] }));
      vi.stubGlobal("fetch", upstream);
      const request = new NextRequest("http://localhost:3000/api/session/login", {
        method: "POST", headers: { Origin: "http://localhost:3000", "X-Auralis-Request": "1", "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: "admin@hospital.test", password: "test-secret" }),
      });
      const response = await sessionPost(request, sessionContext("login"));
      expect(response.status).toBe(200);
      expect(response.headers.get("set-cookie")).toContain("auralis_account_session");
      expect(await response.json()).toEqual({ signed_in: true, must_change_password: false, destination: "/portal" });
      expect(upstream.mock.calls[0][0]).toBe("http://accounts.internal:8101/v1/auth/login");
    } finally {
      if (previous === undefined) delete process.env.ACCOUNT_API_INTERNAL_URL;
      else process.env.ACCOUNT_API_INTERNAL_URL = previous;
    }
  });

  it("rejects a missing account session before forwarding tenant data", async () => {
    const upstream = vi.fn();
    vi.stubGlobal("fetch", upstream);
    const request = new NextRequest("http://localhost:3000/api/account/v1/organizations");
    expect((await accountGet(request, hospitalContext(["v1", "organizations"]))).status).toBe(401);
    expect(upstream).not.toHaveBeenCalled();
  });

  it("allows clinical workspace exchange only inside the synthetic evaluator runtime", async () => {
    const runtime = process.env.EVALUATION_RUNTIME;
    const accountUrl = process.env.ACCOUNT_API_INTERNAL_URL;
    const password = process.env.EVALUATION_HOSPITAL_PASSWORD;
    const upstream = vi.fn();
    vi.stubGlobal("fetch", upstream);
    const request = new NextRequest("http://localhost:3000/api/session/evaluation-clinical", {
      method: "POST", headers: { Cookie: "auralis_account_session=account-token", Origin: "http://localhost:3000", "X-Auralis-Request": "1" }, body: "{}",
    });
    try {
      delete process.env.EVALUATION_RUNTIME;
      expect((await sessionPost(request, sessionContext("evaluation-clinical"))).status).toBe(403);
      expect(upstream).not.toHaveBeenCalled();
      process.env.EVALUATION_RUNTIME = "true";
      process.env.ACCOUNT_API_INTERNAL_URL = "http://accounts.internal:8101";
      process.env.EVALUATION_HOSPITAL_PASSWORD = "server-only-test-secret";
      upstream.mockResolvedValueOnce(Response.json({ evaluation: true }))
        .mockResolvedValueOnce(Response.json({ access_token: "hospital-token", expires_in_seconds: 900 }));
      const response = await sessionPost(request, sessionContext("evaluation-clinical"));
      expect(response.status).toBe(200);
      expect(response.headers.get("set-cookie")).toContain("auralis_session");
      expect(response.headers.get("set-cookie")).toContain("HttpOnly");
      expect(await response.json()).toEqual({ destination: "/app/icu" });
    } finally {
      if (runtime === undefined) delete process.env.EVALUATION_RUNTIME; else process.env.EVALUATION_RUNTIME = runtime;
      if (accountUrl === undefined) delete process.env.ACCOUNT_API_INTERNAL_URL; else process.env.ACCOUNT_API_INTERNAL_URL = accountUrl;
      if (password === undefined) delete process.env.EVALUATION_HOSPITAL_PASSWORD; else process.env.EVALUATION_HOSPITAL_PASSWORD = password;
    }
  });
});
