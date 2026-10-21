"use client";

import { useState } from "react";
import { MappingCopilot } from "@/components/MappingCopilot";
import { ApiError, KeyValue, Panel, Pill, SiteModeBanner, Stat } from "@/components/ui";
import { api, isStatus, pct, type ConnectorHealth, type SiteMode } from "@/lib/api";
import { connectorTone, humanize, minutesLabel } from "@/lib/pilot";
import { usePoll } from "@/lib/usePoll";

type IntegrationStatus = {
  site: { effective_mode: SiteMode };
  simulation_mode: boolean;
  connectors: ConnectorHealth[];
  feed_alarm: boolean;
  mapping_registry: { version: string; sha256: string; entries: number; status: string; signoff: Record<string, unknown> | null };
  encounters: { api: number; replay: number; api_units: string[] };
  replay: { enabled: boolean; beds: number };
  backfill: { jobs: number; observations_accepted: number; last_backfill_at: string | null; alerts_policy: string };
  quarantined_last_24h: number;
  operation: { read_only: boolean; read_only_reason: string | null; external_network_required: boolean; offline_note: string };
  roadmap: Record<string, string>;
};

type ConnectorEvent = {
  event_id: string;
  connector: string;
  received_at: string;
  status: string;
  received: number;
  accepted: number;
  quarantined: number;
  duplicates: number;
  lag_seconds: number | null;
  processing_ms: number | null;
  error: string | null;
  backfill: number;
  actor: string | null;
};

type QuarantineEvent = { audit_id: string; recorded_at: string; reason: string; connector?: string; code?: string; patient_id?: string };
type Mapping = { code: string; system: string; display: string; target: string; unit: string; accepted_units: string[] };

