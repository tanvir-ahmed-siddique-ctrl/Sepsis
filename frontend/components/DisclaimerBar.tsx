"use client";

import { useLocale } from "@/lib/locale";

export function DisclaimerBar() {
  const { t } = useLocale();
  return (
    <div className="bg-ink px-4 py-2 text-center text-xs text-white sm:text-sm">
      {t.disclaimer}
    </div>
  );
}
