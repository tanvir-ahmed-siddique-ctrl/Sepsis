"use client";

import Link from "next/link";
import { PageHeader } from "@/components/ui";
import { useSession } from "@/lib/session";

const modules = [
  { href: "/app/admin/setup", title: "Site & environment", body: "Provisioning, unit setup and local configuration." },
  { href: "/app/admin/integrations", title: "HIS / LIS / monitors", body: "Interface status, mapping and quarantine." },
  { href: "/app/admin/connections", title: "Connectivity diagnostics", body: "Connection ladder and smoke checks." },
  { href: "/app/admin/readiness", title: "Readiness gates", body: "Silent-to-live controls and blocking evidence." },
  { href: "/app/admin/operations", title: "Ops, backup & TLS", body: "Operational health and recovery visibility." },
  { href: "/app/admin/pilot", title: "Silent-mode monitoring", body: "Shadow scoring and burden review." },
  { href: "/app/admin/licence", title: "Licence & release", body: "Local licence package and model version visibility." },
  { href: "/app/model", title: "Model version", body: "Frozen model evidence available to authorized operators." },
];

export default function DeployHomePage() {
  const { me, isAdmin, loading } = useSession();
  if (loading) return <p className="text-sm text-muted">Loading deployment console…</p>;
  if (!me) {
    return (
      <div className="auralis-panel max-w-xl">
        <h1 className="auralis-page-title">Deployment console sign-in required</h1>
        <p className="mt-3 text-sm text-muted">Authenticate with a hospital administrator or clinical IT identity.</p>
        <Link href="/signin" className="auralis-btn-primary mt-6">Sign in</Link>
      </div>
    );
  }
  const allowed = isAdmin || me.role === "clinical_it" || me.role === "operator";
  if (!allowed) {
    return (
      <div className="auralis-panel max-w-xl" role="alert">
        <h1 className="auralis-page-title">Access denied</h1>
        <p className="mt-3 text-sm text-muted">The deployment console is limited to hospital administrators, clinical IT and authorized operators.</p>
        <Link href="/app/icu" className="auralis-btn-secondary mt-6">Return to hospital workspace</Link>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        eyebrow="Hospital Deployment Console"
        title="Commission and monitor the site"
        description="Separate from clinical charting. Use these tools for interfaces, readiness and operational evidence. Unsupported integrations are not shown as live."
      />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {modules.map((item) => (
          <Link key={item.href} href={item.href} className="auralis-panel transition-colors hover:border-teal">
            <h2 className="font-display text-lg font-semibold text-ink">{item.title}</h2>
            <p className="mt-2 text-sm leading-6 text-muted">{item.body}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
