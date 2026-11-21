"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AlertActions } from "@/components/AlertActions";
import { RiskBadge, TrustBadge } from "@/components/RiskBadge";
import { ApiError, EmptyState, PageHeader, Panel, Pill } from "@/components/ui";
import { Icon } from "@/components/ui/Icon";
import { api, API_UNIT, DEMO_UNIT, pct, type Alert } from "@/lib/api";
import { reviewClock } from "@/lib/pilot";
import { useSession } from "@/lib/session";
import { usePoll } from "@/lib/usePoll";

const UNIT_KEY = "predictrx-unit-v3";

const UNIT_LABEL: Record<string, string> = {
  [DEMO_UNIT]: "Main ICU",
  [API_UNIT]: "Integration ICU (simulation)",
  "ward-demo-1": "General Ward",
};

export default function AlertsPage() {
  const { isAdmin } = useSession();
  const [message, setMessage] = useState<string | null>(null);
  const [showShadow, setShowShadow] = useState(false);
  const [unit, setUnit] = useState(DEMO_UNIT);
  const [units, setUnits] = useState<string[]>([DEMO_UNIT, API_UNIT]);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(UNIT_KEY);
      if (stored) setUnit(stored);
    } catch {
      /* private mode */
    }
    void api<{ units: string[] }>("/v1/units")
      .then((body) => {
        if (body.units?.length) setUnits(body.units);
      })
      .catch(() => undefined);
  }, []);

  function chooseUnit(next: string) {
    setUnit(next);
    try {
      window.localStorage.setItem(UNIT_KEY, next);
      window.dispatchEvent(new Event("storage"));
    } catch {
      /* ignore */
    }
  }

  const { data, error, refresh, updatedAt } = usePoll(
    () => api<{ alerts: Alert[] }>(`/v1/alerts?unit_id=${encodeURIComponent(unit)}`),
    3000,
    [unit],
    { cacheKey: `alerts:open:${unit}` },
  );
  const shadow = usePoll(
    () =>
      isAdmin && showShadow
        ? api<{ alerts: Alert[] }>(`/v1/alerts?status=silent&unit_id=${encodeURIComponent(unit)}`)
        : Promise.resolve({ alerts: [] as Alert[] }),
    10000,
    [isAdmin, showShadow, unit],
  );
  const open = (data?.alerts.filter((a) => a.status === "open") ?? []).sort((a, b) => Number(b.overdue) - Number(a.overdue));
  const closed = data?.alerts.filter((a) => a.status !== "open") ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Clinical review"
        title="Alert review"
        description="Same unit as the ICU board. Simulation ICU alerts live under Integration ICU — they are not Main ICU beds."
        actions={
          <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
            <label className="flex max-w-full items-center gap-2 text-sm">
              <span className="shrink-0 text-xs font-medium text-muted">Unit</span>
              <select value={unit} onChange={(event) => chooseUnit(event.target.value)} className="auralis-input !h-10 w-full max-w-[16rem] min-w-0 sm:w-auto">
                {units.map((value) => (
                  <option key={value} value={value}>
                    {UNIT_LABEL[value] ?? value}
                  </option>
                ))}
              </select>
            </label>
            <button type="button" className="auralis-btn-secondary auralis-btn-sm" onClick={() => void refresh()}>
              <Icon name="refresh" size={14} />
              Refresh alerts
            </button>
          </div>
        }
      />

      <p className="auralis-help -mt-3" aria-live="polite">
        {error
          ? "Alert refresh failed · showing last received state"
          : updatedAt
            ? `View refreshed ${updatedAt.toLocaleTimeString()} · ${UNIT_LABEL[unit] ?? unit} · polling every 3 seconds`
            : "Connecting to alert feed…"}
      </p>

      {error && <ApiError error={error} />}
      {message && (
        <p role="status" className="flex items-start gap-2 rounded-lg border border-teal/25 bg-teal-soft/40 px-3.5 py-2.5 text-sm text-ink shadow-soft">
          <Icon name="check" size={16} className="mt-0.5 shrink-0 text-teal" />
          {message}
        </p>
      )}

      {!data && !error && (
        <div className="space-y-3" aria-hidden="true">
          {Array.from({ length: 3 }).map((_, index) => (
            <div key={index} className="auralis-skeleton h-24 rounded-xl" />
          ))}
        </div>
      )}

      <Panel title={`Open (${open.length}) · ${UNIT_LABEL[unit] ?? unit}`}>
        {data && open.length === 0 && (
          <EmptyState
            icon="bell"
            title="No open alerts for this unit"
            body={
              unit === DEMO_UNIT
                ? "Main ICU has no open alerts right now. Switch unit to Integration ICU if you need Simulation ICU drill alerts."
                : "No open alerts right now for this unit."
            }
          />
        )}
        <ul className="space-y-3">
          {open.map((a) => {
            const clock = reviewClock(a);
            return (
              <li
                key={a.alert_id}
                className="grid gap-4 rounded-xl border border-[#D5DDE3] bg-white p-4 shadow-card lg:grid-cols-[minmax(0,1fr)_min(100%,20rem)]"
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <RiskBadge band={a.risk_band} />
                    <TrustBadge state={a.trustgate.state} />
                    <Pill tone={clock.tone}>{clock.label}</Pill>
                    <Pill>{UNIT_LABEL[a.unit_id || unit] ?? a.unit_id ?? unit}</Pill>
                    <Link
                      href={`/patient/${encodeURIComponent(a.patient_id)}`}
                      className="inline-flex items-center gap-1 font-semibold text-teal hover:text-teal-dark"
                    >
                      {a.display_name}
                      <Icon name="arrow-right" size={14} />
                    </Link>
                    <span className="text-xs text-muted">
                      ICU hour {a.hour} · {a.alert_id}
                    </span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-ink">{a.reason}</p>
                  <p className="mt-1 text-xs text-muted">
                    Alert stability {pct(a.trustgate.alert_stability, 0)} · data quality {a.data_quality} · model {a.model_version}
                  </p>
                  <p className="mt-3 text-xs font-medium uppercase tracking-wide text-muted">What drove the score</p>
                  <ul className="mt-1.5 space-y-1 text-sm">
                    {a.factors.slice(0, 4).map((f) => (
                      <li key={f.feature} className="flex items-start gap-2">
                        <span
                          className={`mt-0.5 inline-flex ${f.direction === "raises" ? "text-risk-high" : "text-risk-stable"}`}
                          aria-label={f.direction === "raises" ? "Raises risk" : "Lowers risk"}
                        >
                          <Icon name={f.direction === "raises" ? "trend-up" : "trend-down"} size={14} />
                        </span>
                        <span>
                          {f.plain_language} <span className="text-xs text-muted">({f.organ_system})</span>
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
                <AlertActions
                  alertId={a.alert_id}
                  onDone={(m) => {
                    setMessage(m);
                    void refresh();
                  }}
                />
              </li>
            );
          })}
        </ul>
      </Panel>

      <Panel title={`Resolved (${closed.length})`}>
        {closed.length === 0 ? (
          <p className="text-sm text-muted">No resolved alerts yet.</p>
        ) : (
          <div className="auralis-table-scroll">
            <table className="auralis-table min-w-[36rem]">
              <thead>
                <tr>
                  <th>Patient</th>
                  <th>Hour</th>
                  <th>Band</th>
                  <th>Status</th>
                  <th>Review time</th>
                  <th>By / note</th>
                </tr>
              </thead>
              <tbody>
                {closed.map((a) => {
                  const last = a.actions[a.actions.length - 1];
                  return (
                    <tr key={a.alert_id}>
                      <td className="font-medium text-ink">{a.display_name}</td>
                      <td className="tabular-nums">{a.hour}</td>
                      <td>
                        <RiskBadge band={a.risk_band} />
                      </td>
                      <td className="capitalize">{a.status}</td>
                      <td className="tabular-nums">{a.review_minutes == null ? "—" : `${a.review_minutes} min`}</td>
                      <td className="text-muted">
                        {last ? `${last.user_id}${last.reason ? ` — ${last.reason}` : ""}` : "auto-superseded by higher band"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      {isAdmin && (
        <Panel title="Shadow alerts (pilot team only)" description="Silent pilot and backfill records — not interruptive bedside alerts.">
          <label className="flex items-center gap-2 text-sm text-ink">
            <input
              type="checkbox"
              checked={showShadow}
              onChange={(event) => setShowShadow(event.target.checked)}
              className="rounded border-border text-teal focus:ring-teal"
            />
            Show alerts recorded silently during the pilot or from backfill
          </label>
          {shadow.error && <ApiError error={shadow.error} />}
          {showShadow && (
            <ul className="mt-4 space-y-0 divide-y divide-border border-t border-border">
              {(shadow.data?.alerts ?? []).length === 0 && (
                <li className="py-3 text-sm text-muted">No shadow alerts recorded.</li>
              )}
              {shadow.data?.alerts.map((a) => (
                <li key={a.alert_id} className="flex flex-wrap items-center gap-2 py-3 text-sm">
                  <RiskBadge band={a.risk_band} />
                  <span className="font-medium text-ink">{a.display_name}</span>
                  <span className="text-xs text-muted">
                    {a.unit_id} · {a.raised_at ? new Date(a.raised_at).toLocaleString() : `hour ${a.hour}`}
                  </span>
                  <span className="text-xs text-muted">{a.reason}</span>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      )}
    </div>
  );
}