export default function IntegrationPage() {
  const [message, setMessage] = useState<string | null>(null);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvBackfill, setCsvBackfill] = useState(false);
  const [adtFile, setAdtFile] = useState<File | null>(null);
  const [mappingApproval, setMappingApproval] = useState({
    source_system: "", approver_name: "", approver_role: "", examples_verified: "10", notes: "",
  });
  const status = usePoll(() => api<IntegrationStatus>("/v1/integrations/status"), 5000);
  const events = usePoll(() => api<{ events: ConnectorEvent[] }>("/v1/integrations/events?limit=25"), 5000);
  const quarantine = usePoll(() => api<{ events: QuarantineEvent[] }>("/v1/integrations/quarantine?limit=25"), 10000);
  const mappings = usePoll(() => api<{ entries: Mapping[]; version: string }>("/v1/integrations/mappings"), 60000);

  async function act(path: string, done: (body: Record<string, unknown>) => string) {
    try {
      const body = await api<Record<string, unknown>>(path, { method: "POST" });
      setMessage(done(body));
      await Promise.all([status.refresh(), events.refresh(), quarantine.refresh()]);
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : String(cause));
    }
  }

  async function uploadCsv() {
    if (!csvFile) return;
    try {
      const body = await api<Record<string, unknown>>(`/v1/integrations/csv/lab?backfill=${csvBackfill}`, {
        method: "POST",
        headers: {
          "Content-Type": "text/csv; charset=utf-8",
          "Idempotency-Key": `csv-${csvFile.name}-${csvFile.size}-${csvFile.lastModified}`,
        },
        body: await csvFile.text(),
      });
      setMessage(`CSV import: ${body.accepted} accepted; ${(body.quarantined as unknown[])?.length ?? 0} quarantined.`);
      await Promise.all([status.refresh(), events.refresh(), quarantine.refresh()]);
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : String(cause));
    }
  }

  async function uploadAdt() {
    if (!adtFile) return;
    try {
      const body = await api<{ event: string; duplicate: boolean; encounter: { display_name: string; unit_id: string; bed_id: string | null; status: string } }>(
        "/v1/integrations/hl7v2/adt",
        { method: "POST", headers: { "Content-Type": "text/plain; charset=utf-8" }, body: await adtFile.text() },
      );
      setMessage(
        `ADT ${body.event}${body.duplicate ? " replay" : ""}: ${body.encounter.display_name} · ${body.encounter.unit_id}` +
        `${body.encounter.bed_id ? ` / ${body.encounter.bed_id}` : ""} · ${body.encounter.status}.`,
      );
      await status.refresh();
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : String(cause));
    }
  }

  async function signoffMappings() {
    if (!data) return;
    try {
      await api("/v1/integrations/mappings/signoff", {
        method: "POST",
        body: JSON.stringify({
          ...mappingApproval,
          registry_sha256: data.mapping_registry.sha256,
          examples_verified: Number(mappingApproval.examples_verified),
        }),
      });
      setMessage("Current mapping registry signed off for this source system.");
      await status.refresh();
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : String(cause));
    }
  }

  if (status.error && isStatus(status.error, 403)) {
    return <ApiError error="The Integration Hub is restricted to pilot administrators. Sign in with an admin role." />;
  }
  const data = status.data;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-display text-3xl">Integration hub</h1>
        <p className="mt-1 text-sm text-ink/60">
          Feed health, mapping registry, quarantine and spool. Everything runs on site — no internet connection is needed
          for scoring.
        </p>
      </div>
      {status.error && <ApiError error={status.error} />}
      {data && <SiteModeBanner mode={data.site.effective_mode} />}
      {data?.simulation_mode && (
        <p className="bg-accent/5 px-4 py-3 text-sm text-ink/70">
          Public commissioning simulation. The encounter counts and feed activity below are generated for this judge
          session; no hospital EHR is connected. A hospital installation records its own verified connector events.
        </p>
      )}
      {data?.feed_alarm && (
        <p role="alert" className="border border-risk-high/40 bg-risk-high/5 px-3 py-2 text-sm text-risk-high">
          A connected feed is stale or its circuit breaker is open. Scores for affected encounters may be outdated —
          TrustGate abstains when required vitals age out.
        </p>
      )}
      {data?.operation.read_only && (
        <p role="alert" className="border border-risk-watch/40 bg-risk-watch/5 px-3 py-2 text-sm">
          This instance is read-only ({humanize(data.operation.read_only_reason ?? "unknown")}). Incoming messages are
          spooled until the active writer is available.
        </p>
      )}
      {message && <p className="border border-accent/30 bg-accent/5 px-3 py-2 text-sm">{message}</p>}

      {data && (
        <div className="flex flex-wrap gap-3">
          <Stat label={data.simulation_mode ? "Simulated encounters" : "Live-feed encounters"} value={data.encounters.api} />
          <Stat label="Replay beds" value={data.replay.beds} />
          <Stat label="Quarantined 24 h" value={data.quarantined_last_24h} color={data.quarantined_last_24h ? "text-risk-watch" : "text-ink"} />
          <Stat label="Backfill jobs" value={data.backfill.jobs} />
          <Stat label="Mappings" value={data.mapping_registry.entries} />
        </div>
      )}

      <Panel title="Connectors">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-ink/50">
              <tr>
                <th className="py-1 font-medium">Feed</th>
                <th className="py-1 font-medium">State</th>
                <th className="py-1 font-medium">Last success</th>
                <th className="py-1 font-medium">Quarantine</th>
                <th className="py-1 font-medium">Lag / processing</th>
                <th className="py-1 font-medium">Spool</th>
              </tr>
            </thead>
            <tbody>
              {data?.connectors.map((connector) => (
                <tr key={connector.connector} className="border-t border-ink/5 align-top">
                  <td className="py-2">
                    <p className="font-medium">{connector.label}</p>
                    <p className="text-xs text-ink/50">{connector.standard}</p>
                    <p className="text-xs text-ink/50">{connector.endpoint}</p>
                  </td>
                  <td className="py-2">
                    <Pill tone={connectorTone(connector.state)}>
                      {data.simulation_mode && connector.state === "healthy" ? "Simulation running" : humanize(connector.state)}
                    </Pill>
                    <p className="mt-1 text-xs text-ink/50">circuit {humanize(connector.circuit)}</p>
                    {connector.last_error && <p className="mt-1 max-w-xs text-xs text-risk-high">{connector.last_error}</p>}
                  </td>
                  <td className="py-2 tabular-nums">
                    {connector.minutes_since_success == null ? "never" : `${minutesLabel(connector.minutes_since_success)} ago`}
                    <p className="text-xs text-ink/50">stale after {connector.stale_after_minutes} min</p>
                  </td>
                  <td className="py-2 tabular-nums">
                    {pct(connector.quarantine_rate, 1)}
                    <p className="text-xs text-ink/50">{connector.recent_quarantined} of {connector.recent_received}</p>
                  </td>
                  <td className="py-2 tabular-nums">
                    {connector.median_source_lag_minutes == null ? "—" : `${connector.median_source_lag_minutes} min`} /{" "}
                    {connector.median_processing_ms == null ? "—" : `${connector.median_processing_ms} ms`}
                  </td>
                  <td className="py-2 tabular-nums">{connector.pending_spool}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            className="border border-ink/20 px-3 py-1.5 text-sm"
            onClick={() => void act("/v1/integrations/spool/replay", (b) => `Spool replay: ${b.replayed} replayed, ${b.still_pending} still pending.`)}
          >
            Replay spool
          </button>
          {data?.site.effective_mode === "demo" && (
            <button
              type="button"
              className="border border-accent bg-accent px-3 py-1.5 text-sm text-white"
              onClick={() => void act("/v1/integrations/samples/load", () => "Loaded three synthetic FHIR encounters (integration-test data, not model evidence).")}
            >
              Load synthetic FHIR encounters
            </button>
          )}
        </div>
      </Panel>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Import hospital lab CSV">
          <p className="mb-3 text-sm text-ink/60">
            Accepts common headers such as MRN/patient, visit/encounter, result_time, test_code/LOINC, result and units.
            Unknown codes, units or timestamps go to quarantine.
          </p>
          <div className="space-y-3 text-sm">
            <input type="file" accept=".csv,text/csv" onChange={(event) => setCsvFile(event.target.files?.[0] ?? null)} />
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={csvBackfill} onChange={(event) => setCsvBackfill(event.target.checked)} />
              Retrospective backfill (shadow alerts only)
            </label>
            <button type="button" disabled={!csvFile} onClick={() => void uploadCsv()} className="border border-ink/20 px-3 py-1.5 disabled:opacity-40">
              Validate and import
            </button>
          </div>
        </Panel>
        <Panel title="Commission HL7 ADT">
          <p className="mb-3 text-sm text-ink/60">
            Validates one ADT A01 admission, A02 transfer or A03 discharge message using PID-3, PID-5, PV1-3 and PV1-19.
            Use de-identified commissioning messages until the hospital signs off its interface profile.
          </p>
          <div className="space-y-3 text-sm">
            <input type="file" accept=".hl7,.txt,text/plain" onChange={(event) => setAdtFile(event.target.files?.[0] ?? null)} />
            <button type="button" disabled={!adtFile} onClick={() => void uploadAdt()} className="border border-ink/20 px-3 py-1.5 disabled:opacity-40">
              Validate and apply ADT
            </button>
          </div>
        </Panel>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Recent connector events">
          {events.error && <ApiError error={events.error} />}
          <ul className="max-h-96 space-y-1 overflow-auto text-xs">
            {events.data?.events.map((event) => (
              <li key={event.event_id} className="flex flex-wrap justify-between gap-2 border-b border-ink/5 pb-1">
                <span>
                  {new Date(event.received_at).toLocaleTimeString()} · {event.connector} · <strong>{event.status}</strong>
                  {event.actor === "simulation-relay" ? " · simulated" : ""}
                  {event.backfill ? " · backfill" : ""}
                </span>
                <span className="tabular-nums text-ink/60">
                  {event.accepted}/{event.received} accepted · {event.quarantined} quarantined · {event.duplicates} dup
                </span>
                {event.error && <span className="w-full text-risk-high">{event.error}</span>}
              </li>
            ))}
          </ul>
        </Panel>
        <Panel title="Quarantine">
          {quarantine.error && <ApiError error={quarantine.error} />}
          <ul className="max-h-96 space-y-1 overflow-auto text-xs">
            {quarantine.data?.events.length === 0 && <li className="text-ink/60">Nothing quarantined.</li>}
            {quarantine.data?.events.map((event) => (
              <li key={event.audit_id} className="border-b border-ink/5 pb-1">
                {new Date(event.recorded_at).toLocaleString()} · {event.connector ?? "native_json"} · {event.code ?? "—"} ·{" "}
                <span className="text-risk-high">{humanize(event.reason)}</span>
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Mapping registry">
          {data && (
            <dl className="mb-3">
              <KeyValue label="Version" value={`${data.mapping_registry.version} (${data.mapping_registry.status})`} />
              <KeyValue label="SHA-256" value={<code className="text-xs">{data.mapping_registry.sha256.slice(0, 16)}…</code>} />
            </dl>
          )}
          <div className="max-h-72 overflow-auto">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-white text-ink/50">
                <tr>
                  <th className="py-1 font-medium">LOINC</th>
                  <th className="py-1 font-medium">Display</th>
                  <th className="py-1 font-medium">Target</th>
                  <th className="py-1 font-medium">Units accepted</th>
                </tr>
              </thead>
              <tbody>
                {mappings.data?.entries.map((entry) => (
                  <tr key={entry.code} className="border-t border-ink/5">
                    <td className="py-1 font-mono">{entry.code}</td>
                    <td className="py-1">{entry.display}</td>
                    <td className="py-1">{entry.target}</td>
                    <td className="py-1">{entry.accepted_units?.join(", ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <details className="mt-4 border-t border-ink/10 pt-3">
            <summary className="cursor-pointer text-sm font-medium">Record site mapping sign-off</summary>
            <p className="mt-2 text-xs text-ink/55">
              Sign only after the hospital interface analyst verifies source codes, units, timestamps and at least ten
              representative examples. A registry change invalidates this sign-off.
            </p>
            <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
              <input className="border border-ink/20 px-2 py-1.5" placeholder="Source system" value={mappingApproval.source_system} onChange={(e) => setMappingApproval({ ...mappingApproval, source_system: e.target.value })} />
              <input className="border border-ink/20 px-2 py-1.5" placeholder="Approver name" value={mappingApproval.approver_name} onChange={(e) => setMappingApproval({ ...mappingApproval, approver_name: e.target.value })} />
              <input className="border border-ink/20 px-2 py-1.5" placeholder="Approver role" value={mappingApproval.approver_role} onChange={(e) => setMappingApproval({ ...mappingApproval, approver_role: e.target.value })} />
              <input type="number" min={10} className="border border-ink/20 px-2 py-1.5" placeholder="Examples verified" value={mappingApproval.examples_verified} onChange={(e) => setMappingApproval({ ...mappingApproval, examples_verified: e.target.value })} />
              <textarea className="border border-ink/20 px-2 py-1.5 sm:col-span-2" placeholder="Verification notes" value={mappingApproval.notes} onChange={(e) => setMappingApproval({ ...mappingApproval, notes: e.target.value })} />
              <button type="button" className="border border-ink/20 px-3 py-1.5 sm:col-span-2" onClick={() => void signoffMappings()}>
                Sign current registry SHA
              </button>
            </div>
          </details>
        </Panel>
        <Panel title="Operation & roadmap">
          {data && (
            <dl>
              <KeyValue label="External network required" value={data.operation.external_network_required ? "yes" : "no"} />
              <KeyValue label="Backfill observations" value={data.backfill.observations_accepted} />
              <KeyValue label="Last backfill" value={data.backfill.last_backfill_at ? new Date(data.backfill.last_backfill_at).toLocaleString() : "—"} />
              <KeyValue label="API units" value={data.encounters.api_units.join(", ") || "—"} />
            </dl>
          )}
          <p className="mt-2 text-xs text-ink/55">{data?.operation.offline_note}</p>
          <p className="mt-1 text-xs text-ink/55">{data?.backfill.alerts_policy}</p>
          <ul className="mt-3 space-y-1 text-sm">
            {data &&
              Object.entries(data.roadmap).map(([key, value]) => (
                <li key={key}>
                  <strong className="font-medium">{humanize(key)}:</strong> {value}
                </li>
              ))}
          </ul>
        </Panel>
      </div>

      <MappingCopilot />
    </div>
  );
}
