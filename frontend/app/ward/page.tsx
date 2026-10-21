"use client";

import { useEffect, useMemo, useState } from "react";
import { ApiError, Panel, Pill, Stat } from "@/components/ui";
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
  useEffect(() => { if (!unit && wards.length) setUnit(wards[0].unit_id); }, [unit, wards]);
  const board = usePoll(
    () => unit ? api<{ patients: CensusEncounter[]; note: string }>(`/v1/care/wards/${encodeURIComponent(unit)}/news2`) : Promise.resolve(null),
    10000,
    [unit],
  );
  const patients = board.data?.patients ?? [];
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl">{bn ? "ওয়ার্ড NEWS2 বোর্ড" : "Ward NEWS2 board"}</h1>
          <p className="mt-1 text-sm text-ink/60">{bn ? "প্রকাশিত NEWS2 নিয়ম; এটি প্রশিক্ষিত মডেল বা সেপসিস ডায়াগনসিস নয়।" : "Published NEWS2 rule; not a trained model or a sepsis diagnosis."}</p>
        </div>
        <select value={unit} onChange={(e) => setUnit(e.target.value)} className="border border-ink/20 bg-white px-2 py-1 text-sm">
          {wards.map((ward) => <option key={ward.unit_id} value={ward.unit_id}>{ward.label}</option>)}
        </select>
      </div>
      {board.error && <ApiError error={board.error} />}
      {!wards.length && <Panel><p className="text-sm">Create a ward unit from the bedside charting workflow or API first.</p></Panel>}
      <div className="flex gap-3">
        <Stat label={bn ? "রোগী" : "Patients"} value={patients.length} />
        <Stat label={bn ? "জরুরি" : "Urgent / emergency"} value={patients.filter((row) => ["urgent", "emergency"].includes(row.latest_news2?.urgency || "")).length} color="text-risk-high" />
        <Stat label={bn ? "পর্যবেক্ষণ বাকি" : "Observations due"} value={patients.filter((row) => row.observations_due).length} color="text-risk-watch" />
      </div>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {patients.map((patient) => {
          const news = patient.latest_news2;
          return (
            <Panel key={patient.encounter_key} title={`${patient.bed_id || "—"} · ${patient.display_name}`}>
              <div className="flex items-center justify-between">
                <span className="text-4xl font-semibold tabular-nums">{news?.score ?? "—"}</span>
                <div className="space-x-1">
                  {news?.urgency && <Pill tone={URGENCY_TONE[news.urgency]}>{news.urgency}</Pill>}
                  {patient.observations_due && <Pill tone="warning">{bn ? "এখন মাপুন" : "due now"}</Pill>}
                </div>
              </div>
              {!news?.complete && <p className="mt-2 text-sm text-risk-watch">{bn ? "অনুপস্থিত" : "Missing"}: {news?.missing.join(", ") || patient.missing_required.join(", ")}</p>}
              {news?.response && <p className="mt-2 text-sm text-ink/70">{news.response}</p>}
              <p className="mt-2 text-xs text-ink/45">{news?.source || "No complete NEWS2 observation set yet."}</p>
            </Panel>
          );
        })}
      </div>
    </div>
  );
}
