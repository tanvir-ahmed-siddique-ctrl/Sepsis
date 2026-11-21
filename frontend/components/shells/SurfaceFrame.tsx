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
import { BrandMark } from "@/components/ui/BrandMark";
import { Icon } from "@/components/ui/Icon";

const HOSPITAL_CLINICAL: ShellLink[] = [
  { href: "/app/icu", label: "ICU board", icon: "grid", group: "Monitor" },
  { href: "/app/ward", label: "Ward / NEWS2", icon: "bed", group: "Monitor" },
  { href: "/app/alerts", label: "Alerts", icon: "bell", group: "Monitor" },
  { href: "/app/chart", label: "Charting", icon: "clipboard", group: "Care" },
  { href: "/app/handoff", label: "Handoff", icon: "handoff", group: "Care" },
  { href: "/app/staff", label: "Staff", icon: "users", group: "Team" },
  { href: "/app/profile", label: "Profile", icon: "user", group: "Team" },
];

const HOSPITAL_VIEWER: ShellLink[] = [
  { href: "/app/icu", label: "ICU (read-only)", icon: "grid", group: "Monitor" },
  { href: "/app/alerts", label: "Alerts", icon: "bell", group: "Monitor" },
  { href: "/app/handoff", label: "Handoff", icon: "handoff", group: "Monitor" },
  { href: "/app/staff", label: "Staff", icon: "users", group: "Team" },
  { href: "/app/profile", label: "Profile", icon: "user", group: "Team" },
];

const HOSPITAL_ADMIN: ShellLink[] = [
  { href: "/app/admin/overview", label: "Hospital overview", icon: "gauge", group: "Administration" },
  { href: "/app/admin/users", label: "Staff & access", icon: "users", group: "Administration" },
  { href: "/app/admin/setup", label: "Unit settings", icon: "settings", group: "Administration" },
  { href: "/app/admin/shift-roster", label: "Shift roster", icon: "clock", group: "Administration" },
  { href: "/app/admin/pilot", label: "Silent evaluation", icon: "shield", group: "Governance" },
  { href: "/app/icu", label: "ICU board", icon: "grid", group: "Clinical" },
  { href: "/app/ward", label: "Ward / NEWS2", icon: "bed", group: "Clinical" },
  { href: "/app/alerts", label: "Alerts", icon: "bell", group: "Clinical" },
  { href: "/app/handoff", label: "Handoff", icon: "handoff", group: "Clinical" },
  { href: "/app/staff", label: "Staff directory", icon: "users", group: "Clinical" },
  { href: "/app/admin/integrations", label: "Integrations", icon: "plug", group: "Technical" },
  { href: "/app/admin/connections", label: "Connectivity", icon: "activity", group: "Technical" },
  { href: "/app/admin/readiness", label: "Readiness gates", icon: "check", group: "Technical" },
  { href: "/app/admin/operations", label: "Ops & backup", icon: "server", group: "Technical" },
  { href: "/app/admin/licence", label: "Site licence", icon: "key", group: "Technical" },
  { href: "/deploy", label: "Deployment console", icon: "layers", group: "Technical" },
  { href: "/app/profile", label: "Profile", icon: "user", group: "Account" },
];

/** clinical_it: integrations only. Readiness / ops / licence APIs require admin|operator. */
const CLINICAL_IT: ShellLink[] = [
  { href: "/deploy", label: "Deployment home", icon: "gauge", group: "Overview" },
  { href: "/app/admin/integrations", label: "Integrations", icon: "plug", group: "Interfaces" },
  { href: "/app/admin/connections", label: "Connectivity", icon: "activity", group: "Interfaces" },
  { href: "/app/profile", label: "Profile", icon: "user", group: "Account" },
];

/** Hospital admin deployment console — /app/admin/* requires hospital-admin workspace. */
const DEPLOYMENT: ShellLink[] = [
  { href: "/deploy", label: "Overview", icon: "gauge", group: "Overview" },
  { href: "/app/admin/setup", label: "Site setup", icon: "settings", group: "Interfaces" },
  { href: "/app/admin/integrations", label: "HIS / interfaces", icon: "plug", group: "Interfaces" },
  { href: "/app/admin/connections", label: "Connectivity", icon: "activity", group: "Interfaces" },
  { href: "/app/admin/readiness", label: "Readiness gates", icon: "check", group: "Operations" },
  { href: "/app/admin/operations", label: "Ops & backup", icon: "server", group: "Operations" },
  { href: "/app/admin/licence", label: "Licence", icon: "key", group: "Operations" },
];

/**
 * Hospital operator (platform workspace): metadata routes outside /app.
 * /app/* is gated to clinical|hospital-admin|hospital-integration only.
 */
