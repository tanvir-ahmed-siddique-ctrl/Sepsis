"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { BrandMark } from "@/components/ui/BrandMark";

type NavChild = { href: string; label: string; detail: string };
type NavItem = { href: string; label: string; children?: NavChild[] };

const NAV: NavItem[] = [
  {
    href: "/product",
    label: "Platform",
    children: [
      { href: "/product", label: "ICU Clinical Platform", detail: "6-hour sepsis risk board & bedside chart" },
      { href: "/aurie", label: "Aurie AI", detail: "Bounded clinical context & protocol assistant" },
      { href: "/model", label: "Model Transparency", detail: "Frozen Run-4 model & TrustGate rules" },
      { href: "/workflows", label: "Clinical Workflows", detail: "Alert SLA, ward NEWS2 & shift handoff" },
    ],
  },
  {
    href: "/for-hospitals",
    label: "For Hospitals",
    children: [
      { href: "/for-hospitals", label: "Adoption Journey", detail: "12-step path from assessment to live care" },
      { href: "/forward-deployed-engineering", label: "Forward Deployed Engineering", detail: "On-site integration & commissioning" },
      { href: "/technology-enablement", label: "Technology Enablement", detail: "Servers, networks & monitor readiness" },
      { href: "/site-readiness", label: "Site Readiness", detail: "16-point hospital readiness checklist" },
      { href: "/clinical-evaluation-governance", label: "Silent Evaluation", detail: "Shadow mode & hospital sign-off gates" },
      { href: "/clinical-education", label: "Clinical Education", detail: "Doctor, nurse & IT onboarding" },
    ],
  },
  {
    href: "/solutions",
    label: "Solutions",
    children: [
      { href: "/solutions", label: "Solutions Overview", detail: "ICU, general wards & managed operations" },
      { href: "/deployment-integration", label: "HL7 & FHIR Integration", detail: "Connectors, unit checks & quarantine" },
      { href: "/managed-technology-services", label: "Managed Services", detail: "Ongoing support, backups & SLA" },
      { href: "/business", label: "Commercial Approach", detail: "Institutional scoping & partnership" },
    ],
  },
  { href: "/security", label: "Security" },
  {
    href: "/resources",
    label: "Resources",
    children: [
      { href: "/resources", label: "Resource Library", detail: "Specs, guides & evaluation data" },
      { href: "/evidence", label: "Clinical Evidence", detail: "Holdout validation & safety boundaries" },
      { href: "/api-reference", label: "API & FHIR Docs", detail: "Technical schemas for hospital IT" },
      { href: "/docs", label: "Operations Guide", detail: "Architecture & local deployment" },
    ],
  },
  { href: "/about", label: "About" },
];

