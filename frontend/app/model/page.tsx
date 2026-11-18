"use client";

import ReactECharts from "echarts-for-react";
import { ApiError, Panel } from "@/components/ui";
import { api, pct } from "@/lib/api";
import { usePoll } from "@/lib/usePoll";

type BandReport = {
  threshold: number;
  normalized_utility: number;
  sensitivity: number | null;
  specificity: number | null;
  ppv: number | null;
  false_alerts_per_100_patient_hours: number;
  alerts_per_patient_day: number;
  detected_before_onset: number | null;
  detected_in_optimal_window: number | null;
  median_warning_hours: number | null;
};
type Report = {
  patients: number;
  ranking: { auroc: number; auprc: number; brier: number; ece: number; prevalence: number };
  watch: BandReport;
  high_risk: BandReport;
  utility_optimal: BandReport;
};
type Group = Record<string, { rows: number; auroc: number | null; auprc: number | null; sensitivity: number | null; detected_before_onset?: number | null }>;
type ModelCard = {
  model_version: string;
  frozen: boolean;
  model_hash?: string;
  thresholds: { watch: number; high_risk: number };
  internal_test: Record<string, Report>;
  holdout_dataset_b: (Report & {
    ranking: Report["ranking"] & { prevalence?: number };
    high_risk: BandReport;
    watch?: BandReport;
  }) | null;
  subgroups_internal_test: Record<string, Group>;
  subgroups_holdout?: Record<string, Group> | null;
  release_criteria_internal_test: Record<string, boolean | number>;
  global_shap_top25: Record<string, number>;
  cpu_latency_ms_per_prediction: number;
  label_definition?: string;
  validation_wording?: string;
};

const MODELS: [string, string][] = [
  ["clinical_rule", "SIRS-style rule"],
  ["logistic", "Logistic regression"],
  ["lightgbm", "PredictRx (LightGBM)"],
];

