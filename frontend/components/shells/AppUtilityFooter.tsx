import Link from "next/link";

export function AppUtilityFooter({ surface }: { surface: string }) {
  return (
    <footer className="mt-auto border-t border-border bg-white">
      <div className="auralis-container flex flex-wrap items-center justify-between gap-3 py-3 text-xs text-muted">
        <p>Auralis · {surface} · Clinical decisions remain with the care team</p>
        <div className="flex gap-4">
          <Link href="/docs" className="hover:text-ink">Docs</Link>
          <Link href="/contact" className="hover:text-ink">Support</Link>
          <Link href="/security" className="hover:text-ink">Security</Link>
        </div>
      </div>
    </footer>
  );
}
