---
name: react-best-practices
description: "Vercel and React 19 best practices: strict Server/Client component separation, clean state management, zero unnecessary re-renders, and anti-slop typography and layout."
---

# React 19 & Next.js 16 Best Practices

## 1. Server vs. Client Component Boundaries
- Default to React Server Components (RSC) for data fetching, static rendering, and layout structure.
- Use `"use client"` only at leaf components requiring browser APIs, local state, or interactive events (e.g. SSE listeners, filter tabs, interactive diff toggles).
- Never place `"use client"` at root layout or page levels.
- Avoid passing sensitive environment keys or full DB objects to client components.

## 2. Anti-Slop UI & Layout Discipline
- No neon/purple glowing cards, glassmorphic blurs, or AI-generated radial score dials.
- Use crisp high-contrast neutral borders (`border-neutral-200 dark:border-neutral-800`, 1px hairline).
- Strict typographic hierarchy:
  - Sans (`Inter`, `Geist`, `Space Grotesk`) for UI labels and headings.
  - Monospace (`IBM Plex Mono`, `Geist Mono`, `JetBrains Mono`) with `tabular-nums` for all numbers, metrics, currency (INR/USD), timestamps, p-values, and confidence intervals.
- Generous whitespace, predictable tabular data alignments, and clean visual separation between hard-gate pass/fail banners and statistical metrics.

## 3. Streaming & Error Resilience
- Wrap async streaming sections in `<Suspense fallback={<Skeleton />}>`.
- Isolate failure domains with localized `<ErrorBoundary>`.
- Use native `EventSource` with reconnect backoff and `Last-Event-ID` header handling for durable SSE subscriptions.
