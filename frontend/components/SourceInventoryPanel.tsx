"use client";

import { useEffect, useState } from "react";
import { ApiError, Panel, Pill } from "@/components/ui";
import { api } from "@/lib/api";
import { usePoll } from "@/lib/usePoll";

type Kind = "ehr" | "lis" | "monitor" | "manual" | "interface_engine";
type Method = "none" | "manual" | "csv_lab" | "hl7v2_oru" | "fhir_r4" | "vendor_adapter";
type TimestampBasis = "measurement" | "result" | "receipt" | "unknown";
type OwnerRole = "icu" | "nursing" | "lab" | "biomed" | "it" | "unknown";
type Signal = "HR" | "SBP" | "MAP" | "O2Sat" | "Temp" | "Resp" | "WBC" | "Lactate" | "Creatinine" | "Platelets";

type Source = {
  source_id: string;
  kind: Kind;
  label: string;
  method: Method;
  signals: Signal[];
  expected_interval_minutes: number | null;
  timestamp_basis: TimestampBasis;
  export_confirmed: boolean;
  test_message_verified: boolean;
  manual_chart_dry_run_verified: boolean;
  correction_path_verified: boolean;
  owner_role: OwnerRole;
};

type Inventory = {
  sources: Source[];
  updated_at: string | null;
  simulation_mode: boolean;
  assessment: {
    sources: Array<{ source_id: string; tier: string; connector_state: string | null; declared_test_ready: boolean; feed_observed: boolean; next_action: string }>;
    missing_required_vitals: string[];
    required_vitals_without_hourly_source: string[];
    observed_connected_sources: number;
    next_stage: string;
    scope: string;
  };
};

const SIGNALS: Signal[] = ["HR", "SBP", "MAP", "O2Sat", "Temp", "Resp", "WBC", "Lactate", "Creatinine", "Platelets"];
const KIND_OPTIONS: Kind[] = ["ehr", "lis", "monitor", "manual", "interface_engine"];
const METHOD_OPTIONS: Method[] = ["none", "manual", "csv_lab", "hl7v2_oru", "fhir_r4", "vendor_adapter"];
const OWNER_OPTIONS: OwnerRole[] = ["unknown", "icu", "nursing", "lab", "biomed", "it"];
const TIMESTAMP_OPTIONS: TimestampBasis[] = ["unknown", "measurement", "result", "receipt"];
const inputClass = "w-full border border-ink/20 bg-white px-2 py-1.5 text-sm";

function blank(): Source {
  return {
    source_id: "", kind: "ehr", label: "", method: "none", signals: [], expected_interval_minutes: null,
    timestamp_basis: "unknown", export_confirmed: false, test_message_verified: false,
    manual_chart_dry_run_verified: false, correction_path_verified: false, owner_role: "unknown",
  };
}

