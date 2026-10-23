"use client";

import { useState } from "react";
import { Panel, Pill } from "@/components/ui";
import { api } from "@/lib/api";
import { humanize } from "@/lib/pilot";
import { usePoll } from "@/lib/usePoll";

type Candidate = {
  code: string;
  display: string;
  target: string;
  canonical_unit: string | null;
  score: number;
  semantic_similarity: number | null;
  matched_terms: string[];
  unit_status: string;
  conversion: { factor: number; offset: number } | null;
  range_status: string;
};

type Suggestion = {
  candidates: Candidate[];
  retrieval: { mode: string; embedding_model?: string; detail?: string };
  recommended_code: string | null;
  needs_analyst_confirmation: boolean;
  cautions: string[];
  llm: {
    status: string; detail?: string; model?: string; choice_code?: string; confidence?: string; rationale?: string;
    cautions?: string[]; provider?: string; host?: string | null; external?: boolean;
  };
  proposed_registry_patch: Record<string, unknown> | null;
  prompt: { version: string; sha256: string };
  policy: string;
};

const INPUT = "border border-ink/20 px-2 py-1.5";
const EMPTY = { local_code: "", local_display: "", local_unit: "", sample_min: "", sample_max: "" };

export function MappingCopilot() {
  const unmapped = usePoll(
    () => api<{ unmapped: { source_code: string; rejections: number }[] }>("/v1/integrations/mappings/unmapped"),
    30000,
  );
  const [form, setForm] = useState(EMPTY);
  const [useLlm, setUseLlm] = useState(true);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Suggestion | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function suggest() {
    setBusy(true);
    setError(null);
    try {
      const number = (value: string) => (value.trim() === "" ? null : Number(value));
      setResult(await api<Suggestion>("/v1/integrations/mappings/suggest", {
        method: "POST",
        body: JSON.stringify({
          local_code: form.local_code.trim(),
          local_display: form.local_display.trim(),
          local_unit: form.local_unit.trim() || null,
          sample_min: number(form.sample_min),
          sample_max: number(form.sample_max),
          use_llm: useLlm,
        }),
      }));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Panel title="Mapping copilot (proposal only)">
      <p className="-mt-2 mb-3 text-sm text-ink/70">
        <strong>What this is:</strong> a helper for IT when the hospital lab uses local codes (Bangla labels, vendor
        names) that are not yet in our LOINC registry. You type the <em>field name/unit</em> → it suggests which
        PredictRx signal (HR, Lactate, …) it might be. It never writes the registry by itself and never sees patient
        values.
      </p>
      <p className="mb-3 text-xs text-ink/55">
        Hybrid retrieval (keyword, trigram and synonym matching, optionally fused with embeddings) ranks registry
        candidates; an optional model—on-premises by default, or an API the site approves—may choose among them or
        answer &quot;none&quot;. Nothing changes until an analyst edits the registry and signs the new SHA.
      </p>
      {unmapped.data && unmapped.data.unmapped.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-2 text-xs">
          <span className="text-ink/55">Unmapped in quarantine:</span>
          {unmapped.data.unmapped.slice(0, 8).map((item) => (
            <button
              type="button"
              key={item.source_code}
              className="border border-ink/15 px-2 py-0.5 font-mono"
              onClick={() => setForm({ ...form, local_code: item.source_code.split("|").pop() ?? item.source_code })}
            >
              {item.source_code} × {item.rejections}
            </button>
          ))}
        </div>
      )}
      <form
        className="grid gap-2 text-sm sm:grid-cols-3"
        onSubmit={(event) => {
          event.preventDefault();
          void suggest();
        }}
      >
        <input className={INPUT} placeholder="Local code, e.g. LAB-77" value={form.local_code} onChange={(e) => setForm({ ...form, local_code: e.target.value })} required />
        <input className={INPUT} placeholder="Local name, e.g. S. Creatinine / নাড়ি" value={form.local_display} onChange={(e) => setForm({ ...form, local_display: e.target.value })} required />
        <input className={INPUT} placeholder="Local unit, e.g. µmol/L" value={form.local_unit} onChange={(e) => setForm({ ...form, local_unit: e.target.value })} />
        <input className={INPUT} type="number" step="any" placeholder="Typical low (optional)" value={form.sample_min} onChange={(e) => setForm({ ...form, sample_min: e.target.value })} />
        <input className={INPUT} type="number" step="any" placeholder="Typical high (optional)" value={form.sample_max} onChange={(e) => setForm({ ...form, sample_max: e.target.value })} />
        <label className="flex items-center gap-2 text-xs">
          <input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} /> Ask the model
        </label>
        <button disabled={busy} className="border border-accent bg-accent px-3 py-1.5 font-medium text-white sm:col-span-3 disabled:opacity-60">
          {busy ? "Retrieving and asking the model…" : "Suggest mapping"}
        </button>
      </form>
      {error && <p className="mt-3 text-sm text-risk-high">{error}</p>}
      {result && (
        <div className="mt-4 space-y-3 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium">Recommendation:</span>
            {result.recommended_code ? <code>{result.recommended_code}</code> : <span>none — analyst decision required</span>}
            <Pill tone={result.needs_analyst_confirmation ? "warning" : "success"}>
              {result.needs_analyst_confirmation ? "needs analyst confirmation" : "consistent evidence"}
            </Pill>
            <Pill tone="neutral">LLM {humanize(result.llm.status)}</Pill>
            {result.llm.host && (
              <Pill tone="neutral">
                {result.llm.external ? `External API · ${result.llm.host}` : `On-premises · ${result.llm.host}`}
              </Pill>
            )}
            <Pill tone="neutral">
              Retrieval {result.retrieval.mode}
              {result.retrieval.embedding_model ? ` · ${result.retrieval.embedding_model}` : ""}
            </Pill>
          </div>
          {result.cautions.map((text) => <p key={text} className="border-l-2 border-risk-watch pl-2 text-xs">{text}</p>)}
          {result.llm.status === "ok" && (
            <p className="text-xs text-ink/70">
              <strong>{result.llm.model}</strong> ({result.llm.confidence} confidence): {result.llm.rationale}
            </p>
          )}
          {result.llm.detail && <p className="text-xs text-ink/55">{result.llm.detail}</p>}
          <table className="w-full text-left text-xs">
            <thead className="text-ink/50">
              <tr><th className="py-1">LOINC</th><th>Target</th><th>Lexical score</th><th>Vector sim.</th><th>Unit</th><th>Range</th></tr>
            </thead>
            <tbody>
              {result.candidates.map((item) => (
                <tr key={item.code} className={`border-t border-ink/5 ${item.code === result.recommended_code ? "font-semibold" : ""}`}>
                  <td className="py-1 font-mono">{item.code}</td>
                  <td>{item.target}<span className="block font-normal text-ink/50">{item.display}</span></td>
                  <td>{item.score.toFixed(2)}</td>
                  <td>{item.semantic_similarity == null ? "—" : item.semantic_similarity.toFixed(2)}</td>
                  <td>{humanize(item.unit_status)}{item.conversion ? ` ×${+item.conversion.factor.toFixed(5)}` : ""}</td>
                  <td>{humanize(item.range_status)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {result.proposed_registry_patch && (
            <pre className="overflow-auto bg-ink/5 p-2 text-xs">{JSON.stringify(result.proposed_registry_patch, null, 2)}</pre>
          )}
          <p className="text-xs text-ink/55">
            {result.policy} Prompt {result.prompt.version} · {result.prompt.sha256.slice(0, 12)}…
          </p>
        </div>
      )}
    </Panel>
  );
}
