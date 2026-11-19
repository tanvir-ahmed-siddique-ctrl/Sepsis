"use client";

import Link from "next/link";
import { PageHeader, Stat } from "@/components/ui";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";
import { usePoll } from "@/lib/usePoll";

const modules = [
  { href: "/app/admin/setup", title: "Site & environment", body: "Provisioning, unit setup and local configuration." },
  { href: "/app/admin/integrations", title: "HIS / LIS / monitors", body: "Interface status, mapping and quarantine." },
  { href: "/app/admin/connections", title: "Connectivity diagnostics", body: "Live ladder, feed state and Transfer Shield." },
  { href: "/app/admin/readiness", title: "Readiness gates", body: "Silent-to-live controls and blocking evidence." },
  { href: "/app/admin/operations", title: "Ops, backup & TLS", body: "Operational health and recovery visibility." },
  { href: "/app/admin/licence", title: "Licence & release", body: "Local licence package for this site." },
];

export default function DeployHomePage() {
  const { me, isAdmin, loading } = useSession();
  const status = usePoll(
    () =>
      api<{
        connectors: Array<{ connector: string; state: string }>;
        quarantined_last_24h: number;
        mapping_registry: { status: string };
      }>("/v1/integrations/status"),
    15000,
  );
  const readiness = usePoll(() => api<{ gates: Array<{ passed: boolean }> }>("/v1/site/readiness"), 20000);

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

  const healthy = status.data?.connectors.filter((c) => c.state === "healthy").length ?? 0;
  const total = status.data?.connectors.length ?? 0;
  const gatesPassed = readiness.data?.gates.filter((g) => g.passed).length ?? 0;
  const gatesTotal = readiness.data?.gates.length ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Hospital Deployment Console"
        title="Commission and monitor the site"
        description="Integration, readiness and operational evidence — separate from clinical charting."
      />

      <div className="flex flex-wrap gap-3">
        <Stat label="Healthy feeds" value={total ? `${healthy}/${total}` : "—"} />
        <Stat label="Quarantine (24h)" value={status.data?.quarantined_last_24h ?? "—"} />
        <Stat label="Mapping registry" value={status.data?.mapping_registry.status ?? "—"} />
        <Stat label="Readiness gates" value={gatesTotal ? `${gatesPassed}/${gatesTotal}` : "—"} />
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {modules.map((item) => (
          <Link key={item.href} href={item.href} className="rounded-2xl border border-border bg-[#FAFBFA] p-5 transition-all hover:border-teal hover:bg-white hover:shadow-sm">
            <h2 className="font-display text-lg font-semibold text-ink">{item.title}</h2>
            <p className="mt-2 text-sm leading-6 text-muted">{item.body}</p>
            <span className="mt-4 inline-flex text-xs font-semibold text-teal">Open →</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
