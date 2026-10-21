"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

type PollResult<T> = {
  data: T | null;
  error: Error | null;
  refresh: () => Promise<void>;
};

export function usePoll<T>(
  loader: () => Promise<T>,
  intervalMs: number,
  dependencies: readonly unknown[] = [],
): PollResult<T> {
  const loaderRef = useRef(loader);
  const mountedRef = useRef(false);
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  loaderRef.current = loader;

  const dependencyKey = useMemo(() => JSON.stringify(dependencies), [dependencies]);

  const refresh = useCallback(async () => {
    try {
      const next = await loaderRef.current();
      if (mountedRef.current) {
        setData(next);
        setError(null);
      }
    } catch (cause) {
      if (mountedRef.current) {
        setError(cause instanceof Error ? cause : new Error(String(cause)));
      }
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    void refresh();
    const timer = window.setInterval(() => void refresh(), intervalMs);
    return () => {
      mountedRef.current = false;
      window.clearInterval(timer);
    };
  }, [dependencyKey, intervalMs, refresh]);

  return { data, error, refresh };
}
