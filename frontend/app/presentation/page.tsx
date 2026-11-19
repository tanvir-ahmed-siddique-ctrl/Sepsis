"use client";

import { useCallback, useEffect, useState } from "react";
import ReactECharts from "echarts-for-react";
import { RiskBadge, TrustBadge } from "@/components/RiskBadge";
import { ApiError, BAND_COLOR } from "@/components/ui";
import { Icon } from "@/components/ui/Icon";
import { api, pct, type RiskCurrent, type RiskPoint, type Thresholds } from "@/lib/api";
import { useLocale } from "@/lib/locale";

type Status = {
  model_version: string;
  source_split: string | null;
  median_warning_hours_test: number | null;
  patients: { patient_id: string; kind: string; labelled_onset_hour: number | null; remaining_hours: number }[];
};

/** Replay presentation using the current site's declared source provenance. */
export default function PresentationPage() {
  const { t, locale, setLocale } = useLocale();
  const [status, setStatus] = useState<Status | null>(null);
  const [bed, setBed] = useState<string | null>(null);
  const [current, setCurrent] = useState<RiskCurrent | null>(null);
  const [points, setPoints] = useState<RiskPoint[]>([]);
  const [thresholds, setThresholds] = useState<Thresholds | null>(null);
  const [playing, setPlaying] = useState(false);
  const [pitchSeconds, setPitchSeconds] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (target: string) => {
    const [c, t] = await Promise.all([
      api<RiskCurrent>(`/v1/patients/${target}/risk/current`),
      api<{ points: RiskPoint[]; thresholds: Thresholds }>(`/v1/patients/${target}/risk/timeline`),
    ]);
    setCurrent(c);
    setPoints(t.points);
    setThresholds(t.thresholds);
  }, []);

  const start = useCallback(async () => {
    try {
      await api("/v1/demo/replay/reset", { method: "POST" });
      const s = await api<Status>("/v1/demo/replay/status");
      const target = s.patients.find((p) => p.kind === "typical_detection")?.patient_id ?? s.patients[0].patient_id;
      setStatus(s);
      setBed(target);
      await load(target);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [load]);

  useEffect(() => { void start(); }, [start]);

  useEffect(() => {
    if (!playing || !bed) return;
    const t = setInterval(async () => {
      await api("/v1/demo/replay/step?hours=1", { method: "POST" });
      await load(bed);
    }, 2200);
    return () => clearInterval(t);
  }, [playing, bed, load]);

  useEffect(() => {
    if (pitchSeconds == null || pitchSeconds <= 0) return;
    const timer = setInterval(() => setPitchSeconds((seconds) => seconds == null ? null : Math.max(0, seconds - 1)), 1000);
    return () => clearInterval(timer);
  }, [pitchSeconds]);

  async function beginPitch() {
    await start();
    setPitchSeconds(180);
    setPlaying(true);
  }

  async function selectCase(target: string) {
    setPlaying(false);
    await api("/v1/demo/replay/reset", { method: "POST" });
    setBed(target);
    await load(target);
  }

  if (error) return <ApiError error={error} />;
  if (!current || !thresholds || !status) return <p className="text-center text-sm text-ink/60">Preparing replay…</p>;
  const synthetic = status.source_split?.toLowerCase().includes("synthetic") ?? false;

  const onset = status.patients.find((p) => p.patient_id === bed)?.labelled_onset_hour;
  const pastOnset = onset != null && points.length > 0 && points[points.length - 1].hour >= onset;
  const option = {
    grid: { left: 50, right: 24, top: 24, bottom: 36 },
    xAxis: { type: "category", data: points.map((p) => p.hour), name: "ICU hour", nameLocation: "middle", nameGap: 24 },
    yAxis: { type: "value", min: 0, max: 1, axisLabel: { formatter: (v: number) => `${Math.round(v * 100)}%` } },
    series: [{
      type: "line",
      smooth: true,
      data: points.map((p) => p.probability),
      lineStyle: { width: 4, color: "#0e7490" },
      areaStyle: { opacity: 0.12 },
      showSymbol: false,
      markLine: {
        symbol: "none",
        data: [
          { yAxis: thresholds.high_risk, name: "High-risk threshold", lineStyle: { color: "#b42318", type: "dashed" }, label: { formatter: "High risk" } },
          ...(pastOnset ? [{ xAxis: String(onset), name: "Labelled sepsis onset", lineStyle: { color: "#0f1c24", width: 2 }, label: { formatter: "Labelled onset" } }] : []),
        ],
      },
    }],
  };

  return (
    <div className="mx-auto max-w-6xl space-y-8 py-4">
      <div className="text-center">
        <p className="text-xs uppercase tracking-[0.2em] text-accent">International AI Builders Congress 2026 · HealthSphere AI</p>
        <h1 className="mx-auto mt-2 max-w-4xl font-display text-4xl sm:text-6xl">Earn the right to alert.</h1>
        <p className="mx-auto mt-3 max-w-3xl text-lg text-ink/65">
          Auralis connects fragmented ICU data, shows what is missing, and evaluates deterioration AI safely
          before a hospital exposes clinicians to an alert.
        </p>
        <div className="mt-5 flex flex-wrap justify-center gap-3">
          <button onClick={() => void beginPitch()} className="bg-accent px-6 py-2 font-medium text-white">
            {t.presentation.startPitch}
          </button>
          <button
            type="button"
            onClick={() => setLocale(locale === "en" ? "bn" : "en")}
            className="border border-ink/20 px-4 py-2 text-sm font-medium text-ink/70"
            aria-label="Toggle language"
          >
            {locale === "en" ? "বাংলা" : "EN"}
          </button>
          {pitchSeconds != null && (
            <span
              className={`min-w-24 border px-4 py-2 font-mono text-lg ${pitchSeconds === 0 ? "border-risk-high text-risk-high" : "border-ink/20"}`}
              aria-label={t.presentation.pitchLabel}
            >
              {Math.floor(pitchSeconds / 60)}:{String(pitchSeconds % 60).padStart(2, "0")}
            </span>
          )}
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {[
          ["0.808", "Dataset B held-out retrospective AUROC"],
          ["40,336", "public ICU stays in source datasets"],
          ["6 + edge", "implemented ingest paths"],
          ["220", "ML, backend, frontend and edge tests"],
          ["9", "gates before live alerts"],
        ].map(([value, label]) => (
          <div key={label} className="border border-ink/10 bg-white/90 p-4 text-center">
            <p className="font-display text-3xl text-accent">{value}</p>
            <p className="mt-1 text-xs text-ink/55">{label}</p>
          </div>
        ))}
      </div>

      <p className="text-center text-xs font-semibold uppercase tracking-[0.16em] text-ink/45">{t.presentation.pipelineTitle}</p>
      <div className="grid gap-px overflow-hidden border border-ink/10 bg-ink/10 md:grid-cols-4">
        {(
          locale === "bn"
            ? [
                [`1 · ${t.presentation.connect}`, "FHIR, HL7, ল্যাব CSV, মনিটর বা অফলাইন বেডসাইড চার্ট"],
                [`2 · ${t.presentation.verify}`, "ইউনিট ও কোড ম্যাপ; অজানা/অসম্ভব ডেটা কোয়ারেন্টাইন"],
                [`3 · ${t.presentation.reason}`, "অতীত-শুধু ফিচার, ফ্রোজেন Run 4, দেখার যোগ্য ড্রাইভার"],
                [`4 · ${t.presentation.govern}`, "TrustGate: Alert, Watch, Verify বা Abstain"],
              ]
            : [
                [`1 · ${t.presentation.connect}`, "FHIR, HL7, lab CSV, monitor relay or offline bedside chart"],
                [`2 · ${t.presentation.verify}`, "Map units and codes; quarantine unknown or impossible data"],
                [`3 · ${t.presentation.reason}`, "Past-only features, frozen Run 4 and inspectable drivers"],
                [`4 · ${t.presentation.govern}`, "TrustGate may Alert, Watch, Verify data or Abstain"],
              ]
        ).map(([title, detail]) => (
          <div key={title} className="bg-paper p-4">
            <p className="font-medium">{title}</p>
            <p className="mt-1 text-sm text-ink/55">{detail}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-accent">{synthetic ? "Synthetic evaluation · generated replay" : "Dataset A internal-test replay"}</p>
          <h2 className="mt-1 font-display text-3xl">{bed?.replace("BED-", "Bed ")} — ICU hour {current.hour}</h2>
        </div>
        <label className="text-xs font-medium uppercase tracking-wide text-ink/50">
          Evidence case
          <select
            className="ml-2 border border-ink/20 bg-white px-2 py-1.5 normal-case tracking-normal text-ink"
            value={bed ?? ""}
            onChange={(event) => void selectCase(event.target.value)}
          >
            {status.patients.map((patient) => (
              <option key={patient.patient_id} value={patient.patient_id}>
                {patient.patient_id.replace("BED-", "Bed ")} · {patient.kind.replaceAll("_", " ")}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="grid gap-4 md:grid-cols-[16rem_1fr]">
        <div className="border border-ink/10 bg-white/90 p-6 text-center">
          <p className="text-sm text-ink/50">Challenge-label early warning</p>
          <p className="mt-2 font-display text-7xl tabular-nums" style={{ color: BAND_COLOR[current.risk_band] }}>
            {pct(current.probability)}
          </p>
          <div className="mt-3 flex justify-center gap-2">
            <RiskBadge band={current.risk_band} />
            <TrustBadge state={current.trustgate.state} />
          </div>
          {current.uncertainty != null && <p className="mt-2 text-xs text-ink/50">±{pct(current.uncertainty, 1)} model disagreement (not confidence)</p>}
        </div>
        <div className="border border-ink/10 bg-white/90 p-2">
          <ReactECharts option={option} style={{ height: 300 }} notMerge />
        </div>
      </div>

      <div className="border border-ink/10 bg-white/90 p-5">
        <p className="text-xs uppercase tracking-wide text-ink/50">Why — top drivers this hour</p>
        <ul className="mt-2 grid gap-2 text-lg sm:grid-cols-2">
          {current.contributing_factors.slice(0, 4).map((f) => (
            <li key={f.feature}>
              <span className={`inline-flex align-[-2px] ${f.direction === "raises" ? "text-risk-high" : "text-risk-stable"}`} aria-label={f.direction === "raises" ? "Raises risk" : "Lowers risk"}><Icon name={f.direction === "raises" ? "trend-up" : "trend-down"} size={16} /></span>{" "}
              {f.plain_language}
            </li>
          ))}
        </ul>
      </div>

      <div className="flex flex-wrap items-center justify-center gap-3">
        <button onClick={() => setPlaying((p) => !p)} className="bg-accent px-6 py-2 text-white">
          {playing ? "Pause" : "Play replay"}
        </button>
        <button onClick={() => { setPlaying(false); start(); }} className="border border-ink/20 px-6 py-2 text-ink/70">
          Restart
        </button>
      </div>
      <p className="text-center text-xs text-ink/50">
        {synthetic ? "Formula-generated synthetic case" : "De-identified PhysioNet internal-test case"}, replayed hour by hour through the frozen model
        ({status.model_version}). {synthetic ? "No patient outcome or onset is implied." : `Case chosen by a fixed rule: warning time closest to the test-set median${status.median_warning_hours_test != null ? ` (${status.median_warning_hours_test} h)` : ""}.`} Research prototype — not for clinical use.
      </p>

      <div className="grid gap-4 lg:grid-cols-3">
        <section className="border border-ink/10 bg-white/90 p-5">
          <p className="text-xs uppercase tracking-wide text-ink/45">Why it is different</p>
          <h2 className="mt-1 font-display text-2xl">Safety is part of the intelligence</h2>
          <ul className="mt-3 space-y-2 text-sm text-ink/65">
            <li>• A score alone never creates an interrupt.</li>
            <li>• Freshness, missingness and perturbation stability are visible.</li>
            <li>• Ward NEWS2 and ICU ML remain clinically separated.</li>
            <li>• Every prediction, action and correction is auditable.</li>
          </ul>
        </section>
        <section className="border border-ink/10 bg-white/90 p-5">
          <p className="text-xs uppercase tracking-wide text-ink/45">Commercial path</p>
          <h2 className="mt-1 font-display text-2xl">Workflow value before clinical claims</h2>
          <ol className="mt-3 space-y-2 text-sm text-ink/65">
            <li><strong>1.</strong> Paid readiness and source assessment</li>
            <li><strong>2.</strong> One-ICU installation and integration</li>
            <li><strong>3.</strong> Workflow/research operations subscription</li>
            <li><strong>4.</strong> Clinical module only after local evidence and approval</li>
          </ol>
        </section>
        <section className="border border-ink/10 bg-white/90 p-5">
          <p className="text-xs uppercase tracking-wide text-ink/45">Scale globally</p>
          <h2 className="mt-1 font-display text-2xl">Local data plane, reusable standards</h2>
          <ul className="mt-3 space-y-2 text-sm text-ink/65">
            <li>• Hospital-controlled deployment keeps identifiable data local.</li>
            <li>• FHIR R4, HL7 v2, LOINC and IEEE 11073 mapping paths.</li>
            <li>• Bangladesh Core FHIR alignment is the national interoperability path.</li>
            <li>• Vendor packs can be reused without centralising patient records.</li>
          </ul>
        </section>
      </div>

      <div className="grid gap-4 border-y border-ink/10 py-6 md:grid-cols-[1.1fr_0.9fr]">
        <div>
          <p className="text-xs uppercase tracking-wide text-accent">Measurable first deployment</p>
          <h2 className="mt-1 font-display text-3xl">Measure the system before claiming impact.</h2>
          <p className="mt-2 max-w-2xl text-sm text-ink/60">
            Commissioning measures feed coverage, provenance, quarantine, workflow adoption, alert burden, subgroup
            limitations, restore success and implementation cost. No mortality or outcome-improvement claim is inferred.
          </p>
        </div>
        <div className="bg-mist p-5">
          <p className="text-sm font-medium">The ask</p>
          <p className="mt-2 text-xl">
            One Bangladesh hospital partner for a paid, one-ICU readiness and workflow/research deployment.
          </p>
          <p className="mt-2 text-xs text-ink/50">Cross-functional owner · bounded data source · silent model · explicit stop rules</p>
        </div>
      </div>

      <p className="text-center text-xs text-ink/45">
        Retrospective research prototype. Not approved for clinical use and not validated in Bangladesh. The model does
        not diagnose, prescribe, retrain itself or act autonomously.
      </p>
    </div>
  );
}
