/** Subtle mark that the product is powered by a trained clinical ML model. */
export function ModelMark({
  className = "",
  label = "Holdout-proven sepsis ML",
}: {
  className?: string;
  label?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.12em] text-teal-dark ${className}`.trim()}
      title={label}
    >
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true" className="shrink-0">
        <circle cx="4" cy="5" r="1.6" fill="#0E7490" />
        <circle cx="14" cy="4" r="1.6" fill="#0E7490" />
        <circle cx="9" cy="9" r="2" fill="#0B4F5C" />
        <circle cx="4" cy="14" r="1.6" fill="#0E7490" />
        <circle cx="14" cy="13" r="1.6" fill="#0E7490" />
        <path d="M5.4 5.7 7.6 8.1M12.6 5.1 10.4 7.8M5.5 12.8 7.5 10.4M12.5 12.1 10.5 10.5" stroke="#73C3CF" strokeWidth="1.2" strokeLinecap="round" />
      </svg>
      <span>{label}</span>
    </span>
  );
}
