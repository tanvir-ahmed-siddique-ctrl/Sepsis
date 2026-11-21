"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, useSyncExternalStore } from "react";
import { RiskBadge, TrustBadge } from "@/components/RiskBadge";
import { ReplayControls } from "@/components/ReplayControls";
import { ApiError, BAND_COLOR, EmptyState, PageHeader, Pill, Sparkline, Stat } from "@/components/ui";
import { Icon } from "@/components/ui/Icon";
import { api, API_UNIT, DEMO_UNIT, pct, type PatientOverview, type UnitOverview } from "@/lib/api";
import { useLocale } from "@/lib/locale";
import { minutesLabel } from "@/lib/pilot";
import { useSession } from "@/lib/session";
import { usePoll } from "@/lib/usePoll";

const UNIT_KEY = "predictrx-unit-v3";

function readStoredUnit() {
  try {
    return window.localStorage.getItem(UNIT_KEY);
  } catch {
    return null;
  }
}

function useStoredUnitPreference() {
  return useSyncExternalStore(
    (onStoreChange) => {
      window.addEventListener("storage", onStoreChange);
      return () => window.removeEventListener("storage", onStoreChange);
    },
    readStoredUnit,
    () => null,
  );
}

export default function OverviewPage() {
  const { t } = useLocale();
  const { me, isOperator } = useSession();
  const router = useRouter();
  const storedUnit = useStoredUnitPreference();
  const [unit, setUnit] = useState<string | null>(storedUnit);
  useEffect(() => {
    if (isOperator) router.replace("/operations");
  }, [isOperator, router]);
  const units = usePoll(() => api<{ units: string[]; default_unit: string | null }>("/v1/units"), 15000);

  useEffect(() => {
    if (storedUnit && !unit) setUnit(storedUnit);
  }, [storedUnit, unit]);

  useEffect(() => {
    if (!units.data) return;
    const available = units.data.units;
    const fallback = units.data.default_unit ?? DEMO_UNIT;
    setUnit((current) => {
      // Keep an in-session choice. On first land, Main ICU (icu-demo-1) wins over a
      // stale Integration ICU preference so Advance/Reset and the primary board show.
      let next = current && available.includes(current) ? current : null;
      if (!next) {
        const stored = readStoredUnit();
        if (stored === API_UNIT && available.includes(DEMO_UNIT)) next = DEMO_UNIT;
        else if (stored && available.includes(stored)) next = stored;
        else if (available.includes(DEMO_UNIT)) next = DEMO_UNIT;
        else if (fallback && available.includes(fallback)) next = fallback;
        else next = available.includes(API_UNIT) ? API_UNIT : available[0] ?? DEMO_UNIT;
      }
      if (next) {
        try {
          window.localStorage.setItem(UNIT_KEY, next);
        } catch {
          /* private mode */
        }
      }
      return next;
    });
  }, [units.data]);

  const { data, error, updatedAt, refresh } = usePoll(
    () => api<UnitOverview>(`/v1/units/${encodeURIComponent(unit!)}/overview`),
    3000,
    [unit],
    { enabled: Boolean(unit), cacheKey: unit ? `unit-overview:${unit}` : undefined },
  );

  function chooseUnit(next: string) {
    try {
      window.localStorage.setItem(UNIT_KEY, next);
      window.dispatchEvent(new Event("storage"));
    } catch {
      /* ignore */
    }
    setUnit(next);
  }

  async function toggleOwnership(patient: PatientOverview) {
    const mine = patient.owner === me?.user_id;
    await api(`/v1/patients/${encodeURIComponent(patient.patient_id)}/ownership`, {
      method: mine ? "DELETE" : "POST",
      body: mine ? undefined : JSON.stringify({ shift_label: null }),
    });
    await refresh();
  }

  const description = `${data?.patients.length ?? "…"} ${t.icu.beds} · ${t.icu.model} ${data?.model_version ?? "…"} · ${t.icu.liveBoard}`;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={t.icu.eyebrow}
        title={t.icu.title}
        description={description}
        actions={
          units.data && units.data.units.length > 1 ? (
            <label className="flex max-w-full items-center gap-2 text-sm">
              <span className="shrink-0 text-xs font-medium text-muted">{t.icu.unit}</span>
              <select
                value={unit ?? ""}
                onChange={(event) => chooseUnit(event.target.value)}
                className="auralis-input !h-10 w-full max-w-[14rem] min-w-0 sm:w-auto sm:min-w-[10rem]"
              >
                {units.data.units.map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </label>
          ) : undefined
        }
      />

      <p className="auralis-help -mt-3" aria-live="polite">
        {error
          ? t.icu.refreshFailed
          : updatedAt
            ? `${t.icu.refreshed} ${updatedAt.toLocaleTimeString()} · ${t.icu.polling}`
            : unit
              ? t.icu.connecting
              : t.icu.selecting}
      </p>

      {data && (
        <div className="grid grid-cols-2 gap-2 sm:gap-3 md:grid-cols-3 xl:grid-cols-6">
          <Stat label="Alert" value={data.high_risk_count} color="text-risk-high" />
          <Stat label="Watch" value={data.watch_count} color="text-risk-watch" />
          <Stat label="Verify" value={data.verify_count} color="text-teal" />
          <Stat label="Abstain" value={data.abstain_count} color="text-muted" />
          <Stat label="Open alerts" value={data.open_alerts} />
          <Stat label="Past SLA" value={data.overdue_reviews} color={data.overdue_reviews ? "text-risk-high" : "text-ink"} />
        </div>
      )}

      {(unit === DEMO_UNIT || data?.patients.some((patient) => patient.source_mode === "replay")) && (
        <ReplayControls onChange={refresh} onRefresh={refresh} siteMode={data?.site_mode ?? null} />
      )}
      {unit === API_UNIT && (
        <p className="text-xs text-muted">
          Integration ICU is for connector drills. Switch unit to Main ICU ({DEMO_UNIT}) for the primary board and
          timeline controls.
        </p>
      )}
      {(error || units.error) && <ApiError error={(error ?? units.error) as Error} />}

      {!data && !error && (
        <div className="space-y-3">
          <p className="text-sm text-muted">{t.icu.connecting}</p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" aria-hidden="true">
            {Array.from({ length: 6 }).map((_, index) => (
              <div key={index} className="auralis-skeleton h-40 rounded-xl" />
            ))}
          </div>
        </div>
      )}

      {data && data.patients.length === 0 && (
        <EmptyState
          icon="grid"
          title={data.bedside_blinded ? "Scores blinded for bedside staff" : "No scored encounters"}
          body={
            data.bedside_blinded
              ? "Silent pilot: live-feed scores are blinded to bedside staff by design."
              : "No scored encounters in this unit yet."
          }
        />
      )}

      {data && data.patients.length > 0 && (
        <section className="grid gap-2.5 sm:grid-cols-2 sm:gap-3 lg:grid-cols-3">
          {data.patients.map((p) => (
            <article
              key={p.patient_id}
              className={`min-w-0 rounded-xl border bg-white p-3.5 shadow-soft sm:p-4 ${
                p.review_overdue
                  ? "border-risk-high"
                  : p.unresolved_alerts
                    ? "border-risk-high/40"
                    : "border-border"
              }`}
            >
              <Link href={`/patient/${encodeURIComponent(p.patient_id)}`} className="block group">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate font-semibold text-ink transition-colors group-hover:text-teal">{p.display_name}</p>
                    <p className="mt-0.5 text-xs leading-snug text-muted">
                      {p.age ?? "—"} y · {p.sex ?? "—"} · ICU hour {p.hour} ·{" "}
                      {p.source_mode === "api" ? "hospital connector" : "scored encounter"}
                    </p>
                  </div>
                  <span className="shrink-0">
                    <RiskBadge band={p.risk_band} />
                  </span>
                </div>
                <div className="mt-3 flex items-end justify-between gap-2 sm:gap-3">
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-muted">{t.scoreLabel}</p>
                    <p className="text-xl font-semibold tabular-nums tracking-tight sm:text-2xl" style={{ color: BAND_COLOR[p.risk_band] }}>
                      {pct(p.probability)}
                      {p.uncertainty != null && p.probability != null && (
                        <span className="ml-1 text-xs font-normal text-muted">±{pct(p.uncertainty)}</span>
                      )}
                    </p>
                  </div>
                  <div className="w-24 shrink-0 sm:w-28">
                    <Sparkline values={p.trend} color={BAND_COLOR[p.risk_band]} />
                  </div>
                </div>
              </Link>
              <div className="mt-3 flex flex-wrap items-center gap-1.5">
                <TrustBadge state={(p.open_alert_trust_state || p.trust_state) as typeof p.trust_state} />
                {p.unresolved_alerts > 0 && (
                  <Pill tone={p.review_overdue ? "danger" : "warning"}>
                    {(() => {
                      const openMin = p.oldest_open_alert_minutes;
                      const sla = p.review_sla_minutes ?? data.review_sla_minutes ?? 15;
                      if (openMin == null) return "Open alert";
                      if (p.review_overdue) return `Overdue by ${Math.max(0, Math.round(openMin - sla))} min`;
                      return `Open ${Math.round(openMin)} of ${sla} min`;
                    })()}
                  </Pill>
                )}
                {p.open_alert_hour != null && p.open_alert_hour !== p.hour && (
                  <Pill>Alert @ hour {p.open_alert_hour}</Pill>
                )}
                {p.missing_required_signals.map((signal) => (
                  <Pill key={signal} tone="warning">
                    {signal} missing/stale
                  </Pill>
                ))}
              </div>
              {p.open_alert_id && me && (me.role === "clinician" || me.role === "admin") && (
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="auralis-btn-primary auralis-btn-sm"
                    onClick={() =>
                      void api(`/v1/alerts/${p.open_alert_id}/acknowledge`, {
                        method: "POST",
                        body: JSON.stringify({ action: "acknowledged", reason: "Seen from ICU board" }),
                      }).then(() => refresh())
                    }
                  >
                    Seen
                  </button>
                  <button
                    type="button"
                    className="auralis-btn-secondary auralis-btn-sm"
                    onClick={() =>
                      void api(`/v1/alerts/${p.open_alert_id}/acknowledge`, {
                        method: "POST",
                        body: JSON.stringify({
                          action: "snoozed",
                          reason: "Quiet 1h — treating at bedside",
                          quiet_minutes: 60,
                        }),
                      }).then(() => refresh())
                    }
                  >
                    Quiet 1h
                  </button>
                </div>
              )}
              <div className="mt-3 flex items-center justify-between gap-2 border-t border-border pt-3 text-xs text-muted">
                <span className="min-w-0 truncate">
                  Vitals age {p.data_freshness_minutes == null ? "—" : `${p.data_freshness_minutes} min`} · owner{" "}
                  <strong className="font-medium text-ink">{p.owner ?? "unassigned"}</strong>
                </span>
                {me && (
                  <button type="button" onClick={() => void toggleOwnership(p)} className="auralis-btn-ghost auralis-btn-sm shrink-0">
                    {p.owner === me.user_id ? "Release" : p.owner ? "Take over" : "Claim"}
                  </button>
                )}
              </div>
              {p.scored_at && (
                <p className="mt-2 flex items-center gap-1.5 text-xs text-muted">
                  <Icon name="clock" size={12} />
                  Model processed {new Date(p.scored_at).toLocaleTimeString()}
                </p>
              )}
            </article>
          ))}
        </section>
      )}
      {data && (
        <p className="auralis-help">
          Thresholds set on validation patients: Watch ≥ {pct(data.thresholds.watch, 1)} · High risk ≥{" "}
          {pct(data.thresholds.high_risk, 1)} · review SLA {data.review_sla_minutes} min.
        </p>
      )}
    </div>
  );
}
