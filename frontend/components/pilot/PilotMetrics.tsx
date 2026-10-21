"use client";

import ReactECharts from "echarts-for-react";
import { KeyValue, Panel, Pill, Stat } from "@/components/ui";
import { pct } from "@/lib/api";
import { humanize } from "@/lib/pilot";

type Group = {
  encounters: number;
  patient_hours: number;
  coverage: number | null;
  alerts: number;
  alerts_per_100_patient_hours: number | null;
  adjudicated_sepsis: number;
  sensitivity: number | null;
};

export type PilotMetricsData = {
  generated_at: string;
  scope: { unit_id: string | null; pilot_only: boolean };
  site_mode: string;
  model_version: string;
  thresholds: { watch: number; high_risk: number };
  volume: { encounters: number; patient_hours: number; scored_hours: number; pilot_days: number; first_scored_at: string | null; last_scored_at: string | null };
  coverage: { covered_rate: number | null; trust_states: Record<string, number>; insufficient_history_rate: number | null };
  missingness: Record<string, { missing_rate: number | null; stale_over_2h_rate: number | null }>;
  latency: { median_processing_ms: number | null; p95_processing_ms: number | null; median_source_lag_minutes: number | null; p95_source_lag_minutes: number | null };
  alert_burden: { alerts: number; shadow_alerts: number; interruptive_alerts: number; alerts_per_100_patient_hours: number | null; alerts_per_encounter_day: number | null };
  detection: {
    adjudicated_sepsis: number;
    adjudicated_no_sepsis: number;
    detected: number;
    sensitivity: number | null;
    median_lead_hours: number | null;
    no_sepsis_encounters_with_alert: number;
    false_alert_encounter_rate: number | null;
    window: string;
  };
  calibration: {
    status: "computed" | "insufficient_labels";
    labelled_hours: number;
    positive_hours: number;
    prevalence?: number;
    mean_predicted?: number;
    calibration_in_the_large?: number;
    brier?: number;
    bins?: { range: [number, number]; n: number; mean_predicted: number; observed_rate: number }[];
    label_definition: string;
  };
  subgroups: { sex: Record<string, Group>; age_band: Record<string, Group> };
  review: { sla_minutes: number; acknowledged_alerts: number; median_minutes_to_first_action: number | null; p90_minutes_to_first_action: number | null; within_sla_rate: number | null; open_past_sla: number };
  feedback: { usefulness: Record<string, number>; workflow: Record<string, number>; total: number };
  threshold_simulation: {
    note: string;
    rows: {
      threshold: number;
      is_current_high_risk: boolean;
      is_current_watch: boolean;
      flagged_hour_rate: number | null;
      episodes: number;
      episodes_per_100_patient_hours: number | null;
      sensitivity: number | null;
      false_alert_encounter_rate: number | null;
    }[];
  };
  trends: { date: string; patient_hours: number; mean_probability: number | null; mean_input_shift: number | null; missing_required_rate: number | null; alerts: number; quarantined_received_that_day: number }[];
};

const num = (value: number | null | undefined, digits = 2) => (value == null ? "—" : value.toFixed(digits));

