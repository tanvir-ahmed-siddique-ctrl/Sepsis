"use client";

import Link from "next/link";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";
import { usePoll } from "@/lib/usePoll";
import { Icon } from "@/components/ui/Icon";

type Ops = {
  writer: { read_only: boolean; read_only_reason: string | null };
  database: { healthy: boolean };
  audit: { events_verified: number; linkage_valid: boolean; content_hash_mismatches: number };
  model: { version: string; sha256: string; frozen: boolean };
  site: { site_id: string; effective_mode: string };
};

const VENDOR_COMMERCIAL_ROLES = ["root_admin", "platform_admin", "finance_legal", "evaluation_operator"];

export default function SuperAdminPage() {
  const { me, account, isOperator } = useSession();
  const status = usePoll(() => (isOperator ? api<Ops>("/v1/ops/status") : Promise.resolve(null)), 15000, [isOperator]);

  if (!me) {
    return (
      <div className="max-w-2xl py-16">
        <h1 className="text-3xl font-semibold">Platform operator sign-in</h1>
        <p className="mt-3 text-sm text-ink/60">Use your assigned operator credentials to access the vendor control plane.</p>
        <Link href="/login" className="mt-5 inline-block bg-ink px-5 py-3 text-sm font-semibold text-white">
          Sign in
        </Link>
      </div>
    );
  }
  if (!isOperator) {
    return (
      <div className="max-w-2xl py-16">
        <h1 className="text-3xl font-semibold">Operator workspace</h1>
        <p className="mt-3 text-sm text-ink/60">This workspace requires the platform operator role assigned to your account.</p>
        <Link href="/signin" className="auralis-link mt-5">
          Return to sign in
          <Icon name="arrow-right" size={16} />
        </Link>
      </div>
    );
  }

  const ops = status.data;
  const integrity = ops
    ? ops.database.healthy && ops.audit.linkage_valid && ops.audit.content_hash_mismatches === 0 && !ops.writer.read_only
    : null;
  const vendorCommercial =
    Boolean(account?.vendor) && VENDOR_COMMERCIAL_ROLES.includes(account?.role || "");
  const fleetUrl = process.env.NEXT_PUBLIC_FLEET_URL || "/fleet";

  return (
    <div className="space-y-9 pb-16">
      <header className="bg-[#080C14] px-7 py-9 text-slate-50 sm:px-10">
        <p className="text-xs font-semibold uppercase tracking-[.2em] text-cyan-300">Vendor control plane / operator</p>
        <div className="mt-5 flex flex-wrap items-end justify-between gap-5">
          <div>
            <h1 className="text-4xl font-semibold tracking-tight">Fleet command</h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-300">
              Site metadata and fleet heartbeat for the hospital operator role. Patient-level clinical data remains in
              hospital custody. CRM and billing use a separate vendor account.
            </p>
          </div>
          <Link
            href={fleetUrl}
            className="bg-cyan-400 px-5 py-3 text-sm font-semibold text-slate-950 transition-colors duration-150 hover:bg-cyan-300"
          >
            Open fleet console
            <Icon name="external" size={15} />
          </Link>
        </div>
      </header>

      <section aria-labelledby="local-site-title">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-accent">Live metadata / current deployment</p>
            <h2 id="local-site-title" className="mt-2 text-2xl font-semibold">
              Site diagnostics
            </h2>
          </div>
          <span className="text-xs text-ink/50">Refreshes every 15 seconds</span>
        </div>
        {status.error && (
          <p role="alert" className="mt-4 border-l-2 border-risk-high bg-white p-4 text-sm text-risk-high">
            Site status unavailable: {status.error.message}
          </p>
        )}
        {!status.error && !ops && <p className="mt-4 text-sm text-ink/60">Loading signed site status…</p>}
        {ops && (
          <div className="mt-5 grid gap-px bg-slate-300 md:grid-cols-2 xl:grid-cols-4">
            <div className="bg-white p-5">
              <p className="text-xs uppercase tracking-widest text-ink/50">Site ID</p>
              <p className="mt-4 break-all font-mono text-lg">{ops.site.site_id}</p>
              <p className="mt-2 text-xs text-ink/50">Mode: {ops.site.effective_mode}</p>
            </div>
            <div className="bg-white p-5">
              <p className="text-xs uppercase tracking-widest text-ink/50">Runtime integrity</p>
              <p className={`mt-4 text-lg font-semibold ${integrity ? "text-emerald-700" : "text-risk-high"}`}>
                {integrity ? "Healthy" : "Needs review"}
              </p>
              <p className="mt-2 text-xs text-ink/50">
                {ops.writer.read_only ? ops.writer.read_only_reason || "Read-only writer" : "Writer active"} · audit{" "}
                {ops.audit.linkage_valid ? "linked" : "invalid"}
              </p>
            </div>
            <div className="bg-white p-5">
              <p className="text-xs uppercase tracking-widest text-ink/50">Model release</p>
              <p className="mt-4 break-all font-mono text-sm">{ops.model.version}</p>
              <p className="mt-2 text-xs text-ink/50">
                SHA-256 {ops.model.sha256.slice(0, 12)}… · {ops.model.frozen ? "frozen" : "unfrozen"}
              </p>
            </div>
            <div className="bg-white p-5">
              <p className="text-xs uppercase tracking-widest text-ink/50">Verified audit events</p>
              <p className="mt-4 font-mono text-2xl">{ops.audit.events_verified.toLocaleString()}</p>
              <p className="mt-2 text-xs text-ink/50">Content mismatches: {ops.audit.content_hash_mismatches}</p>
            </div>
          </div>
        )}
      </section>

      <section aria-labelledby="controls-title">
        <div className="flex flex-wrap items-end justify-between gap-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-accent">Control surfaces</p>
            <h2 id="controls-title" className="mt-2 text-2xl font-semibold">
              Operate without crossing the clinical boundary.
            </h2>
          </div>
          <p className="max-w-md text-xs leading-5 text-ink/50">
            The hospital operator role can open site diagnostics. Commercial CRM requires a vendor control-plane account
            with a finance or platform role — not this hospital session alone.
          </p>
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-2">
          <Link
            href={fleetUrl}
            className="group flex min-h-48 flex-col bg-white p-6 transition-colors duration-150 hover:bg-slate-50"
          >
            <span className="font-mono text-xs text-accent">01</span>
            <h3 className="mt-4 text-xl font-semibold">Fleet heartbeat</h3>
            <p className="mt-2 text-sm leading-6 text-ink/60">
              Signed, patient-free status metadata from registered site deployments.
            </p>
            <span className="mt-auto inline-flex items-center gap-1.5 pt-5 text-sm font-semibold text-teal">
              Open fleet heartbeat
              <Icon name="arrow-right" size={15} className="transition-transform group-hover:translate-x-0.5" />
            </span>
          </Link>

          {vendorCommercial ? (
            <Link
              href="/platform/commercial"
              className="group flex min-h-48 flex-col bg-white p-6 transition-colors duration-150 hover:bg-slate-50"
            >
              <span className="font-mono text-xs text-accent">02</span>
              <h3 className="mt-4 text-xl font-semibold">Commercial operations</h3>
              <p className="mt-2 text-sm leading-6 text-ink/60">
                Vendor CRM: quotations, contracts, licences, invoices and renewals for your control-plane role.
              </p>
              <span className="mt-auto inline-flex items-center gap-1.5 pt-5 text-sm font-semibold text-teal">
                Open vendor commercial
                <Icon name="arrow-right" size={15} className="transition-transform group-hover:translate-x-0.5" />
              </span>
            </Link>
          ) : (
            <div className="flex min-h-48 flex-col border border-dashed border-slate-300 bg-slate-50 p-6" role="status">
              <span className="font-mono text-xs text-accent">02</span>
              <h3 className="mt-4 text-xl font-semibold">Commercial operations</h3>
              <p className="mt-2 text-sm leading-6 text-ink/60">
                Not available on the hospital operator session. Sign in with a vendor control-plane account that holds
                root admin, platform admin, finance/legal, or evaluation operator — for example{" "}
                <code className="rounded bg-white px-1 font-mono text-xs">vendor@auralis.demo</code>. This is not the
                hospital customer portal and not a clinical sample role.
              </p>
              <Link href="/signin?next=%2Fplatform%2Fcommercial" className="auralis-link mt-auto pt-5">
                Sign in with a vendor account
                <Icon name="arrow-right" size={15} />
              </Link>
            </div>
          )}

          <Link
            href="/operations"
            className="group flex min-h-48 flex-col bg-white p-6 transition-colors duration-150 hover:bg-slate-50"
          >
            <span className="font-mono text-xs text-accent">03</span>
            <h3 className="mt-4 text-xl font-semibold">Site operations</h3>
            <p className="mt-2 text-sm leading-6 text-ink/60">
              Writer lease, connector health, readiness gates, model provenance and audit-chain verification for this
              site. Metadata only — no patient charts.
            </p>
            <span className="mt-auto inline-flex items-center gap-1.5 pt-5 text-sm font-semibold text-teal">
              Inspect current site
              <Icon name="arrow-right" size={15} className="transition-transform group-hover:translate-x-0.5" />
            </span>
          </Link>

          <Link
            href="/business"
            className="group flex min-h-48 flex-col bg-white p-6 transition-colors duration-150 hover:bg-slate-50"
          >
            <span className="font-mono text-xs text-accent">04</span>
            <h3 className="mt-4 text-xl font-semibold">Deployment offer</h3>
            <p className="mt-2 text-sm leading-6 text-ink/60">
              Assessment, silent pilot, implementation and annual licence structure for hospital buyers.
            </p>
            <span className="mt-auto inline-flex items-center gap-1.5 pt-5 text-sm font-semibold text-teal">
              Review commercial offer
              <Icon name="arrow-right" size={15} className="transition-transform group-hover:translate-x-0.5" />
            </span>
          </Link>
        </div>
      </section>

      <p className="text-xs leading-6 text-ink/50">
        No hospital fleet size, outcome rate or SLA is shown until backed by registered site telemetry and signed
        commercial records.
      </p>
    </div>
  );
}
