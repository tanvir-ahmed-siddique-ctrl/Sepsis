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
import { ApiError, BAND_COLOR, PageHeader, Panel, Pill } from "@/components/ui";
import { Icon } from "@/components/ui/Icon";
import { api, isStatus, pct, type Alert, type AuditEvent, type RiskCurrent, type RiskPoint, type Thresholds } from "@/lib/api";
import { reviewClock } from "@/lib/pilot";
import { usePoll } from "@/lib/usePoll";

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
  if (!data) return <p className="text-sm text-muted">Loading patient risk…</p>;
  const { current, points, thresholds, alerts, audit, evidence } = data;
  const openAlert = alerts.find((a) => a.status === "open");
  const requiredSignals = ["HR", "SBP", "MAP", "O2Sat"];
  const title = current.source_mode === "replay" ? current.patient_id.replace("BED-", "Bed ") : current.patient_id;
  const sourceLabel = current.source_mode === "api" ? "hospital connector" : "scored encounter";

  return (
    <div className="space-y-6">
      <PageHeader
        title={title}
        description={`ICU hour ${current.hour} · ${current.unit_id} · ${sourceLabel} · model ${current.model_version}`}
        back={{ href: "/icu", label: "ICU board" }}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <TrustBadge state={current.trustgate.state} />
            <Pill>Owner: {current.owner ?? "unassigned"}</Pill>
            {current.source_mode === "replay" && <ReplayControls onChange={refresh} />}
          </div>
        }
      />

      {current.trustgate.state === "verify_data" && (
        <Panel className="border-teal/30 bg-teal-soft/40" title="Verify data — do not treat this as a reliable alarm">
          <p className="text-sm leading-6 text-ink">
            The score exists, but freshness, availability, or perturbation stability failed the reliability gate.
            Confirm the source observations before interrupting care.
          </p>
          <p className="mt-2 text-xs text-muted">{current.trustgate.reasons.map((reason) => reason.replaceAll("_", " ")).join(" · ")}</p>
        </Panel>
      )}
      {current.trustgate.state === "abstain" && (
        <Panel className="border-border bg-muted-surface" title="Abstain — not enough reliable input to interrupt">
          <p className="text-sm leading-6 text-ink">
            TrustGate withheld coverage because history is incomplete or required vitals are severely stale or missing.
          </p>
          <p className="mt-2 text-xs text-muted">{current.trustgate.reasons.map((reason) => reason.replaceAll("_", " ")).join(" · ")}</p>
        </Panel>
      )}
      {openAlert && (
        <Panel className="border-risk-high/40 bg-risk-high/[0.04]" title="Open alert — clinician review required">
          <p className="text-sm leading-6 text-ink">{openAlert.reason}</p>
          <p className="mb-3 mt-1 text-xs text-muted">
            Raised at ICU hour {openAlert.hour} · data quality {openAlert.data_quality} · model {openAlert.model_version} ·{" "}
            <span className={openAlert.overdue ? "font-semibold text-risk-high" : ""}>{reviewClock(openAlert).label}</span>
          </p>
          <AlertActions alertId={openAlert.alert_id} onDone={(m) => { setMessage(m); refresh(); }} />
        </Panel>
      )}
      {message && (
        <p role="status" className="rounded-lg border border-teal/25 bg-teal-soft/40 px-3.5 py-2.5 text-sm text-ink">
          {message}
        </p>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <Panel>
          <div className="flex items-center justify-between">
            <p className="auralis-eyebrow">Calibrated probability</p>
            <RiskBadge band={current.risk_band} />
          </div>
          <p className="mt-2 text-5xl font-semibold tabular-nums tracking-tight" style={{ color: BAND_COLOR[current.risk_band] }}>
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
          <p className="mt-3 text-xs text-muted">
            {current.trustgate.reasons.map((reason) => reason.replaceAll("_", " ")).join(" · ")}
          </p>
        </Panel>
        <Panel title="Risk timeline" className="lg:col-span-2">
          <RiskChart points={points} thresholds={thresholds} />
        </Panel>
      </div>

      <Panel title="Why the model scored this hour this way" description="TreeSHAP contributions grouped by clinical variable. They explain the model's score — they are not a diagnosis or treatment advice.">
        {current.contributing_factors.length === 0 ? (
          <p className="text-sm text-muted">Not enough observed hours to score yet.</p>
        ) : (
          <ul className="space-y-2">
            {current.contributing_factors.map((f) => {
              const max = Math.max(...current.contributing_factors.map((x) => x.magnitude));
              return (
                <li key={f.feature} className="grid grid-cols-[1fr_auto] items-center gap-3 border-b border-border pb-2 sm:grid-cols-[14rem_1fr_auto]">
                  <div>
                    <p className="text-sm font-medium text-ink">{f.plain_language}</p>
                    <p className="text-xs text-muted">{f.organ_system}</p>
                  </div>
                  <div className="hidden h-2 rounded-full bg-muted-surface sm:block">
                    <div
                      className={f.direction === "raises" ? "h-2 rounded-full bg-risk-high/70" : "h-2 rounded-full bg-risk-stable/70"}
                      style={{ width: `${(f.magnitude / max) * 100}%` }}
                    />
                  </div>
                  <span className={`inline-flex items-center gap-1 text-xs font-semibold ${f.direction === "raises" ? "text-risk-high" : "text-risk-stable"}`}>
                    <Icon name={f.direction === "raises" ? "trend-up" : "trend-down"} size={14} />
                    {f.direction === "raises" ? "Raises" : "Lowers"}
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
            <p className="text-sm text-muted">No scored feature to map yet.</p>
          ) : (
            <div className="space-y-4">
              {evidence.map((item) => (
                <dl key={item.feature} className="space-y-1.5 border-b border-border pb-3 text-sm">
                  <p className="font-medium text-ink">{item.feature}</p>
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
              <p className="text-xs text-muted">
                Graph {evidence[0].graph_version}. {evidence[0].model_influence.meaning} {evidence[0].disclaimer}
              </p>
            </div>
          )}
        </Panel>
        <Panel title="Required-vital freshness" description="Conservative aggregate uses the oldest of HR, SBP, MAP, and SpO2 — not the freshest one vital.">
          <ul className="space-y-1 text-sm">
            {requiredSignals.map((signal) => {
              const minutes = current.signal_freshness_minutes?.[signal];
              return (
                <li key={signal} className="flex justify-between border-b border-border py-1.5">
                  <span className="text-ink">{signal}</span>
                  <span className="tabular-nums text-muted">{minutes == null ? "missing" : `${minutes} min`}</span>
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
            <p className="text-sm text-muted">No alerts for this patient.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {alerts.map((a) => (
                <li key={a.alert_id} className="flex justify-between gap-2 border-b border-border pb-2">
                  <span className="text-ink">Hour {a.hour} · {a.reason}</span>
                  <span className="shrink-0 text-xs uppercase text-muted">{a.status}</span>
                </li>
              ))}
            </ul>
          )}
        </Panel>
        <Panel title="Audit trail">
          <ul className="space-y-1 font-mono text-xs text-muted">
            {audit.map((e) => (
              <li key={e.audit_id}>
                {e.event} {e.hour != null ? `· h${e.hour}` : ""} {e.risk_band ? `· ${e.risk_band}` : ""}{" "}
                {e.user_id ? `· ${e.user_id}` : ""} <span className="text-muted/70">{e.audit_id}</span>
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
      <dt className="text-muted">{label}</dt>
      <dd className="text-right capitalize text-ink">{value}</dd>
    </div>
  );
}

function RiskChart({ points, thresholds }: { points: RiskPoint[]; thresholds: Thresholds }) {
  // Prefer a readable recent window; keep enough history that a line (not a lone pin) can form.
  const windowed = points.length > 48 ? points.slice(-48) : points;
  const scored = windowed.filter((p) => p.probability != null);
  // If almost everything is abstain/null, still plot the scored hours so the trend is visible.
  const seriesPoints = scored.length >= 2 && scored.length / Math.max(windowed.length, 1) < 0.25 ? scored : windowed;
  const categories = seriesPoints.map((p) => `h${p.hour}`);
  const values = seriesPoints.map((p) => p.probability);
  const scoredCount = values.filter((v) => v != null).length;
  const peak = Math.max(thresholds.high_risk, thresholds.watch, ...values.filter((v): v is number => v != null), 0.05);
  const alertPts = seriesPoints
    .filter((p) => p.alert_id && p.probability != null)
    .map((p) => ({ coord: [`h${p.hour}`, p.probability] as [string, number], value: "alert", name: "alert" }));

  const option = {
    grid: { left: 48, right: 28, top: 28, bottom: 32 },
    xAxis: {
      type: "category",
      data: categories,
      boundaryGap: false,
      axisLabel: {
        color: "#667085",
        hideOverlap: true,
        interval: categories.length > 24 ? Math.floor(categories.length / 8) : 0,
      },
      axisTick: { alignWithLabel: true },
    },
    yAxis: {
      type: "value",
      min: 0,
      max: Math.min(1, Math.max(0.25, peak * 1.25)),
      splitLine: { lineStyle: { color: "#EEF2F6" } },
      axisLabel: { formatter: (v: number) => `${Math.round(v * 100)}%`, color: "#667085" },
    },
    tooltip: {
      trigger: "axis",
      valueFormatter: (v: number | null) => (v == null ? "—" : `${(v * 100).toFixed(1)}%`),
    },
    series: [
      {
        type: "line",
        smooth: scoredCount > 3,
        data: values,
        showSymbol: true,
        symbolSize: scoredCount <= 3 ? 10 : 6,
        connectNulls: true,
        lineStyle: { width: 2.5, color: "#0e7490" },
        itemStyle: { color: "#0e7490", borderColor: "#fff", borderWidth: 1 },
        areaStyle: {
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(14,116,144,0.22)" },
              { offset: 1, color: "rgba(14,116,144,0.02)" },
            ],
          },
        },
        markLine: {
          symbol: "none",
          label: { formatter: "{b}", color: "#667085", position: "insideEndTop" },
          data: [
            { name: "W", yAxis: thresholds.watch, lineStyle: { color: "#b7791f", type: "dashed", width: 1.5 } },
            { name: "Hi", yAxis: thresholds.high_risk, lineStyle: { color: "#b42318", type: "dashed", width: 1.5 } },
          ],
        },
        markPoint: {
          symbol: "pin",
          symbolSize: 40,
          itemStyle: { color: "#b42318" },
          label: { formatter: "alert", color: "#fff", fontSize: 10 },
          data: alertPts,
        },
      },
    ],
  };

  if (seriesPoints.length === 0) {
    return <p className="py-16 text-center text-sm text-muted">No scored hours yet for this encounter.</p>;
  }

  return <ReactECharts option={option} style={{ height: 280 }} notMerge opts={{ renderer: "canvas" }} />;
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
    <div className="rounded-xl border border-border bg-white p-3 shadow-soft">
      <div className="flex justify-between text-xs">
        <span className="text-muted">{label}</span>
        <span className="font-semibold tabular-nums text-ink">{latest == null ? "—" : `${latest.toFixed(1)} ${unit}`}</span>
      </div>
      <ReactECharts option={option} style={{ height: 56 }} notMerge />
    </div>
  );
}
