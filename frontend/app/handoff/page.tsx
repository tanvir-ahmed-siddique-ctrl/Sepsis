"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { RiskBadge, TrustBadge } from "@/components/RiskBadge";
import { ApiError, EmptyState, PageHeader, Pill } from "@/components/ui";
import { Icon } from "@/components/ui/Icon";
import { api, DEMO_UNIT, pct, type RiskBand, type TrustState } from "@/lib/api";
import { humanize, minutesLabel } from "@/lib/pilot";
import { usePoll } from "@/lib/usePoll";

type HandoffBed = {
  patient_id: string;
  display_name: string;
  source_mode: string;
  owner: { owner: string; shift_label: string | null; claimed_at: string } | null;
  hour: number;
  risk_band: RiskBand;
  probability: number | null;
  probability_6h_ago: number | null;
  trend: "rising" | "falling" | "steady" | "unknown";
  trust_state: TrustState;
  trust_reasons: string[];
  open_alert: { alert_id: string; minutes_open: number | null; overdue: boolean; reason: string } | null;
  last_alert_action: { action: string; user_id: string; at: string; reason: string | null } | null;
  data_gaps: string[];
  top_factors: string[];
  notes: { note_id: string; user_id: string; note: string; recorded_at: string }[];
};

type Handoff = { unit_id: string; generated_at: string; review_sla_minutes: number; beds: HandoffBed[]; note: string; disclaimer: string };

const TREND_LABEL = { rising: "Rising", falling: "Falling", steady: "Steady", unknown: "No 6 h baseline" };
const TREND_ICON = { rising: "trend-up", falling: "trend-down", steady: "trend-flat", unknown: null } as const;

const UNIT_KEY = "predictrx-unit-v3";

export default function HandoffPage() {
  const [unit, setUnit] = useState<string>(DEMO_UNIT);
  useEffect(() => {
    try {
      setUnit(window.localStorage.getItem(UNIT_KEY) ?? DEMO_UNIT);
    } catch {
      setUnit(DEMO_UNIT);
    }
  }, []);
  const { data, error } = usePoll(
    () => api<Handoff>(`/v1/units/${encodeURIComponent(unit!)}/handoff`),
    10000,
    [unit],
    { enabled: Boolean(unit), cacheKey: unit ? `handoff:${unit}` : undefined },
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Shift handoff"
        description={`Unit ${unit ?? "…"} · assembled from recorded scores, alerts, actions and clinician notes — no generated text.`}
        actions={
          <button type="button" onClick={() => window.print()} className="auralis-btn-secondary auralis-btn-sm">
            <Icon name="doc" size={14} />
            Print handoff
          </button>
        }
      />

      {error && <ApiError error={error} />}

      {!data && !error && (
        <div className="space-y-3" aria-hidden="true">
          {Array.from({ length: 3 }).map((_, index) => (
            <div key={index} className="auralis-skeleton h-28 rounded-xl" />
          ))}
        </div>
      )}

      {data && data.beds.length === 0 && (
        <EmptyState icon="handoff" title="No visible beds" body="No visible beds for this unit." />
      )}

      <div className="overflow-hidden rounded-xl border border-[#D5DDE3] bg-white shadow-card">
        {data?.beds.map((bed, index) => (
          <article
            key={bed.patient_id}
            className={`px-4 py-4 sm:px-5 ${index > 0 ? "border-t border-border/80" : ""} ${
              bed.open_alert?.overdue ? "bg-risk-high/[0.03]" : ""
            }`}
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0 max-w-full">
                <Link
                  href={`/patient/${encodeURIComponent(bed.patient_id)}`}
                  className="inline-flex max-w-full items-center gap-1.5 text-base font-semibold text-ink hover:text-teal"
                >
                  <span className="truncate">{bed.display_name}</span>
                  <Icon name="arrow-right" size={14} className="shrink-0" />
                </Link>
                <p className="mt-0.5 break-words text-xs text-muted">
                  ICU hour {bed.hour} · {bed.source_mode === "api" ? "hospital connector" : "scored encounter"} · owner{" "}
                  {bed.owner ? `${bed.owner.owner}${bed.owner.shift_label ? ` (${bed.owner.shift_label})` : ""}` : "unassigned"}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <RiskBadge band={bed.risk_band} />
                <TrustBadge state={bed.trust_state} />
                <span className="text-sm tabular-nums text-ink">
                  {pct(bed.probability)}{" "}
                  <span className="text-muted">
                    <span className="hidden sm:inline">(6 h ago {pct(bed.probability_6h_ago)})</span>
                    <span className="sm:hidden">({pct(bed.probability_6h_ago)})</span>
                  </span>
                </span>
                <Pill tone={bed.trend === "rising" ? "warning" : "neutral"}>
                  {TREND_ICON[bed.trend] && <Icon name={TREND_ICON[bed.trend]!} size={12} />}
                  {TREND_LABEL[bed.trend]}
                </Pill>
              </div>
            </div>
            <div className="mt-3 grid gap-3 text-sm md:grid-cols-3">
              <div>
                <p className="text-xs font-medium text-muted">Alert</p>
                {bed.open_alert ? (
                  <p className={`mt-1 ${bed.open_alert.overdue ? "font-medium text-risk-high" : "text-ink"}`}>
                    Open {minutesLabel(bed.open_alert.minutes_open)}
                    {bed.open_alert.overdue ? ` — past ${data.review_sla_minutes} min SLA` : ""}
                  </p>
                ) : (
                  <p className="mt-1 text-muted">No open alert</p>
                )}
                {bed.last_alert_action && (
                  <p className="mt-1 text-xs text-muted">
                    Last: {bed.last_alert_action.action} by {bed.last_alert_action.user_id}
                    {bed.last_alert_action.reason ? ` — ${bed.last_alert_action.reason}` : ""}
                  </p>
                )}
              </div>
              <div>
                <p className="text-xs font-medium text-muted">Data & TrustGate</p>
                <p className="mt-1 text-ink">{bed.data_gaps.length ? bed.data_gaps.join(" · ") : "Required vitals current"}</p>
                <p className="mt-1 text-xs text-muted">{bed.trust_reasons.map(humanize).join(" · ")}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-muted">Top drivers</p>
                <ul className="mt-1 space-y-0.5 text-ink">
                  {bed.top_factors.map((factor) => (
                    <li key={factor} className="flex items-start gap-1.5">
                      <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-muted" aria-hidden="true" />
                      {factor}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            {bed.notes.length > 0 && (
              <ul className="mt-3 space-y-1.5 border-t border-border/70 pt-3 text-sm">
                {bed.notes.map((note) => (
                  <li key={note.note_id}>
                    <span className="text-xs text-muted">
                      {new Date(note.recorded_at).toLocaleString()} · {note.user_id}:
                    </span>{" "}
                    <span className="text-ink">{note.note}</span>
                  </li>
                ))}
              </ul>
            )}
          </article>
        ))}
      </div>
      {data && <p className="auralis-help">{data.disclaimer}</p>}
    </div>
  );
}
