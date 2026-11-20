import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "PropEval — Pre-Release Prompt Regression & Reliability Workbench for Indian Real Estate Voice AI",
  description: "Detect TRAI DNC violations, RERA hallucinations, 8 kHz acoustic misparses, and tool failures before prompt deployment.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-canvas text-ink-primary flex flex-col antialiased overflow-x-hidden">
        {/* Unified Sticky Product Navbar (huvo.ai craft) */}
        <header className="h-14 border-b border-border bg-surface/95 backdrop-blur-sm px-4 sm:px-6 flex items-center justify-between sticky top-0 z-50">
          <div className="flex items-center gap-4 sm:gap-8">
            <Link href="/" className="flex items-center gap-2.5 group shrink-0">
              <span className="w-2.5 h-2.5 rounded-sm bg-ink-primary group-hover:scale-110 transition-transform" />
              <span className="font-mono font-bold text-sm tracking-wider uppercase text-ink-primary">
                PropEval
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                v0.5.0
              </span>
            </Link>

            <nav className="hidden md:flex items-center gap-1 text-xs font-medium text-slate-600">
              <Link
                href="/"
                className="py-1 px-2.5 rounded-md hover:text-ink-primary hover:bg-slate-100 transition-colors"
              >
                Product
              </Link>
              <Link
                href="/workbench"
                className="py-1 px-2.5 rounded-md hover:text-ink-primary hover:bg-slate-100 transition-colors"
              >
                Live Workbench
              </Link>
              <Link
                href="/registry"
                className="py-1 px-2.5 rounded-md hover:text-ink-primary hover:bg-slate-100 transition-colors"
              >
                Registry
              </Link>
              <a
                href="https://github.com/saahilpal/propeval/blob/main/benchmarks/BENCHMARK_REPORT.md"
                target="_blank"
                rel="noreferrer"
                className="py-1 px-2.5 rounded-md hover:text-ink-primary hover:bg-slate-100 transition-colors"
              >
                Benchmarks
              </a>
              <a
                href="https://github.com/saahilpal/propeval"
                target="_blank"
                rel="noreferrer"
                className="py-1 px-2.5 rounded-md hover:text-ink-primary hover:bg-slate-100 transition-colors"
              >
                GitHub
              </a>
              <a
                href="https://huggingface.co/sahilpal/propeval-laya-hinglish-realestate-v1"
                target="_blank"
                rel="noreferrer"
                className="py-1 px-2.5 rounded-md hover:text-ink-primary hover:bg-slate-100 transition-colors"
              >
                Hugging Face
              </a>
            </nav>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden lg:flex items-center gap-2 text-xs font-mono text-slate-500 bg-slate-50 px-2.5 py-1 rounded-md border border-slate-200">
              <span className="inline-block w-2 h-2 rounded-full bg-accent-emerald animate-pulse" />
              <span>Postgres 17</span>
              <span className="text-slate-300">|</span>
              <span className="text-accent-emerald font-medium">$0.00 Spend</span>
            </div>

            <Link
              href="/workbench"
              className="text-xs font-medium bg-ink-primary text-white hover:bg-slate-800 px-3 py-1.5 rounded-md transition-colors shrink-0 flex items-center gap-1.5"
            >
              <span>Open Workbench</span>
              <span className="text-[10px]">→</span>
            </Link>
          </div>
        </header>

        <main className="flex-1 flex flex-col w-full max-w-full overflow-x-hidden">{children}</main>
      </body>
    </html>
  );
}
