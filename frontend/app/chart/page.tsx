"use client";

import { useEffect, useMemo, useState } from "react";
import { BedQr } from "@/components/BedQr";
import { ApiError, EmptyState, PageHeader, Panel, Pill, Stat } from "@/components/ui";
import { Icon } from "@/components/ui/Icon";
import { api, DEMO_UNIT, type CareUnit, type CensusEncounter, type UnitOverview } from "@/lib/api";
import { useLocale } from "@/lib/locale";
import { enqueue, flushOutbox, outboxItems } from "@/lib/outbox";
import { usePoll } from "@/lib/usePoll";

type CensusPayload = { encounters: CensusEncounter[]; due_count: number; complete_count: number };

async function loadCensus(unitId: string): Promise<CensusPayload> {
  const census = await api<CensusPayload>(`/v1/care/census?unit_id=${encodeURIComponent(unitId)}`);
  if (census.encounters.length > 0) return census;
  // Main ICU beds live on the board overview; if census is briefly empty during a
  // timeline step, fall back so charting never looks like a vacant unit.
  try {
    const overview = await api<UnitOverview>(`/v1/units/${encodeURIComponent(unitId)}/overview`);
    const encounters: CensusEncounter[] = overview.patients.map((patient) => ({
      encounter_key: patient.patient_id,
      patient_id: patient.patient_id,
      display_name: patient.display_name,
      encounter_id: `replay-${patient.patient_id}`,
      unit_id: unitId,
      bed_id: patient.display_name?.startsWith("Bed ")
        ? patient.display_name.replace("Bed ", "BED-")
        : patient.patient_id,
      kind: "icu",
      status: "admitted",
      source_mode: patient.source_mode,
      hypercapnic_scale2: false,
      age: patient.age,
      sex: patient.sex,
      admitted_at: null,
      missing_required: patient.missing_required_signals || [],
      stale_required: [],
      complete_required: (patient.missing_required_signals || []).length === 0,
      latest_news2: null,
      latest_vitals: null,
      risk_band: patient.risk_band,
      observations_due: (patient.missing_required_signals || []).length > 0,
      chart_writable: true,
    }));
    return {
      encounters,
      due_count: encounters.filter((row) => row.observations_due).length,
      complete_count: encounters.filter((row) => row.complete_required).length,
    };
  } catch {
    return census;
  }
}

const EMPTY_VITALS = {
  heart_rate: "",
  spo2: "",
  temperature: "",
  temperature_unit: "C",
  systolic_bp: "",
  diastolic_bp: "",
  mean_arterial_pressure: "",
  respiration_rate: "",
  on_oxygen: "",
  avpu: "",
  lactate: "",
  wbc: "",
  creatinine: "",
  platelets: "",
};

