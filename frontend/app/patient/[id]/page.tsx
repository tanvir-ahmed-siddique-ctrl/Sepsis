"use client";

import { use, useState } from "react";
import ReactECharts from "echarts-for-react";
import { AlertActions } from "@/components/AlertActions";
import { ClinicalContextPanel } from "@/components/patient/ClinicalContextPanel";
import { GuidancePanel } from "@/components/patient/GuidancePanel";
import { ProvenancePanel } from "@/components/patient/ProvenancePanel";
import { WorkflowPanel } from "@/components/patient/WorkflowPanel";
import { RiskBadge, TrustBadge } from "@/components/RiskBadge";
import { ReplayControls } from "@/components/ReplayControls";
import { ApiError, BAND_COLOR, Panel, Pill } from "@/components/ui";
import { api, isStatus, pct, type Alert, type AuditEvent, type RiskCurrent, type RiskPoint, type Thresholds } from "@/lib/api";
import { reviewClock } from "@/lib/pilot";
import { usePoll } from "@/lib/usePoll";
import { useSession } from "@/lib/session";

type EvidenceQuery = {
  feature: string;
  mapped: boolean;
  graph_version: string;
  model_influence: { meaning: string };
  curated_clinical_context: {
    organ_systems: { label: string }[];
    dysfunction_concepts: { label: string }[];
    evidence_sources: { label: string }[];
    meaning: string;
  };
  safeguards: { label: string }[];
  disclaimer: string;
  unmapped_action: string | null;
};

type Bundle = {
  current: RiskCurrent;
  points: RiskPoint[];
  thresholds: Thresholds;
  alerts: Alert[];
  audit: AuditEvent[];
  evidence: EvidenceQuery[];
};

const VITALS: { key: string; label: string; unit: string }[] = [
  { key: "HR", label: "Heart rate", unit: "bpm" },
  { key: "MAP", label: "MAP", unit: "mmHg" },
  { key: "Resp", label: "Resp rate", unit: "/min" },
  { key: "Temp", label: "Temperature", unit: "°C" },
  { key: "O2Sat", label: "SpO2", unit: "%" },
  { key: "Lactate", label: "Lactate", unit: "mmol/L" },
  { key: "WBC", label: "WBC", unit: "×10³/µL" },
  { key: "Creatinine", label: "Creatinine", unit: "mg/dL" },
];

