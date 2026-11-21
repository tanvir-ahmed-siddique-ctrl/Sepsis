"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ShiftStrip } from "@/components/ShiftStrip";
import { api } from "@/lib/api";
import { useLocale } from "@/lib/locale";
import { humanize } from "@/lib/pilot";
import { useSession } from "@/lib/session";

const clinical = [
  { href: "/app/icu", label: "ICU" }, { href: "/app/chart", label: "Charting" },
  { href: "/app/ward", label: "Ward / NEWS2" }, { href: "/app/alerts", label: "Alerts" },
  { href: "/app/handoff", label: "Handoff" }, { href: "/app/staff", label: "Staff" },
];
const clinicalViewer = [
  { href: "/app/icu", label: "ICU (read-only)" }, { href: "/app/alerts", label: "Alerts (read-only)" },
  { href: "/app/handoff", label: "Handoff" }, { href: "/app/staff", label: "Staff" },
];
const clinicalIt = [
  { href: "/deploy", label: "Deployment home" },
  { href: "/app/admin/integrations", label: "Integrations" },
  { href: "/connection", label: "Connection ladder" },
  { href: "/integration", label: "Integration hub" },
];
const admin = [
  { href: "/app/admin/overview", label: "Admin home" }, { href: "/app/admin/users", label: "Users" },
  { href: "/app/admin/setup", label: "Site setup" }, { href: "/app/admin/integrations", label: "Integrations" },
  { href: "/app/admin/pilot", label: "Pilot" }, { href: "/app/admin/readiness", label: "Readiness" },
  { href: "/app/admin/operations", label: "Site operations" }, { href: "/app/model", label: "Model evidence" },
  { href: "/app/admin/licence", label: "Site licence" },
];

