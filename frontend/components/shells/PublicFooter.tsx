import Link from "next/link";
import { BrandMark } from "@/components/ui/BrandMark";

const COLUMNS = [
  {
    title: "Product",
    links: [
      { href: "/product", label: "Platform" },
      { href: "/aurie", label: "Aurie AI" },
      { href: "/model", label: "Model transparency" },
      { href: "/workflows", label: "Workflows" },
    ],
  },
  {
    title: "Solutions",
    links: [
      { href: "/solutions", label: "Solution map" },
      { href: "/for-hospitals", label: "For hospitals" },
      { href: "/how-auralis-works", label: "How Auralis works" },
      { href: "/technology-enablement", label: "Technology enablement" },
      { href: "/forward-deployed-engineering", label: "FDE" },
      { href: "/deployment-integration", label: "Deployment & integration" },
      { href: "/services", label: "Engagement models" },
    ],
  },
  {
    title: "Resources",
    links: [
      { href: "/resources", label: "Resource centre" },
      { href: "/docs", label: "Documentation" },
      { href: "/api-reference", label: "Integration API" },
      { href: "/evidence", label: "Evidence" },
    ],
  },
  {
    title: "Company",
    links: [
      { href: "/about", label: "About" },
      { href: "/security", label: "Security" },
      { href: "/contact", label: "Contact" },
      { href: "/business", label: "Commercial scope" },
    ],
  },
];

export function PublicFooter() {
  return (
    <footer className="mt-auto bg-[#0F1C24] text-[#C9D5D3]">
      <div className="auralis-container-public py-14">
        <div className="grid gap-10 lg:grid-cols-[1.1fr_2fr]">
          <div>
            <BrandMark tone="dark" />
            <p className="mt-5 max-w-sm text-sm leading-6 text-[#9AAEAB]">
              Hospital-local ICU early-warning software. Clinical data stays with the hospital. Clinical decisions remain with clinicians.
            </p>
            <div className="mt-6 flex gap-4 text-sm">
              <a href="https://www.linkedin.com" className="hover:text-white" rel="noreferrer" target="_blank">LinkedIn</a>
              <a href="mailto:contact@auralis.health" className="hover:text-white">Email</a>
            </div>
          </div>
          <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {COLUMNS.map((column) => (
              <div key={column.title}>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-white">{column.title}</p>
                <ul className="mt-4 space-y-2.5 text-sm">
                  {column.links.map((link) => (
                    <li key={link.href}><Link href={link.href} className="hover:text-white">{link.label}</Link></li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
        <div className="mt-12 flex flex-wrap items-center justify-between gap-4 border-t border-white/10 pt-6 text-xs text-[#8FA3A0]">
          <p>© {new Date().getFullYear()} Auralis. All rights reserved.</p>
          <div className="flex flex-wrap gap-5">
            <Link href="/security" className="hover:text-white">Security</Link>
            <Link href="/docs" className="hover:text-white">Privacy Policy</Link>
            <Link href="/docs" className="hover:text-white">Terms of Service</Link>
            <Link href="/contact" className="hover:text-white">Contact</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
