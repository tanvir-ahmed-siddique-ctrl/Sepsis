"use client";

import { useState } from "react";
import { ApiError, Panel, Pill } from "@/components/ui";
import { api, type GuidancePassage, type GuidanceResponse, type GuidanceSearch } from "@/lib/api";
import { humanize } from "@/lib/pilot";
import { usePoll } from "@/lib/usePoll";

export function GuidancePanel({ features }: { features: string[] }) {
  const key = features.join(",");
  const guidance = usePoll(
    () => (key ? api<GuidanceResponse>(`/v1/evidence/guidance?features=${encodeURIComponent(key)}`) : Promise.resolve(null)),
    60000,
    [key],
  );
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState<GuidanceSearch | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);

  async function runSearch(event: React.FormEvent) {
    event.preventDefault();
    if (query.trim().length < 2) return;
    try {
      setSearch(await api<GuidanceSearch>(`/v1/evidence/guidance/search?q=${encodeURIComponent(query.trim())}`));
      setSearchError(null);
    } catch (cause) {
      setSearchError(cause instanceof Error ? cause.message : String(cause));
    }
  }

  return (
    <Panel title="Guideline context (cited, not patient-specific)">
      <p className="-mt-2 mb-3 text-xs text-ink/55">
        Retrieved deterministically from a versioned registry and site-approved local protocols, matched to the
        organ-system concepts of the top score drivers. Treatment and dosing questions are refused by policy.
      </p>
      {guidance.error && <ApiError error={guidance.error} />}
      {guidance.data?.withheld_reason && (
        <p className="mb-2 border border-risk-watch/40 bg-risk-watch/5 px-3 py-2 text-sm">
          Guideline registry v{guidance.data.registry_version} is not yet approved by this site — only approved local
          protocols are shown.
        </p>
      )}
      <ol className="space-y-3">
        {guidance.data?.passages.slice(0, 5).map((passage) => <PassageItem key={passage.passage_id} passage={passage} />)}
      </ol>
      {guidance.data && guidance.data.passages.length === 0 && <p className="text-sm text-ink/60">No passages matched.</p>}

      <form onSubmit={runSearch} className="mt-4 flex gap-2 border-t border-ink/5 pt-3">
        <label className="sr-only" htmlFor="guidance-search">Search guideline context</label>
        <input
          id="guidance-search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          maxLength={200}
          placeholder="e.g. lactate measurement, screening, SOFA"
          className="flex-1 border border-ink/20 bg-white px-2 py-1.5 text-sm outline-none focus:border-accent"
        />
        <button type="submit" className="border border-ink/20 px-3 py-1.5 text-sm">Search</button>
      </form>
      {searchError && <p role="alert" className="mt-2 text-xs text-risk-high">{searchError}</p>}
      {search?.refused && (
        <p role="status" className="mt-2 border border-risk-high/30 bg-risk-high/5 px-3 py-2 text-sm">
          {search.refusal_reason} <span className="text-xs text-ink/55">(matched: {search.matched_terms?.join(", ")})</span>
        </p>
      )}
      {search && !search.refused && (
        <ol className="mt-3 space-y-3">
          {search.results.length === 0 && <li className="text-sm text-ink/60">No matching passages.</li>}
          {search.results.map((passage) => <PassageItem key={passage.passage_id} passage={passage} />)}
        </ol>
      )}
      <p className="mt-3 text-xs text-ink/50">{guidance.data?.disclaimer}</p>
    </Panel>
  );
}

function PassageItem({ passage }: { passage: GuidancePassage }) {
  const { citation } = passage;
  return (
    <li className="border-l-2 border-accent/40 pl-3">
      <div className="mb-1 flex flex-wrap items-center gap-1.5">
        <Pill tone={passage.source_type === "local_protocol" ? "success" : "info"}>
          {passage.source_type === "local_protocol" ? "Local protocol" : "Guideline"}
        </Pill>
        <Pill>{humanize(passage.topic)}</Pill>
        {passage.strength && <Pill>{passage.strength}</Pill>}
      </div>
      <blockquote className="text-sm">“{passage.text}”</blockquote>
      <p className="mt-1 text-xs text-ink/55">
        {citation.title} · {citation.publisher} · v{citation.version}
        {citation.section ? ` · ${citation.section}` : ""}
        {citation.recommendation ? ` · rec. ${citation.recommendation}` : ""}
        {citation.document_ref ? ` · ${citation.document_ref}` : ""} · review due {citation.review_due}
        {citation.url && (
          <>
            {" · "}
            <a href={citation.url} target="_blank" rel="noreferrer" className="text-accent underline">source</a>
          </>
        )}
      </p>
    </li>
  );
}
