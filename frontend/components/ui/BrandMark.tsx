import Link from "next/link";

export function BrandMark({ href = "/", tone = "light", compact = false }: { href?: string; tone?: "light" | "dark"; compact?: boolean }) {
  const word = tone === "dark" ? "text-white" : "text-ink";
  const mark = tone === "dark" ? "bg-teal text-white" : "bg-teal text-white";
  return (
    <Link href={href} className={`inline-flex items-center gap-2.5 ${word}`}>
      <span className={`inline-flex h-8 w-8 items-center justify-center font-display text-sm font-bold ${mark}`} aria-hidden="true">
        A
      </span>
      <span className={`font-display font-semibold tracking-tight ${compact ? "text-base" : "text-lg"}`}>Auralis</span>
    </Link>
  );
}
