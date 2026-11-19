"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { BrandMark } from "@/components/ui/BrandMark";
import { Icon } from "@/components/ui/Icon";

type NavChild = { href: string; label: string; detail: string };
type NavItem = { href: string; label: string; children?: NavChild[] };

const NAV: NavItem[] = [
  {
    href: "/product",
    label: "Platform",
    children: [
      { href: "/product", label: "ICU clinical platform", detail: "Six-hour sepsis risk board and bedside chart" },
      { href: "/aurie", label: "Aurie assistant", detail: "Bounded clinical context and protocol help" },
      { href: "/model", label: "Model transparency", detail: "Frozen model card and TrustGate rules" },
      { href: "/workflows", label: "Clinical workflows", detail: "Alert SLA, ward NEWS2 and shift handoff" },
    ],
  },
  {
    href: "/for-hospitals",
    label: "For hospitals",
    children: [
      { href: "/for-hospitals", label: "Adoption journey", detail: "From assessment to supervised live care" },
      { href: "/forward-deployed-engineering", label: "Forward deployed engineering", detail: "On-site integration and commissioning" },
      { href: "/technology-enablement", label: "Technology enablement", detail: "Servers, networks and monitor readiness" },
      { href: "/site-readiness", label: "Site readiness", detail: "Hospital readiness checklist" },
      { href: "/clinical-evaluation-governance", label: "Silent evaluation", detail: "Shadow mode and sign-off gates" },
      { href: "/clinical-education", label: "Clinical education", detail: "Doctor, nurse and IT onboarding" },
    ],
  },
  {
    href: "/solutions",
    label: "Solutions",
    children: [
      { href: "/solutions", label: "Solutions overview", detail: "ICU, general wards and managed operations" },
      { href: "/deployment-integration", label: "HL7 and FHIR integration", detail: "Connectors, unit checks and quarantine" },
      { href: "/managed-technology-services", label: "Managed services", detail: "Ongoing support, backups and SLA" },
      { href: "/business", label: "Commercial approach", detail: "Institutional scoping and partnership" },
    ],
  },
  { href: "/security", label: "Security" },
  {
    href: "/resources",
    label: "Resources",
    children: [
      { href: "/resources", label: "Resource library", detail: "Specifications, guides and evaluation data" },
      { href: "/evidence", label: "Clinical evidence", detail: "Holdout validation and safety boundaries" },
      { href: "/api-reference", label: "API and FHIR docs", detail: "Technical schemas for hospital IT" },
      { href: "/docs", label: "Operations guide", detail: "Architecture and local deployment" },
    ],
  },
  { href: "/about", label: "About" },
  { href: "/contact", label: "Book" },
];

