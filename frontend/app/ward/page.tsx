"use client";

import { useEffect, useMemo, useState } from "react";
import { ApiError, EmptyState, PageHeader, Pill, Stat } from "@/components/ui";
import { Icon } from "@/components/ui/Icon";
import { api, type CareUnit, type CensusEncounter } from "@/lib/api";
import { useLocale } from "@/lib/locale";
import { usePoll } from "@/lib/usePoll";

const URGENCY_TONE = {
  emergency: "danger",
  urgent: "danger",
  low: "warning",
  routine: "success",
} as const;

export default function WardPage() {
  const { locale } = useLocale();
  const bn = locale === "bn";
  const units = usePoll(() => api<{ units: CareUnit[] }>("/v1/care/units"), 30000);
  const wards = useMemo(() => units.data?.units.filter((unit) => unit.kind === "ward") ?? [], [units.data]);
  const [unit, setUnit] = useState("ward-demo-1");
  useEffect(() => {
    if (!unit && wards.length) setUnit(wards[0].unit_id);
  }, [unit, wards]);
  const board = usePoll(
    () => api<{ patients: CensusEncounter[]; note: string }>(`/v1/care/wards/${encodeURIComponent(unit)}/news2`),
    10000,
    [unit],
    { enabled: Boolean(unit), cacheKey: unit ? `ward-news2:${unit}` : undefined },
  );
  const patients = board.data?.patients ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title={bn ? "ওয়ার্ড NEWS2 বোর্ড" : "Ward NEWS2 board"}
        description={
          bn
            ? "প্রকাশিত NEWS2 নিয়ম; এটি প্রশিক্ষিত মডেল বা সেপসিস ডায়াগনসিস নয়।"
            : "Published NEWS2 rule; not a trained model or a sepsis diagnosis."
        }
        actions={
          wards.length > 0 ? (
            <label className="flex max-w-full items-center gap-2 text-sm">
              <span className="shrink-0 text-xs font-medium text-muted">{bn ? "ওয়ার্ড" : "Ward"}</span>
              <select value={unit} onChange={(e) => setUnit(e.target.value)} className="auralis-input !h-10 w-full max-w-[16rem] min-w-0 sm:w-auto sm:min-w-[12rem]">
                {wards.map((ward) => (
                  <option key={ward.unit_id} value={ward.unit_id}>
                    {ward.label}
                  </option>
                ))}
              </select>
            </label>
          ) : undefined
        }
      />

      <p role="status" className="flex items-start gap-2 text-sm text-muted">
        <Icon name="info" size={16} className="mt-0.5 shrink-0 text-teal" />
        {bn
          ? "NEWS2 প্রকাশিত নিয়ম অনুযায়ী গণনা হয়; এটি ICU সেপসিস মডেলের স্কোর নয়।"
          : "NEWS2 is scored from published bedside rules. It does not feed the ICU sepsis model."}
      </p>

      {(board.error || units.error) && <ApiError error={(board.error || units.error)!} />}

      {!board.data && !board.error && (
        <div className="space-y-3" aria-hidden="true">
          {Array.from({ length: 3 }).map((_, index) => (
            <div key={index} className="auralis-skeleton h-16 w-full" />
          ))}
        </div>
      )}

      {units.data && !wards.length && (
        <EmptyState
          icon="building"
          title={bn ? "কোনো ওয়ার্ড নেই" : "No ward units yet"}
          body="Create a ward unit from the bedside charting workflow or API first."
        />
      )}

      {wards.length > 0 && (
        <div className="flex flex-wrap gap-y-3 border-b border-border/70 pb-4">
          <Stat label={bn ? "রোগী" : "Patients"} value={patients.length} />
          <Stat
            label={bn ? "জরুরি" : "Urgent / emergency"}
            value={patients.filter((row) => ["urgent", "emergency"].includes(row.latest_news2?.urgency || "")).length}
            color="text-risk-high"
          />
          <Stat
            label={bn ? "পর্যবেক্ষণ বাকি" : "Observations due"}
            value={patients.filter((row) => row.observations_due).length}
            color="text-risk-watch"
          />
        </div>
      )}

      {wards.length > 0 && patients.length === 0 && !board.error && (
        <EmptyState
          icon="users"
          title={bn ? "কোনো রোগী নেই" : "No patients on this ward"}
          body={bn ? "এই ওয়ার্ডে এখনো কোনো ভর্তি নেই।" : "No admitted encounters are currently scored for NEWS2 on this ward."}
        />
      )}

      <ul className="divide-y divide-border/70">
        {patients.map((patient) => {
          const news = patient.latest_news2;
          return (
            <li key={patient.encounter_key} className="flex flex-wrap items-start justify-between gap-4 py-4 first:pt-1">
              <div className="min-w-0">
                <p className="font-semibold text-ink">
                  {patient.bed_id || "—"} · {patient.display_name}
                </p>
                {news?.response && <p className="mt-1.5 max-w-2xl text-sm leading-6 text-muted">{news.response}</p>}
                {!news?.complete && (
                  <p className="mt-1.5 text-sm text-risk-watch">
                    {bn ? "অনুপস্থিত" : "Missing"}: {news?.missing.join(", ") || patient.missing_required.join(", ")}
                  </p>
                )}
                <p className="mt-2 text-xs text-muted">{news?.source || "No complete NEWS2 observation set yet."}</p>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <span className="font-display text-3xl font-semibold tabular-nums tracking-tight text-ink">{news?.score ?? "—"}</span>
                <div className="flex flex-col items-end gap-1.5">
                  {news?.urgency && <Pill tone={URGENCY_TONE[news.urgency]}>{news.urgency}</Pill>}
                  {patient.observations_due && <Pill tone="warning">{bn ? "এখন মাপুন" : "due now"}</Pill>}
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
