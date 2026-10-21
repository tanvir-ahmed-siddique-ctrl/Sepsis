"use client";

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { COPY, readLocale, writeLocale, type Locale } from "@/lib/copy";

type LocaleContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (typeof COPY)[Locale];
};

const LocaleContext = createContext<LocaleContextValue | null>(null);

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");
  useEffect(() => {
    setLocaleState(readLocale());
  }, []);
  const value = useMemo(
    () => ({
      locale,
      setLocale: (next: Locale) => {
        writeLocale(next);
        setLocaleState(next);
      },
      t: COPY[locale],
    }),
    [locale],
  );
  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale() {
  const value = useContext(LocaleContext);
  if (!value) throw new Error("useLocale must be used inside LocaleProvider");
  return value;
}
