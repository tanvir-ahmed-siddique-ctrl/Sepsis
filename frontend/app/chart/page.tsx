"use client";

import { useEffect, useMemo, useState } from "react";
import { BedQr } from "@/components/BedQr";
import { ApiError, Panel, Pill, Stat } from "@/components/ui";
import { api, type CareUnit, type CensusEncounter } from "@/lib/api";
import { useLocale } from "@/lib/locale";
import { enqueue, flushOutbox, outboxItems } from "@/lib/outbox";
import { usePoll } from "@/lib/usePoll";

const INPUT = "w-full border border-ink/20 bg-white px-2 py-1.5 text-sm outline-none focus:border-accent";
const EMPTY_VITALS = {
  heart_rate: "", spo2: "", temperature: "", temperature_unit: "C", systolic_bp: "",
  diastolic_bp: "", mean_arterial_pressure: "", respiration_rate: "", on_oxygen: "",
  avpu: "", lactate: "", wbc: "", creatinine: "", platelets: "",
};

export default function ChartPage() {
  const { locale } = useLocale();
  const bn = locale === "bn";
  const units = usePoll(() => api<{ units: CareUnit[] }>("/v1/care/units"), 30000);
  const [unit, setUnit] = useState("");
  const census = usePoll(
    () => unit ? api<{ encounters: CensusEncounter[]; due_count: number; complete_count: number }>(`/v1/care/census?unit_id=${encodeURIComponent(unit)}`) : Promise.resolve(null),
    10000,
    [unit],
  );
  const completeness = usePoll(
    () => unit ? api<{ completeness: number | null }>(`/v1/care/completeness?unit_id=${encodeURIComponent(unit)}&hours=8`) : Promise.resolve(null),
    30000,
    [unit],
  );
  const [selected, setSelected] = useState<string | null>(null);
  const [vitals, setVitals] = useState(EMPTY_VITALS);
  const [outbox, setOutbox] = useState(0);
  const [message, setMessage] = useState<string | null>(null);
  const [transferUnit, setTransferUnit] = useState("");
  const [transferBed, setTransferBed] = useState("");
  const [admit, setAdmit] = useState({
    patient_id: "", encounter_id: "", display_name: "", bed_id: "", age: "", sex: "", hypercapnic_scale2: false,
  });

  useEffect(() => {
    if (!unit && units.data?.units.length) setUnit(units.data.units[0].unit_id);
  }, [unit, units.data]);
  useEffect(() => { void outboxItems().then((items) => setOutbox(items.length)); }, []);
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
    const numeric = ["heart_rate", "spo2", "temperature", "systolic_bp", "diastolic_bp", "mean_arterial_pressure", "respiration_rate", "lactate", "wbc", "creatinine", "platelets"];
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
    await api("/v1/care/encounters", {
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
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl">{bn ? "বেডসাইড চার্টিং" : "Bedside charting"}</h1>
          <p className="mt-1 text-sm text-ink/60">{bn ? "আইসিইউ ও ওয়ার্ডের পর্যবেক্ষণ—অফলাইনে রাখে, সংযোগ এলে সিঙ্ক করে।" : "ICU and ward observations—queued offline and synced when the server returns."}</p>
        </div>
        <label className="text-sm">
          <span className="mr-2 text-ink/55">{bn ? "ইউনিট" : "Unit"}</span>
          <select className={INPUT} value={unit} onChange={(e) => { setUnit(e.target.value); setSelected(null); }}>
            {units.data?.units.map((row) => <option key={row.unit_id} value={row.unit_id}>{row.label} ({row.kind})</option>)}
          </select>
        </label>
      </div>
      {(units.error || census.error) && <ApiError error={(units.error || census.error)!} />}
      <div className="flex flex-wrap gap-3">
        <Stat label={bn ? "ভর্তি" : "Admitted"} value={census.data?.encounters.length ?? 0} />
        <Stat label={bn ? "এখন মাপা দরকার" : "Observations due"} value={census.data?.due_count ?? 0} color={census.data?.due_count ? "text-risk-high" : "text-ink"} />
        <Stat label={bn ? "সম্পূর্ণ" : "Complete"} value={census.data?.complete_count ?? 0} />
        <Stat label={bn ? "৮ ঘণ্টার ডেটা" : "8 h completeness"} value={completeness.data?.completeness == null ? "—" : `${Math.round(completeness.data.completeness * 100)}%`} />
        <Stat label={bn ? "অফলাইন কিউ" : "Offline queue"} value={outbox} color={outbox ? "text-risk-watch" : "text-ink"} />
        {outbox > 0 && <button className="border border-ink/20 px-3 py-1.5 text-sm" onClick={() => void sync()}>{bn ? "এখন সিঙ্ক" : "Sync now"}</button>}
      </div>
      <p className="border border-accent/25 bg-accent/5 px-3 py-2 text-xs text-ink/65">
        Competition environment: the API ICU and Demo Ward are populated with synthetic commissioning encounters so
        this workflow can be demonstrated without hospital patient data.
      </p>
      <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr]">
        <Panel title={bn ? "বেড তালিকা" : "Bed list"}>
          <div className="space-y-2">
            {census.data?.encounters.map((row) => (
              <button type="button" key={row.encounter_key} onClick={() => setSelected(row.encounter_key)}
                className={`flex w-full items-center justify-between border p-3 text-left ${selected === row.encounter_key ? "border-accent bg-accent/5" : "border-ink/10"}`}>
                <span><strong>{row.bed_id || "—"} · {row.display_name}</strong><span className="block text-xs text-ink/50">{row.encounter_id}</span></span>
                <span className="space-x-1">{row.observations_due && <Pill tone="warning">{bn ? "বাকি" : "due"}</Pill>}{row.latest_news2?.score != null && <Pill>NEWS2 {row.latest_news2.score}</Pill>}</span>
              </button>
            ))}
          </div>
        </Panel>
        <Panel title={current ? `${current.bed_id || ""} ${current.display_name}` : (bn ? "একটি বেড বেছে নিন" : "Choose a bed")}>
          {current && (
            <div className="grid gap-5 xl:grid-cols-[1fr_auto]">
            <form className="grid gap-3 sm:grid-cols-3" onSubmit={(event) => { event.preventDefault(); void submitVitals(); }}>
              {[
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
              ].map(([key, label, unitLabel]) => (
                <label key={key} className="text-xs font-medium text-ink/60">{label}
                  <input type="number" step="any" className={`${INPUT} mt-1`} value={vitals[key as keyof typeof vitals]} onChange={(e) => setVitals({ ...vitals, [key]: e.target.value })} placeholder={unitLabel} />
                </label>
              ))}
              <label className="text-xs font-medium text-ink/60">{bn ? "তাপমাত্রার একক" : "Temperature unit"}
                <select className={`${INPUT} mt-1`} value={vitals.temperature_unit} onChange={(e) => setVitals({ ...vitals, temperature_unit: e.target.value })}><option>C</option><option>F</option></select>
              </label>
              <label className="text-xs font-medium text-ink/60">{bn ? "অক্সিজেন" : "Supplemental oxygen"}
                <select className={`${INPUT} mt-1`} value={vitals.on_oxygen} onChange={(e) => setVitals({ ...vitals, on_oxygen: e.target.value })}><option value="">—</option><option value="false">No</option><option value="true">Yes</option></select>
              </label>
              <label className="text-xs font-medium text-ink/60">AVPU
                <select className={`${INPUT} mt-1`} value={vitals.avpu} onChange={(e) => setVitals({ ...vitals, avpu: e.target.value })}><option value="">—</option><option>A</option><option>V</option><option>P</option><option>U</option></select>
              </label>
              <button className="border border-accent bg-accent px-3 py-2 text-sm font-medium text-white sm:col-span-3">{bn ? "চার্ট সংরক্ষণ" : "Save chart"}</button>
            </form>
            <div className="space-y-3">
              <BedQr encounterKey={current.encounter_key} bed={current.bed_id || current.encounter_id} />
              <select className={INPUT} value={transferUnit} onChange={(e) => setTransferUnit(e.target.value)}>
                <option value="">{bn ? "স্থানান্তর…" : "Transfer to…"}</option>
                {units.data?.units.filter((row) => row.unit_id !== current.unit_id).map((row) => <option key={row.unit_id} value={row.unit_id}>{row.label}</option>)}
              </select>
              <input className={INPUT} value={transferBed} onChange={(e) => setTransferBed(e.target.value)} placeholder={bn ? "নতুন বেড (ঐচ্ছিক)" : "New bed (optional)"} />
              <button type="button" disabled={!transferUnit} className="w-full border border-ink/20 px-2 py-1 text-xs disabled:opacity-40" onClick={() => void transferOrDischarge("transfer")}>{bn ? "স্থানান্তর" : "Transfer"}</button>
              {current.kind === "ward" && (
                <button type="button" className="w-full border border-ink/20 px-2 py-1 text-xs" onClick={() => void changeNews2Scale()}>
                  NEWS2 SpO₂ Scale {current.hypercapnic_scale2 ? "2 (change to 1)" : "1 (change to 2)"}
                </button>
              )}
              <button type="button" className="w-full border border-risk-high/30 px-2 py-1 text-xs text-risk-high" onClick={() => void transferOrDischarge("discharge")}>{bn ? "ডিসচার্জ" : "Discharge"}</button>
            </div>
            </div>
          )}
        </Panel>
      </div>
      <details className="border border-ink/10 bg-white p-4">
        <summary className="cursor-pointer text-sm font-medium">{bn ? "রোগী ভর্তি করুন" : "Admit patient"}</summary>
        <form className="mt-3 grid gap-3 md:grid-cols-3" onSubmit={(event) => { event.preventDefault(); void admitPatient(); }}>
          {(["patient_id", "encounter_id", "display_name", "bed_id", "age"] as const).map((key) => (
            <input key={key} className={INPUT} required={["patient_id", "encounter_id", "display_name"].includes(key)} value={admit[key]} onChange={(e) => setAdmit({ ...admit, [key]: e.target.value })} placeholder={key.replaceAll("_", " ")} />
          ))}
          <select className={INPUT} value={admit.sex} onChange={(e) => setAdmit({ ...admit, sex: e.target.value })}><option value="">Sex —</option><option>F</option><option>M</option><option>X</option><option>unknown</option></select>
          {units.data?.units.find((row) => row.unit_id === unit)?.kind === "ward" && (
            <label className="flex items-center gap-2 border border-ink/10 px-2 py-1.5 text-xs">
              <input type="checkbox" checked={admit.hypercapnic_scale2} onChange={(e) => setAdmit({ ...admit, hypercapnic_scale2: e.target.checked })} />
              Clinician-confirmed hypercapnic respiratory failure (NEWS2 SpO₂ Scale 2)
            </label>
          )}
          <button className="border border-ink/20 px-3 py-1.5 text-sm">{bn ? "ভর্তি" : "Admit"}</button>
        </form>
      </details>
      {message && <p role="status" className="border border-ink/10 bg-white p-3 text-sm">{message}</p>}
      <p className="text-xs text-ink/45">Offline charts remain on this hospital-managed device until synced. Do not use personal devices for identifiable data.</p>
    </div>
  );
}
