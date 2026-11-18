import Link from "next/link";
import { BrandMark } from "@/components/ui/BrandMark";

const COLUMNS = [
  {
    title: "Platform",
    links: [
      { href: "/product", label: "ICU Clinical Platform" },
      { href: "/aurie", label: "Aurie AI" },
      { href: "/model", label: "Model Transparency" },
      { href: "/workflows", label: "Clinical Workflows" },
      { href: "/signin", label: "Open Live Demo" },
    ],
  },
  {
    title: "Hospitals",
    links: [
      { href: "/for-hospitals", label: "Adoption Journey" },
      { href: "/forward-deployed-engineering", label: "Forward Deployed Eng." },
      { href: "/technology-enablement", label: "Technology Enablement" },
      { href: "/deployment-integration", label: "HL7 & FHIR Integration" },
      { href: "/services", label: "Engagement Models" },
    ],
  },
  {
    title: "Resources",
    links: [
      { href: "/resources", label: "Resource Library" },
      { href: "/evidence", label: "Clinical Evidence" },
      { href: "/api-reference", label: "API & FHIR Reference" },
      { href: "/docs", label: "Operations Docs" },
    ],
  },
  {
    title: "Company",
    links: [
      { href: "/about", label: "About Auralis" },
      { href: "/security", label: "Security & Privacy" },
      { href: "/business", label: "Commercial Approach" },
      { href: "/contact", label: "Contact" },
    ],
  },
];

export function PublicFooter() {
  return (
    <footer className="mt-auto border-t border-border bg-[#F8FAFA] text-ink">
      <div className="auralis-container-public py-16">
        <div className="grid gap-12 lg:grid-cols-[1.15fr_2fr]">
          <div>
            <BrandMark />
            <p className="mt-4 max-w-sm text-sm leading-6 text-muted">
              Hospital-local ICU early-warning software & Forward Deployed Engineering. Clinical data stays inside your hospital; clinical decisions stay with your doctors.
            </p>
            <div className="mt-6 flex items-center gap-4 text-sm font-medium text-teal">
              <Link href="/signin" className="hover:underline">
                Launch Live Workspace →
              </Link>
              <span className="text-border">|</span>
              <Link href="/contact" className="hover:underline">
                Request Consultation
              </Link>
            </div>
          </div>

          <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {COLUMNS.map((column) => (
              <div key={column.title}>
                <p className="text-xs font-semibold uppercase tracking-wider text-ink">{column.title}</p>
                <ul className="mt-4 space-y-2.5 text-sm text-muted">
                  {column.links.map((link) => (
                    <li key={link.href}>
                      <Link href={link.href} className="transition-colors hover:text-teal">
                        {link.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-12 flex flex-wrap items-center justify-between gap-4 border-t border-border pt-6 text-xs text-muted">
          <p>© {new Date().getFullYear()} Auralis Health. Assistive decision-support software — not an autonomous medical device.</p>
          <div className="flex flex-wrap gap-5">
            <Link href="/security" className="hover:text-ink">Security</Link>
            <Link href="/evidence" className="hover:text-ink">Evidence Boundary</Link>
            <Link href="/docs" className="hover:text-ink">Privacy & Terms</Link>
            <Link href="/contact" className="hover:text-ink">Contact</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
