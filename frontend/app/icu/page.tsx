"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { RiskBadge, TrustBadge } from "@/components/RiskBadge";
import { ReplayControls } from "@/components/ReplayControls";
import { ApiError, BAND_COLOR, Pill, SiteModeBanner, Sparkline, Stat } from "@/components/ui";
import { api, API_UNIT, DEMO_UNIT, pct, type PatientOverview, type UnitOverview } from "@/lib/api";
import { useLocale } from "@/lib/locale";
import { minutesLabel } from "@/lib/pilot";
import { useSession } from "@/lib/session";
import { usePoll } from "@/lib/usePoll";

const UNIT_KEY = "predictrx-unit-v2";

export default function OverviewPage() {
  const { t } = useLocale();
  const { me, isOperator } = useSession();
  const router = useRouter();
  const [unit, setUnit] = useState<string | null>(null);
  useEffect(() => {
    if (isOperator) router.replace("/operations");
  }, [isOperator, router]);
  const units = usePoll(() => api<{ units: string[]; default_unit: string | null }>("/v1/units"), 15000);

  useEffect(() => {
    if (unit || !units.data) return;
    const stored = window.localStorage.getItem(UNIT_KEY);
    const available = units.data.units;
    setUnit(stored && available.includes(stored) ? stored : available.includes(API_UNIT) ? API_UNIT : units.data.default_unit ?? DEMO_UNIT);
  }, [unit, units.data]);

  const { data, error, updatedAt, refresh } = usePoll(
    () => (unit ? api<UnitOverview>(`/v1/units/${encodeURIComponent(unit)}/overview`) : Promise.resolve(null)),
    3000,
    [unit],
  );

  function chooseUnit(next: string) {
    window.localStorage.setItem(UNIT_KEY, next);
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

  return (
    <div className="space-y-5">
      <section className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl text-ink">ICU command centre</h1>
          <p className="mt-1 text-sm text-ink/65">
            {data?.site_mode === "demo"
              ? `${data?.patients.length ?? 0} ${me?.evaluation_runtime ? "synthetic evaluation encounters" : "de-identified replay/scored encounters"} in this unit · model ${data?.model_version ?? "…"}`
              : `Hospital-local live feed · model ${data?.model_version ?? "…"}`}
          </p>
          <p className="mt-2 font-mono text-xs text-ink/55" aria-live="polite">
            {error ? "Feed refresh failed · showing last received state" : updatedAt ? `View refreshed ${updatedAt.toLocaleTimeString()} · polling every 3 seconds` : "Connecting to local feed…"}
          </p>
          {units.data && units.data.units.length > 1 && (
            <label className="mt-2 flex items-center gap-2 text-sm">
              <span className="text-ink/55">Unit</span>
              <select
                value={unit ?? ""}
                onChange={(event) => chooseUnit(event.target.value)}
                className="border border-ink/20 bg-white px-2 py-1"
              >
                {units.data.units.map((value) => (
                  <option key={value} value={value}>{value}</option>
                ))}
              </select>
            </label>
          )}
        </div>
        {data && (
          <div className="flex flex-wrap gap-3 text-sm">
            <Stat label="Alert" value={data.high_risk_count} color="text-risk-high" />
            <Stat label="Watch" value={data.watch_count} color="text-risk-watch" />
            <Stat label="Verify" value={data.verify_count} color="text-accent" />
            <Stat label="Abstain" value={data.abstain_count} color="text-ink/70" />
            <Stat label="Open alerts" value={data.open_alerts} />
            <Stat label="Past SLA" value={data.overdue_reviews} color={data.overdue_reviews ? "text-risk-high" : "text-ink"} />
          </div>
        )}
      </section>

      {data && (
        <SiteModeBanner
          mode={data.site_mode}
          detail={data.blinded_encounters > 0 ? `${data.blinded_encounters} live-feed encounter(s) hidden from bedside view.` : undefined}
        />
      )}
      {data?.site_mode === "demo" && unit === DEMO_UNIT && <ReplayControls onChange={refresh} />}
      {(error || units.error) && <ApiError error={(error ?? units.error) as Error} />}

      {data && data.patients.length === 0 && (
        <p className="border border-ink/10 bg-white/70 px-4 py-6 text-sm text-ink/60">
          {data.bedside_blinded
            ? "Silent pilot: live-feed scores are blinded to bedside staff by design."
            : "No scored encounters in this unit yet."}
        </p>
      )}

      {data && data.patients.length > 0 && (
        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {data.patients.map((p) => (
            <article
              key={p.patient_id}
              className={`border bg-white/85 p-4 ${p.review_overdue ? "border-risk-high" : p.unresolved_alerts ? "border-risk-high/50" : "border-ink/10"}`}
            >
              <Link href={`/patient/${encodeURIComponent(p.patient_id)}`} className="block hover:text-accent">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-medium">{p.display_name}</p>
                    <p className="text-xs text-ink/55">
                      {p.age ?? "—"} y · {p.sex ?? "—"} · ICU hour {p.hour} ·{" "}
                      {p.source_mode === "api" ? (data.site_mode === "demo" ? "generated feed" : "hospital connector") : me?.evaluation_runtime ? "synthetic evaluation replay" : "de-identified PhysioNet replay"}
                    </p>
                  </div>
                  <RiskBadge band={p.risk_band} />
                </div>
                <div className="mt-3 flex items-end justify-between gap-3">
                  <div>
                    <p className="text-xs text-ink/50">{t.scoreLabel}</p>
                    <p className="text-2xl font-semibold tabular-nums" style={{ color: BAND_COLOR[p.risk_band] }}>
                      {pct(p.probability)}
                      {p.uncertainty != null && p.probability != null && (
                        <span className="ml-1 text-xs font-normal text-ink/45">±{pct(p.uncertainty)}</span>
                      )}
                    </p>
                  </div>
                  <div className="w-28">
                    <Sparkline values={p.trend} color={BAND_COLOR[p.risk_band]} />
                  </div>
                </div>
              </Link>
              <div className="mt-3 flex flex-wrap items-center gap-1.5">
                <TrustBadge state={p.trust_state} />
                {p.unresolved_alerts > 0 && (
                  <Pill tone={p.review_overdue ? "danger" : "warning"}>
                    {p.review_overdue ? "Review overdue" : "Open alert"}
                    {p.oldest_open_alert_minutes != null ? ` · ${minutesLabel(p.oldest_open_alert_minutes)}` : ""}
                  </Pill>
                )}
                {p.missing_required_signals.map((signal) => (
                  <Pill key={signal} tone="warning">{signal} missing/stale</Pill>
                ))}
              </div>
              {p.open_alert_id && me && (me.role === "clinician" || me.role === "admin") && (
                <div className="mt-2 flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="border border-accent bg-accent px-2 py-1 text-xs text-white"
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
                    className="border border-ink/20 px-2 py-1 text-xs"
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
              <div className="mt-3 flex items-center justify-between text-xs text-ink/55">
                <span>
                  Vitals age {p.data_freshness_minutes == null ? "—" : `${p.data_freshness_minutes} min`} · owner{" "}
                  <strong className="font-medium text-ink/75">{p.owner ?? "unassigned"}</strong>
                </span>
                {me && (
                  <button
                    type="button"
                    onClick={() => void toggleOwnership(p)}
                    className="border border-ink/20 px-2 py-0.5 text-ink/70 hover:text-ink"
                  >
                    {p.owner === me.user_id ? "Release" : p.owner ? "Take over" : "Claim"}
                  </button>
                )}
              </div>
              {p.scored_at && <p className="mt-2 text-xs text-ink/50">Model processed {new Date(p.scored_at).toLocaleTimeString()}</p>}
            </article>
          ))}
        </section>
      )}
      {data && (
        <p className="text-xs text-ink/50">
          Thresholds set on validation patients: Watch ≥ {pct(data.thresholds.watch, 1)} · High risk ≥{" "}
          {pct(data.thresholds.high_risk, 1)} · review SLA {data.review_sla_minutes} min.
        </p>
      )}
    </div>
  );
}