export function AppNav() {
  const pathname = usePathname();
  const [hidden, setHidden] = useState(false);
  const previousY = useRef(0);
  const [menuOpen, setMenuOpen] = useState(false);
  const [workspaces, setWorkspaces] = useState<Array<{ id: string; label: string; path: string }>>([]);
  const { t } = useLocale();
  const { me, account, isAdmin, isOperator, loading, signOut } = useSession();
  useEffect(() => {
    if (!me) { setWorkspaces([]); return; }
    let active = true;
    void api<{ workspaces: Array<{ id: string; label: string; path: string }> }>("/v1/auth/workspaces")
      .then((result) => { if (active) setWorkspaces(result.workspaces); })
      .catch(() => { if (active) setWorkspaces([]); });
    return () => { active = false; };
  }, [me]);
  useEffect(() => {
    let frame = 0;
    const onScroll = () => {
      if (frame) return;
      frame = window.requestAnimationFrame(() => {
        const y = window.scrollY;
        if (y < 32 || y < previousY.current - 6) setHidden(false);
        else if (y > previousY.current + 6) setHidden(true);
        previousY.current = y;
        frame = 0;
      });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => { window.removeEventListener("scroll", onScroll); if (frame) window.cancelAnimationFrame(frame); };
  }, []);
  if (["/presentation", "/signin", "/login", "/system-check"].includes(pathname)) return null;
  const publicView = !me && !account && !loading;
  const hospitalLinks = me?.role === "clinical_viewer"
    ? clinicalViewer
    : me?.role === "clinical_it"
      ? clinicalIt
      : clinical.filter((item) => me?.role !== "integration");
  const links = !me ? [] : isOperator
    ? [
        { href: "/platform/overview", label: "Control plane" },
        { href: "/operations", label: "Site diagnostics" },
        { href: "/readiness", label: "Readiness gates" },
        { href: "/business", label: "Commercial model" },
      ]
    : [...hospitalLinks, { href: "/workflows", label: "Workflow guide" }];
  const accountLinks = account?.vendor
    ? [
      { href: "/platform/accounts", label: "Organization registry" },
      ...(["root_admin", "platform_admin", "finance_legal", "evaluation_operator"].includes(account.role) ? [{ href: "/platform/commercial", label: "Contracts & finance" }] : []),
      ...(["root_admin", "platform_admin", "deployment_engineer", "support_engineer", "security_compliance", "evaluation_operator"].includes(account.role) ? [{ href: "/platform/service", label: "Deployment & service" }] : []),
      ...(["root_admin", "platform_admin", "finance_legal", "security_compliance", "evaluation_operator"].includes(account.role) ? [{ href: "/platform/documents", label: "Documents" }] : []),
    ] : account ? [{ href: "/portal", label: "Organization" }, { href: "/portal/commercial", label: "Contracts & finance" }, { href: "/portal/service", label: "Deployment & service" }, { href: "/portal/documents", label: "Documents" }] : [];
  function linkClass(href: string) {
    const active = pathname === href || pathname.startsWith(href + "/");
    return "whitespace-nowrap text-sm transition-colors duration-150 " + (active ? "font-semibold text-forest underline decoration-2 underline-offset-8" : "text-slate hover:text-ink");
  }
  return (
    <header className={"sticky top-0 z-40 border-b border-[#D6DCD8] bg-[#FCFBF8]/95 text-ink backdrop-blur transition-transform duration-200 " + (hidden ? "-translate-y-full" : "translate-y-0")}>
      {me && !isOperator && <ShiftStrip />}
      <nav className="mx-auto flex max-w-[1440px] flex-wrap items-center gap-4 px-4 py-3 sm:px-6" aria-label="Primary">
        <Link href="/" className="mr-auto shrink-0 font-semibold tracking-tight text-ink">Auralis</Link>
        {publicView && <div className="hidden items-center gap-5 xl:flex">{[
          ["/#platform","Platform"],["/#architecture","Architecture"],["/#intelligence","Clinical system"],["/#evidence","Evidence"],["/services","Services"],["/contact","Contact"],
        ].map(([href,label])=><Link key={href} href={href} className="whitespace-nowrap text-sm text-slate transition-colors hover:text-forest">{label}</Link>)}</div>}
        {account && <div className="hidden items-center gap-5 lg:flex">{accountLinks.map((item) => <Link key={item.href} href={item.href} className={linkClass(item.href)}>{item.label}</Link>)}</div>}
        {me && <div className="hidden flex-wrap items-center gap-x-5 gap-y-2 lg:flex">{links.map((item)=>{const active=pathname===item.href||pathname.startsWith(item.href+"/");return <Link key={item.href} href={item.href} aria-current={active?"page":undefined} className={linkClass(item.href)}>{item.label}</Link>})}
          {isAdmin && !isOperator && <details open={pathname.startsWith("/app/admin")} className="group relative"><summary className="cursor-pointer list-none whitespace-nowrap text-sm text-slate transition-colors hover:text-ink">Hospital administration <span aria-hidden="true">⌄</span></summary><div className="absolute right-0 top-full z-50 mt-3 grid min-w-64 gap-1 border border-[#D6DCD8] bg-[#FCFBF8] p-2 shadow-lg">{admin.map((item)=>{const active=pathname===item.href||pathname.startsWith(item.href+"/");return <Link key={item.href} href={item.href} aria-current={active?"page":undefined} className={"px-3 py-2 text-sm hover:bg-[#E9ECEA] " +(active?"font-semibold text-forest":"text-ink")}>{item.label}</Link>})}</div></details>}
        </div>}
        <div className="flex items-center gap-3">
          {me && workspaces.length > 1 && <details className="relative hidden sm:block"><summary className="cursor-pointer text-xs font-semibold text-forest">Workspaces</summary><div className="absolute right-0 top-full z-50 mt-3 min-w-48 border border-[#D6DCD8] bg-warm p-2 shadow-lg">{workspaces.map((workspace)=><Link key={workspace.id} href={workspace.path} className="block px-3 py-2 text-sm text-ink hover:bg-[#E9ECEA]">{workspace.label}</Link>)}</div></details>}
          {me && <Link href="/app/profile" className="hidden text-sm text-slate hover:text-forest sm:inline" title={"Signed in · " + humanize(me.auth_mode)}>{me.display_name || humanize(me.role)}</Link>}
          {account && <span className="hidden text-sm text-slate sm:inline">{account.display_name}</span>}
          {me || account ? <button type="button" onClick={signOut} className="border border-[#C6CECA] px-3 py-2 text-xs font-semibold hover:border-forest">Sign out</button> : <Link href="/signin" className="bg-forest px-4 py-2 text-xs font-semibold text-white transition-colors hover:bg-[#1E443D]">{t.nav.signIn}</Link>}
          {me && <button type="button" className="border border-[#C6CECA] px-2.5 py-2 text-xs lg:hidden" aria-expanded={menuOpen} aria-label="Toggle workspace navigation" onClick={() => setMenuOpen((v)=>!v)}>Menu</button>}
        </div>
        {me && menuOpen && <div className="order-3 flex w-full flex-wrap gap-x-5 gap-y-3 border-t border-[#D6DCD8] pt-3 lg:hidden">{links.map((item)=><Link key={item.href} href={item.href} onClick={()=>setMenuOpen(false)} className={linkClass(item.href)}>{item.label}</Link>)}{workspaces.length > 1 && <div className="basis-full border-t border-[#D6DCD8] pt-3"><p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate">Workspaces</p>{workspaces.map((workspace)=><Link key={workspace.id} href={workspace.path} onClick={()=>setMenuOpen(false)} className="mr-5 text-sm text-forest">{workspace.label}</Link>)}</div>}{isAdmin && !isOperator && <div className="basis-full border-t border-[#D6DCD8] pt-3"><p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate">Hospital administration</p><div className="flex flex-wrap gap-x-5 gap-y-3">{admin.map((item)=><Link key={item.href} href={item.href} onClick={()=>setMenuOpen(false)} className={linkClass(item.href)}>{item.label}</Link>)}</div></div>}</div>}
        {account && <div className="order-3 flex w-full flex-wrap gap-4 border-t border-[#D6DCD8] pt-3 lg:hidden">{accountLinks.map((item) => <Link key={item.href} href={item.href} className="text-sm font-semibold text-forest">{item.label}</Link>)}</div>}
      </nav>
    </header>
  );
}
