"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { RiskBadge, TrustBadge } from "@/components/RiskBadge";
import { ApiError, Panel, Pill } from "@/components/ui";
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

const TREND_LABEL = { rising: "▲ rising", falling: "▼ falling", steady: "→ steady", unknown: "— no 6 h baseline" };

export default function HandoffPage() {
  const [unit, setUnit] = useState<string | null>(null);
  useEffect(() => setUnit(window.localStorage.getItem("predictrx-unit") ?? DEMO_UNIT), []);
  const { data, error } = usePoll(
    () => (unit ? api<Handoff>(`/v1/units/${encodeURIComponent(unit)}/handoff`) : Promise.resolve(null)),
    10000,
    [unit],
  );

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl">Shift handoff</h1>
          <p className="mt-1 text-sm text-ink/60">
            Unit {unit ?? "…"} · assembled from recorded scores, alerts, actions and clinician notes — no generated text.
          </p>
        </div>
        <button type="button" onClick={() => window.print()} className="border border-ink/20 px-3 py-1.5 text-sm">
          Print handoff
        </button>
      </div>
      {error && <ApiError error={error} />}
      {data && data.beds.length === 0 && <p className="text-sm text-ink/60">No visible beds for this unit.</p>}
      <div className="space-y-3">
        {data?.beds.map((bed) => (
          <Panel key={bed.patient_id} className={bed.open_alert?.overdue ? "border-risk-high" : ""}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <Link href={`/patient/${encodeURIComponent(bed.patient_id)}`} className="font-display text-xl hover:text-accent">
                  {bed.display_name}
                </Link>
                <p className="text-xs text-ink/55">
                  ICU hour {bed.hour} · {bed.source_mode === "api" ? "live feed" : "replay"} · owner{" "}
                  {bed.owner ? `${bed.owner.owner}${bed.owner.shift_label ? ` (${bed.owner.shift_label})` : ""}` : "unassigned"}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <RiskBadge band={bed.risk_band} />
                <TrustBadge state={bed.trust_state} />
                <span className="text-sm tabular-nums">
                  {pct(bed.probability)} <span className="text-ink/50">(6 h ago {pct(bed.probability_6h_ago)})</span>
                </span>
                <Pill tone={bed.trend === "rising" ? "warning" : "neutral"}>{TREND_LABEL[bed.trend]}</Pill>
              </div>
            </div>
            <div className="mt-3 grid gap-3 text-sm md:grid-cols-3">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-ink/50">Alert status</p>
                {bed.open_alert ? (
                  <p className={bed.open_alert.overdue ? "text-risk-high" : ""}>
                    Open {minutesLabel(bed.open_alert.minutes_open)}
                    {bed.open_alert.overdue ? ` — past ${data.review_sla_minutes} min SLA` : ""}
                  </p>
                ) : (
                  <p className="text-ink/60">No open alert</p>
                )}
                {bed.last_alert_action && (
                  <p className="text-xs text-ink/55">
                    Last action: {bed.last_alert_action.action} by {bed.last_alert_action.user_id}
                    {bed.last_alert_action.reason ? ` — ${bed.last_alert_action.reason}` : ""}
                  </p>
                )}
              </div>
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-ink/50">Data gaps & TrustGate</p>
                <p>{bed.data_gaps.length ? bed.data_gaps.join(" · ") : "Required vitals current"}</p>
                <p className="text-xs text-ink/55">{bed.trust_reasons.map(humanize).join(" · ")}</p>
              </div>
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-ink/50">Top score drivers</p>
                <ul className="list-disc pl-4">
                  {bed.top_factors.map((factor) => <li key={factor}>{factor}</li>)}
                </ul>
              </div>
            </div>
            {bed.notes.length > 0 && (
              <ul className="mt-3 space-y-1 border-t border-ink/5 pt-2 text-sm">
                {bed.notes.map((note) => (
                  <li key={note.note_id}>
                    <span className="text-xs text-ink/50">{new Date(note.recorded_at).toLocaleString()} · {note.user_id}:</span>{" "}
                    {note.note}
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        ))}
      </div>
      {data && <p className="text-xs text-ink/50">{data.disclaimer}</p>}
    </div>
  );
}
