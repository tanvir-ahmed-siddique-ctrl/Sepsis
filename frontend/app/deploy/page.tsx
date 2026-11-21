"use client";

import Link from "next/link";
import { PageHeader, Stat } from "@/components/ui";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";
import { usePoll } from "@/lib/usePoll";
import { Icon, type IconName } from "@/components/ui/Icon";

type DeployModule = { href: string; title: string; body: string; icon: IconName; roles: Array<"admin" | "clinical_it" | "operator"> };

const modules: DeployModule[] = [
  { href: "/app/admin/setup", title: "Site & environment", body: "Provisioning, unit setup and local configuration.", icon: "settings", roles: ["admin"] },
  { href: "/app/admin/integrations", title: "HIS / LIS / monitors", body: "Interface status, mapping and quarantine.", icon: "plug", roles: ["admin", "clinical_it"] },
  { href: "/app/admin/connections", title: "Connectivity diagnostics", body: "Live ladder, feed state and Transfer Shield.", icon: "activity", roles: ["admin", "clinical_it"] },
  { href: "/app/admin/readiness", title: "Readiness gates", body: "Silent-to-live controls and blocking evidence.", icon: "check", roles: ["admin"] },
  { href: "/app/admin/operations", title: "Ops, backup & TLS", body: "Operational health and recovery visibility.", icon: "server", roles: ["admin"] },
  { href: "/app/admin/licence", title: "Licence & release", body: "Local licence package for this site.", icon: "key", roles: ["admin"] },
  { href: "/operations", title: "Site diagnostics", body: "Writer lease, connectors, gates and audit integrity (metadata only).", icon: "server", roles: ["operator"] },
  { href: "/readiness", title: "Readiness passport", body: "Site readiness passport and live gate status for operators.", icon: "check", roles: ["operator"] },
];

export default function DeployHomePage() {
  const { me, isAdmin, loading } = useSession();
  const canPollIntegrations = Boolean(me && (isAdmin || me.role === "clinical_it" || me.role === "operator"));
  const canPollReadiness = Boolean(me && (isAdmin || me.role === "operator"));
  const status = usePoll(
    () =>
      canPollIntegrations
        ? api<{
            connectors: Array<{ connector: string; state: string }>;
            simulation_mode?: boolean;
            quarantined_last_24h: number;
            mapping_registry: { status: string };
          }>("/v1/integrations/status")
        : Promise.resolve(null),
    15000,
    [canPollIntegrations],
  );
  const readiness = usePoll(
    () => (canPollReadiness ? api<{ gates: Array<{ passed: boolean }> }>("/v1/site/readiness") : Promise.resolve(null)),
    20000,
    [canPollReadiness],
  );

  if (loading) return <p className="text-sm text-muted">Loading deployment console…</p>;
  if (!me) {
    return (
      <div className="auralis-panel max-w-xl">
        <h1 className="auralis-page-title">Deployment console sign-in required</h1>
        <p className="mt-3 text-sm text-muted">Authenticate with a hospital administrator or clinical IT identity.</p>
        <Link href="/signin" className="auralis-btn-primary mt-6">
          Sign in
        </Link>
      </div>
    );
  }
  const allowed = isAdmin || me.role === "clinical_it" || me.role === "operator";
  if (!allowed) {
    return (
      <div className="auralis-panel max-w-xl" role="alert">
        <h1 className="auralis-page-title">Access denied</h1>
        <p className="mt-3 text-sm text-muted">
          The deployment console is limited to hospital administrators, clinical IT and authorized operators.
        </p>
        <Link href="/app/icu" className="auralis-btn-secondary mt-6">
          Return to hospital workspace
        </Link>
      </div>
    );
  }

  const roleKey = isAdmin ? "admin" : (me.role as "clinical_it" | "operator");
  const visibleModules = modules.filter((item) => item.roles.includes(roleKey));
  const healthy = status.data?.connectors.filter((c) => c.state === "healthy").length ?? 0;
  const total = status.data?.connectors.length ?? 0;
  const gatesPassed = readiness.data?.gates.filter((g) => g.passed).length ?? 0;
  const gatesTotal = readiness.data?.gates.length ?? 0;
  const [registryState = "", ...registryRest] = (status.data?.mapping_registry.status ?? "").split(" — ");
  const registryDetail = registryRest.join(" — ");

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Hospital deployment console"
        title="Commission and monitor the site"
        description={
          me.role === "clinical_it"
            ? "HIS interfaces and connectivity for clinical IT. Readiness, site operations and licence remain hospital-admin or operator roles."
            : me.role === "operator"
              ? "Metadata diagnostics for the platform operator. Hospital-admin pages under /app stay unavailable to this role."
              : "Integration, readiness and operational evidence — separate from clinical charting."
        }
      />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat
          label="Healthy feeds"
          value={total ? `${healthy}/${total}` : "—"}
        />
        <Stat label="Quarantine (24h)" value={status.data?.quarantined_last_24h ?? "—"} />
        <Stat label="Mapping registry" value={<span className="capitalize">{registryState || "—"}</span>} hint={registryDetail || undefined} />
        <Stat
          label="Readiness gates"
          value={canPollReadiness && gatesTotal ? `${gatesPassed}/${gatesTotal}` : "—"}
          hint={!canPollReadiness ? "Visible to hospital admin and operator" : undefined}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {visibleModules.map((item) => (
          <Link key={item.href} href={item.href} className="group auralis-card-link">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted-surface text-navy transition-colors group-hover:bg-teal-soft group-hover:text-teal-dark">
              <Icon name={item.icon} size={17} />
            </span>
            <h2 className="mt-4 text-base font-semibold text-ink">{item.title}</h2>
            <p className="mt-2 text-sm leading-6 text-muted">{item.body}</p>
            <span className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-teal">
              Open
              <Icon name="arrow-right" size={15} className="transition-transform group-hover:translate-x-0.5" />
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