export default function ChartPage() {
  const { locale } = useLocale();
  const bn = locale === "bn";
  const units = usePoll(() => api<{ units: CareUnit[] }>("/v1/care/units"), 30000);
  const [unit, setUnit] = useState("");
  const census = usePoll(() => loadCensus(unit), 10000, [unit], {
    enabled: Boolean(unit),
    cacheKey: unit ? `census:${unit}` : undefined,
  });
  const completeness = usePoll(
    () => api<{ completeness: number | null }>(`/v1/care/completeness?unit_id=${encodeURIComponent(unit)}&hours=8`),
    30000,
    [unit],
    { enabled: Boolean(unit), cacheKey: unit ? `completeness:${unit}` : undefined },
  );
  const [selected, setSelected] = useState<string | null>(null);
  const [vitals, setVitals] = useState(EMPTY_VITALS);
  const [outbox, setOutbox] = useState(0);
  const [message, setMessage] = useState<string | null>(null);
  const [transferUnit, setTransferUnit] = useState("");
  const [transferBed, setTransferBed] = useState("");
  const [admit, setAdmit] = useState({
    patient_id: "",
    encounter_id: "",
    display_name: "",
    bed_id: "",
    age: "",
    sex: "",
    hypercapnic_scale2: false,
  });

  useEffect(() => {
    if (unit || !units.data?.units.length) return;
    const preferred =
      units.data.units.find((row) => row.unit_id === DEMO_UNIT) ||
      units.data.units.find((row) => row.kind === "icu") ||
      units.data.units[0];
    setUnit(preferred.unit_id);
  }, [unit, units.data]);
  useEffect(() => {
    void outboxItems().then((items) => setOutbox(items.length));
  }, []);
  useEffect(() => {
    if (selected || !census.data) return;
    const requested = new URLSearchParams(window.location.search).get("bed");
    if (requested && census.data.encounters.some((row) => row.encounter_key === requested)) setSelected(requested);
  }, [census.data, selected]);

  const current = useMemo(
    () => census.data?.encounters.find((row) => row.encounter_key === selected) ?? null,
    [census.data, selected],
  );

  async function sync() {
    const result = await flushOutbox(async (item) => {
      await api(item.path, { method: "POST", body: JSON.stringify(item.body) });
    });
    setOutbox(result.pending);
    setMessage(`${result.sent} queued chart(s) synced; ${result.pending} pending.`);
    await census.refresh();
  }

  async function submitVitals() {
    if (!current) return;
    const numeric = [
      "heart_rate",
      "spo2",
      "temperature",
      "systolic_bp",
      "diastolic_bp",
      "mean_arterial_pressure",
      "respiration_rate",
      "lactate",
      "wbc",
      "creatinine",
      "platelets",
    ];
    const body: Record<string, unknown> = {
      measured_at: new Date().toISOString(),
      temperature_unit: vitals.temperature_unit,
      on_oxygen: vitals.on_oxygen === "" ? null : vitals.on_oxygen === "true",
      avpu: vitals.avpu || null,
    };
    for (const key of numeric) body[key] = vitals[key as keyof typeof vitals] === "" ? null : Number(vitals[key as keyof typeof vitals]);
    const path = `/v1/care/encounters/${encodeURIComponent(current.encounter_key)}/chart`;
    try {
      await api(path, { method: "POST", body: JSON.stringify(body) });
      setMessage(bn ? "পর্যবেক্ষণ সংরক্ষিত হয়েছে।" : "Observations saved.");
      setVitals(EMPTY_VITALS);
      await census.refresh();
    } catch (error) {
      if (!navigator.onLine || error instanceof TypeError) {
        await enqueue(path, body);
        setOutbox((count) => count + 1);
        setMessage(bn ? "অফলাইন: এই চার্টটি ডিভাইসে রাখা হয়েছে।" : "Offline: chart stored on this device for later sync.");
      } else {
        setMessage(error instanceof Error ? error.message : String(error));
      }
    }
  }

  async function admitPatient() {
    const admitted = await api<CensusEncounter>("/v1/care/encounters", {
      method: "POST",
      body: JSON.stringify({
        ...admit,
        unit_id: unit,
        bed_id: admit.bed_id || null,
        age: admit.age ? Number(admit.age) : null,
        sex: admit.sex || null,
      }),
    });
    setAdmit({ patient_id: "", encounter_id: "", display_name: "", bed_id: "", age: "", sex: "", hypercapnic_scale2: false });
    setSelected(admitted.encounter_key);
    setMessage(
      bn
        ? "রোগী ভর্তি হয়েছে। প্রথম পর্যবেক্ষণগুলো দিন; পর্যাপ্ত ICU data থাকলে এরপর score তৈরি হবে।"
        : "Patient admitted. Enter the first observations; the ICU score is calculated when enough valid data is available.",
    );
    await census.refresh();
  }

  async function transferOrDischarge(action: "transfer" | "discharge") {
    if (!current) return;
    if (action === "discharge" && !window.confirm(`Discharge ${current.display_name}?`)) return;
    await api(`/v1/care/encounters/${encodeURIComponent(current.encounter_key)}/${action}`, {
      method: "POST",
      body: action === "transfer" ? JSON.stringify({ unit_id: transferUnit, bed_id: transferBed.trim() || null }) : undefined,
    });
    setTransferUnit("");
    setTransferBed("");
    setSelected(null);
    await census.refresh();
  }

  async function changeNews2Scale() {
    if (!current || current.kind !== "ward") return;
    const enabled = !current.hypercapnic_scale2;
    const reason = window.prompt(
      enabled
        ? "Clinical reason confirming hypercapnic respiratory failure for NEWS2 SpO₂ Scale 2:"
        : "Clinical reason for returning this patient to NEWS2 SpO₂ Scale 1:",
    );
    if (!reason?.trim()) return;
    try {
      await api(`/v1/care/encounters/${encodeURIComponent(current.encounter_key)}/news2-scale`, {
        method: "POST",
        body: JSON.stringify({ hypercapnic_scale2: enabled, reason: reason.trim() }),
      });
      setMessage(`NEWS2 SpO₂ Scale ${enabled ? 2 : 1} selected for this encounter.`);
      await census.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={bn ? "বেডসাইড" : "Bedside"}
        title={bn ? "বেডসাইড চার্টিং" : "Bedside charting"}
        description={
          bn
            ? "আইসিইউ ও ওয়ার্ডের পর্যবেক্ষণ—অফলাইনে রাখে, সংযোগ এলে সিঙ্ক করে।"
            : "ICU and ward observations—queued offline and synced when the server returns."
        }
        actions={
          <label className="flex max-w-full items-center gap-2 text-sm">
            <span className="shrink-0 text-xs font-medium text-muted">{bn ? "ইউনিট" : "Unit"}</span>
            <select
              className="auralis-input !h-10 w-full max-w-[16rem] min-w-0 sm:w-auto sm:min-w-[12rem]"
              value={unit}
              onChange={(e) => {
                setUnit(e.target.value);
                setSelected(null);
              }}
            >
              {units.data?.units.map((row) => (
                <option key={row.unit_id} value={row.unit_id}>
                  {row.label} ({row.kind})
                </option>
              ))}
            </select>
          </label>
        }
      />

      {(units.error || census.error) && <ApiError error={(units.error || census.error)!} />}

      {!units.data && !units.error && (
        <p className="text-sm text-muted">{bn ? "কেয়ার ইউনিট লোড হচ্ছে…" : "Loading care units…"}</p>
      )}

      <div className="flex flex-wrap items-stretch gap-3">
        <Stat label={bn ? "ভর্তি" : "Admitted"} value={census.data?.encounters.length ?? 0} />
        <Stat
          label={bn ? "এখন মাপা দরকার" : "Observations due"}
          value={census.data?.due_count ?? 0}
          color={census.data?.due_count ? "text-risk-high" : "text-ink"}
        />
        <Stat label={bn ? "সম্পূর্ণ" : "Complete"} value={census.data?.complete_count ?? 0} />
        <Stat
          label={bn ? "৮ ঘণ্টার ডেটা" : "8 h completeness"}
          value={completeness.data?.completeness == null ? "—" : `${Math.round(completeness.data.completeness * 100)}%`}
        />
        <Stat label={bn ? "অফলাইন কিউ" : "Offline queue"} value={outbox} color={outbox ? "text-risk-watch" : "text-ink"} />
        {outbox > 0 && (
          <button type="button" className="auralis-btn-secondary auralis-btn-sm self-end" onClick={() => void sync()}>
            <Icon name="refresh" size={14} />
            {bn ? "এখন সিঙ্ক" : "Sync now"}
          </button>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr]">
        <Panel title={bn ? "বেড তালিকা" : "Bed list"}>
          {!census.data?.encounters.length ? (
            <EmptyState
              icon="bed"
              title={bn ? "কোনো বেড নেই" : "No beds in this unit"}
              body={bn ? "রোগী ভর্তি করে শুরু করুন।" : "Admit a patient below to start charting."}
            />
          ) : (
            <div className="space-y-2">
              {census.data.encounters.map((row) => (
                <button
                  type="button"
                  key={row.encounter_key}
                  onClick={() => setSelected(row.encounter_key)}
                  className={`flex w-full min-h-11 items-center justify-between gap-3 rounded-xl border p-3.5 text-left transition-colors ${
                    selected === row.encounter_key
                      ? "border-teal bg-teal-soft/50"
                      : "border-border bg-white hover:border-[#C3CDD3]"
                  }`}
                >
                  <span className="min-w-0">
                    <strong className="block truncate text-ink">
                      {row.bed_id || "—"} · {row.display_name}
                    </strong>
                    <span className="mt-0.5 block truncate font-mono text-xs text-muted">{row.encounter_id}</span>
                  </span>
                  <span className="flex shrink-0 flex-wrap justify-end gap-1.5">
                    {row.source_mode === "replay" && <Pill>{bn ? "বোর্ড সিঙ্ক" : "board sync"}</Pill>}
                    {row.risk_band && <Pill>{row.risk_band.replace(/_/g, " ")}</Pill>}
                    {row.observations_due && <Pill tone="warning">{bn ? "বাকি" : "due"}</Pill>}
                    {row.latest_news2?.score != null && <Pill>NEWS2 {row.latest_news2.score}</Pill>}
                  </span>
                </button>
              ))}
            </div>
          )}
        </Panel>

        <Panel title={current ? `${current.bed_id || ""} ${current.display_name}`.trim() : bn ? "একটি বেড বেছে নিন" : "Choose a bed"}>
          {!current && (
            <p className="text-sm text-muted">{bn ? "চার্ট করার জন্য বাম দিক থেকে একটি বেড নির্বাচন করুন।" : "Select a bed from the list to enter observations."}</p>
          )}
          {current && (
            <div className="grid gap-5 xl:grid-cols-[1fr_auto]">
              {current.latest_vitals && (
                <div className="xl:col-span-2 space-y-2 rounded-xl border border-border bg-muted-surface/40 p-3 text-sm">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                    {bn ? "সর্বশেষ vitals (বোর্ড সিঙ্ক)" : "Latest vitals (board sync)"}
                  </p>
                  <dl className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                    {Object.entries(current.latest_vitals).map(([code, value]) => (
                      <div key={code} className="rounded-lg border border-border bg-white px-3 py-2">
                        <dt className="text-[11px] font-semibold uppercase tracking-wide text-muted">{code}</dt>
                        <dd className="mt-0.5 font-mono text-sm text-ink">{value == null ? "—" : value}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
              )}
              <form
                className="grid min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-3"
                onSubmit={(event) => {
                  event.preventDefault();
                  void submitVitals();
                }}
              >
                {(
                  [
                    ["heart_rate", bn ? "হৃদস্পন্দন" : "Heart rate", "bpm"],
                    ["spo2", "SpO₂", "%"],
                    ["temperature", bn ? "তাপমাত্রা" : "Temperature", vitals.temperature_unit],
                    ["systolic_bp", "SBP", "mmHg"],
                    ["diastolic_bp", "DBP", "mmHg"],
                    ["mean_arterial_pressure", "MAP", "auto if blank"],
                    ["respiration_rate", bn ? "শ্বাসের হার" : "Respiratory rate", "/min"],
                    ["lactate", "Lactate", "mmol/L"],
                    ["wbc", "WBC", "10³/µL"],
                    ["creatinine", "Creatinine", "mg/dL"],
                    ["platelets", "Platelets", "10³/µL"],
                  ] as const
                ).map(([key, label, unitLabel]) => (
                  <label key={key} className="auralis-label">
                    {label}
                    <input
                      type="number"
                      step="any"
                      className="auralis-input mt-1"
                      value={vitals[key]}
                      onChange={(e) => setVitals({ ...vitals, [key]: e.target.value })}
                      placeholder={unitLabel}
                    />
                  </label>
                ))}
                <label className="auralis-label">
                  {bn ? "তাপমাত্রার একক" : "Temperature unit"}
                  <select
                    className="auralis-input mt-1"
                    value={vitals.temperature_unit}
                    onChange={(e) => setVitals({ ...vitals, temperature_unit: e.target.value })}
                  >
                    <option>C</option>
                    <option>F</option>
                  </select>
                </label>
                <label className="auralis-label">
                  {bn ? "অক্সিজেন" : "Supplemental oxygen"}
                  <select
                    className="auralis-input mt-1"
                    value={vitals.on_oxygen}
                    onChange={(e) => setVitals({ ...vitals, on_oxygen: e.target.value })}
                  >
                    <option value="">—</option>
                    <option value="false">No</option>
                    <option value="true">Yes</option>
                  </select>
                </label>
                <label className="auralis-label">
                  AVPU
                  <select
                    className="auralis-input mt-1"
                    value={vitals.avpu}
                    onChange={(e) => setVitals({ ...vitals, avpu: e.target.value })}
                  >
                    <option value="">—</option>
                    <option>A</option>
                    <option>V</option>
                    <option>P</option>
                    <option>U</option>
                  </select>
                </label>
                <button type="submit" className="auralis-btn-primary sm:col-span-2 xl:col-span-3">
                  {bn ? "চার্ট সংরক্ষণ" : "Save chart"}
                </button>
              </form>
              <div className="space-y-3">
                <BedQr encounterKey={current.encounter_key} bed={current.bed_id || current.encounter_id} />
                <select className="auralis-input" value={transferUnit} onChange={(e) => setTransferUnit(e.target.value)}>
                  <option value="">{bn ? "স্থানান্তর…" : "Transfer to…"}</option>
                  {units.data?.units
                    .filter((row) => row.unit_id !== current.unit_id)
                    .map((row) => (
                      <option key={row.unit_id} value={row.unit_id}>
                        {row.label}
                      </option>
                    ))}
                </select>
                <input
                  className="auralis-input"
                  value={transferBed}
                  onChange={(e) => setTransferBed(e.target.value)}
                  placeholder={bn ? "নতুন বেড (ঐচ্ছিক)" : "New bed (optional)"}
                />
                <button
                  type="button"
                  disabled={!transferUnit}
                  className="auralis-btn-secondary auralis-btn-sm w-full disabled:opacity-40"
                  onClick={() => void transferOrDischarge("transfer")}
                >
                  {bn ? "স্থানান্তর" : "Transfer"}
                </button>
                {current.kind === "ward" && (
                  <button type="button" className="auralis-btn-ghost auralis-btn-sm w-full" onClick={() => void changeNews2Scale()}>
                    NEWS2 SpO₂ Scale {current.hypercapnic_scale2 ? "2 (change to 1)" : "1 (change to 2)"}
                  </button>
                )}
                <button
                  type="button"
                  className="auralis-btn-ghost auralis-btn-sm w-full text-risk-high hover:text-risk-high"
                  onClick={() => void transferOrDischarge("discharge")}
                >
                  {bn ? "ডিসচার্জ" : "Discharge"}
                </button>
              </div>
            </div>
          )}
        </Panel>
      </div>

      <details className="auralis-panel group">
        <summary className="cursor-pointer list-none text-sm font-semibold text-ink marker:content-none [&::-webkit-details-marker]:hidden">
          <span className="inline-flex items-center gap-2">
            <Icon name="chevron-right" size={16} className="transition-transform group-open:rotate-90" />
            {bn ? "রোগী ভর্তি করুন" : "Admit patient"}
          </span>
        </summary>
        <form
          className="mt-4 grid gap-3 md:grid-cols-3"
          onSubmit={(event) => {
            event.preventDefault();
            void admitPatient();
          }}
        >
          {(["patient_id", "encounter_id", "display_name", "bed_id", "age"] as const).map((key) => (
            <input
              key={key}
              className="auralis-input"
              required={["patient_id", "encounter_id", "display_name"].includes(key)}
              value={admit[key]}
              onChange={(e) => setAdmit({ ...admit, [key]: e.target.value })}
              placeholder={key.replaceAll("_", " ")}
            />
          ))}
          <select className="auralis-input" value={admit.sex} onChange={(e) => setAdmit({ ...admit, sex: e.target.value })}>
            <option value="">Sex —</option>
            <option>F</option>
            <option>M</option>
            <option>X</option>
            <option>unknown</option>
          </select>
          {units.data?.units.find((row) => row.unit_id === unit)?.kind === "ward" && (
            <label className="flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-xs text-ink md:col-span-2">
              <input
                type="checkbox"
                checked={admit.hypercapnic_scale2}
                onChange={(e) => setAdmit({ ...admit, hypercapnic_scale2: e.target.checked })}
                className="rounded border-border text-teal focus:ring-teal"
              />
              Clinician-confirmed hypercapnic respiratory failure (NEWS2 SpO₂ Scale 2)
            </label>
          )}
          <button type="submit" className="auralis-btn-secondary">
            {bn ? "ভর্তি" : "Admit"}
          </button>
        </form>
      </details>

      {message && (
        <p role="status" className="rounded-lg border border-border bg-white px-3.5 py-2.5 text-sm text-ink">
          {message}
        </p>
      )}
      <p className="auralis-help">
        Offline charts remain on this hospital-managed device until synced. Do not use personal devices for identifiable
        data.
      </p>
    </div>
  );
}
