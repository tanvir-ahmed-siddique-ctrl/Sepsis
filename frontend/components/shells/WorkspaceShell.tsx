"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";
import { BrandMark } from "@/components/ui/BrandMark";
import { AppUtilityFooter } from "@/components/shells/AppUtilityFooter";
import { useSession } from "@/lib/session";
import { humanize } from "@/lib/pilot";

export type ShellLink = { href: string; label: string };

export function WorkspaceShell({
  surfaceLabel,
  homeHref,
  links,
  context,
  children,
  topAccessory,
}: {
  surfaceLabel: string;
  homeHref: string;
  links: ShellLink[];
  context?: string;
  children: ReactNode;
  topAccessory?: ReactNode;
}) {
  const pathname = usePathname();
  const { me, account, signOut } = useSession();
  const [open, setOpen] = useState(false);
  const identity = me?.display_name || account?.display_name || "Signed in";
  const role = me ? humanize(me.role) : account ? humanize(account.role) : "";

  function linkClass(href: string) {
    const active = pathname === href || pathname.startsWith(href + "/");
    return `block border-l-2 px-3 py-2 text-sm ${active ? "border-teal bg-muted-surface font-semibold text-teal" : "border-transparent text-muted hover:border-border hover:bg-white hover:text-ink"}`;
  }

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <header className="sticky top-0 z-40 border-b border-border bg-white">
        <div className="auralis-container flex items-center gap-4 py-3">
          <BrandMark href={homeHref} compact />
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-teal">{surfaceLabel}</p>
            {context && <p className="truncate text-xs text-muted">{context}</p>}
          </div>
          <div className="ml-auto flex items-center gap-2">
            {topAccessory}
            <span className="hidden text-sm text-muted sm:inline">{identity}{role ? ` · ${role}` : ""}</span>
            <Link href={me ? "/app/profile" : "/signin"} className="auralis-btn-ghost hidden sm:inline-flex">Account</Link>
            <button type="button" onClick={signOut} className="auralis-btn-secondary">Sign out</button>
            <button type="button" className="auralis-btn-secondary lg:hidden" aria-expanded={open} onClick={() => setOpen((v) => !v)}>Menu</button>
          </div>
        </div>
      </header>
      <div className="auralis-container grid gap-6 py-6 lg:grid-cols-[15rem_minmax(0,1fr)]">
        <aside className={`border border-border bg-white ${open ? "block" : "hidden lg:block"}`}>
          <nav className="p-2" aria-label={`${surfaceLabel} navigation`}>
            {links.map((item) => (
              <Link key={item.href} href={item.href} className={linkClass(item.href)} onClick={() => setOpen(false)}>
                {item.label}
              </Link>
            ))}
          </nav>
        </aside>
        <div className="min-w-0">{children}</div>
      </div>
      <AppUtilityFooter surface={surfaceLabel} />
    </div>
  );
}
