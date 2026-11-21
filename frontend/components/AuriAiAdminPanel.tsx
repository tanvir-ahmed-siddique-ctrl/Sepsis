"use client";

import { useEffect, useState } from "react";
import { Panel, Pill } from "@/components/ui";
import { api } from "@/lib/api";

type AuriStatus = {
  brand: string;
  mode: string;
  model: string | null;
  configured: boolean;
  has_api_key: boolean;
  external_approved: boolean;
  url_host: string | null;
  source: string;
  local_default: boolean;
  scores_sepsis: boolean;
  note: string;
};

/**
 * Hospital admin / clinical IT only. API keys POST to the local server and are
 * never echoed back. Public demo blocks cloud key intake.
 */
export function AuriAiAdminPanel() {
  const [status, setStatus] = useState<AuriStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    enabled: true,
    provider: "ollama" as "ollama" | "openai",
    url: "http://127.0.0.1:11434",
    model: "qwen3.5:4b",
    api_key: "",
    clear_api_key: false,
    external_approved: false,
    embed_model: "",
  });

  async function refresh() {
    try {
      const next = await api<AuriStatus>("/v1/site/auri-ai");
      setStatus(next);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Auri AI status unavailable");
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setNotice(null);
    setError(null);
    try {
      const body = {
        ...form,
        api_key: form.api_key.trim() || null,
        embed_model: form.embed_model.trim() || null,
        url: form.url.trim() || null,
      };
      const next = await api<AuriStatus>("/v1/site/auri-ai", {
        method: "PUT",
        body: JSON.stringify(body),
      });
      setStatus(next);
      setForm((prev) => ({ ...prev, api_key: "", clear_api_key: false }));
      setNotice("Auri AI settings saved on the hospital-local server. The API key is not shown again.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Panel title="Auri AI · site assistant runtime">
      <p className="max-w-3xl text-sm leading-6 text-muted">
        Local-first co-pilot for mapping, explainers, and (gated) drafts. Vendor-bundled cloud credentials — when your
        licence includes them — are installed here by admin / clinical IT. Keys stay encrypted on this hospital server;
        the browser never keeps them. Auri AI <strong className="text-ink">never</strong> writes the sepsis score.
      </p>

      {status && (
        <div className="mt-3 flex flex-wrap gap-2">
          <Pill tone={status.configured ? "success" : "neutral"}>{status.configured ? "Configured" : "Retrieval only"}</Pill>
          <Pill tone="neutral">Source · {status.source}</Pill>
          <Pill tone="neutral">{status.mode}{status.model ? ` · ${status.model}` : ""}</Pill>
          <Pill tone={status.has_api_key ? "success" : "neutral"}>
            {status.has_api_key ? "API key on server" : "No cloud key"}
          </Pill>
          <Pill tone="neutral">Scores sepsis · no</Pill>
        </div>
      )}
      {status?.note && <p className="mt-2 text-xs text-muted">{status.note}</p>}
      {error && <p className="mt-2 text-sm text-risk-high">{error}</p>}
      {notice && <p className="mt-2 text-sm text-risk-stable">{notice}</p>}

      <form className="mt-4 grid gap-3 sm:grid-cols-2" onSubmit={(event) => void save(event)}>
        <label className="text-sm">
          <span className="mb-1 block text-muted">Mode</span>
          <select
            className="auralis-input w-full"
            value={form.provider}
            onChange={(e) =>
              setForm({
                ...form,
                provider: e.target.value as "ollama" | "openai",
                url: e.target.value === "ollama" ? "http://127.0.0.1:11434" : form.url,
              })
            }
          >
            <option value="ollama">Local · Ollama / Qwen (default)</option>
            <option value="openai">Cloud · OpenAI-compatible (vendor or site key)</option>
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-muted">Model id</span>
          <input className="auralis-input w-full" value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })} />
        </label>
        <label className="text-sm sm:col-span-2">
          <span className="mb-1 block text-muted">Endpoint URL</span>
          <input className="auralis-input w-full" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} placeholder="http://127.0.0.1:11434 or https://…" />
        </label>
        <label className="text-sm sm:col-span-2">
          <span className="mb-1 block text-muted">API key (optional · write-only)</span>
          <input
            className="auralis-input w-full"
            type="password"
            autoComplete="off"
            value={form.api_key}
            onChange={(e) => setForm({ ...form, api_key: e.target.value })}
            placeholder={status?.has_api_key ? "Leave blank to keep existing server key" : "Paste once — stored encrypted on server"}
          />
        </label>
        <label className="flex items-center gap-2 text-sm text-ink">
          <input type="checkbox" checked={form.enabled} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} />
          Enable Auri LLM (otherwise deterministic retrieval only)
        </label>
        <label className="flex items-center gap-2 text-sm text-ink">
          <input
            type="checkbox"
            checked={form.external_approved}
            onChange={(e) => setForm({ ...form, external_approved: e.target.checked })}
          />
          Approve external / cloud endpoint for this site
        </label>
        <label className="flex items-center gap-2 text-sm text-ink sm:col-span-2">
          <input
            type="checkbox"
            checked={form.clear_api_key}
            onChange={(e) => setForm({ ...form, clear_api_key: e.target.checked })}
          />
          Clear stored API key
        </label>
        <div className="sm:col-span-2">
          <button type="submit" className="auralis-btn-primary" disabled={busy}>
            {busy ? "Saving…" : "Save Auri AI on local server"}
          </button>
        </div>
      </form>
    </Panel>
  );
}
