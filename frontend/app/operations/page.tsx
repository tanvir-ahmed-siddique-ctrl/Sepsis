"use client";

import { GatesPanel, type Readiness } from "@/components/pilot/PilotGovernance";
import { ApiError, KeyValue, Panel, Pill, Stat } from "@/components/ui";
import { api, type ConnectorHealth, type SiteMode } from "@/lib/api";
import { connectorTone, humanize, minutesLabel } from "@/lib/pilot";
import { useSession } from "@/lib/session";
import { usePoll } from "@/lib/usePoll";

const FLEET_URL = process.env.NEXT_PUBLIC_FLEET_URL;

type OpsStatus = {
  writer: { this_instance: string; read_only: boolean; read_only_reason: string | null; horizontal_scaling: string };
  database: { healthy: boolean; dialect: string };
  audit: { events_verified: number; linkage_valid: boolean; content_hash_mismatches: number; head_hash: string };
  model: { version: string; sha256: string; frozen: boolean };
  site: { site_id: string; effective_mode: SiteMode };
  retention_days: number;
};

type IntegrationStatus = {
  connectors: ConnectorHealth[];
  feed_alarm: boolean;
  mapping_registry: { version: string; sha256: string; entries: number; status: string };
  quarantined_last_24h: number;
};

export default function OperationsPage() {
  const { me, isAdmin, isOperator } = useSession();
  const allowed = isAdmin || isOperator;
  const ops = usePoll(() => (allowed ? api<OpsStatus>("/v1/ops/status") : Promise.resolve(null)), 15000, [allowed]);
  const feeds = usePoll(
    () => (allowed ? api<IntegrationStatus>("/v1/integrations/status") : Promise.resolve(null)),
    15000,
    [allowed],
  );
  const gates = usePoll(() => (allowed ? api<Readiness>("/v1/site/readiness") : Promise.resolve(null)), 30000, [allowed]);
  const heartbeat = usePoll(
    () =>
      allowed
        ? api<{ payload: Record<string, unknown>; signature_algorithm: string }>("/v1/ops/heartbeat")
        : Promise.resolve(null),
    60000,
    [allowed],
  );

  if (!me) return <p className="text-sm text-ink/60">Sign in as a hospital administrator or platform operator.</p>;
  if (!allowed) {
    return (
      <ApiError
        error="Site operations require the hospital admin or platform operator role. Clinical IT can use Integrations and Connectivity; readiness gates and ops metadata stay with admin/operator."
      />
    );
  }
  const error = ops.error ?? feeds.error ?? gates.error;
  if (error) return <ApiError error={error} />;
  if (!ops.data || !feeds.data) return <p className="text-sm text-ink/60">Loading deployment health…</p>;

  const audit = ops.data.audit;
  const auditValid = audit.linkage_valid && audit.content_hash_mismatches === 0;
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl">Operations console</h1>
        <p className="mt-1 text-sm text-ink/60">
          Deployment health for site {ops.data.site.site_id}. This view carries metadata only: connector status, gates,
          audit integrity and model provenance.
        </p>
      </div>
      {isOperator && (
        <div role="status" className="border border-accent/30 bg-accent/5 px-4 py-2 text-sm">
          Platform operator access: patient lists, charts, alerts and audit events are not available to this account.
          Clinical data access requires a hospital-issued clinical role.
        </div>
      )}
      {FLEET_URL && (
        <div className="border border-ink/10 bg-white px-4 py-2 text-sm">
          This page is inside the hospital. The vendor sees every hospital only through signed, patient-free
          heartbeats:{" "}
          <a href={FLEET_URL} className="font-medium text-accent underline">
            open the vendor fleet console
          </a>
          .
        </div>
      )}

      <div className="flex flex-wrap gap-3">
        <Stat label="Site mode" value={humanize(ops.data.site.effective_mode)} />
        <Stat label="Connectors" value={feeds.data.connectors.length} />
        <Stat label="Quarantined 24 h" value={feeds.data.quarantined_last_24h} />
        <Stat label="Audit events" value={audit.events_verified.toLocaleString()} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Platform integrity">
          <dl>
            <KeyValue label="Database" value={ops.data.database.healthy ? `healthy (${ops.data.database.dialect})` : "unhealthy"} />
            <KeyValue label="Writer" value={ops.data.writer.read_only ? `read-only — ${ops.data.writer.read_only_reason ?? "unknown"}` : "active"} />
            <KeyValue label="Audit chain" value={<Pill tone={auditValid ? "success" : "danger"}>{auditValid ? "verified" : "broken"}</Pill>} />
            <KeyValue label="Model" value={`${ops.data.model.version}${ops.data.model.frozen ? " · frozen" : ""}`} />
            <KeyValue label="Model SHA-256" value={<code className="text-xs">{ops.data.model.sha256.slice(0, 16)}…</code>} />
            <KeyValue label="Retention" value={`${ops.data.retention_days} days`} />
          </dl>
        </Panel>
        <Panel title="Integration feeds">
          {feeds.data.feed_alarm && <p className="mb-2 text-sm text-risk-high">Feed alarm: a connected feed is stale or its circuit is open.</p>}
          <ul className="space-y-2 text-sm">
            {feeds.data.connectors.map((item) => (
              <li key={item.connector} className="flex items-center justify-between gap-3 border-b border-ink/5 pb-1">
                <span>{humanize(item.connector)}</span>
                <span className="flex items-center gap-2">
                  <span className="text-xs text-ink/55">{minutesLabel(item.minutes_since_success)}</span>
                  <Pill tone={connectorTone(item.state)}>{humanize(item.state)}</Pill>
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-ink/55">
            Mapping registry {feeds.data.mapping_registry.version} · {feeds.data.mapping_registry.entries} entries ·{" "}
            {humanize(feeds.data.mapping_registry.status)}
          </p>
        </Panel>
      </div>

      {gates.data && <GatesPanel gates={gates.data.gates} policy={gates.data.policy} />}

      {heartbeat.data && (
        <Panel title="Fleet heartbeat — everything the vendor control plane receives">
          <p className="-mt-2 mb-3 text-xs text-ink/55">
            Pushed outbound every few minutes, signed with {heartbeat.data.signature_algorithm}. The console rejects any field
            outside this allowlist, so patient, bed and user data cannot leave the hospital through this channel.
          </p>
          <pre className="max-h-80 overflow-auto bg-ink/5 p-3 text-xs">{JSON.stringify(heartbeat.data.payload, null, 2)}</pre>
        </Panel>
      )}
    </div>
  );
}
