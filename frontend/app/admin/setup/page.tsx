"use client";

import Link from "next/link";
import { GatesPanel, type Readiness } from "@/components/pilot/PilotGovernance";
import { ApiError, Panel, Pill, Stat } from "@/components/ui";
import { api, type CareUnit, type LocalUser } from "@/lib/api";
import { usePoll } from "@/lib/usePoll";

type SetupSnapshot = {
  ready: { status: string; checks: Record<string, boolean>; model_hash: string };
  users: LocalUser[];
  units: CareUnit[];
  integration: {
    connectors: Array<{ connector: string; state: string; last_success_at: string | null }>;
    mapping_registry: { version: string; entries: number; status: string };
    quarantined_last_24h: number;
  };
  readiness: Readiness;
};

const STEPS = [
  ["1. Governance", "Name the clinical owner, data controller, IT owner and incident contact. Complete ethics/legal review before patient data."],
  ["2. Identity", "Prefer hospital OIDC. Otherwise create named local accounts, require password change and 2FA, and assign minimum unit scope."],
  ["3. Units and beds", "Create ICU/ward IDs that match the hospital master list. Print QR labels only after the ward manager verifies bed mapping."],
  ["4. Patient identity", "Use the hospital MRN plus visit/encounter ID. Never use names as identifiers; agree how merges and duplicate MRNs are escalated."],
  ["5. Data feeds", "Start with lab CSV or FHIR/HL7 from a test environment. Add the monitor relay only on the hospital LAN with a scoped integration key."],
  ["6. Mapping validation", "For every source code, verify target code, unit, timestamp, reference workflow and at least ten real examples. Unknowns stay quarantined."],
  ["7. Silent validation", "Run retrospectively, then silently for 28+ days. Clinicians remain blinded while outcomes, missingness and feed failures are measured."],
  ["8. Go-live decision", "A hospital committee reviews all readiness gates. The software cannot diagnose, prescribe, or enable live alerts by itself."],
] as const;

export default function SiteSetupPage() {
  const snapshot = usePoll<SetupSnapshot>(async () => {
    const [ready, users, units, integration, readiness] = await Promise.all([
      api<SetupSnapshot["ready"]>("/ready"),
      api<{ users: LocalUser[] }>("/v1/auth/users"),
      api<{ units: CareUnit[] }>("/v1/care/units"),
      api<SetupSnapshot["integration"]>("/v1/integrations/status"),
      api<Readiness>("/v1/site/readiness"),
    ]);
    return { ready, users: users.users, units: units.units, integration, readiness };
  }, 15000);

  if (snapshot.error) return <ApiError error={snapshot.error} />;
  const data = snapshot.data;
  if (!data) return <p className="text-sm text-ink/60">Loading hospital setup…</p>;

  const activeAdmins = data.users.filter((user) => user.role === "admin" && !user.disabled).length;
  const activeUsers = data.users.filter((user) => !user.disabled).length;
  const healthyFeeds = data.integration.connectors.filter((item) => item.state === "healthy").length;
  const passedGates = data.readiness.gates.filter((gate) => gate.passed).length;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-display text-3xl">Hospital setup</h1>
        <p className="mt-1 max-w-3xl text-sm text-ink/60">
          Operator checklist from installation to a governed silent pilot. Technical readiness does not replace hospital
          approval, local validation or regulatory review.
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        <Stat label="System" value={data.ready.status} color={data.ready.status === "ready" ? "text-risk-low" : "text-risk-high"} />
        <Stat label="Active users" value={activeUsers} />
        <Stat label="Active admins" value={activeAdmins} color={activeAdmins >= 2 ? "text-risk-low" : "text-risk-watch"} />
        <Stat label="Care units" value={data.units.length} />
        <Stat label="Healthy feeds" value={`${healthyFeeds}/${data.integration.connectors.length}`} />
        <Stat label="Readiness gates" value={`${passedGates}/${data.readiness.gates.length}`} />
      </div>

      <Panel title="Immediate blockers">
        <div className="flex flex-wrap gap-2 text-sm">
          {activeAdmins < 2 && <Pill tone="warning">Create a second administrator</Pill>}
          {data.units.length === 0 && <Pill tone="danger">No care units configured</Pill>}
          {data.integration.quarantined_last_24h > 0 && <Pill tone="warning">{data.integration.quarantined_last_24h} quarantined rows in 24 h</Pill>}
          {data.integration.mapping_registry.status !== "ready" && <Pill tone="danger">Mapping registry not ready</Pill>}
          {Object.entries(data.ready.checks).filter(([, ok]) => !ok).map(([name]) => <Pill key={name} tone="danger">{name} failed</Pill>)}
          {activeAdmins >= 2 && data.units.length > 0 && data.integration.mapping_registry.status === "ready" && Object.values(data.ready.checks).every(Boolean) && (
            <Pill tone="success">Technical baseline ready; governance gates still apply</Pill>
          )}
        </div>
        <div className="mt-3 flex flex-wrap gap-3 text-sm">
          <Link className="underline" href="/admin/users">Manage users and units</Link>
          <Link className="underline" href="/integration">Validate feeds and mappings</Link>
          <Link className="underline" href="/readiness">Review evidence passport</Link>
          <Link className="underline" href="/pilot">Review silent-pilot gates</Link>
        </div>
      </Panel>

      <div className="grid gap-4 lg:grid-cols-2">
        {STEPS.map(([title, detail]) => (
          <Panel key={title} title={title}>
            <p className="text-sm">{detail}</p>
          </Panel>
        ))}
      </div>

      <GatesPanel gates={data.readiness.gates} policy={data.readiness.policy} />

      <Panel title="Data boundary">
        <ul className="list-disc space-y-1 pl-5 text-sm">
          <li>Keep identifiable data and backups inside the hospital-controlled environment.</li>
          <li>Send only minimum required fields; use TLS, scoped credentials and a documented retention period.</li>
          <li>Quarantine unknown codes, impossible values, missing encounter IDs and unit mismatches—never guess mappings.</li>
          <li>Maintain a source-to-target mapping sign-off sheet and a downtime/paper-chart reconciliation procedure.</li>
          <li>Run 4 remains frozen and ICU-only; ward observations use deterministic NEWS2 and never enter the ICU model.</li>
        </ul>
      </Panel>
    </div>
  );
}
