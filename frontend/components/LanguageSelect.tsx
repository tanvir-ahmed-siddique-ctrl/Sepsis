"use client";

import { useLocale } from "@/lib/locale";
import type { Locale } from "@/lib/copy";

const OPTIONS: Array<{ value: Locale; short: string; full: string }> = [
  { value: "en", short: "EN", full: "English" },
  { value: "bn", short: "বাং", full: "বাংলা" },
];

/**
 * Compact locale control for signed-in hospital / vendor chrome only.
 * UI strings switch; clinical codes stay English.
 */
export function LanguageSelect({ className = "" }: { className?: string }) {
  const { locale, setLocale } = useLocale();
  const current = OPTIONS.find((option) => option.value === locale) ?? OPTIONS[0];

  return (
    <div className={`relative inline-flex ${className}`}>
      <label className="sr-only" htmlFor="auralis-language">
        Interface language
      </label>
      <select
        id="auralis-language"
        value={locale}
        aria-label={`Language: ${current.full}`}
        title={current.full}
        onChange={(event) => setLocale(event.target.value as Locale)}
        className="h-9 max-w-[4.5rem] cursor-pointer appearance-none rounded-full border border-border bg-white py-0 pl-3 pr-7 text-[11px] font-semibold tracking-wide text-ink outline-none transition-colors hover:border-[#C3CDD3] hover:shadow-soft focus:border-navy"
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%236B7280' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E\")",
          backgroundRepeat: "no-repeat",
          backgroundPosition: "right 0.35rem center",
        }}
      >
        {OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.short}
          </option>
        ))}
      </select>
    </div>
  );
}
