"use client";

import { useEffect, useMemo, useState } from "react";
import { ApiError, EmptyState, PageHeader, Panel, Pill, Stat } from "@/components/ui";
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
  const [unit, setUnit] = useState("");
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
        eyebrow={bn ? "ওয়ার্ড কেয়ার" : "Ward care"}
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

      <p role="status" className="flex items-start gap-2 rounded-lg border border-teal/25 bg-teal-soft/40 px-3.5 py-2.5 text-sm text-ink">
        <Icon name="info" size={16} className="mt-0.5 shrink-0 text-teal" />
        {bn
          ? "NEWS2 প্রকাশিত নিয়ম অনুযায়ী গণনা হয়; এটি ICU সেপসিস মডেলের স্কোর নয়।"
          : "NEWS2 is scored from published bedside rules. It does not feed the ICU sepsis model."}
      </p>

      {board.error && <ApiError error={board.error} />}

      {wards.length > 0 && !board.data && !board.error && (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3" aria-hidden="true">
          {Array.from({ length: 3 }).map((_, index) => (
            <div key={index} className="auralis-skeleton h-36 rounded-xl" />
          ))}
        </div>
      )}

      {!wards.length && (
        <EmptyState
          icon="building"
          title={bn ? "কোনো ওয়ার্ড নেই" : "No ward units yet"}
          body="Create a ward unit from the bedside charting workflow or API first."
        />
      )}

      {wards.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-3">
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

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {patients.map((patient) => {
          const news = patient.latest_news2;
          return (
            <Panel key={patient.encounter_key} title={`${patient.bed_id || "—"} · ${patient.display_name}`}>
              <div className="flex items-center justify-between gap-3">
                <span className="text-4xl font-semibold tabular-nums tracking-tight text-ink">{news?.score ?? "—"}</span>
                <div className="flex flex-wrap justify-end gap-1.5">
                  {news?.urgency && <Pill tone={URGENCY_TONE[news.urgency]}>{news.urgency}</Pill>}
                  {patient.observations_due && <Pill tone="warning">{bn ? "এখন মাপুন" : "due now"}</Pill>}
                </div>
              </div>
              {!news?.complete && (
                <p className="mt-3 text-sm text-risk-watch">
                  {bn ? "অনুপস্থিত" : "Missing"}: {news?.missing.join(", ") || patient.missing_required.join(", ")}
                </p>
              )}
              {news?.response && <p className="mt-3 text-sm leading-6 text-muted">{news.response}</p>}
              <p className="mt-3 text-xs text-muted">{news?.source || "No complete NEWS2 observation set yet."}</p>
            </Panel>
          );
        })}
      </div>
    </div>
  );
}
