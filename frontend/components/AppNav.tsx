"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ShiftStrip } from "@/components/ShiftStrip";
import { useLocale } from "@/lib/locale";
import { humanize } from "@/lib/pilot";
import { useSession } from "@/lib/session";

export function AppNav() {
  const pathname = usePathname();
  const [hidden, setHidden] = useState(false);
  const previousY = useRef(0);
  useEffect(() => {
    let frame = 0;
    const onScroll = () => {
      if (frame) return;
      frame = window.requestAnimationFrame(() => {
        const currentY = window.scrollY;
        if (currentY < 32 || currentY < previousY.current - 6) setHidden(false);
        else if (currentY > previousY.current + 6) setHidden(true);
        previousY.current = currentY;
        frame = 0;
      });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => { window.removeEventListener("scroll", onScroll); if (frame) window.cancelAnimationFrame(frame); };
  }, []);
  const { locale, setLocale, t } = useLocale();
  const { me, isAdmin, isOperator } = useSession();
  if (pathname === "/presentation") return null;
  const publicView = !me;
  const links = [
    ...(!me
      ? [
          { href: "/#platform", label: "Platform" },
          { href: "/#architecture", label: "Architecture" },
          { href: "/#intelligence", label: "Intelligence" },
          { href: "/#evidence", label: "Evidence" },
          { href: "/#deployment", label: "Deployment" },
        ]
      : isOperator
      ? [
          { href: process.env.NEXT_PUBLIC_FLEET_URL || "/fleet", label: "Fleet console" },
          { href: "/super-admin", label: "Platform" },
          { href: "/operations", label: "Operations" },
          { href: "/connection", label: "Connection" },
          { href: "/evidence", label: "Evidence" },
          { href: "/business", label: "Business" },
        ]
      : [
          { href: "/icu", label: t.nav.overview },
          { href: "/home", label: "Portal" },
          { href: "/staff", label: "On shift" },
          { href: "/chart", label: t.nav.chart },
          { href: "/ward", label: t.nav.ward },
          { href: "/alerts", label: t.nav.alerts },
          { href: "/handoff", label: t.nav.handoff },
          { href: "/workflows", label: "How it works" },
          { href: "/connection", label: "Connection" },
          { href: "/evidence", label: "Evidence" },
          { href: "/business", label: "For hospitals" },
        ]),
    ...(isAdmin
      ? [
          { href: "/pilot", label: t.nav.pilot },
          { href: "/integration", label: t.nav.integration },
          { href: "/operations", label: "Operations" },
          { href: "/admin/setup", label: "Site setup" },
          { href: "/admin/users", label: t.nav.users },
          { href: "/model", label: t.nav.model },
          { href: "/readiness", label: t.nav.readiness },
          { href: "/api-reference", label: "Integration API" },
        ]
      : []),
  ];
  return (
    <header className={`sticky top-0 z-40 border-b backdrop-blur transition-transform duration-200 ${publicView ? "border-slate-800 bg-[#080C14]/95 text-slate-50" : "border-slate-200 bg-white/95 text-ink"} ${hidden ? "-translate-y-full" : "translate-y-0"}`}>
      {me && <ShiftStrip />}
      <nav className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-5 gap-y-2 px-4 py-3 sm:px-6" aria-label="Primary">
        <Link href="/" className={`mr-auto text-lg font-semibold tracking-tight ${publicView ? "text-slate-50" : "text-ink"}`}>
          <span className={publicView ? "text-cyan-300" : "text-accent"} aria-hidden="true">⌁ </span>PredictRx <span className={publicView ? "text-cyan-300" : "text-accent"}>Sentinel</span>
        </Link>
        {links.map((link) => {
          const active = pathname === link.href || pathname.startsWith(link.href + "/");
          return (
            <Link
              key={link.href}
              href={link.href}
              aria-current={active ? "page" : undefined}
              className={`text-sm font-medium transition duration-150 ${publicView ? "hidden lg:inline" : ""} ${
                active ? (publicView ? "text-cyan-300" : "text-accent underline decoration-2 underline-offset-4") : (publicView ? "text-slate-400 hover:text-slate-50" : "text-ink/60 hover:text-ink")
              }`}
            >
              {link.label}
            </Link>
          );
        })}
        {me && (
            <span className="rounded-full bg-mist px-2.5 py-1 text-xs text-ink/60" title={`Signed in · ${humanize(me.auth_mode)}`}>
              {humanize(me.role)}
          </span>
        )}
        {me && <Link href="/profile" className="text-sm font-medium text-accent">My app</Link>}
        <Link
          href="/login"
          aria-current={pathname === "/login" ? "page" : undefined}
          className={`px-4 py-2 text-xs font-semibold transition-colors duration-150 ${publicView ? "bg-cyan-400 text-slate-950 hover:bg-cyan-300" : "bg-ink text-white"}`}
        >
          {me ? "Session" : t.nav.signIn}
        </Link>
        <button
          type="button"
          onClick={() => setLocale(locale === "en" ? "bn" : "en")}
          className={`px-2.5 py-1.5 text-xs ${publicView ? "border border-slate-700 text-slate-200" : "bg-mist text-ink/70"}`}
          aria-label="Toggle clinician language"
        >
          {locale === "en" ? "বাংলা" : "EN"}
        </button>
      </nav>
    </header>
  );
}
