"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { AttentionBanner } from "@/components/AttentionBanner";
import { AlertNotifier } from "@/components/AlertNotifier";
import { OfflineSync } from "@/components/OfflineSync";
import { EvaluationSwitcher } from "@/components/EvaluationSwitcher";
import { ShiftStrip } from "@/components/ShiftStrip";
import { PublicFooter } from "@/components/shells/PublicFooter";
import { PublicHeader } from "@/components/shells/PublicHeader";
import { WorkspaceShell, type ShellLink } from "@/components/shells/WorkspaceShell";
import { resolveSurface } from "@/lib/surfaces";
import { useSession } from "@/lib/session";

const HOSPITAL_CLINICAL: ShellLink[] = [
  { href: "/app/icu", label: "ICU board" },
  { href: "/app/chart", label: "Charting" },
  { href: "/app/ward", label: "Ward / NEWS2" },
  { href: "/app/alerts", label: "Alerts" },
  { href: "/app/handoff", label: "Handoff" },
  { href: "/app/staff", label: "Staff" },
  { href: "/app/profile", label: "Profile" },
];

const HOSPITAL_VIEWER: ShellLink[] = [
  { href: "/app/icu", label: "ICU (read-only)" },
  { href: "/app/alerts", label: "Alerts" },
  { href: "/app/handoff", label: "Handoff" },
  { href: "/app/staff", label: "Staff" },
  { href: "/app/profile", label: "Profile" },
];

const HOSPITAL_ADMIN: ShellLink[] = [
  { href: "/app/admin/overview", label: "Hospital overview" },
  { href: "/app/admin/users", label: "Staff & access" },
  { href: "/app/admin/setup", label: "Unit settings" },
  { href: "/app/admin/pilot", label: "Silent evaluation" },
  { href: "/app/icu", label: "ICU board" },
  { href: "/app/staff", label: "Shift roster" },
  { href: "/app/profile", label: "Profile" },
  { href: "/deploy", label: "Deployment console" },
];

const CLINICAL_IT: ShellLink[] = [
  { href: "/deploy", label: "Deployment home" },
  { href: "/app/admin/integrations", label: "Integrations" },
  { href: "/app/admin/connections", label: "Connectivity" },
  { href: "/app/admin/readiness", label: "Readiness" },
  { href: "/app/admin/operations", label: "Site operations" },
  { href: "/app/admin/licence", label: "Site licence" },
  { href: "/app/profile", label: "Profile" },
];

const DEPLOYMENT: ShellLink[] = [
  { href: "/deploy", label: "Overview" },
  { href: "/app/admin/setup", label: "Site setup" },
  { href: "/app/admin/integrations", label: "HIS / interfaces" },
  { href: "/app/admin/connections", label: "Connectivity" },
  { href: "/app/admin/readiness", label: "Readiness gates" },
  { href: "/app/admin/operations", label: "Ops & backup" },
  { href: "/app/admin/licence", label: "Licence" },
];

const VENDOR: ShellLink[] = [
  { href: "/platform/overview", label: "Control plane home" },
  { href: "/platform/accounts", label: "Tenants & access" },
  { href: "/platform/commercial", label: "Commercial" },
  { href: "/platform/service", label: "Support & service" },
  { href: "/platform/documents", label: "Documents" },
];

const OPERATOR_FLEET: ShellLink[] = [
  { href: "/platform/overview", label: "Fleet overview" },
];

const CUSTOMER: ShellLink[] = [
  { href: "/portal", label: "Organization home" },
  { href: "/portal/commercial", label: "Contracts & finance" },
  { href: "/portal/service", label: "Service & offboarding" },
  { href: "/portal/documents", label: "Documents" },
];

const EVALUATION: ShellLink[] = [
  { href: "/system-check", label: "Evaluation gate" },
  { href: "/app/icu", label: "Synthetic ICU" },
  { href: "/app/alerts", label: "Review history" },
  { href: "/evidence", label: "Evidence notes" },
];

function hospitalLinks(role?: string, isAdmin?: boolean): ShellLink[] {
  if (role === "clinical_viewer") return HOSPITAL_VIEWER;
  if (role === "clinical_it") return CLINICAL_IT;
  if (isAdmin || role === "admin") return HOSPITAL_ADMIN;
  return HOSPITAL_CLINICAL;
}

function SignInGate({ pathname, label }: { pathname: string; label: string }) {
  const signInHref = `/signin?next=${encodeURIComponent(pathname || "/")}`;
  return (
    <div className="auralis-container py-16">
      <div className="auralis-panel mx-auto max-w-xl">
        <h1 className="auralis-page-title">{label}</h1>
        <p className="mt-3 text-sm text-muted">
          Sign in with the matching demo role (or your hospital credentials) to open this workspace.
        </p>
        <Link href={signInHref} className="auralis-btn-primary mt-6">
          Sign in
        </Link>
      </div>
    </div>
  );
}

