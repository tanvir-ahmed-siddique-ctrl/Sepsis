import Link from "next/link";
import type { Metadata } from "next";

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
          <a href={safeEntry} rel="noopener noreferrer" className="mt-5 inline-flex bg-forest px-5 py-3 text-sm font-semibold text-white">Open isolated System Check ↗</a>
        </section>
      ) : (
        <section className="border-l-2 border-risk-watch bg-warm p-6">
          <p className="font-semibold">Isolated environment is not configured</p>
          <p className="mt-2 text-sm leading-6 text-muted">This deployment still uses the clinical service runtime. No role-switch token will be issued here. Configure a separate synthetic evaluation runtime and set EVALUATION_SYSTEM_CHECK_URL before enabling evaluation access.</p>
        </section>
      )}
      <Link href="/signin" className="text-sm font-semibold text-forest underline underline-offset-2">Return to sign-in</Link>
    </div>
  );
}
