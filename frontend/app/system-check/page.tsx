import Link from "next/link";
import type { Metadata } from "next";
import { Icon } from "@/components/ui/Icon";

export const metadata: Metadata = {
  title: "Judge System Check | Auralis",
  description: "Availability of the isolated synthetic evaluation environment.",
  robots: { index: false, follow: false },
};

export default function SystemCheckPage() {
  const configuredEntry = process.env.EVALUATION_SYSTEM_CHECK_URL;
  const safeEntry = (() => {
    if (!configuredEntry) return null;
    try {
      const url = new URL(configuredEntry);
      if (url.protocol !== "https:" && !(url.protocol === "http:" && ["localhost", "127.0.0.1"].includes(url.hostname))) return null;
      if (url.username || url.password) return null;
      return url.toString();
    } catch {
      return null;
    }
  })();
  return (
    <div className="mx-auto max-w-3xl space-y-8 py-12">
      <header className="border-b border-[#D6DCD8] pb-7">
        <p className="text-xs font-semibold uppercase tracking-[.18em] text-forest">Judge System Check</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight">Synthetic evaluation environment</h1>
        <p className="mt-4 text-sm leading-7 text-slate">This entry must use an isolated evaluation deployment with synthetic records and simulated side effects.</p>
      </header>
      {safeEntry ? (
        <section className="border-l-2 border-forest bg-warm p-6">
          <p className="font-semibold">Evaluation deployment configured</p>
          <p className="mt-2 text-sm leading-6 text-slate">Continue to the separately configured evaluation environment. It does not use this site&apos;s session.</p>
          <a href={safeEntry} rel="noopener noreferrer" className="auralis-btn-primary mt-5">Open isolated system check<Icon name="external" size={15} /></a>
        </section>
      ) : (
        <section className="border-l-2 border-risk-watch bg-warm p-6">
          <p className="font-semibold">Isolated environment is not configured</p>
          <p className="mt-2 text-sm leading-6 text-muted">This deployment still uses the clinical service runtime. No role-switch token will be issued here. Configure a separate synthetic evaluation runtime and set EVALUATION_SYSTEM_CHECK_URL before enabling evaluation access.</p>
        </section>
      )}
      <section className="space-y-3 border border-[#D6DCD8] bg-white p-6">
        <p className="font-semibold">Product tour (this deployment)</p>
        <p className="text-sm leading-6 text-muted">
          Walk the full Auralis stack on this site — evidence, ICU board, charting, and deployment. De-identified
          PhysioNet replay only; no hospital patient data.
        </p>
        <div className="flex flex-wrap gap-3 pt-1">
          <Link href="/judge" className="auralis-btn-primary">
            Open product tour
            <Icon name="arrow-right" size={15} />
          </Link>
          <Link href="/presentation" className="auralis-btn-secondary">
            Presentation
          </Link>
        </div>
      </section>
      <Link href="/signin" className="text-sm font-semibold text-forest underline underline-offset-2">Return to sign-in</Link>
    </div>
  );
}
