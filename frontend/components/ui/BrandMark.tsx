import Link from "next/link";

/** Orbit emblem used as the compact brand glyph. */
export function BrandGlyph({
  size = 30,
  className = "",
  title,
}: {
  size?: number;
  className?: string;
  title?: string;
}) {
  return (
    // eslint-disable-next-line @next/next/no-img-element -- local brand asset; avoid next/image hydration quirks in shells
    <img
      src="/app-icon.png"
      alt={title ?? ""}
      width={size}
      height={size}
      className={`rounded-lg object-cover ${className}`.trim()}
      style={{ width: size, height: size }}
      decoding="async"
      aria-hidden={title ? undefined : true}
    />
  );
}

/** Teal Wave wordmark — light surfaces use navy letters; dark surfaces use white letters. */
export function BrandWordmark({
  tone = "light",
  height = 22,
  className = "",
}: {
  tone?: "light" | "dark";
  height?: number;
  className?: string;
}) {
  const src = tone === "dark" ? "/wordmark-on-dark-180.png" : "/wordmark-on-light-180.png";
  // Intrinsic 180-wide crop; keep aspect ~4.85:1 from trimmed assets.
  const width = Math.round(height * 4.85);
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt="Auralis"
      width={width}
      height={height}
      className={`h-auto w-auto max-w-full object-contain object-left ${className}`.trim()}
      style={{ height, maxHeight: height }}
      decoding="async"
    />
  );
}

export function BrandMark({
  href = "/",
  tone = "light",
  compact = false,
}: {
  href?: string;
  tone?: "light" | "dark";
  compact?: boolean;
}) {
  const glyph = compact ? 28 : 32;
  const wordHeight = compact ? 18 : 22;
  return (
    <Link
      href={href}
      className="inline-flex min-w-0 max-w-full items-center gap-2 sm:gap-2.5"
      aria-label="Auralis home"
    >
      <BrandGlyph size={glyph} className="shrink-0" />
      <BrandWordmark
        tone={tone}
        height={wordHeight}
        className={
          compact
            ? "max-w-[7.5rem] sm:max-w-[9rem]"
            : "max-w-[7rem] sm:max-w-[10.5rem] lg:max-w-none"
        }
      />
    </Link>
  );
}
