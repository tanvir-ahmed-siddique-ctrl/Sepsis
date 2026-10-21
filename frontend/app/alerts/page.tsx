"use client";

import Link from "next/link";
import { useState } from "react";
import { AlertActions } from "@/components/AlertActions";
import { RiskBadge, TrustBadge } from "@/components/RiskBadge";
import { ApiError, Panel, Pill } from "@/components/ui";
import { api, pct, type Alert } from "@/lib/api";
import { reviewClock } from "@/lib/pilot";
import { useSession } from "@/lib/session";
import { usePoll } from "@/lib/usePoll";

export default function AlertsPage() {
  const { isAdmin } = useSession();
  const [message, setMessage] = useState<string | null>(null);
  const [showShadow, setShowShadow] = useState(false);
  const { data, error, refresh } = usePoll(() => api<{ alerts: Alert[] }>("/v1/alerts"), 3000);
  const shadow = usePoll(
    () => (isAdmin && showShadow ? api<{ alerts: Alert[] }>("/v1/alerts?status=silent") : Promise.resolve({ alerts: [] as Alert[] })),
    10000,
    [isAdmin, showShadow],
  );
  const open = (data?.alerts.filter((a) => a.status === "open") ?? []).sort((a, b) => Number(b.overdue) - Number(a.overdue));
  const closed = data?.alerts.filter((a) => a.status !== "open") ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl">Alert review</h1>
        <p className="mt-1 text-sm text-ink/60">
          Every alert needs a human decision. The system never takes clinical action on its own. Overdue reviews are
          listed first.
        </p>
      </div>
      {error && <ApiError error={error} />}
      {message && <p className="border border-accent/30 bg-accent/5 px-3 py-2 text-sm text-accent">{message}</p>}

      <Panel title={`Open (${open.length})`}>
        {open.length === 0 && <p className="text-sm text-ink/60">No open alerts. Advance the replay on the ICU overview.</p>}
        <ul className="space-y-4">
          {open.map((a) => {
            const clock = reviewClock(a);
            return (
              <li key={a.alert_id} className="grid gap-4 border-b border-ink/5 pb-4 lg:grid-cols-[1fr_20rem]">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <RiskBadge band={a.risk_band} />
                    <TrustBadge state={a.trustgate.state} />
                    <Pill tone={clock.tone}>{clock.label}</Pill>
                    <Link href={`/patient/${encodeURIComponent(a.patient_id)}`} className="font-medium text-accent hover:underline">
                      {a.display_name}
                    </Link>
                    <span className="text-xs text-ink/45">ICU hour {a.hour} · {a.alert_id}</span>
                  </div>
                  <p className="mt-2 text-sm">{a.reason}</p>
                  <p className="mt-1 text-xs text-ink/50">
                    Alert stability {pct(a.trustgate.alert_stability, 0)} · data quality {a.data_quality} · model {a.model_version}
                  </p>
                  <p className="mt-3 text-xs font-medium uppercase tracking-wide text-ink/50">What drove the score</p>
                  <ul className="mt-1 space-y-0.5 text-sm">
                    {a.factors.slice(0, 4).map((f) => (
                      <li key={f.feature}>
                        <span className={f.direction === "raises" ? "text-risk-high" : "text-risk-stable"}>
                          {f.direction === "raises" ? "▲" : "▼"}
                        </span>{" "}
                        {f.plain_language} <span className="text-xs text-ink/45">({f.organ_system})</span>
                      </li>
                    ))}
                  </ul>
                </div>
                <AlertActions alertId={a.alert_id} onDone={(m) => { setMessage(m); refresh(); }} />
              </li>
            );
          })}
        </ul>
      </Panel>

      <Panel title={`Resolved (${closed.length})`}>
        <table className="w-full text-left text-sm">
          <thead className="text-xs text-ink/50">
            <tr>
              <th className="py-1 font-medium">Patient</th>
              <th className="py-1 font-medium">Hour</th>
              <th className="py-1 font-medium">Band</th>
              <th className="py-1 font-medium">Status</th>
              <th className="py-1 font-medium">Review time</th>
              <th className="py-1 font-medium">By / note</th>
            </tr>
          </thead>
          <tbody>
            {closed.map((a) => {
              const last = a.actions[a.actions.length - 1];
              return (
                <tr key={a.alert_id} className="border-t border-ink/5">
                  <td className="py-1.5">{a.display_name}</td>
                  <td className="py-1.5 tabular-nums">{a.hour}</td>
                  <td className="py-1.5"><RiskBadge band={a.risk_band} /></td>
                  <td className="py-1.5 capitalize">{a.status}</td>
                  <td className="py-1.5 tabular-nums">{a.review_minutes == null ? "—" : `${a.review_minutes} min`}</td>
                  <td className="py-1.5 text-ink/60">{last ? `${last.user_id}${last.reason ? ` — ${last.reason}` : ""}` : "auto-superseded by higher band"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Panel>

      {isAdmin && (
        <Panel title="Shadow alerts (pilot team only)">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={showShadow} onChange={(event) => setShowShadow(event.target.checked)} />
            Show alerts recorded silently during the pilot or from backfill
          </label>
          {shadow.error && <ApiError error={shadow.error} />}
          {showShadow && (
            <ul className="mt-3 space-y-1 text-sm">
              {(shadow.data?.alerts ?? []).length === 0 && <li className="text-ink/60">No shadow alerts recorded.</li>}
              {shadow.data?.alerts.map((a) => (
                <li key={a.alert_id} className="flex flex-wrap items-center gap-2 border-b border-ink/5 pb-1">
                  <RiskBadge band={a.risk_band} />
                  <span>{a.display_name}</span>
                  <span className="text-xs text-ink/50">{a.unit_id} · {a.raised_at ? new Date(a.raised_at).toLocaleString() : `hour ${a.hour}`}</span>
                  <span className="text-xs text-ink/50">{a.reason}</span>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      )}
    </div>
  );
}
