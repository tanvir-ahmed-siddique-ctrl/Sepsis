"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

type PollOptions = {
  /** When false, skip fetching and leave the last good payload visible. */
  enabled?: boolean;
  /** Persist last good payload across remounts (same key) so boards don't flash empty. */
  cacheKey?: string;
};

type PollResult<T> = {
  data: T | null;
  error: Error | null;
  updatedAt: Date | null;
  refresh: () => Promise<void>;
};

const pollCache = new Map<string, { data: unknown; at: number }>();

export function usePoll<T>(
  loader: () => Promise<T>,
  intervalMs: number,
  dependencies: readonly unknown[] = [],
  options: PollOptions = {},
): PollResult<T> {
  const { enabled = true, cacheKey } = options;
  const loaderRef = useRef(loader);
  const mountedRef = useRef(false);
  const requestId = useRef(0);
  const cacheKeyRef = useRef(cacheKey);
  cacheKeyRef.current = cacheKey;

  const [data, setData] = useState<T | null>(() => {
    if (!cacheKey) return null;
    const hit = pollCache.get(cacheKey);
    return hit ? (hit.data as T) : null;
  });
  const [error, setError] = useState<Error | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(() => {
    if (!cacheKey) return null;
    const hit = pollCache.get(cacheKey);
    return hit ? new Date(hit.at) : null;
  });
  loaderRef.current = loader;

  const dependencyKey = useMemo(() => JSON.stringify(dependencies), [dependencies]);

  const refresh = useCallback(async () => {
    if (!enabled) return;
    const currentRequest = ++requestId.current;
    try {
      const next = await loaderRef.current();
      if (mountedRef.current && currentRequest === requestId.current) {
        setData(next);
        setError(null);
        const at = Date.now();
        setUpdatedAt(new Date(at));
        if (cacheKeyRef.current) {
          // Do not sticky-cache empty clinical boards. A transient Main ICU
          // rebuild (or timed-out follow-up) previously froze chart/NEWS2/handoff
          // on "0 beds" / endless skeletons.
          const empty =
            next &&
            typeof next === "object" &&
            (("encounters" in next && Array.isArray((next as { encounters: unknown[] }).encounters) && (next as { encounters: unknown[] }).encounters.length === 0) ||
              ("beds" in next && Array.isArray((next as { beds: unknown[] }).beds) && (next as { beds: unknown[] }).beds.length === 0) ||
              ("patients" in next && Array.isArray((next as { patients: unknown[] }).patients) && (next as { patients: unknown[] }).patients.length === 0));
          if (!empty) pollCache.set(cacheKeyRef.current, { data: next, at });
          else pollCache.delete(cacheKeyRef.current);
        }
      }
    } catch (cause) {
      if (mountedRef.current && currentRequest === requestId.current) {
        setError(cause instanceof Error ? cause : new Error(String(cause)));
      }
    }
  }, [enabled]);

  useEffect(() => {
    mountedRef.current = true;
    requestId.current += 1;
    if (!enabled) {
      return () => {
        mountedRef.current = false;
        requestId.current += 1;
      };
    }

    if (cacheKey) {
      const hit = pollCache.get(cacheKey);
      if (hit) {
        setData(hit.data as T);
        setUpdatedAt(new Date(hit.at));
        setError(null);
      } else {
        setData(null);
        setUpdatedAt(null);
        setError(null);
      }
    } else {
      // No cache: clear so a late response from a previous dependency cannot paint.
      setData(null);
      setUpdatedAt(null);
      setError(null);
    }

    void refresh();
    const timer = window.setInterval(() => void refresh(), intervalMs);
    return () => {
      mountedRef.current = false;
      requestId.current += 1;
      window.clearInterval(timer);
    };
  }, [dependencyKey, intervalMs, refresh, enabled, cacheKey]);

  return { data, error, updatedAt, refresh };
}
