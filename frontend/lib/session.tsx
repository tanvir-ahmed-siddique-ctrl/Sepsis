"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, announceSessionChange, SESSION_EVENT, type Me } from "@/lib/api";
import { accountApi } from "@/lib/account-api";

type AccountIdentity = { user_id: string; email: string; display_name: string; role: string; vendor: boolean; evaluation: boolean; must_change_password: boolean; organization_ids: string[]; workspaces: Array<{ id: string; path: string }> };

async function webSession(action: "login" | "pin" | "exchange" | "logout", body: unknown = {}) {
  const response = await fetch(`/api/session/${action}`, {
    method: "POST", credentials: "same-origin", cache: "no-store",
    headers: { "Content-Type": "application/json", "X-Auralis-Request": "1" }, body: JSON.stringify(body),
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = result?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((item) => item?.msg || String(item)).join("; ")
          : result?.message || `Sign-in failed (${response.status})`;
    throw new Error(message);
  }
  announceSessionChange();
  return result;
}

type SessionValue = {
  me: Me | null;
  account: AccountIdentity | null;
  error: Error | null;
  loading: boolean;
  isAdmin: boolean;
  isOperator: boolean;
  refresh: () => Promise<void>;
  signInLocal: (userId: string, password: string, totpCode?: string) => Promise<{ must_change_password: boolean; destination: string | null }>;
  signInPin: (userId: string, pin: string, totpCode?: string) => Promise<void>;
  signInWithToken: (token: string) => Promise<void>;
  signOut: () => void;
};

const SessionContext = createContext<SessionValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [account, setAccount] = useState<AccountIdentity | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    let hospitalError: Error | null = null;
    try {
      setMe(await api<Me>("/v1/auth/me"));
    } catch (cause) {
      setMe(null);
      hospitalError = cause instanceof Error ? cause : new Error(String(cause));
    }
    try {
      setAccount(await accountApi<AccountIdentity>("/v1/auth/me"));
      setError(null);
    } catch {
      setAccount(null);
      setError(hospitalError);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    window.sessionStorage.removeItem("predictrx-access-token");
    void refresh();
    const onChange = () => void refresh();
    window.addEventListener(SESSION_EVENT, onChange);
    const timer = window.setInterval(() => void refresh(), 30000);
    return () => {
      window.removeEventListener(SESSION_EVENT, onChange);
      window.clearInterval(timer);
    };
  }, [refresh]);

  const value = useMemo<SessionValue>(
    () => ({
      me,
      account,
      error,
      loading,
      isAdmin: Boolean(me?.roles.includes("admin")),
      isOperator: me?.role === "operator",
      refresh,
      signInLocal: async (userId, password, totpCode) => {
        const result = await webSession("login", { user_id: userId, password, totp_code: totpCode || null });
        return { must_change_password: Boolean(result.must_change_password), destination: result.destination || null };
      },
      signInPin: async (userId, pin, totpCode) => {
        await webSession("pin", { user_id: userId, pin, totp_code: totpCode || null });
      },
      signInWithToken: async (token) => {
        await webSession("exchange", { token: token.trim() });
      },
      signOut: () => {
        void webSession("logout").catch(() => { announceSessionChange(); });
      },
    }),
    [me, account, error, loading, refresh],
  );
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used inside SessionProvider");
  return value;
}
