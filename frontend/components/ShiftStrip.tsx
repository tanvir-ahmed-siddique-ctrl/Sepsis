"use client";

import Link from "next/link";
import { api } from "@/lib/api";
import { usePoll } from "@/lib/usePoll";

type CurrentShift = {
  shift: { id: string; label: string; start: string; end: string } | null;
  shift_id: string | null;
  staff: { user_id: string; display_name: string; role: string }[];
  count: number;
};

export function ShiftStrip() {
  const { data } = usePoll(() => api<CurrentShift>("/v1/site/shift-roster/current"), 60000);
  if (!data) return null;
  const label = data.shift?.label ?? "Shift";
  const window = data.shift ? `${data.shift.start}–${data.shift.end}` : "";
  return (
    <div className="border-b border-ink/10 bg-mist/60">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-3 gap-y-1 px-4 py-1.5 text-xs sm:px-6">
        <span className="font-medium text-ink/70">
          Now: {label}
          {window ? ` (${window})` : ""}
        </span>
        {data.staff.length === 0 ? (
          <span className="text-ink/50">
            No roster for this shift —{" "}
            <Link href="/admin/shift-roster" className="text-accent underline">
              set who is on
            </Link>
          </span>
        ) : (
          <span className="text-ink/80">
            {data.staff.map((p) => p.display_name).join(" · ")}
          </span>
        )}
        <Link href="/admin/shift-roster" className="ml-auto text-accent underline">
          Edit roster
        </Link>
      </div>
    </div>
  );
}