export function SurfaceFrame({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const surface = resolveSurface(pathname);
  const { me, account, isAdmin, isOperator, loading } = useSession();

  if (surface === "presentation") {
    return <>{children}</>;
  }

  if (surface === "auth") {
    return <div className="min-h-screen bg-canvas">{children}</div>;
  }

  if (surface === "public") {
    return (
      <div className="flex min-h-screen flex-col bg-canvas">
        <PublicHeader />
        <main id="workspace-content" className="flex-1">{children}</main>
        <PublicFooter />
      </div>
    );
  }

  const clinicalHelpers = me ? (
    <>
      {!isOperator && surface === "hospital" && <ShiftStrip />}
      <AttentionBanner />
      <OfflineSync />
      <AlertNotifier />
    </>
  ) : null;

  if (surface === "vendor" || (account?.vendor && !me)) {
    if (!loading && !account?.vendor && !me) {
      return <SignInGate pathname={pathname} label="Vendor sign-in required" />;
    }
    const vendorLinks = account?.vendor
      ? VENDOR.filter((link) => {
          if (link.href === "/platform/commercial") {
            return ["root_admin", "platform_admin", "finance_legal", "evaluation_operator"].includes(account.role || "");
          }
          if (link.href === "/platform/service") {
            return ["root_admin", "platform_admin", "deployment_engineer", "support_engineer", "security_compliance", "evaluation_operator"].includes(account.role || "");
          }
          if (link.href === "/platform/documents") {
            return ["root_admin", "platform_admin", "finance_legal", "security_compliance", "evaluation_operator"].includes(account.role || "");
          }
          return true;
        })
      : OPERATOR_FLEET;
    return (
      <>
        {clinicalHelpers}
        <WorkspaceShell
          surfaceLabel={account?.vendor ? "Vendor Control Plane" : "Fleet Operator Console"}
          homeHref="/platform/overview"
          links={vendorLinks}
          context={
            account?.vendor
              ? "Tenants, CRM, licences — no patient records"
              : "Hospital-issued operator session · use vendor@auralis.demo for CRM"
          }
        >
          {children}
        </WorkspaceShell>
        <EvaluationSwitcher />
      </>
    );
  }

  if (surface === "customer") {
    if (!loading && !account) {
      return <SignInGate pathname={pathname} label="Organization sign-in required" />;
    }
    return (
      <>
        {clinicalHelpers}
        <WorkspaceShell
          surfaceLabel="Customer Portal"
          homeHref="/portal"
          links={CUSTOMER}
          context={account?.organization_ids?.[0] ? `Organization · ${account.organization_ids[0]}` : "Organization account"}
        >
          {children}
        </WorkspaceShell>
      </>
    );
  }

  if (surface === "evaluation" || me?.evaluation_runtime) {
    return (
      <>
        {clinicalHelpers}
        <WorkspaceShell
          surfaceLabel="Evaluation Environment"
          homeHref="/system-check"
          links={EVALUATION}
          context="Synthetic / replay data only"
          topAccessory={
            <span className="hidden rounded-full border border-border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-teal sm:inline">
              Synthetic
            </span>
          }
        >
          {children}
        </WorkspaceShell>
        <EvaluationSwitcher />
      </>
    );
  }

  if (surface === "deployment") {
    if (!loading && !me && !account) {
      return <SignInGate pathname={pathname} label="Deployment sign-in required" />;
    }
    const deployLinks = me?.role === "clinical_it" ? CLINICAL_IT : DEPLOYMENT;
    return (
      <>
        {clinicalHelpers}
        <WorkspaceShell
          surfaceLabel="Hospital Deployment Console"
          homeHref="/deploy"
          links={deployLinks}
          context="Site commissioning & integration"
        >
          {children}
        </WorkspaceShell>
        <EvaluationSwitcher />
      </>
    );
  }

  if (!me && !loading && !account) {
    return <SignInGate pathname={pathname || "/app/icu"} label="Hospital sign-in required" />;
  }

  return (
    <>
      {clinicalHelpers}
      <WorkspaceShell
        surfaceLabel="Hospital Workspace"
        homeHref={isAdmin ? "/app/admin/overview" : me?.role === "clinical_it" ? "/deploy" : "/app/icu"}
        links={hospitalLinks(me?.role, isAdmin)}
        context={me?.units?.length ? `Units · ${me.units.join(", ")}` : "Authorized clinical workspace"}
      >
        {children}
      </WorkspaceShell>
      <EvaluationSwitcher />
    </>
  );
}
