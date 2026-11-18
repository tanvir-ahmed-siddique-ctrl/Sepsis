"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { BrandMark } from "@/components/ui/BrandMark";

type NavItem = { href: string; label: string; children?: Array<{ href: string; label: string; detail: string }> };

const NAV: NavItem[] = [
  {
    href: "/product",
    label: "Product",
    children: [
      { href: "/product", label: "Platform overview", detail: "Hospital-local ICU risk review workflow" },
      { href: "/model", label: "Model transparency", detail: "Frozen model scope and limitations" },
      { href: "/workflows", label: "Clinical workflows", detail: "Bedside review and handoff path" },
    ],
  },
  {
    href: "/aurie",
    label: "Aurie AI",
    children: [
      { href: "/aurie", label: "Aurie overview", detail: "Assistive clinical context, not autonomous care" },
      { href: "/evidence", label: "Evidence boundary", detail: "What is measured and what is not claimed" },
    ],
  },
  {
    href: "/solutions",
    label: "Solutions",
    children: [
      { href: "/solutions", label: "Solution map", detail: "ICU, ward surveillance and governance" },
      { href: "/services", label: "Engagement models", detail: "Assessment, silent pilot and support" },
      { href: "/technology-enablement", label: "Technology enablement", detail: "Infrastructure and equipment coordination" },
      { href: "/business", label: "Commercial approach", detail: "Licence bands without published prices" },
    ],
  },
  {
    href: "/for-hospitals",
    label: "For Hospitals",
    children: [
      { href: "/for-hospitals", label: "Hospital journey", detail: "Consultation through governed commissioning" },
      { href: "/how-auralis-works", label: "How Auralis works", detail: "Local software and measured rollout" },
      { href: "/forward-deployed-engineering", label: "Forward Deployed Engineering", detail: "Site engineers and delivery workspace" },
      { href: "/site-readiness", label: "Site readiness", detail: "Evidence-backed checklist states" },
      { href: "/clinical-evaluation-governance", label: "Evaluation & governance", detail: "Silent evaluation and sign-off gates" },
      { href: "/managed-technology-services", label: "Managed services", detail: "Contracted support scope" },
      { href: "/clinical-education", label: "Education & training", detail: "Evidence-based capability building" },
    ],
  },
  { href: "/deployment-integration", label: "Deployment & Integration" },
  { href: "/security", label: "Security" },
  {
    href: "/resources",
    label: "Resources",
    children: [
      { href: "/resources", label: "Resource centre", detail: "Guides and technical references" },
      { href: "/docs", label: "Documentation", detail: "Operations and architecture notes" },
      { href: "/api-reference", label: "Integration API", detail: "Connector and FHIR reference" },
      { href: "/evidence", label: "Evidence", detail: "Retrospective evaluation summary" },
    ],
  },
  { href: "/about", label: "About" },
  { href: "/contact", label: "Contact" },
];

export function PublicHeader() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [menu, setMenu] = useState<string | null>(null);
  const root = useRef<HTMLElement>(null);

  useEffect(() => {
    setOpen(false);
    setMenu(null);
  }, [pathname]);

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
    <header ref={root} className="sticky top-0 z-50 border-b border-border bg-white/95 backdrop-blur">
      <div className="auralis-container-public flex items-center gap-4 py-3.5">
        <BrandMark />
        <nav className="ml-auto hidden items-center gap-1 xl:flex" aria-label="Public">
          {NAV.map((item) => (
            <div key={item.href} className="relative">
              {item.children ? (
                <button
                  type="button"
                  className={`px-2.5 py-2 text-sm ${active(item.href) ? "font-semibold text-teal" : "text-muted hover:text-ink"}`}
                  aria-expanded={menu === item.href}
                  onClick={() => setMenu((current) => (current === item.href ? null : item.href))}
                >
                  {item.label}
                </button>
              ) : (
                <Link href={item.href} className={`px-2.5 py-2 text-sm ${active(item.href) ? "font-semibold text-teal" : "text-muted hover:text-ink"}`}>
                  {item.label}
                </Link>
              )}
              {item.children && menu === item.href && (
                <div className="absolute left-0 top-full z-50 mt-2 w-[22rem] border border-border bg-white p-2 shadow-soft">
                  {item.children.map((child) => (
                    <Link key={child.href} href={child.href} className="block px-3 py-2.5 hover:bg-muted-surface" onClick={() => setMenu(null)}>
                      <span className="block text-sm font-semibold text-ink">{child.label}</span>
                      <span className="mt-0.5 block text-xs text-muted">{child.detail}</span>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-2 xl:ml-4">
          <Link href="/signin" className="auralis-btn-ghost hidden sm:inline-flex">Sign In</Link>
          <Link href="/contact" className="auralis-btn-primary">Request a Consultation</Link>
          <button type="button" className="auralis-btn-secondary xl:hidden" aria-expanded={open} aria-label="Open menu" onClick={() => setOpen((value) => !value)}>
            Menu
          </button>
        </div>
      </div>
      {open && (
        <div className="border-t border-border bg-white xl:hidden">
          <div className="auralis-container-public grid gap-1 py-4">
            {NAV.map((item) => (
              <div key={item.href} className="border-b border-border/70 py-2">
                <Link href={item.href} className="block py-1 text-sm font-semibold text-ink" onClick={() => setOpen(false)}>{item.label}</Link>
                {item.children?.map((child) => (
                  <Link key={child.href} href={child.href} className="block py-1 pl-3 text-sm text-muted" onClick={() => setOpen(false)}>{child.label}</Link>
                ))}
              </div>
            ))}
            <Link href="/signin" className="auralis-btn-secondary mt-2 justify-self-start" onClick={() => setOpen(false)}>Sign In</Link>
          </div>
        </div>
      )}
    </header>
  );
}
