"use client";

import Link from "next/link";
import { PageHeader } from "@/components/ui";
import { useSession } from "@/lib/session";

const sections = [
  { href: "/app/admin/overview", title: "Hospital overview", body: "Site command hub for administrators." },
  { href: "/app/admin/users", title: "Staff & members", body: "Users, units and access assignments." },
  { href: "/app/admin/setup", title: "Unit & operational settings", body: "Local configuration and governance setup." },
  { href: "/app/admin/integrations", title: "Integration health", body: "Feeds, mapping and quarantine." },
  { href: "/app/admin/pilot", title: "Silent pilot", body: "Shadow scoring and review burden." },
  { href: "/app/admin/operations", title: "Operations audit", body: "Operational health and recovery visibility." },
  { href: "/deploy", title: "Deployment console", body: "Full commissioning and diagnostics surface." },
];

export default function HospitalAdminPage() {
  const { me, isAdmin, loading } = useSession();
  if (loading) return <p className="text-sm text-muted">Loading…</p>;
  if (!me) return <p className="text-sm text-muted">Sign in to the hospital workspace.</p>;
  if (!isAdmin) return <p className="text-sm text-muted" role="alert">This workspace requires a hospital administrator.</p>;

  return (
    <div>
      <PageHeader
        eyebrow="Hospital Admin"
        title="Hospital overview"
        description="Manage staff, operational settings and readiness evidence for your authorized hospital tenant only."
      />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {sections.map((item) => (
          <Link key={item.href} href={item.href} className="auralis-panel transition-colors hover:border-teal">
            <h2 className="font-display text-lg font-semibold">{item.title}</h2>
            <p className="mt-2 text-sm text-muted">{item.body}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