const OPERATOR_SITE: ShellLink[] = [
  { href: "/platform/overview", label: "Fleet overview", icon: "gauge", group: "Overview" },
  { href: "/operations", label: "Site diagnostics", icon: "server", group: "Operations" },
  { href: "/readiness", label: "Readiness gates", icon: "check", group: "Operations" },
];

const VENDOR: ShellLink[] = [
  { href: "/platform/overview", label: "Control plane home", icon: "gauge", group: "Overview" },
  { href: "/platform/accounts", label: "Organizations & sites", icon: "building", group: "Customers" },
  { href: "/platform/commercial", label: "Commercial", icon: "briefcase", group: "Customers" },
  { href: "/platform/partnership", label: "Partnership / FDE", icon: "layers", group: "Customers" },
  { href: "/platform/service", label: "Support & service", icon: "lifebuoy", group: "Operations" },
  { href: "/platform/documents", label: "Documents", icon: "doc", group: "Operations" },
  { href: "/operations", label: "Fleet site diagnostics", icon: "server", group: "Fleet" },
  { href: "/readiness", label: "Readiness overview", icon: "check", group: "Fleet" },
  { href: "/super-admin", label: "Operator desk", icon: "key", group: "Fleet" },
];

const OPERATOR_FLEET: ShellLink[] = [
  { href: "/platform/overview", label: "Fleet overview", icon: "gauge", group: "Overview" },
  { href: "/operations", label: "Site diagnostics", icon: "server", group: "Operations" },
  { href: "/readiness", label: "Readiness gates", icon: "check", group: "Operations" },
];

const VENDOR_COMMERCIAL_ROLES = ["root_admin", "platform_admin", "finance_legal", "evaluation_operator"];
const VENDOR_SERVICE_ROLES = ["root_admin", "platform_admin", "deployment_engineer", "support_engineer", "security_compliance", "evaluation_operator"];
const VENDOR_DOCUMENT_ROLES = ["root_admin", "platform_admin", "finance_legal", "security_compliance", "evaluation_operator"];
const VENDOR_PARTNERSHIP_ROLES = ["root_admin", "platform_admin", "deployment_engineer", "evaluation_operator"];
const VENDOR_FLEET_ROLES = ["root_admin", "platform_admin", "evaluation_operator"];

const CUSTOMER: ShellLink[] = [
  { href: "/portal", label: "Organization home", icon: "building" },
  { href: "/portal/commercial", label: "Contracts & finance", icon: "briefcase" },
  { href: "/portal/service", label: "Service & offboarding", icon: "lifebuoy" },
  { href: "/portal/documents", label: "Documents", icon: "doc" },
];

const EVALUATION: ShellLink[] = [
  { href: "/system-check", label: "Evaluation gate", icon: "shield" },
  { href: "/app/icu", label: "Synthetic ICU", icon: "grid" },
  { href: "/app/alerts", label: "Review history", icon: "bell" },
  { href: "/evidence", label: "Evidence notes", icon: "doc" },
];

function hospitalLinks(role?: string, isAdmin?: boolean): ShellLink[] {
  if (role === "clinical_viewer") return HOSPITAL_VIEWER;
  if (role === "clinical_it") return CLINICAL_IT;
  if (isAdmin || role === "admin") return HOSPITAL_ADMIN;
  return HOSPITAL_CLINICAL;
}