export function PublicHeader() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [menu, setMenu] = useState<string | null>(null);
  const [scrolled, setScrolled] = useState(false);
  const root = useRef<HTMLElement>(null);
  const scrolledRef = useRef(false);

  useEffect(() => {
    setOpen(false);
    setMenu(null);
  }, [pathname]);

  useEffect(() => {
    // Hysteresis + fixed bar height: no height/scale animation (that caused the scroll jerk).
    const onScroll = () => {
      const y = window.scrollY;
      const next = scrolledRef.current ? y > 8 : y > 28;
      if (next === scrolledRef.current) return;
      scrolledRef.current = next;
      setScrolled(next);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    function onDoc(event: MouseEvent) {
      if (!root.current?.contains(event.target as Node)) setMenu(null);
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setMenu(null);
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

  function active(item: NavItem) {
    if (pathname === item.href) return true;
    return Boolean(item.children?.some((child) => pathname === child.href || pathname.startsWith(`${child.href}/`)));
  }

  return (
    <header
      ref={root}
      className={`sticky top-0 z-50 h-14 border-b backdrop-blur-xl transition-[background-color,border-color,box-shadow] duration-200 ${
        scrolled
          ? "border-border/70 bg-white/92 shadow-[0_8px_28px_-22px_rgba(11,20,34,0.35)]"
          : "border-transparent bg-[#F3FAFB]/80 shadow-none"
      }`}
    >
      <div className="auralis-container-public flex h-full items-center justify-between gap-2 sm:gap-4">
        <div className="min-w-0 shrink">
          <BrandMark compact />
        </div>

        <nav className="hidden items-center gap-0.5 lg:flex" aria-label="Primary">
          {NAV.map((item) => {
            const isCurrent = active(item);
            const isOpen = menu === item.href;
            const base = `inline-flex h-9 items-center gap-1 rounded-lg px-2.5 text-[13px] font-medium transition-colors sm:px-3 sm:text-[14px] ${
              isCurrent || isOpen ? "text-ink" : "text-muted hover:text-ink"
            } ${isOpen ? "bg-muted-surface" : "hover:bg-muted-surface/70"}`;
            return (
              <div
                key={item.href}
                className="relative"
                onMouseEnter={() => item.children && setMenu(item.href)}
                onMouseLeave={() => item.children && setMenu((cur) => (cur === item.href ? null : cur))}
              >
                {item.children ? (
                  <button
                    type="button"
                    className={base}
                    aria-expanded={isOpen}
                    aria-haspopup="true"
                    onClick={() => setMenu((cur) => (cur === item.href ? null : item.href))}
                  >
                    {item.label}
                    <Icon
                      name="chevron-down"
                      size={14}
                      className={`text-muted transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
                    />
                  </button>
                ) : (
                  <Link href={item.href} className={base} aria-current={isCurrent ? "page" : undefined}>
                    {item.label}
                  </Link>
                )}
                {isCurrent && (
                  <span className="absolute inset-x-3 -bottom-[11px] h-0.5 rounded-full bg-navy" aria-hidden="true" />
                )}

                {item.children && isOpen && (
                  <div className="absolute left-0 top-full z-50 pt-2">
                    <div
                      className={`auralis-fade-up rounded-xl border border-border bg-white p-2 shadow-lift ${
                        item.children.length > 4 ? "grid w-[36rem] grid-cols-2 gap-0.5" : "w-[22rem] space-y-0.5"
                      }`}
                    >
                      {item.children.map((child) => (
                        <Link
                          key={child.href}
                          href={child.href}
                          className="group flex items-start justify-between gap-3 rounded-lg px-3 py-2.5 transition-colors hover:bg-muted-surface"
                          onClick={() => setMenu(null)}
                        >
                          <span>
                            <span className="block text-sm font-medium text-ink">{child.label}</span>
                            <span className="mt-0.5 block text-xs leading-snug text-muted">{child.detail}</span>
                          </span>
                          <Icon
                            name="chevron-right"
                            size={14}
                            className="mt-1 text-muted opacity-0 transition-all group-hover:translate-x-0.5 group-hover:opacity-100"
                          />
                        </Link>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </nav>

        <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
          <Link href="/signin" className="auralis-btn-ghost hidden h-9 text-ink sm:inline-flex">
            Sign in
          </Link>
          <Link href="/contact" className="auralis-btn-primary h-9 min-h-0 px-3 sm:px-4">
            <span className="sm:hidden">Book</span>
            <span className="hidden sm:inline">Book a consultation</span>
          </Link>
          <button
            type="button"
            className="auralis-icon-btn h-9 w-9 lg:hidden"
            aria-expanded={open}
            aria-controls="mobile-nav"
            aria-label={open ? "Close navigation" : "Open navigation"}
            onClick={() => setOpen((v) => !v)}
          >
            <Icon name={open ? "close" : "menu"} size={18} />
          </button>
        </div>
      </div>

      {open && (
        <div id="mobile-nav" className="max-h-[calc(100vh-3.5rem)] overflow-y-auto border-t border-border bg-white lg:hidden">
          <div className="auralis-container-public space-y-1 py-4">
            {NAV.map((item) =>
              item.children ? (
                <details key={item.href} className="group border-b border-border/70 py-1" open={active(item)}>
                  <summary className="flex cursor-pointer list-none items-center justify-between py-2.5 text-[15px] font-medium text-ink [&::-webkit-details-marker]:hidden">
                    {item.label}
                    <Icon name="chevron-down" size={16} className="text-muted transition-transform group-open:rotate-180" />
                  </summary>
                  <div className="grid gap-0.5 pb-2 sm:grid-cols-2">
                    {item.children.map((child) => (
                      <Link
                        key={child.href}
                        href={child.href}
                        className="rounded-lg px-3 py-2 text-sm text-muted hover:bg-muted-surface hover:text-ink"
                      >
                        {child.label}
                      </Link>
                    ))}
                  </div>
                </details>
              ) : (
                <Link
                  key={item.href}
                  href={item.href}
                  className="flex items-center justify-between border-b border-border/70 py-3.5 text-[15px] font-medium text-ink"
                >
                  {item.label}
                  <Icon name="chevron-right" size={16} className="text-muted" />
                </Link>
              ),
            )}
            <div className="grid gap-2 pt-3 sm:grid-cols-2">
              <Link href="/signin" className="auralis-btn-secondary">
                Sign in
              </Link>
              <Link href="/contact" className="auralis-btn-primary">
                Book a consultation
              </Link>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
