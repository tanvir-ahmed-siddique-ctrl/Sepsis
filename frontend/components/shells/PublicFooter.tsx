import Link from "next/link";
import { BrandMark } from "@/components/ui/BrandMark";
import { Icon } from "@/components/ui/Icon";

const COLUMNS = [
  {
    title: "Platform",
    links: [
      { href: "/product", label: "ICU clinical platform" },
      { href: "/aurie", label: "Aurie assistant" },
      { href: "/model", label: "Model transparency" },
      { href: "/workflows", label: "Clinical workflows" },
      { href: "/signin", label: "Sign in" },
    ],
  },
  {
    title: "Hospitals",
    links: [
      { href: "/for-hospitals", label: "Adoption journey" },
      { href: "/forward-deployed-engineering", label: "Forward deployed engineering" },
      { href: "/technology-enablement", label: "Technology enablement" },
      { href: "/deployment-integration", label: "HL7 and FHIR integration" },
      { href: "/services", label: "Engagement models" },
    ],
  },
  {
    title: "Resources",
    links: [
      { href: "/resources", label: "Resource library" },
      { href: "/evidence", label: "Clinical evidence" },
      { href: "/api-reference", label: "API and FHIR reference" },
      { href: "/docs", label: "Operations docs" },
    ],
  },
  {
    title: "Company",
    links: [
      { href: "/about", label: "About Auralis" },
      { href: "/security", label: "Security and privacy" },
      { href: "/business", label: "Commercial approach" },
      { href: "/contact", label: "Contact" },
    ],
  },
];

export function PublicFooter({ showHomeWordmark = false }: { showHomeWordmark?: boolean } = {}) {
  return (
    <footer className="mt-auto bg-navy text-white/70">
      <div className="auralis-container-public pb-10 pt-16">
        <div className="grid gap-12 lg:grid-cols-[1.1fr_2fr]">
          <div className="min-w-0">
            <BrandMark tone="dark" />
            <p className="mt-5 max-w-sm text-sm leading-6">
              Hospital-local ICU early-warning software with forward deployed engineering. Clinical data stays inside your hospital; clinical decisions stay with your clinicians.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link href="/signin" className="group inline-flex h-10 items-center gap-2 rounded-lg bg-white px-4 text-sm font-semibold text-navy transition-colors hover:bg-[#E8EDF0]">
                Open live ICU board
                <Icon name="arrow-right" size={16} className="transition-transform group-hover:translate-x-0.5" />
              </Link>
              <Link href="/contact" className="inline-flex h-10 items-center rounded-lg border border-white/15 px-4 text-sm font-semibold text-white transition-colors hover:border-white/30 hover:bg-white/5">
                Book a consultation
              </Link>
            </div>
          </div>

          <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {COLUMNS.map((column) => (
              <div key={column.title}>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#73C3CF]">{column.title}</p>
                <ul className="mt-4 space-y-2.5 text-sm">
                  {column.links.map((link) => (
                    <li key={link.href}>
                      <Link href={link.href} className="transition-colors hover:text-white">
                        {link.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-14 flex flex-wrap items-center justify-between gap-4 border-t border-white/10 pt-6 text-xs text-white/50">
          <p>© {new Date().getFullYear()} Auralis Health. Assistive decision-support software, not an autonomous medical device.</p>
          <div className="flex flex-wrap gap-5">
            <Link href="/security" className="hover:text-white">Security</Link>
            <Link href="/evidence" className="hover:text-white">Evidence boundary</Link>
            <Link href="/docs" className="hover:text-white">Privacy and terms</Link>
            <Link href="/contact" className="hover:text-white">Contact</Link>
          </div>
        </div>
      </div>

      {showHomeWordmark ? (
        <div
          className="relative overflow-hidden border-t border-white/10"
          aria-hidden="true"
        >
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(115,195,207,0.18),transparent_60%)]" />
          <div className="pointer-events-none absolute inset-0 opacity-[0.35] [background-image:radial-gradient(rgba(255,255,255,0.12)_1px,transparent_1px)] [background-size:22px_22px]" />
          <div className="relative mx-auto flex w-full max-w-[100rem] items-center justify-center px-4 py-10 sm:px-8 sm:py-14 lg:py-16">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/wordmark-footer.png"
              alt=""
              className="h-auto w-full max-w-5xl object-contain opacity-95"
            />
          </div>
        </div>
      ) : null}
    </footer>
  );
}
