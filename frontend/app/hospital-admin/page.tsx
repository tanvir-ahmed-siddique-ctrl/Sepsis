"use client";

import Link from "next/link";
import { ApiError, PageHeader, Stat } from "@/components/ui";
import { api, DEMO_UNIT, type UnitOverview } from "@/lib/api";
import { useSession } from "@/lib/session";
import { usePoll } from "@/lib/usePoll";

const quickLinks = [
  { href: "/app/admin/users", title: "Staff & access", body: "Named accounts, roles and unit scope." },
  { href: "/app/admin/setup", title: "Unit settings", body: "Care units, readiness snapshot and blockers." },
  { href: "/app/admin/pilot", title: "Silent evaluation", body: "Shadow scoring burden before live alerts." },
  { href: "/app/icu", title: "ICU board", body: "Live six-hour risk board for the adult ICU." },
  { href: "/app/staff", title: "Shift roster", body: "On-duty ownership for the current shift." },
  { href: "/deploy", title: "Deployment console", body: "Feeds, mapping and commissioning (IT)." },
];

export default function HospitalAdminPage() {
  const { me, isAdmin, loading } = useSession();
  const overview = usePoll(() => api<UnitOverview>(`/v1/units/${encodeURIComponent(DEMO_UNIT)}/overview`), 8000);
  const alerts = usePoll(() => api<{ alerts: Array<{ status: string }> }>("/v1/alerts?status=open"), 8000);
  const readiness = usePoll(() => api<{ gates: Array<{ passed: boolean }> }>("/v1/site/readiness"), 20000);

  if (loading) return <p className="text-sm text-muted">Loading…</p>;
  if (!me) return <p className="text-sm text-muted">Sign in to the hospital workspace.</p>;
  if (!isAdmin) {
    return (
      <p className="text-sm text-muted" role="alert">
        This workspace requires a hospital administrator.
      </p>
    );
  }

  const openAlerts = alerts.data?.alerts.length ?? 0;
  const beds = overview.data?.patients?.length ?? 0;
  const highRisk =
    overview.data?.patients?.filter((p) => p.risk_band === "high_risk" || p.trust_state === "alert").length ?? 0;
  const gatesPassed = readiness.data?.gates.filter((g) => g.passed).length ?? 0;
  const gatesTotal = readiness.data?.gates.length ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Hospital Admin"
        title="Hospital overview"
        description="Live site pulse for administrators — staffing, ICU burden and readiness. Deployment tools stay in the IT console."
      />

      {(overview.error || alerts.error) && <ApiError error={overview.error || alerts.error} />}

      <div className="flex flex-wrap gap-3">
        <Stat label="ICU beds scored" value={beds || "—"} />
        <Stat label="Elevated risk" value={highRisk} color={highRisk ? "text-risk-high" : "text-risk-low"} />
        <Stat label="Open alerts" value={openAlerts} color={openAlerts ? "text-risk-high" : undefined} />
        <Stat label="Readiness gates" value={gatesTotal ? `${gatesPassed}/${gatesTotal}` : "—"} />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {quickLinks.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="rounded-2xl border border-border bg-[#FAFBFA] p-5 transition-all hover:border-teal hover:bg-white hover:shadow-sm"
          >
            <h2 className="font-display text-lg font-semibold">{item.title}</h2>
            <p className="mt-2 text-sm text-muted">{item.body}</p>
            <span className="mt-4 inline-flex text-xs font-semibold text-teal">Open →</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
