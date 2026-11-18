"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

type PollResult<T> = {
  data: T | null;
  error: Error | null;
  updatedAt: Date | null;
  refresh: () => Promise<void>;
};

export function usePoll<T>(
  loader: () => Promise<T>,
  intervalMs: number,
  dependencies: readonly unknown[] = [],
): PollResult<T> {
  const loaderRef = useRef(loader);
  const mountedRef = useRef(false);
  const requestId = useRef(0);
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  loaderRef.current = loader;

  const dependencyKey = useMemo(() => JSON.stringify(dependencies), [dependencies]);

  const refresh = useCallback(async () => {
    const currentRequest = ++requestId.current;
    try {
      const next = await loaderRef.current();
      if (mountedRef.current && currentRequest === requestId.current) {
        setData(next);
        setError(null);
        setUpdatedAt(new Date());
      }
    } catch (cause) {
      if (mountedRef.current && currentRequest === requestId.current) {
        setError(cause instanceof Error ? cause : new Error(String(cause)));
      }
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    requestId.current += 1;
    setData(null);
    setError(null);
    setUpdatedAt(null);
    void refresh();
    const timer = window.setInterval(() => void refresh(), intervalMs);
    return () => {
      mountedRef.current = false;
      requestId.current += 1;
      window.clearInterval(timer);
    };
  }, [dependencyKey, intervalMs, refresh]);

  return { data, error, updatedAt, refresh };
}
