"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { BrandGlyph, BrandMark } from "@/components/ui/BrandMark";
import { Icon, type IconName } from "@/components/ui/Icon";
import { AppUtilityFooter } from "@/components/shells/AppUtilityFooter";
import { InstallAppControl } from "@/components/InstallAppControl";
import { LanguageSelect } from "@/components/LanguageSelect";
import { useSession } from "@/lib/session";
import { humanize } from "@/lib/pilot";

export type ShellLink = { href: string; label: string; icon?: IconName; group?: string };

const SIDEBAR_KEY = "auralis-sidebar-collapsed";

function groupLinks(links: ShellLink[]) {
  const groups: Array<{ name?: string; items: ShellLink[] }> = [];
  for (const link of links) {
    const last = groups[groups.length - 1];
    if (last && last.name === link.group) last.items.push(link);
    else groups.push({ name: link.group, items: [link] });
  }
  return groups;
}

export function WorkspaceShell({
  surfaceLabel,
  homeHref,
  links,
  context,
  children,
  topAccessory,
  showInstallApp = false,
}: {
  surfaceLabel: string;
  homeHref: string;
  links: ShellLink[];
  context?: string;
  children: ReactNode;
  topAccessory?: ReactNode;
  /** Hospital workspaces offer PWA install from the top bar. */
  showInstallApp?: boolean;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { me, account, signOut } = useSession();
  const [open, setOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const identity = me?.display_name || me?.user_id || account?.display_name || "Signed in";
  const role = me ? humanize(me.role) : account ? humanize(account.role) : "";
  const accountHref = me ? "/app/profile" : account ? "/platform/accounts" : "/signin";
  const current = links
    .filter((item) => pathname === item.href || pathname.startsWith(item.href + "/"))
    .sort((a, b) => b.href.length - a.href.length)[0];

  useEffect(() => {
    try {
      setCollapsed(window.localStorage.getItem(SIDEBAR_KEY) === "1");
    } catch {
      /* private mode */
    }
  }, []);

  useEffect(() => {
    setOpen(false);
    setMenuOpen(false);
  }, [pathname]);

  useEffect(() => {
    function onDoc(event: MouseEvent) {
      if (!menuRef.current?.contains(event.target as Node)) setMenuOpen(false);
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setMenuOpen(false);
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  function toggleCollapsed() {
    setCollapsed((value) => {
      const next = !value;
      try {
        window.localStorage.setItem(SIDEBAR_KEY, next ? "1" : "0");
      } catch {
        /* ignore */
      }
      return next;
    });
  }

  function handleSignOut() {
    signOut();
    router.push("/signin");
    router.refresh();
  }

  const nav = (iconOnly: boolean) => (
    <nav className="space-y-5" aria-label={`${surfaceLabel} navigation`}>
      {groupLinks(links).map((group, gi) => (
        <div key={group.name ?? gi}>
          {group.name && !iconOnly && (
            <p className="mb-1.5 px-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-muted/80">{group.name}</p>
          )}
          {group.name && iconOnly && <div className="mx-auto mb-2 h-px w-6 bg-border" aria-hidden="true" />}
          <ul className="space-y-0.5">
            {group.items.map((item) => {
              const active = current?.href === item.href;
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    title={iconOnly ? item.label : undefined}
                    aria-label={iconOnly ? item.label : undefined}
                    aria-current={active ? "page" : undefined}
                    className={`group relative flex items-center rounded-lg text-sm transition-colors ${
                      iconOnly ? "justify-center px-2 py-2.5" : "gap-2.5 px-3 py-2"
                    } ${
                      active ? "bg-white font-semibold text-ink shadow-soft ring-1 ring-border" : "text-muted hover:bg-white/70 hover:text-ink"
                    }`}
                  >
                    {active && !iconOnly && (
                      <span className="absolute -left-3 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-teal" aria-hidden="true" />
                    )}
                    <Icon name={item.icon ?? "chevron-right"} size={17} className={active ? "text-teal" : "text-muted/80 group-hover:text-ink"} />
                    {!iconOnly && <span className="truncate">{item.label}</span>}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );

  return (
    <div
      className={`min-h-screen bg-white text-ink lg:grid ${
        collapsed ? "lg:grid-cols-[4.25rem_minmax(0,1fr)]" : "lg:grid-cols-[16.5rem_minmax(0,1fr)]"
      }`}
    >
      {/* Sidebar (desktop) */}
      <aside className="sticky top-0 hidden h-screen flex-col border-r border-border bg-canvas lg:flex">
        <div className={`min-w-0 pb-4 pt-5 ${collapsed ? "px-2" : "px-5"}`}>
          {collapsed ? (
            <Link href={homeHref} className="mx-auto flex h-10 w-10 items-center justify-center" aria-label="Auralis home">
              <BrandGlyph size={28} />
            </Link>
          ) : (
            <BrandMark href={homeHref} compact />
          )}
          {!collapsed && (
            <>
              <p className="mt-4 text-[11px] font-semibold uppercase tracking-[0.14em] text-teal">{surfaceLabel}</p>
              {context && (
                <p className="mt-0.5 truncate text-xs text-muted" title={context}>
                  {context}
                </p>
              )}
            </>
          )}
        </div>
        <div className={`flex-1 overflow-y-auto pb-4 ${collapsed ? "px-1.5" : "px-3"}`}>{nav(collapsed)}</div>
        <div className={`border-t border-border ${collapsed ? "p-2" : "p-3"}`}>
          {!collapsed && (
            <Link href={accountHref} className="flex items-center gap-3 rounded-lg px-2 py-2 transition-colors hover:bg-white">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-navy text-xs font-semibold text-white">
                {identity.slice(0, 1).toUpperCase()}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium text-ink">{identity}</span>
                {role && <span className="block truncate text-xs text-muted">{role}</span>}
              </span>
            </Link>
          )}
          <button
            type="button"
            onClick={toggleCollapsed}
            className={`auralis-btn-ghost mt-1 w-full ${collapsed ? "justify-center px-0" : "justify-start px-2"}`}
            aria-pressed={collapsed}
            aria-label={collapsed ? "Expand navigation" : "Minimize navigation"}
            title={collapsed ? "Expand navigation" : "Minimize navigation"}
          >
            <Icon name={collapsed ? "chevron-right" : "chevron-left"} size={16} />
            {!collapsed && "Minimize"}
          </button>
          {!collapsed && (
            <button type="button" onClick={handleSignOut} className="auralis-btn-ghost mt-0.5 w-full justify-start px-2">
              <Icon name="logout" size={16} />
              Sign out
            </button>
          )}
          {collapsed && (
            <button type="button" onClick={handleSignOut} className="auralis-icon-btn mx-auto mt-1 h-10 w-10" aria-label="Sign out" title="Sign out">
              <Icon name="logout" size={16} />
            </button>
          )}
        </div>
      </aside>

      {/* Mobile drawer */}
      {open && (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label={`${surfaceLabel} navigation`}>
          <button type="button" className="absolute inset-0 bg-navy/30 backdrop-blur-[2px]" aria-label="Close navigation" onClick={() => setOpen(false)} />
          <div className="auralis-fade-up absolute inset-y-0 left-0 flex w-[min(17.5rem,calc(100vw-2.5rem))] max-w-full flex-col bg-canvas shadow-lift">
            <div className="flex items-center justify-between gap-2 px-4 py-4 sm:px-5">
              <div className="min-w-0">
                <BrandMark href={homeHref} compact />
              </div>
              <button type="button" className="auralis-icon-btn h-10 w-10 shrink-0" onClick={() => setOpen(false)} aria-label="Close navigation">
                <Icon name="close" size={16} />
              </button>
            </div>
            <p className="px-5 text-[11px] font-semibold uppercase tracking-[0.14em] text-teal">{surfaceLabel}</p>
            <div className="mt-4 flex-1 overflow-y-auto px-3 pb-4">{nav(false)}</div>
            <div className="space-y-2 border-t border-border p-3">
              {showInstallApp && <InstallAppControl />}
              <div className="flex items-center justify-between gap-2 px-1">
                <span className="text-xs font-medium text-muted">Language</span>
                <LanguageSelect />
              </div>
              <button type="button" onClick={handleSignOut} className="auralis-btn-secondary w-full">
                <Icon name="logout" size={16} />
                Sign out
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-col">
        <header className="sticky top-0 z-40 border-b border-border bg-white/95 backdrop-blur-md">
          <div className="flex h-14 items-center gap-2 px-3 sm:gap-3 sm:px-6 lg:px-8">
            <button type="button" className="auralis-icon-btn h-10 w-10 shrink-0 lg:hidden" aria-expanded={open} aria-label="Open navigation" onClick={() => setOpen(true)}>
              <Icon name="menu" size={18} />
            </button>
            <button
              type="button"
              className="auralis-icon-btn hidden h-10 w-10 shrink-0 lg:inline-flex"
              onClick={toggleCollapsed}
              aria-pressed={collapsed}
              aria-label={collapsed ? "Expand navigation" : "Minimize navigation"}
              title={collapsed ? "Expand navigation" : "Minimize navigation"}
            >
              <Icon name={collapsed ? "chevron-right" : "chevron-left"} size={16} />
            </button>
            <nav aria-label="Breadcrumb" className="flex min-w-0 flex-1 items-center gap-1.5 text-sm">
              <Link href={homeHref} className="hidden truncate text-muted hover:text-ink sm:inline">
                {surfaceLabel}
              </Link>
              {current && current.href !== homeHref && (
                <>
                  <Icon name="chevron-right" size={14} className="hidden shrink-0 text-muted/60 sm:block" />
                  <span className="truncate font-medium text-ink">{current.label}</span>
                </>
              )}
              {(!current || current.href === homeHref) && <span className="truncate font-medium text-ink sm:hidden">{surfaceLabel}</span>}
            </nav>
            <div className="ml-auto flex shrink-0 items-center gap-1.5 sm:gap-2">
              {showInstallApp && (
                <>
                  <span className="sm:hidden">
                    <InstallAppControl compact />
                  </span>
                  <span className="hidden sm:inline-flex">
                    <InstallAppControl />
                  </span>
                </>
              )}
              {topAccessory}
              <LanguageSelect />
              <div className="relative" ref={menuRef}>
                <button
                  type="button"
                  onClick={() => setMenuOpen((v) => !v)}
                  aria-expanded={menuOpen}
                  aria-haspopup="menu"
                  className="flex items-center gap-2 rounded-full border border-border bg-white py-1 pl-1 pr-2.5 text-sm transition-colors hover:border-[#C3CDD3]"
                >
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-navy text-[11px] font-semibold text-white">
                    {identity.slice(0, 1).toUpperCase()}
                  </span>
                  <span className="hidden max-w-[10rem] truncate font-medium text-ink sm:inline">{identity}</span>
                  <Icon name="chevron-down" size={14} className={`text-muted transition-transform ${menuOpen ? "rotate-180" : ""}`} />
                </button>
                {menuOpen && (
                  <div role="menu" className="auralis-fade-up absolute right-0 top-full z-50 mt-2 w-60 rounded-xl border border-border bg-white p-1.5 shadow-lift">
                    <div className="px-3 py-2">
                      <p className="truncate text-sm font-semibold text-ink">{identity}</p>
                      {role && <p className="truncate text-xs text-muted">{role}</p>}
                    </div>
                    <div className="my-1 h-px bg-border" />
                    <Link role="menuitem" href={accountHref} className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-ink hover:bg-muted-surface">
                      <Icon name="user" size={16} className="text-muted" />
                      {me ? "Profile and security" : "Account"}
                    </Link>
                    {showInstallApp && (
                      <button
                        role="menuitem"
                        type="button"
                        className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm text-ink hover:bg-muted-surface"
                        onClick={() => {
                          setMenuOpen(false);
                          document.querySelector<HTMLButtonElement>('[aria-label="Install Auralis app"]')?.click();
                        }}
                      >
                        <Icon name="download" size={16} className="text-muted" />
                        Install app
                      </button>
                    )}
                    <button role="menuitem" type="button" onClick={handleSignOut} className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm text-ink hover:bg-muted-surface">
                      <Icon name="logout" size={16} className="text-muted" />
                      Sign out
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </header>
        <main id="workspace-content" className="auralis-workspace min-w-0 flex-1 overflow-x-clip px-3 py-5 sm:px-6 sm:py-6 lg:px-8 lg:py-8">
          {children}
        </main>
        <AppUtilityFooter surface={surfaceLabel} />
      </div>
    </div>
  );
}
