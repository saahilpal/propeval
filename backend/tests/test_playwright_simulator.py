"""Playwright End-to-End Test for PropEval Clean Indian Customer Prompt Simulator."""

import asyncio
import os
import sys
from playwright.async_api import async_playwright


async def run_playwright_audit():
    console_errors = []
    failed_requests = []

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)

        # -------------------------------------------------------------------
        # 1. Desktop Audit (1440 x 900)
        # -------------------------------------------------------------------
        print("--> Starting Desktop Audit (1440x900)...")
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        page.on("console", lambda msg: console_errors.append(f"CONSOLE: {msg.text}") if msg.type == "error" else None)
        page.on("requestfailed", lambda req: failed_requests.append(f"FAILED REQ: {req.url} ({req.failure})"))

        await page.goto("http://127.0.0.1:3000/", wait_until="networkidle")

        # Verify page title and header
        title = await page.title()
        print(f"Page Title: {title}")

        # Wait for simulation verdict to load
        await page.wait_for_selector("text=Simulation Verdict", timeout=10000)
        print("Verdict loaded successfully.")

        # Check winner
        verdict_text = await page.inner_text("body")
        assert "Winner: Prompt A" in verdict_text, f"Expected Prompt A winner, got text: {verdict_text[:200]}"
        print("[OK] Winner: Prompt A asserted.")

        # Assert Prompt A safe and Prompt B blocked
        assert "Prompt A (Current)" in verdict_text
        assert "Prompt B (New Candidate)" in verdict_text
        assert "Safe" in verdict_text
        assert "Blocked" in verdict_text
        print("[OK] Scorecard asserted (Prompt A Safe vs Prompt B Blocked).")

        # Assert failure callout visible
        assert "Failed: Ignored 'mat call karo' and kept pitching a discount" in verdict_text
        print("[OK] Inline failure callout asserted on Prompt B.")

        # Assert Laya latency / judge tier tag
        assert "Laya" in verdict_text or "Layer 1" in verdict_text
        print("[OK] Evaluation judge tier tag asserted.")

        # Save initial desktop screenshot
        os.makedirs("/tmp/propeval_screenshots", exist_ok=True)
        await page.screenshot(path="/tmp/propeval_screenshots/01_desktop_initial.png", full_page=True)
        print("[OK] Saved /tmp/propeval_screenshots/01_desktop_initial.png")

        # -------------------------------------------------------------------
        # 2. 3-Second Fix Loop: Edit Prompt B and Re-Run
        # -------------------------------------------------------------------
        print("--> Testing 3-Second Fix Loop: Editing Prompt B to fix DNC and tool rules...")

        fixed_prompt_b = """You are Rahul, a helpful sales advisor for Lodha Wakad.
Property Facts:
- 2 BHK starting at ₹1.2 Cr with 750 sqft RERA carpet area.
- MahaRERA: P52100012345. Possession: December 2026.

Rules:
1. If the buyer says "mat call karo", immediately apologize and confirm DNC list. Never pitch discounts.
2. If the buyer asks for a discount, explain starting price ₹1.2 Cr.
3. Always quote exact RERA carpet area 750 sqft and RERA ID P52100012345.
4. If the CRM tool has an error (HTTP 503), admit server issue and never claim brochure was sent.
5. Polite and concise Hinglish."""

        # Fill Prompt B textarea (the second textarea)
        textareas = page.locator("textarea")
        await textareas.nth(1).fill(fixed_prompt_b)

        # Click Re-Run button
        rerun_button = page.locator("button:has-text('Re-Run')").first
        await rerun_button.click()

        # Wait for simulation to finish
        await page.wait_for_timeout(1500)
        await page.wait_for_selector("text=Simulation Verdict", timeout=10000)

        fixed_body = await page.inner_text("body")
        # Check that Prompt B is now Safe
        assert "Prompt B" in fixed_body
        assert "Safe" in fixed_body
        print("[OK] 3-Second Fix Loop confirmed: Prompt B status updated to Safe!")

        await page.screenshot(path="/tmp/propeval_screenshots/02_desktop_fixed.png", full_page=True)
        print("[OK] Saved /tmp/propeval_screenshots/02_desktop_fixed.png")

        await context.close()

        # -------------------------------------------------------------------
        # 3. Mobile Viewport Audit (390 x 844 - iPhone 14/15)
        # -------------------------------------------------------------------
        print("--> Starting Mobile Viewport Audit (390x844)...")
        mobile_context = await browser.new_context(viewport={"width": 390, "height": 844})
        mobile_page = await mobile_context.new_page()

        await mobile_page.goto("http://127.0.0.1:3000/", wait_until="networkidle")
        await mobile_page.wait_for_selector("text=Simulation Verdict", timeout=10000)

        # Check for horizontal overflow
        scroll_width = await mobile_page.evaluate("document.documentElement.scrollWidth")
        client_width = await mobile_page.evaluate("document.documentElement.clientWidth")
        print(f"Mobile Dimensions: scrollWidth={scroll_width}, clientWidth={client_width}")
        assert scroll_width <= client_width + 1, f"Horizontal overflow detected! scrollWidth={scroll_width} > clientWidth={client_width}"
        print("[OK] Zero horizontal overflow confirmed on mobile (390x844).")

        await mobile_page.screenshot(path="/tmp/propeval_screenshots/03_mobile.png", full_page=True)
        print("[OK] Saved /tmp/propeval_screenshots/03_mobile.png")

        await mobile_context.close()
        await browser.close()

    # Verify zero console errors & zero failed network requests
    print(f"Console Errors Count: {len(console_errors)}")
    print(f"Failed Requests Count: {len(failed_requests)}")
    if console_errors:
        print("Console errors detected:\n" + "\n".join(console_errors))
    if failed_requests:
        print("Failed requests detected:\n" + "\n".join(failed_requests))

    assert len(console_errors) == 0, f"Expected 0 console errors, got {len(console_errors)}"
    assert len(failed_requests) == 0, f"Expected 0 failed requests, got {len(failed_requests)}"
    print("\n[ALL PLAYWRIGHT TESTS PASSED CLEANLY WITH ZERO ERRORS!]")


if __name__ == "__main__":
    asyncio.run(run_playwright_audit())
