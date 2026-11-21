"use client";

import { useLocale } from "@/lib/locale";
import type { Locale } from "@/lib/copy";

const OPTIONS: Array<{ value: Locale; label: string; native: string }> = [
  { value: "en", label: "English", native: "English" },
  { value: "bn", label: "Bangla", native: "বাংলা" },
];

/**
 * Visible chrome language control. Clinical codes / disease names stay English
 * in the product; this only switches UI strings (menus, help, empty states).
 */
export function LanguageSelect({ className = "" }: { className?: string }) {
  const { locale, setLocale } = useLocale();
  return (
    <label className={`inline-flex items-center gap-1.5 ${className}`}>
      <span className="hidden text-[11px] font-medium uppercase tracking-[0.08em] text-muted sm:inline">Language</span>
      <select
        className="h-9 min-w-[7.5rem] cursor-pointer rounded-lg border border-border bg-white px-2.5 text-sm font-medium text-ink shadow-soft outline-none transition-colors hover:border-teal focus:border-teal focus:ring-2 focus:ring-teal/20"
        value={locale}
        aria-label="Interface language"
        onChange={(event) => setLocale(event.target.value as Locale)}
      >
        {OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.native} · {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