export default function ModelPage() {
  const { data, error } = usePoll(() => api<ModelCard>("/v1/model"), 30000);
  if (error) return <ApiError error={error} />;
  if (!data) return <p className="text-sm text-ink/60">Loading model card…</p>;
  const t = data.internal_test;
  const num = (v: number | null | undefined, d = 3) => (v == null ? "—" : v.toFixed(d));

  const rows: [string, (r: Report) => string][] = [
    ["AUROC", (r) => num(r.ranking.auroc)],
    ["AUPRC", (r) => num(r.ranking.auprc)],
    ["Calibration error (ECE)", (r) => num(r.ranking.ece, 4)],
    ["Brier score", (r) => num(r.ranking.brier, 4)],
    ["PhysioNet utility (challenge-optimal threshold)", (r) => num(r.utility_optimal?.normalized_utility)],
    ["PhysioNet utility (high-risk alert threshold)", (r) => num(r.high_risk.normalized_utility)],
    ["Hour-level sensitivity (high risk)", (r) => pct(r.high_risk.sensitivity, 1)],
    ["Hour-level specificity (high risk)", (r) => pct(r.high_risk.specificity, 1)],
    ["Septic patients alerted before onset", (r) => pct(r.high_risk.detected_before_onset, 1)],
    ["…of which 0–12 h before onset", (r) => pct(r.high_risk.detected_in_optimal_window, 1)],
    ["Median warning (all early alerts)", (r) => (r.high_risk.median_warning_hours == null ? "—" : `${r.high_risk.median_warning_hours} h`)],
    ["False alerts / 100 patient-hours", (r) => num(r.high_risk.false_alerts_per_100_patient_hours, 2)],
    ["Alerts / patient-day", (r) => num(r.high_risk.alerts_per_patient_day, 2)],
  ];

  const shap = Object.entries(data.global_shap_top25 ?? {}).slice(0, 15).reverse();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl">Aurie · model transparency</h1>
        <p className="mt-1 text-sm text-ink/60">
          {data.model_version} · {data.frozen ? "frozen" : "not frozen (still in development)"} · CPU latency{" "}
          {data.cpu_latency_ms_per_prediction?.toFixed(0)} ms per prediction
        </p>
      </div>

      <Panel title="Internal test (Dataset A patients never used for training, calibration or thresholds)">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[36rem] text-left text-sm">
            <thead className="text-xs text-ink/50">
              <tr>
                <th className="py-2 font-medium">Metric</th>
                {MODELS.map(([k, label]) => (
                  <th key={k} className={`py-2 font-medium ${k === "lightgbm" ? "text-accent" : ""}`}>{label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map(([label, f]) => (
                <tr key={label} className="border-t border-ink/5">
                  <td className="py-1.5">{label}</td>
                  {MODELS.map(([k]) => (
                    <td key={k} className={`py-1.5 tabular-nums ${k === "lightgbm" ? "font-semibold" : "text-ink/70"}`}>
                      {t[k] ? f(t[k]) : "—"}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs text-ink/50">
          {t.lightgbm?.patients.toLocaleString()} patients · prevalence {pct(t.lightgbm?.ranking.prevalence, 1)} of
          patient-hours. Thresholds (Watch {pct(data.thresholds.watch, 1)}, High risk {pct(data.thresholds.high_risk, 1)})
          were chosen on validation patients only.
        </p>
      </Panel>

      <Panel title="Cross-hospital holdout (Dataset B)">
        {data.holdout_dataset_b ? (
          <div className="space-y-3 text-sm">
            <p>
              {data.validation_wording ??
                "Site-held-out retrospective validation on a geographically distinct public hospital cohort."}
            </p>
            <p className="text-xs text-ink/55">{data.label_definition}</p>
            <dl className="grid gap-2 sm:grid-cols-2">
              <div>AUROC <span className="font-semibold tabular-nums">{num(data.holdout_dataset_b.ranking.auroc)}</span></div>
              <div>AUPRC <span className="font-semibold tabular-nums">{num(data.holdout_dataset_b.ranking.auprc)}</span></div>
              <div>ECE <span className="font-semibold tabular-nums">{num(data.holdout_dataset_b.ranking.ece, 4)}</span></div>
              <div>High-risk utility <span className="font-semibold tabular-nums">{num(data.holdout_dataset_b.high_risk.normalized_utility)}</span></div>
              <div>Pre-onset detection <span className="font-semibold tabular-nums">{pct(data.holdout_dataset_b.high_risk.detected_before_onset, 1)}</span></div>
              <div>0–12 h window <span className="font-semibold tabular-nums">{pct(data.holdout_dataset_b.high_risk.detected_in_optimal_window, 1)}</span></div>
              <div>False alerts / 100 h <span className="font-semibold tabular-nums">{num(data.holdout_dataset_b.high_risk.false_alerts_per_100_patient_hours, 2)}</span></div>
              <div>Median warning <span className="font-semibold tabular-nums">{data.holdout_dataset_b.high_risk.median_warning_hours ?? "—"} h</span></div>
            </dl>
            <p className="text-xs text-ink/55">
              Public Challenge training set B, not secret Hospital C. Not prospective, not Bangladesh-validated, and not
              clinical outcome evidence. In the preregistered one-time comparison, Run 4 beat the clinical-rule and logistic
              baselines on AUPRC and utility (paired patient bootstrap intervals exclude zero). 95% CI: AUROC 0.797–0.820,
              AUPRC 0.071–0.090, utility 0.213–0.263. Calibration slope 0.80, so local recalibration is required.
            </p>
          </div>
        ) : (
          <p className="text-sm text-ink/60">
            Dataset B metrics are not loaded. The frozen holdout file is scored exactly once after freeze.
          </p>
        )}
      </Panel>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="What the model relies on (mean |SHAP|, validation)">
          <ReactECharts
            style={{ height: 380 }}
            option={{
              grid: { left: 150, right: 16, top: 8, bottom: 24 },
              xAxis: { type: "value", axisLabel: { color: "#667085" } },
              yAxis: { type: "category", data: shap.map(([k]) => k), axisLabel: { color: "#0f1c24", fontSize: 11 } },
              series: [{ type: "bar", data: shap.map(([, v]) => v), itemStyle: { color: "#0e7490" } }],
            }}
          />
        </Panel>
        <Panel title="Release criteria (internal test)">
          <ul className="space-y-2 text-sm">
            {Object.entries(data.release_criteria_internal_test ?? {}).map(([k, v]) => (
              <li key={k} className="flex justify-between gap-2 border-b border-ink/5 pb-1">
                <span>{k.replaceAll("_", " ")}</span>
                <span className={typeof v === "boolean" ? (v ? "text-risk-stable" : "text-risk-high") : ""}>
                  {typeof v === "boolean" ? (v ? "pass" : "fail") : `${(v * 100).toFixed(1)}%`}
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-4 text-xs text-ink/55">
            Trained on US ICU data (PhysioNet 2019). This is not evidence of validity for Bangladeshi patients; local
            retrospective validation and recalibration come before any pilot.
          </p>
        </Panel>
      </div>

      <Panel title="AI system reasoning — why this architecture, not the most complex model">
        <div className="grid gap-5 text-sm lg:grid-cols-3">
          <div>
            <p className="font-medium">Input and representation</p>
            <p className="mt-1 text-ink/60">
              Validated observations become past-only 24-hour trends, freshness, missingness, ratios and organ-context
              features. Unknown codes and units are quarantined before inference.
            </p>
          </div>
          <div>
            <p className="font-medium">Model selection discipline</p>
            <p className="mt-1 text-ink/60">
              Frozen LightGBM beat the clinical-rule and logistic baselines on the preregistered holdout. GRU-D, TCN,
              organ-graph, residual-hazard and broader tabular challengers failed the locked utility gate and were rejected.
            </p>
          </div>
          <div>
            <p className="font-medium">Output and evidence boundary</p>
            <p className="mt-1 text-ink/60">
              Calibration and TrustGate turn a score into Alert, Watch, Verify data or Abstain. TreeSHAP explains model
              influence; separately retrieved, versioned guideline passages provide non-causal context and refuse
              treatment or dosing queries.
            </p>
          </div>
        </div>
        <p className="mt-4 border-t border-ink/10 pt-3 text-xs text-ink/55">
          Complexity was not rewarded for its own sake. Negative experiments remain in the ledger so judges and hospitals
          can verify why the simpler frozen model shipped and what evidence would be required to replace it.
        </p>
      </Panel>

      <Panel title="Fairness and robustness (internal test, high-risk threshold)">
        <div className="grid gap-4 md:grid-cols-2">
          {Object.entries(data.subgroups_internal_test ?? {}).map(([gname, groups]) => (
            <div key={gname}>
              <p className="mb-1 text-xs font-medium uppercase tracking-wide text-ink/50">{gname.replace("_", " ")}</p>
              <table className="w-full text-left text-sm">
                <thead className="text-xs text-ink/45">
                  <tr><th className="font-medium">Group</th><th className="font-medium">AUROC</th><th className="font-medium">AUPRC</th><th className="font-medium">Sensitivity</th></tr>
                </thead>
                <tbody>
                  {Object.entries(groups).map(([g, m]) => (
                    <tr key={g} className="border-t border-ink/5">
                      <td className="py-1">{g}</td>
                      <td className="tabular-nums">{num(m.auroc)}</td>
                      <td className="tabular-nums">{num(m.auprc)}</td>
                      <td className="tabular-nums">{pct(m.sensitivity, 1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
