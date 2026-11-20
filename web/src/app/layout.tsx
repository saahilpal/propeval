import type { Metadata } from "next";
import { Navbar } from "@/components/Navbar";
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
        <Navbar />
        <main className="flex-1 flex flex-col w-full max-w-full overflow-x-hidden">{children}</main>
      </body>
    </html>
  );
}
