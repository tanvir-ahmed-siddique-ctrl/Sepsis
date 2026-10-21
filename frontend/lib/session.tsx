"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, SESSION_EVENT, writeToken, type Me, type UserRole } from "@/lib/api";

type SessionValue = {
  me: Me | null;
  error: Error | null;
  loading: boolean;
  isAdmin: boolean;
  isOperator: boolean;
  refresh: () => Promise<void>;
  signInDemo: (userId: string, role: UserRole, units?: string) => Promise<void>;
  signInLocal: (userId: string, password: string, totpCode?: string) => Promise<{ must_change_password: boolean }>;
  signInPin: (userId: string, pin: string, totpCode?: string) => Promise<void>;
  signInWithToken: (token: string) => Promise<void>;
  signOut: () => void;
};

const SessionContext = createContext<SessionValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setMe(await api<Me>("/v1/auth/me"));
      setError(null);
    } catch (cause) {
      setMe(null);
      setError(cause instanceof Error ? cause : new Error(String(cause)));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
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
      error,
      loading,
      isAdmin: Boolean(me?.roles.includes("admin")),
      isOperator: me?.role === "operator",
      refresh,
      signInDemo: async (userId, role, units) => {
        const params = new URLSearchParams({ user_id: userId, role });
        if (units?.trim()) params.set("units", units.trim());
        const token = await api<{ access_token: string }>(`/v1/auth/demo-token?${params}`, { method: "POST" });
        writeToken(token.access_token);
      },
      signInLocal: async (userId, password, totpCode) => {
        const token = await api<{ access_token: string; must_change_password: boolean }>("/v1/auth/login", {
          method: "POST",
          body: JSON.stringify({ user_id: userId, password, totp_code: totpCode || null }),
        });
        writeToken(token.access_token);
        return { must_change_password: token.must_change_password };
      },
      signInPin: async (userId, pin, totpCode) => {
        const token = await api<{ access_token: string }>("/v1/auth/pin-login", {
          method: "POST",
          body: JSON.stringify({ user_id: userId, pin, totp_code: totpCode || null }),
        });
        writeToken(token.access_token);
      },
      signInWithToken: async (token) => {
        writeToken(token.trim());
      },
      signOut: () => {
        void api("/v1/auth/logout", { method: "POST" }).catch(() => undefined);
        writeToken(null);
      },
    }),
    [me, error, loading, refresh],
  );
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used inside SessionProvider");
  return value;
}