function SignInGate({
  pathname,
  label,
  description,
}: {
  pathname: string;
  label: string;
  description: string;
}) {
  const signInHref = `/signin?next=${encodeURIComponent(pathname || "/")}`;
  return (
    <div className="flex min-h-screen flex-col bg-canvas">
      <div className="px-6 py-5 sm:px-10">
        <BrandMark href="/" compact />
      </div>
      <div className="flex flex-1 items-center justify-center px-6 pb-24">
        <div className="w-full max-w-md rounded-2xl border border-border bg-white p-8 text-center shadow-card">
          <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-full bg-muted-surface text-navy">
            <Icon name="lock" size={20} />
          </span>
          <h1 className="mt-5 text-xl font-semibold text-ink">{label}</h1>
          <p className="mt-2 text-sm leading-6 text-muted">{description}</p>
          <div className="mt-7 flex flex-col gap-2.5 sm:flex-row sm:justify-center">
            <Link href={signInHref} className="group auralis-btn-primary">
              Sign in
              <Icon name="arrow-right" size={16} className="transition-transform group-hover:translate-x-0.5" />
            </Link>
            <Link href="/" className="auralis-btn-secondary">
              Back to website
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

function deploymentLinksForRole(role?: string): ShellLink[] {
  if (role === "clinical_it") return CLINICAL_IT;
  if (role === "operator") return OPERATOR_SITE;
  return DEPLOYMENT;
}

export function SurfaceFrame({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const surface = resolveSurface(pathname);
  const { me, account, isAdmin, isOperator, loading } = useSession();

  if (surface === "presentation") {
    return <>{children}</>;
  }

  if (surface === "auth") {
    return <div className="min-h-screen bg-white">{children}</div>;
  }

  if (surface === "public") {
    const isHome = pathname === "/" || pathname === "/home";
    return (
      <div className="flex min-h-screen flex-col bg-canvas">
        <PublicHeader />
        <main id="workspace-content" className="flex-1">{children}</main>
        <PublicFooter showHomeWordmark={isHome} />
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
      return (
        <SignInGate
          pathname={pathname}
          label="Vendor sign-in required"
          description="Open this surface with a vendor control-plane account (for example vendor@auralis.demo). A hospital operator session alone cannot open CRM or tenant tools."
        />
      );
    }
    const vendorLinks = account?.vendor
      ? VENDOR.filter((link) => {
          if (link.href === "/platform/commercial") {
            return VENDOR_COMMERCIAL_ROLES.includes(account.role || "");
          }
          if (link.href === "/platform/service") {
            return VENDOR_SERVICE_ROLES.includes(account.role || "");
          }
          if (link.href === "/platform/documents") {
            return VENDOR_DOCUMENT_ROLES.includes(account.role || "");
          }
          if (link.href === "/platform/partnership") {
            return VENDOR_PARTNERSHIP_ROLES.includes(account.role || "");
          }
          if (link.href === "/operations" || link.href === "/readiness" || link.href === "/super-admin") {
            return VENDOR_FLEET_ROLES.includes(account.role || "");
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
              : "Hospital operator · site metadata only · CRM needs a separate vendor account"
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
      return (
        <SignInGate
          pathname={pathname}
          label="Organization account required"
          description="This is the hospital customer portal for contracts and organisation records. It needs an organisation account, not a hospital clinical role, fleet operator session, or vendor control-plane login."
        />
      );
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
            <span className="hidden rounded-full border border-teal/25 bg-teal-soft/50 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-teal-dark sm:inline">
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
      return (
        <SignInGate
          pathname={pathname}
          label="Deployment sign-in required"
          description="Sign in with a hospital administrator, clinical IT, or platform operator identity to open site commissioning tools."
        />
      );
    }
    // Hospital admins keep the same workspace nav when opening /deploy —
    // Technical is hierarchy, not a different role shell.
    const keepHospitalNav = Boolean(isAdmin && me?.role !== "clinical_it" && me?.role !== "operator");
    if (keepHospitalNav) {
      return (
        <>
          {clinicalHelpers}
          <WorkspaceShell
            surfaceLabel="Hospital Workspace"
            homeHref="/app/admin/overview"
            links={HOSPITAL_ADMIN}
            context={me?.units?.length ? `Units · ${me.units.join(", ")}` : "Authorized clinical workspace"}
            showInstallApp
          >
            {children}
          </WorkspaceShell>
          <EvaluationSwitcher />
        </>
      );
    }
    const deployLinks = deploymentLinksForRole(me?.role);
    const operatorSurface = me?.role === "operator";
    return (
      <>
        {clinicalHelpers}
        <WorkspaceShell
          surfaceLabel={operatorSurface ? "Fleet Operator Console" : "Hospital Deployment Console"}
          homeHref={operatorSurface ? "/platform/overview" : "/deploy"}
          links={deployLinks}
          context={
            operatorSurface
              ? "Site metadata diagnostics · no patient records · no hospital-admin pages"
              : me?.role === "clinical_it"
                ? "HIS interfaces & connectivity · readiness/ops/licence stay with hospital admin"
                : "Site commissioning & integration"
          }
          showInstallApp={!operatorSurface}
        >
          {children}
        </WorkspaceShell>
        <EvaluationSwitcher />
      </>
    );
  }

  if (!me && !loading && !account) {
    return (
      <SignInGate
        pathname={pathname || "/app/icu"}
        label="Hospital sign-in required"
        description="Sign in with your hospital credentials, or a matching sample role, to open this workspace."
      />
    );
  }

  return (
    <>
      {clinicalHelpers}
      <WorkspaceShell
        surfaceLabel="Hospital Workspace"
        homeHref={isAdmin ? "/app/admin/overview" : me?.role === "clinical_it" ? "/deploy" : "/app/icu"}
        links={hospitalLinks(me?.role, isAdmin)}
        context={me?.units?.length ? `Units · ${me.units.join(", ")}` : "Authorized clinical workspace"}
        showInstallApp
      >
        {children}
      </WorkspaceShell>
      <EvaluationSwitcher />
    </>
  );
}