export function SourceInventoryPanel() {
  const inventory = usePoll(() => api<Inventory>("/v1/integrations/source-inventory"), 60000);
  const [sources, setSources] = useState<Source[]>([]);
  const [draft, setDraft] = useState<Source>(blank);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [initialized, setInitialized] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (inventory.data && !initialized) {
      setSources(inventory.data.sources);
      setInitialized(true);
    }
  }, [inventory.data, initialized]);

  function addOrUpdate() {
    if (!draft.label.trim()) {
      setMessage("Enter a source label, such as ICU monitor gateway or LIS export.");
      return;
    }
    if (sources.length >= 20 && !editingId) {
      setMessage("The inventory supports up to 20 sources.");
      return;
    }
    const entry = { ...draft, label: draft.label.trim(), source_id: editingId ?? `src-${crypto.randomUUID().replaceAll("-", "").slice(0, 12)}` };
    setSources((current) => editingId ? current.map((item) => item.source_id === editingId ? entry : item) : [...current, entry]);
    setDraft(blank());
    setEditingId(null);
    setMessage("Source added locally. Save the inventory to record it on this site.");
  }

  async function save() {
    try {
      const result = await api<Inventory>("/v1/integrations/source-inventory", {
        method: "PUT", body: JSON.stringify({ sources }),
      });
      setSources(result.sources);
      setMessage("Source inventory saved and audited. Declarations still need test and measured feed evidence.");
      await inventory.refresh();
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : String(cause));
    }
  }

  const assessment = inventory.data?.assessment;
  return (
    <Panel title="Hospital source inventory">
      <p className="mb-3 text-sm text-ink/60">
        Record what this hospital can actually export before connecting patient data. Use system names only—no patient
        identifiers, chart text or credentials. A declaration does not prove a working feed or authorize alerts.
      </p>
      {inventory.error && <ApiError error={inventory.error} />}
      {inventory.data?.simulation_mode && (
        <p className="mb-3 bg-accent/5 px-3 py-2 text-xs">Judge environment: entries here are commissioning examples, not a real hospital inventory.</p>
      )}
      {assessment && (
        <div className="mb-4 flex flex-wrap items-center gap-2 text-sm">
          <Pill tone={assessment.missing_required_vitals.length ? "warning" : "success"}>
            {assessment.missing_required_vitals.length ? `Declared vital gaps: ${assessment.missing_required_vitals.join(", ")}` : "Required vitals declared"}
          </Pill>
          {assessment.required_vitals_without_hourly_source.length > 0 && (
            <Pill tone="warning">Hourly cadence unverified: {assessment.required_vitals_without_hourly_source.join(", ")}</Pill>
          )}
          <span>{assessment.observed_connected_sources} declared sources with observed connector activity</span>
          <span className="text-ink/55">Next: {assessment.next_stage.replaceAll("_", " ")}</span>
        </div>
      )}
      {sources.length > 0 && (
        <div className="mb-4 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-ink/55"><tr><th className="py-1">Source</th><th>Route</th><th>Signals</th><th>Evidence</th><th>Next action</th><th /></tr></thead>
            <tbody>{sources.map((source) => {
              const result = assessment?.sources.find((item) => item.source_id === source.source_id);
              return <tr key={source.source_id} className="border-t border-ink/10 align-top">
                <td className="py-2 font-medium">{source.label}<span className="block text-xs font-normal text-ink/50">{source.kind}</span></td>
                <td>{source.method.replaceAll("_", " ")}{result && <span className="block text-xs text-ink/50">{result.tier} · {result.connector_state ?? "manual/unavailable"}</span>}</td>
                <td>{source.signals.join(", ") || "None declared"}</td>
                <td>{result?.feed_observed ? "Feed seen" : result?.declared_test_ready ? "Test declared" : "Unverified"}</td>
                <td className="max-w-52 text-xs">{result?.next_action ?? "Save to assess"}</td>
                <td className="whitespace-nowrap text-right"><button className="underline" type="button" onClick={() => { setDraft(source); setEditingId(source.source_id); }}>Edit</button>{" · "}<button className="underline" type="button" onClick={() => setSources((current) => current.filter((item) => item.source_id !== source.source_id))}>Remove</button></td>
              </tr>;
            })}</tbody>
          </table>
        </div>
      )}
      <div className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
        <label>System name<input className={inputClass} maxLength={80} value={draft.label} onChange={(event) => setDraft({ ...draft, label: event.target.value })} placeholder="ICU monitor gateway" /></label>
        <label>Source type<select className={inputClass} value={draft.kind} onChange={(event) => setDraft({ ...draft, kind: event.target.value as Kind })}>{KIND_OPTIONS.map((item) => <option key={item} value={item}>{item.replaceAll("_", " ")}</option>)}</select></label>
        <label>Connection route<select className={inputClass} value={draft.method} onChange={(event) => setDraft({ ...draft, method: event.target.value as Method, export_confirmed: false, test_message_verified: false, manual_chart_dry_run_verified: false })}>{METHOD_OPTIONS.map((item) => <option key={item} value={item}>{item.replaceAll("_", " ")}</option>)}</select></label>
        <label>Source owner role<select className={inputClass} value={draft.owner_role} onChange={(event) => setDraft({ ...draft, owner_role: event.target.value as OwnerRole })}>{OWNER_OPTIONS.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
        <label>Timestamp represents<select className={inputClass} value={draft.timestamp_basis} onChange={(event) => setDraft({ ...draft, timestamp_basis: event.target.value as TimestampBasis })}>{TIMESTAMP_OPTIONS.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
        <label>Expected interval (minutes, if periodic)<input className={inputClass} type="number" min={1} max={1440} value={draft.expected_interval_minutes ?? ""} onChange={(event) => setDraft({ ...draft, expected_interval_minutes: event.target.value ? Number(event.target.value) : null })} placeholder="Labs can be event-driven" /></label>
      </div>
      <fieldset className="mt-3"><legend className="text-sm font-medium">Signals this source can supply</legend><div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm">{SIGNALS.map((signal) => <label key={signal} className="flex items-center gap-1"><input type="checkbox" checked={draft.signals.includes(signal)} onChange={(event) => setDraft({ ...draft, signals: event.target.checked ? [...draft.signals, signal] : draft.signals.filter((item) => item !== signal) })} />{signal}</label>)}</div></fieldset>
      <div className="mt-3 flex flex-wrap gap-4 text-sm">
        {draft.method === "manual" ? <label className="flex items-center gap-1"><input type="checkbox" checked={draft.manual_chart_dry_run_verified} onChange={(event) => setDraft({ ...draft, manual_chart_dry_run_verified: event.target.checked })} />Bedside chart dry run verified</label> : <>
          <label className="flex items-center gap-1"><input type="checkbox" checked={draft.export_confirmed} onChange={(event) => setDraft({ ...draft, export_confirmed: event.target.checked, test_message_verified: event.target.checked && draft.test_message_verified })} />Export confirmed</label>
          <label className="flex items-center gap-1"><input type="checkbox" checked={draft.test_message_verified} disabled={!draft.export_confirmed || draft.method === "none"} onChange={(event) => setDraft({ ...draft, test_message_verified: event.target.checked })} />Test message verified</label>
        </>}
        <label className="flex items-center gap-1"><input type="checkbox" checked={draft.correction_path_verified} onChange={(event) => setDraft({ ...draft, correction_path_verified: event.target.checked })} />Correction path verified</label>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <button type="button" className="border border-ink/20 px-3 py-1.5 text-sm" onClick={addOrUpdate}>{editingId ? "Update source" : "Add source"}</button>
        <button type="button" className="bg-accent px-3 py-1.5 text-sm text-white" onClick={() => void save()}>Save inventory</button>
      </div>
      {message && <p role="status" className="mt-2 text-sm">{message}</p>}
      {assessment && <p className="mt-3 text-xs text-ink/50">{assessment.scope}</p>}
    </Panel>
  );
}
