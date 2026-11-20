import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "PropEval — Hinglish Voice AI Evaluation Workbench",
  description: "Prompt regression and statistical evaluation workbench for Indian real-estate voice AI agents.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-canvas text-ink-primary flex flex-col antialiased">
        {/* Anti-Slop Top Navigation */}
        <header className="h-12 border-b border-border bg-surface px-6 flex items-center justify-between sticky top-0 z-50">
          <div className="flex items-center gap-6">
            <Link href="/" className="flex items-center gap-2 group">
              <span className="font-mono font-bold text-sm tracking-wider uppercase text-ink-primary">
                PropEval
              </span>
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-gray-100 text-ink-secondary border border-border">
                v0.1.0
              </span>
            </Link>

            <nav className="flex items-center gap-4 text-xs font-medium text-ink-secondary">
              <Link
                href="/"
                className="hover:text-ink-primary transition-colors py-1 px-2 rounded hover:bg-gray-50"
              >
                Workbench
              </Link>
              <Link
                href="/registry"
                className="hover:text-ink-primary transition-colors py-1 px-2 rounded hover:bg-gray-50"
              >
                Prompt & RERA Registry
              </Link>
            </nav>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-xs font-mono text-ink-secondary">
              <span className="inline-block w-2 h-2 rounded-full bg-accent-emerald animate-pulse" />
              <span>Postgres 17 (port 5433)</span>
              <span className="text-gray-300">|</span>
              <span className="text-accent-emerald font-semibold">$0.00 Local Spend</span>
            </div>
          </div>
        </header>

        <main className="flex-1 flex flex-col">{children}</main>
      </body>
    </html>
  );
}