export default function PatientPage({ params }: { params: Promise<{ id: string }> }) {
  const { me } = useSession();
  const { id: routeId } = use(params);
  const id = encodeURIComponent(decodeURIComponent(routeId));
  const [message, setMessage] = useState<string | null>(null);
  const { data, error, refresh } = usePoll<Bundle>(async () => {
    const [current, timeline, alerts, audit] = await Promise.all([
      api<RiskCurrent>(`/v1/patients/${id}/risk/current`),
      api<{ points: RiskPoint[]; thresholds: Thresholds }>(`/v1/patients/${id}/risk/timeline`),
      api<{ alerts: Alert[] }>(`/v1/alerts?patient_id=${id}`),
      api<{ events: AuditEvent[] }>(`/v1/audit?patient_id=${id}&limit=12`),
    ]);
    const topFeatures = current.contributing_factors.slice(0, 3).map((factor) => factor.feature);
    const evidence = topFeatures.length
      ? (await api<{ results: EvidenceQuery[] }>(`/v1/evidence/features?names=${encodeURIComponent(topFeatures.join(","))}`)).results
      : [];
    return { current, points: timeline.points, thresholds: timeline.thresholds, alerts: alerts.alerts, audit: audit.events, evidence };
  }, 3000, [id]);

  if (error && isStatus(error, 403)) {
    return (
      <Panel title="Blinded during the silent pilot">
        <p className="text-sm">
          This encounter comes from a live hospital feed. While the site runs a silent pilot, scores are recorded for
          evaluation but hidden from bedside staff so they cannot influence care.
        </p>
      </Panel>
    );
  }
  if (error) return <ApiError error={error} />;
  if (!data) return <p className="text-sm text-ink/60">Loading patient risk…</p>;
  const { current, points, thresholds, alerts, audit, evidence } = data;
  const openAlert = alerts.find((a) => a.status === "open");
  const requiredSignals = ["HR", "SBP", "MAP", "O2Sat"];
  const title = current.source_mode === "replay" ? current.patient_id.replace("BED-", "Bed ") : current.patient_id;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl">{title}</h1>
          <p className="text-sm text-ink/60">
            ICU hour {current.hour} · {current.unit_id} · {current.source_mode === "api" ? "live feed" : me?.evaluation_runtime ? "synthetic evaluation replay" : "held-out replay"} ·
            model {current.model_version}
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            <TrustBadge state={current.trustgate.state} />
            <Pill>Owner: {current.owner ?? "unassigned"}</Pill>
          </div>
        </div>
        {current.source_mode === "replay" && <ReplayControls onChange={refresh} />}
      </div>

      {current.trustgate.state === "verify_data" && (
        <Panel className="border-accent/40 bg-accent/5" title="Verify data — do not treat this as a reliable alarm">
          <p className="text-sm">
            The score exists, but freshness, availability, or perturbation stability failed the reliability gate.
            Confirm the source observations before interrupting care.
          </p>
          <p className="mt-2 text-xs text-ink/55">{current.trustgate.reasons.map((reason) => reason.replaceAll("_", " ")).join(" · ")}</p>
        </Panel>
      )}
      {current.trustgate.state === "abstain" && (
        <Panel className="border-ink/20 bg-ink/5" title="Abstain — not enough reliable input to interrupt">
          <p className="text-sm">
            TrustGate withheld coverage because history is incomplete or required vitals are severely stale or missing.
          </p>
          <p className="mt-2 text-xs text-ink/55">{current.trustgate.reasons.map((reason) => reason.replaceAll("_", " ")).join(" · ")}</p>
        </Panel>
      )}
      {openAlert && (
        <Panel className="border-risk-high/40 bg-risk-high/5" title="Open alert — clinician review required">
          <p className="text-sm">{openAlert.reason}</p>
          <p className="mb-3 mt-1 text-xs text-ink/55">
            Raised at ICU hour {openAlert.hour} · data quality {openAlert.data_quality} · model {openAlert.model_version} ·{" "}
            <span className={openAlert.overdue ? "font-semibold text-risk-high" : ""}>{reviewClock(openAlert).label}</span>
          </p>
          <AlertActions alertId={openAlert.alert_id} onDone={(m) => { setMessage(m); refresh(); }} />
        </Panel>
      )}
      {message && <p className="border border-accent/30 bg-accent/5 px-3 py-2 text-sm text-accent">{message}</p>}

      <div className="grid gap-4 lg:grid-cols-3">
        <Panel>
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase tracking-wide text-ink/50">Calibrated probability</p>
            <RiskBadge band={current.risk_band} />
          </div>
          <p className="mt-2 font-display text-5xl tabular-nums" style={{ color: BAND_COLOR[current.risk_band] }}>
            {pct(current.probability)}
          </p>
          <dl className="mt-4 space-y-2 text-sm">
            <Row
              label="Model disagreement"
              value={current.trustgate.disagreement_validated ? `±${pct(current.uncertainty, 1)}` : "Not validated (not gated)"}
            />
            <Row label="Data quality" value={current.data_quality.replaceAll("_", " ")} />
            <Row label="Vitals age" value={current.data_freshness_minutes == null ? "—" : `${current.data_freshness_minutes} min`} />
            <Row label="Input-shift proxy" value={pct(current.trustgate.input_shift_score, 0)} />
            <Row
              label="Alert stability"
              value={current.trustgate.alert_stability == null ? "Not evaluated" : pct(current.trustgate.alert_stability, 0)}
            />
            <Row label="Watch / High-risk thresholds" value={`${pct(thresholds.watch, 1)} / ${pct(thresholds.high_risk, 1)}`} />
          </dl>
          <p className="mt-3 text-xs text-ink/50">
            {current.trustgate.reasons.map((reason) => reason.replaceAll("_", " ")).join(" · ")}
          </p>
        </Panel>
        <Panel title="Risk timeline" className="lg:col-span-2">
          <RiskChart points={points} thresholds={thresholds} />
        </Panel>
      </div>

      <Panel title="Why the model scored this hour this way">
        <p className="-mt-2 mb-3 text-xs text-ink/55">
          TreeSHAP contributions grouped by clinical variable. They explain the model&apos;s score — they are not a
          diagnosis or treatment advice.
        </p>
        {current.contributing_factors.length === 0 ? (
          <p className="text-sm text-ink/60">Not enough observed hours to score yet.</p>
        ) : (
          <ul className="space-y-2">
            {current.contributing_factors.map((f) => {
              const max = Math.max(...current.contributing_factors.map((x) => x.magnitude));
              return (
                <li key={f.feature} className="grid grid-cols-[1fr_auto] items-center gap-3 border-b border-ink/5 pb-2 sm:grid-cols-[14rem_1fr_auto]">
                  <div>
                    <p className="text-sm font-medium">{f.plain_language}</p>
                    <p className="text-xs text-ink/50">{f.organ_system}</p>
                  </div>
                  <div className="hidden h-2 bg-ink/5 sm:block">
                    <div
                      className={f.direction === "raises" ? "h-2 bg-risk-high/70" : "h-2 bg-risk-stable/70"}
                      style={{ width: `${(f.magnitude / max) * 100}%` }}
                    />
                  </div>
                  <span className={`text-xs font-semibold ${f.direction === "raises" ? "text-risk-high" : "text-risk-stable"}`}>
                    {f.direction === "raises" ? "▲ raises" : "▼ lowers"}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </Panel>

      <ClinicalContextPanel patientId={current.encounter_key ?? current.patient_id} onSaved={refresh} />

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Evidence graph for the top drivers">
          {evidence.length === 0 ? (
            <p className="text-sm text-ink/60">No scored feature to map yet.</p>
          ) : (
            <div className="space-y-4">
              {evidence.map((item) => (
                <dl key={item.feature} className="space-y-1.5 border-b border-ink/5 pb-3 text-sm">
                  <p className="font-medium">{item.feature}</p>
                  <Row label="Mapped observation" value={item.mapped ? "Yes" : "No — curation requested"} />
                  <Row
                    label="Organ systems"
                    value={item.curated_clinical_context.organ_systems.map((entry) => entry.label).join(", ") || "—"}
                  />
                  <Row
                    label="Curated concepts"
                    value={item.curated_clinical_context.dysfunction_concepts.map((entry) => entry.label).join(", ") || "—"}
                  />
                  <Row label="Safeguards" value={item.safeguards.map((entry) => entry.label).join(" · ") || "—"} />
                </dl>
              ))}
              <p className="text-xs text-ink/55">
                Graph {evidence[0].graph_version}. {evidence[0].model_influence.meaning} {evidence[0].disclaimer}
              </p>
            </div>
          )}
        </Panel>
        <Panel title="Required-vital freshness">
          <p className="-mt-2 mb-3 text-xs text-ink/55">
            Conservative aggregate uses the oldest of HR, SBP, MAP, and SpO2 — not the freshest one vital.
          </p>
          <ul className="space-y-1 text-sm">
            {requiredSignals.map((signal) => {
              const minutes = current.signal_freshness_minutes?.[signal];
              return (
                <li key={signal} className="flex justify-between border-b border-ink/5 py-1">
                  <span>{signal}</span>
                  <span className="tabular-nums">{minutes == null ? "missing" : `${minutes} min`}</span>
                </li>
              );
            })}
          </ul>
        </Panel>
      </div>

      <GuidancePanel features={evidence.map((item) => item.feature)} />

      <WorkflowPanel
        patientId={current.encounter_key ?? current.patient_id}
        owner={current.owner}
        latestAlertId={alerts[0]?.alert_id ?? null}
      />

      <ProvenancePanel patientId={current.encounter_key ?? current.patient_id} />

      <Panel title="Vitals and labs (last 24 h, forward-filled within clinical limits)">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {VITALS.map((v) => (
            <VitalChart key={v.key} label={v.label} unit={v.unit} points={points.slice(-24)} field={v.key} />
          ))}
        </div>
      </Panel>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Alert history">
          {alerts.length === 0 ? (
            <p className="text-sm text-ink/60">No alerts for this patient.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {alerts.map((a) => (
                <li key={a.alert_id} className="flex justify-between gap-2 border-b border-ink/5 pb-2">
                  <span>Hour {a.hour} · {a.reason}</span>
                  <span className="shrink-0 text-xs uppercase text-ink/50">{a.status}</span>
                </li>
              ))}
            </ul>
          )}
        </Panel>
        <Panel title="Audit trail">
          <ul className="space-y-1 font-mono text-xs text-ink/70">
            {audit.map((e) => (
              <li key={e.audit_id}>
                {e.event} {e.hour != null ? `· h${e.hour}` : ""} {e.risk_band ? `· ${e.risk_band}` : ""}{" "}
                {e.user_id ? `· ${e.user_id}` : ""} <span className="text-ink/40">{e.audit_id}</span>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-2">
      <dt className="text-ink/50">{label}</dt>
      <dd className="text-right capitalize">{value}</dd>
    </div>
  );
}

function RiskChart({ points, thresholds }: { points: RiskPoint[]; thresholds: Thresholds }) {
  const alertPts = points.filter((p) => p.alert_id).map((p) => ({ coord: [`h${p.hour}`, p.probability], value: "alert" }));
  const option = {
    grid: { left: 44, right: 16, top: 20, bottom: 28 },
    xAxis: { type: "category", data: points.map((p) => `h${p.hour}`), axisLabel: { color: "#667085" } },
    yAxis: { type: "value", min: 0, max: (v: { max: number }) => Math.min(1, Math.max(0.2, v.max * 1.2)), axisLabel: { formatter: (v: number) => `${Math.round(v * 100)}%`, color: "#667085" } },
    tooltip: { trigger: "axis", valueFormatter: (v: number) => (v == null ? "—" : `${(v * 100).toFixed(1)}%`) },
    series: [
      {
        type: "line",
        smooth: true,
        data: points.map((p) => p.probability),
        lineStyle: { width: 2, color: "#0e7490" },
        itemStyle: { color: "#0e7490" },
        areaStyle: { opacity: 0.1 },
        markLine: {
          symbol: "none",
          label: { formatter: "{b}", color: "#667085" },
          data: [
            { name: "Watch", yAxis: thresholds.watch, lineStyle: { color: "#b7791f", type: "dashed" } },
            { name: "High risk", yAxis: thresholds.high_risk, lineStyle: { color: "#b42318", type: "dashed" } },
          ],
        },
        markPoint: { symbol: "pin", symbolSize: 34, itemStyle: { color: "#b42318" }, data: alertPts },
      },
    ],
  };
  return <ReactECharts option={option} style={{ height: 260 }} notMerge />;
}

function VitalChart({ label, unit, points, field }: { label: string; unit: string; points: RiskPoint[]; field: string }) {
  const values = points.map((p) => p.vitals[field] ?? null);
  const latest = [...values].reverse().find((v) => v != null);
  const option = {
    grid: { left: 4, right: 4, top: 4, bottom: 4 },
    xAxis: { type: "category", show: false, data: points.map((p) => p.hour) },
    yAxis: { type: "value", show: false, scale: true },
    series: [{ type: "line", data: values, showSymbol: false, connectNulls: false, lineStyle: { color: "#0f1c24", width: 1.5 } }],
  };
  return (
    <div className="border border-ink/5 p-2">
      <div className="flex justify-between text-xs">
        <span className="text-ink/60">{label}</span>
        <span className="font-semibold tabular-nums">{latest == null ? "—" : `${latest.toFixed(1)} ${unit}`}</span>
      </div>
      <ReactECharts option={option} style={{ height: 56 }} notMerge />
    </div>
  );
}