export function PublicHeader() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [menu, setMenu] = useState<string | null>(null);
  const [scrolled, setScrolled] = useState(false);
  const root = useRef<HTMLElement>(null);

  useEffect(() => {
    setOpen(false);
    setMenu(null);
  }, [pathname]);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 18);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    function onDoc(event: MouseEvent) {
      if (!root.current?.contains(event.target as Node)) setMenu(null);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  function active(href: string) {
    return pathname === href || (href !== "/" && pathname.startsWith(href));
  }

  return (
    <header
      ref={root}
      className={`sticky top-0 z-50 transition-all duration-300 ${
        scrolled ? "py-2.5" : "border-b border-border/70 bg-white/90 py-4 backdrop-blur-md"
      }`}
    >
      <div className="auralis-container-public">
        <div
          className={`flex items-center justify-between gap-4 transition-all duration-300 ${
            scrolled
              ? "rounded-full border border-border/90 bg-white/92 px-5 py-2.5 shadow-[0_10px_30px_-12px_rgba(15,31,38,0.12)] backdrop-blur-xl"
              : ""
          }`}
        >
          <BrandMark />

          <nav className="hidden items-center gap-1 lg:flex" aria-label="Primary">
            {NAV.map((item) => {
              const isCurrent = active(item.href);
              const isOpen = menu === item.href;
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
                      className={`inline-flex items-center gap-1.5 rounded-full px-3.5 py-2 text-sm font-medium transition-colors ${
                        isCurrent || isOpen
                          ? "bg-muted-surface text-ink"
                          : "text-muted hover:bg-muted-surface/70 hover:text-ink"
                      }`}
                      aria-expanded={isOpen}
                      onClick={() => setMenu((cur) => (cur === item.href ? null : item.href))}
                    >
                      <span>{item.label}</span>
                      <svg
                        viewBox="0 0 12 12"
                        className={`h-3 w-3 text-muted transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.75"
                      >
                        <path d="M2.5 4.5L6 8l3.5-3.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </button>
                  ) : (
                    <Link
                      href={item.href}
                      className={`inline-flex items-center rounded-full px-3.5 py-2 text-sm font-medium transition-colors ${
                        isCurrent
                          ? "bg-muted-surface text-ink"
                          : "text-muted hover:bg-muted-surface/70 hover:text-ink"
                      }`}
                    >
                      {item.label}
                    </Link>
                  )}

                  {item.children && isOpen && (
                    <div className="absolute left-0 top-full z-50 pt-2">
                      <div
                        className={`rounded-2xl border border-border bg-white p-2.5 shadow-[0_20px_50px_-15px_rgba(15,31,38,0.16)] ${
                          item.children.length > 4 ? "grid w-[34rem] grid-cols-2 gap-1" : "w-[21rem] space-y-0.5"
                        }`}
                      >
                        {item.children.map((child) => (
                          <Link
                            key={child.href}
                            href={child.href}
                            className="group block rounded-xl px-3.5 py-2.5 transition-colors hover:bg-muted-surface"
                            onClick={() => setMenu(null)}
                          >
                            <span className="block text-sm font-semibold text-ink group-hover:text-teal">
                              {child.label}
                            </span>
                            <span className="mt-0.5 block text-xs leading-snug text-muted">{child.detail}</span>
                          </Link>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </nav>

          <div className="flex items-center gap-2">
            <Link
              href="/signin"
              className="hidden rounded-full border border-border bg-white px-4 py-2 text-sm font-semibold text-ink transition-colors hover:border-teal hover:text-teal sm:inline-flex"
            >
              Live Demo / Sign In
            </Link>
            <Link
              href="/contact"
              className="inline-flex items-center rounded-full bg-teal px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all hover:bg-teal-dark"
            >
              Book Consultation
            </Link>
            <button
              type="button"
              className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-border bg-white text-ink lg:hidden"
              aria-expanded={open}
              aria-label="Toggle navigation"
              onClick={() => setOpen((v) => !v)}
            >
              <svg viewBox="0 0 20 20" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8">
                {open ? (
                  <path d="M5 5l10 10M15 5L5 15" strokeLinecap="round" />
                ) : (
                  <path d="M3 6h14M3 10h14M3 14h14" strokeLinecap="round" />
                )}
              </svg>
            </button>
          </div>
        </div>
      </div>

      {open && (
        <div className="mt-2 border-t border-border bg-white shadow-lg lg:hidden">
          <div className="auralis-container-public space-y-3 py-5">
            {NAV.map((item) => (
              <div key={item.href} className="border-b border-border/60 pb-3">
                <Link href={item.href} className="block text-sm font-semibold text-ink" onClick={() => setOpen(false)}>
                  {item.label}
                </Link>
                {item.children && (
                  <div className="mt-2 grid gap-1.5 pl-3 sm:grid-cols-2">
                    {item.children.map((child) => (
                      <Link
                        key={child.href}
                        href={child.href}
                        className="block py-1 text-xs text-muted hover:text-teal"
                        onClick={() => setOpen(false)}
                      >
                        {child.label}
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ))}
            <div className="flex flex-wrap gap-2.5 pt-1">
              <Link href="/signin" className="auralis-btn-secondary" onClick={() => setOpen(false)}>
                Live Demo / Sign In
              </Link>
              <Link href="/contact" className="auralis-btn-primary" onClick={() => setOpen(false)}>
                Book Consultation
              </Link>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
