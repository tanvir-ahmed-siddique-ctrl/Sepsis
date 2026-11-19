"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
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
  const router = useRouter();
  const { me, account, signOut } = useSession();
  const [open, setOpen] = useState(false);
  const identity = me?.display_name || account?.display_name || "Signed in";
  const role = me ? humanize(me.role) : account ? humanize(account.role) : "";

  function linkClass(href: string) {
    const active = pathname === href || pathname.startsWith(href + "/");
    return `block rounded-lg px-3 py-2.5 text-sm transition-colors ${
      active
        ? "bg-teal/10 font-semibold text-teal"
        : "text-muted hover:bg-muted-surface hover:text-ink"
    }`;
  }

  function handleSignOut() {
    signOut();
    router.push("/signin");
    router.refresh();
  }

  return (
    <div className="min-h-screen bg-[#F4F7F6] text-ink">
      <header className="sticky top-0 z-40 border-b border-border/80 bg-white/95 backdrop-blur-md">
        <div className="auralis-container flex items-center gap-4 py-3.5">
          <BrandMark href={homeHref} compact />
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-teal">{surfaceLabel}</p>
            {context && <p className="truncate text-xs text-muted">{context}</p>}
          </div>
          <div className="ml-auto flex items-center gap-2">
            {topAccessory}
            <span className="hidden rounded-full bg-muted-surface px-3 py-1.5 text-xs font-medium text-ink sm:inline">
              {identity}
              {role ? ` · ${role}` : ""}
            </span>
            <Link href={me ? "/app/profile" : account ? "/platform/accounts" : "/signin"} className="auralis-btn-ghost hidden sm:inline-flex">
              Account
            </Link>
            <button type="button" onClick={handleSignOut} className="auralis-btn-secondary">
              Sign out
            </button>
            <button
              type="button"
              className="auralis-btn-secondary lg:hidden"
              aria-expanded={open}
              onClick={() => setOpen((v) => !v)}
            >
              Menu
            </button>
          </div>
        </div>
      </header>
      <div className="auralis-container grid gap-6 py-6 lg:grid-cols-[16rem_minmax(0,1fr)]">
        <aside className={`rounded-2xl border border-border bg-white p-2 shadow-sm ${open ? "block" : "hidden lg:block"}`}>
          <nav className="space-y-0.5" aria-label={`${surfaceLabel} navigation`}>
            {links.map((item) => (
              <Link key={item.href} href={item.href} className={linkClass(item.href)} onClick={() => setOpen(false)}>
                {item.label}
              </Link>
            ))}
          </nav>
        </aside>
        <div className="auralis-workspace min-w-0 rounded-2xl border border-border bg-white p-5 shadow-sm sm:p-7">{children}</div>
      </div>
      <AppUtilityFooter surface={surfaceLabel} />
    </div>
  );
}