export function PilotMetrics({ metrics }: { metrics: PilotMetricsData }) {
  const { volume, coverage, latency, alert_burden: burden, detection, calibration, review, feedback } = metrics;
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3">
        <Stat label="Encounters" value={volume.encounters} />
        <Stat label="Patient-hours" value={volume.patient_hours} />
        <Stat label="Pilot days" value={volume.pilot_days} />
        <Stat label="Covered" value={pct(coverage.covered_rate)} />
        <Stat label="Alerts /100 h" value={num(burden.alerts_per_100_patient_hours)} />
        <Stat label="Sensitivity" value={pct(detection.sensitivity)} />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Panel title="Detection (adjudicated)">
          <dl>
            <KeyValue label="Sepsis / no sepsis" value={`${detection.adjudicated_sepsis} / ${detection.adjudicated_no_sepsis}`} />
            <KeyValue label="Detected" value={detection.detected} />
            <KeyValue label="Sensitivity" value={pct(detection.sensitivity)} />
            <KeyValue label="Median lead" value={detection.median_lead_hours == null ? "—" : `${detection.median_lead_hours} h`} />
            <KeyValue label="No-sepsis encounters alerted" value={`${detection.no_sepsis_encounters_with_alert} (${pct(detection.false_alert_encounter_rate)})`} />
          </dl>
          <p className="mt-2 text-xs text-ink/55">Window: {detection.window}.</p>
        </Panel>
        <Panel title="Calibration">
          {calibration.status === "insufficient_labels" ? (
            <p className="text-sm text-ink/60">
              Not enough adjudicated hours yet ({calibration.labelled_hours} labelled, {calibration.positive_hours} positive; need ≥ 20
              with ≥ 1 positive).
            </p>
          ) : (
            <>
              <dl>
                <KeyValue label="Prevalence (hourly)" value={pct(calibration.prevalence, 1)} />
                <KeyValue label="Mean predicted" value={pct(calibration.mean_predicted, 1)} />
                <KeyValue label="Calibration-in-the-large" value={num(calibration.calibration_in_the_large, 4)} />
                <KeyValue label="Brier" value={num(calibration.brier, 4)} />
              </dl>
              <CalibrationChart bins={calibration.bins ?? []} />
            </>
          )}
          <p className="mt-2 text-xs text-ink/55">{calibration.label_definition}</p>
        </Panel>
        <Panel title="Burden, latency & review">
          <dl>
            <KeyValue label="Shadow / interruptive" value={`${burden.shadow_alerts} / ${burden.interruptive_alerts}`} />
            <KeyValue label="Alerts per encounter-day" value={num(burden.alerts_per_encounter_day)} />
            <KeyValue label="Processing p50 / p95" value={`${num(latency.median_processing_ms, 0)} / ${num(latency.p95_processing_ms, 0)} ms`} />
            <KeyValue label="Source lag p50 / p95" value={`${num(latency.median_source_lag_minutes, 1)} / ${num(latency.p95_source_lag_minutes, 1)} min`} />
            <KeyValue label="Time to first action p50" value={review.median_minutes_to_first_action == null ? "—" : `${review.median_minutes_to_first_action} min`} />
            <KeyValue label={`Within ${review.sla_minutes} min SLA`} value={pct(review.within_sla_rate)} />
            <KeyValue label="Open past SLA" value={review.open_past_sla} />
          </dl>
        </Panel>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Threshold simulation (recorded predictions only)">
          <SimulationChart rows={metrics.threshold_simulation.rows} />
          <table className="mt-2 w-full text-left text-xs">
            <thead className="text-ink/50">
              <tr>
                <th className="py-1 font-medium">Threshold</th>
                <th className="py-1 font-medium">Episodes /100 h</th>
                <th className="py-1 font-medium">Flagged hours</th>
                <th className="py-1 font-medium">Sensitivity</th>
                <th className="py-1 font-medium">No-sepsis alerted</th>
              </tr>
            </thead>
            <tbody>
              {metrics.threshold_simulation.rows.map((row) => (
                <tr key={row.threshold} className={`border-t border-ink/5 ${row.is_current_high_risk || row.is_current_watch ? "font-semibold" : ""}`}>
                  <td className="py-1 tabular-nums">
                    {pct(row.threshold, 1)} {row.is_current_high_risk && <Pill tone="danger">high risk</Pill>} {row.is_current_watch && <Pill tone="warning">watch</Pill>}
                  </td>
                  <td className="py-1 tabular-nums">{num(row.episodes_per_100_patient_hours)}</td>
                  <td className="py-1 tabular-nums">{pct(row.flagged_hour_rate, 1)}</td>
                  <td className="py-1 tabular-nums">{pct(row.sensitivity)}</td>
                  <td className="py-1 tabular-nums">{pct(row.false_alert_encounter_rate)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-xs text-ink/55">{metrics.threshold_simulation.note}</p>
        </Panel>
        <Panel title="Daily drift & data quality">
          <TrendChart trends={metrics.trends} />
          <p className="mt-2 text-xs text-ink/55">
            Mean probability and input-shift proxy by source day; rising missingness or quarantine usually means a feed or
            documentation change, not a sicker population.
          </p>
        </Panel>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Panel title="Subgroups">
          {(["sex", "age_band"] as const).map((key) => (
            <table key={key} className="mb-3 w-full text-left text-xs">
              <thead className="text-ink/50">
                <tr>
                  <th className="py-1 font-medium">{humanize(key)}</th>
                  <th className="py-1 font-medium">Enc.</th>
                  <th className="py-1 font-medium">Alerts /100 h</th>
                  <th className="py-1 font-medium">Sens. (n)</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(metrics.subgroups[key]).map(([group, values]) => (
                  <tr key={group} className="border-t border-ink/5">
                    <td className="py-1">{group}</td>
                    <td className="py-1 tabular-nums">{values.encounters}</td>
                    <td className="py-1 tabular-nums">{num(values.alerts_per_100_patient_hours)}</td>
                    <td className="py-1 tabular-nums">{pct(values.sensitivity)} ({values.adjudicated_sepsis})</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ))}
          <p className="text-xs text-ink/55">Small subgroups are unstable; read counts before rates.</p>
        </Panel>
        <Panel title="Missing required signals">
          <dl>
            {Object.entries(metrics.missingness).map(([signal, values]) => (
              <KeyValue key={signal} label={signal} value={`${pct(values.missing_rate)} missing · ${pct(values.stale_over_2h_rate)} > 2 h old`} />
            ))}
            <KeyValue label="Insufficient history" value={pct(coverage.insufficient_history_rate)} />
          </dl>
        </Panel>
        <Panel title={`Clinician feedback (${feedback.total})`}>
          <dl>
            {Object.entries(feedback.usefulness).map(([key, value]) => (
              <KeyValue key={key} label={humanize(key)} value={value} />
            ))}
          </dl>
          <p className="mt-2 text-xs font-medium uppercase tracking-wide text-ink/50">Workflow tags</p>
          <dl>
            {Object.entries(feedback.workflow).map(([key, value]) => (
              <KeyValue key={key} label={humanize(key)} value={value} />
            ))}
          </dl>
        </Panel>
      </div>
    </div>
  );
}

function CalibrationChart({ bins }: { bins: { mean_predicted: number; observed_rate: number; n: number }[] }) {
  const max = Math.max(0.05, ...bins.map((bin) => Math.max(bin.mean_predicted, bin.observed_rate))) * 1.1;
  const option = {
    grid: { left: 44, right: 12, top: 12, bottom: 32 },
    xAxis: { type: "value", name: "predicted", nameLocation: "middle", nameGap: 20, min: 0, max, axisLabel: { formatter: (v: number) => `${Math.round(v * 100)}%` } },
    yAxis: { type: "value", min: 0, max, axisLabel: { formatter: (v: number) => `${Math.round(v * 100)}%` } },
    tooltip: { trigger: "item" },
    series: [
      { type: "line", data: [[0, 0], [max, max]], showSymbol: false, lineStyle: { type: "dashed", color: "#98a2b3" } },
      { type: "scatter", data: bins.map((bin) => [bin.mean_predicted, bin.observed_rate, bin.n]), symbolSize: 10, itemStyle: { color: "#0e7490" } },
    ],
  };
  return <ReactECharts option={option} style={{ height: 180 }} notMerge />;
}

function SimulationChart({ rows }: { rows: PilotMetricsData["threshold_simulation"]["rows"] }) {
  const option = {
    grid: { left: 44, right: 44, top: 24, bottom: 28 },
    legend: { top: 0, textStyle: { fontSize: 10 } },
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: rows.map((row) => `${(row.threshold * 100).toFixed(1)}%`) },
    yAxis: [
      { type: "value", name: "/100 h", nameTextStyle: { fontSize: 10 } },
      { type: "value", min: 0, max: 1, axisLabel: { formatter: (v: number) => `${Math.round(v * 100)}%` } },
    ],
    series: [
      { name: "Episodes /100 h", type: "bar", data: rows.map((row) => row.episodes_per_100_patient_hours), itemStyle: { color: "#b7791f" } },
      { name: "Sensitivity", type: "line", yAxisIndex: 1, data: rows.map((row) => row.sensitivity), itemStyle: { color: "#0e7490" } },
    ],
  };
  return <ReactECharts option={option} style={{ height: 200 }} notMerge />;
}

function TrendChart({ trends }: { trends: PilotMetricsData["trends"] }) {
  const option = {
    grid: { left: 44, right: 44, top: 24, bottom: 28 },
    legend: { top: 0, textStyle: { fontSize: 10 } },
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: trends.map((day) => day.date) },
    yAxis: [
      { type: "value", axisLabel: { formatter: (v: number) => `${Math.round(v * 100)}%` } },
      { type: "value", name: "count", nameTextStyle: { fontSize: 10 } },
    ],
    series: [
      { name: "Mean probability", type: "line", data: trends.map((day) => day.mean_probability), itemStyle: { color: "#0e7490" } },
      { name: "Input shift", type: "line", data: trends.map((day) => day.mean_input_shift), itemStyle: { color: "#667085" } },
      { name: "Missing required", type: "line", data: trends.map((day) => day.missing_required_rate), itemStyle: { color: "#b42318" } },
      { name: "Alerts", type: "bar", yAxisIndex: 1, data: trends.map((day) => day.alerts), itemStyle: { color: "#b7791f" } },
    ],
  };
  return <ReactECharts option={option} style={{ height: 220 }} notMerge />;
}
