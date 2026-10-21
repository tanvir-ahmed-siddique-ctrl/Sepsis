"use client";

import { GatesPanel, type Readiness } from "@/components/pilot/PilotGovernance";
import { ApiError, KeyValue, Panel } from "@/components/ui";
import { api } from "@/lib/api";
import { humanize } from "@/lib/pilot";
import { useSession } from "@/lib/session";
import { usePoll } from "@/lib/usePoll";

type Passport = {
  passport_version: string;
  generated_at: string;
  site_id: string;
  model_version: string;
  evidence_sha256?: string;
  recommended_mode: string;
  blockers: string[];
  next_actions: string[];
  limitations: string[];
  local_site_evidence?: boolean;
  sections: Record<string, Record<string, unknown>>;
};

function renderValue(value: unknown): string {
  if (value == null) return "—";
  if (typeof value === "number") return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(4);
  if (typeof value === "boolean") return value ? "yes" : "no";
  if (Array.isArray(value)) return value.map(renderValue).join(" – ");
  if (typeof value === "object") {
    return Object.entries(value as Record<string, unknown>).map(([key, inner]) => `${humanize(key)} ${renderValue(inner)}`).join(" · ");
  }
  return String(value);
}

const LONG_TEXT = new Set(["description", "finding", "interpretation", "evidence"]);

export default function ReadinessPage() {
  const { isAdmin: admin, isOperator } = useSession();
  const isAdmin = admin || isOperator;
  const { data, error } = usePoll(() => api<Passport>("/v1/model/passport"), 30000);
  const site = usePoll(() => (isAdmin ? api<Readiness>("/v1/site/readiness") : Promise.resolve(null)), 30000, [isAdmin]);
  if (error) return <ApiError error={error} />;
  if (!data) return <p className="text-sm text-ink/60">Loading hospital readiness passport…</p>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl">Hospital Readiness Passport</h1>
        <p className="mt-1 text-sm text-ink/60">
          SafeLaunch gate for a site. This is not regulatory approval and not a live-alert recommendation.
        </p>
      </div>
      <Panel title={`Recommended mode: ${data.recommended_mode}`}>
        <p className="text-sm">
          Evidence site {data.site_id} · model {data.model_version} · passport {data.passport_version}
        </p>
        <p className="mt-2 text-xs text-ink/55">
          Local site evidence: {data.local_site_evidence ? "yes" : "no — public Dataset B is not a local hospital validation"}
          {data.evidence_sha256 ? ` · evidence SHA-256 ${data.evidence_sha256.slice(0, 16)}…` : ""}
        </p>
      </Panel>

      {site.data && <GatesPanel gates={site.data.gates} policy={site.data.policy} />}
      {!isAdmin && (
        <p className="text-xs text-ink/55">Live site gates (silent-pilot evidence) are visible to pilot administrators.</p>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Blockers">
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {data.blockers.map((item) => <li key={item}>{humanize(item)}</li>)}
          </ul>
        </Panel>
        <Panel title="Required next actions">
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {data.next_actions.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </Panel>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {Object.entries(data.sections).map(([name, section]) => (
          <Panel key={name} title={humanize(name)}>
            <dl>
              {Object.entries(section)
                .filter(([key]) => !LONG_TEXT.has(key))
                .map(([key, value]) => <KeyValue key={key} label={humanize(key)} value={renderValue(value)} />)}
            </dl>
            {Object.entries(section)
              .filter(([key]) => LONG_TEXT.has(key))
              .map(([key, value]) => (
                <p key={key} className="mt-2 text-xs text-ink/60">
                  <span className="font-medium">{humanize(key)}:</span> {String(value)}
                </p>
              ))}
          </Panel>
        ))}
      </div>

      <Panel title="Limitations">
        <ul className="list-disc space-y-1 pl-5 text-sm">
          {data.limitations.map((item) => <li key={item}>{item}</li>)}
        </ul>
      </Panel>
    </div>
  );
}
