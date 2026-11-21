"""Playwright E2E Verification for PropEval Indian Customer Prompt Simulator."""

from __future__ import annotations

import os
import pytest
from playwright.async_api import Page, async_playwright

LOCAL_URL = "http://localhost:3000"


def attach_error_tracker(page: Page, errors_list: list[str]) -> None:
    page.on(
        "console",
        lambda msg: errors_list.append(f"[{msg.type}] {msg.text}")
        if msg.type == "error"
        else None,
    )
    page.on("pageerror", lambda exc: errors_list.append(f"[pageerror] {exc}"))


@pytest.mark.asyncio
async def test_playwright_simulator_desktop_and_mobile():
    os.makedirs("/tmp/propeval_screenshots", exist_ok=True)
    all_errors: list[str] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # -------------------------------------------------------------------
        # 1. Desktop Viewport (1440x900)
        # -------------------------------------------------------------------
        context_desktop = await browser.new_context(viewport={"width": 1440, "height": 900})
        page_desktop = await context_desktop.new_page()
        attach_error_tracker(page_desktop, all_errors)

        await page_desktop.goto(f"{LOCAL_URL}/", wait_until="networkidle")

        # Check title and simulator elements
        await page_desktop.wait_for_selector("text=Indian Customer Prompt Simulator")
        await page_desktop.wait_for_selector("text=Prompt A (Current)")
        await page_desktop.wait_for_selector("text=Prompt B (New Candidate)")
        await page_desktop.wait_for_selector("text=Simulation Verdict", timeout=12000)

        # Assert initial winner is Prompt A
        body_text = await page_desktop.inner_text("body")
        assert "Winner: Prompt A" in body_text
        assert "Safe" in body_text
        assert "Blocked" in body_text
        assert "Failed: Ignored 'mat call karo' and kept pitching a discount" in body_text

        await page_desktop.screenshot(
            path="/tmp/propeval_screenshots/01_desktop_initial.png", full_page=True
        )

        # -------------------------------------------------------------------
        # 2. 3-Second Fix Loop: Edit Prompt B and Re-Run
        # -------------------------------------------------------------------
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

        textareas = page_desktop.locator("textarea")
        await textareas.nth(1).fill(fixed_prompt_b)

        rerun_btn = page_desktop.locator("button:has-text('Re-Run')").first
        await rerun_btn.click()

        await page_desktop.wait_for_timeout(1500)
        await page_desktop.wait_for_selector("text=Simulation Verdict", timeout=12000)

        fixed_body = await page_desktop.inner_text("body")
        assert "Prompt B" in fixed_body
        assert "Safe" in fixed_body

        await page_desktop.screenshot(
            path="/tmp/propeval_screenshots/02_desktop_fixed.png", full_page=True
        )
        await context_desktop.close()

        # -------------------------------------------------------------------
        # 3. Mobile Viewport (390x844 - iPhone 14/15)
        # -------------------------------------------------------------------
        context_mobile = await browser.new_context(viewport={"width": 390, "height": 844})
        page_mobile = await context_mobile.new_page()
        attach_error_tracker(page_mobile, all_errors)

        await page_mobile.goto(f"{LOCAL_URL}/", wait_until="networkidle")
        await page_mobile.wait_for_selector("text=Simulation Verdict", timeout=12000)

        # Check for zero horizontal overflow
        scroll_width = await page_mobile.evaluate("document.documentElement.scrollWidth")
        client_width = await page_mobile.evaluate("document.documentElement.clientWidth")
        assert scroll_width <= client_width + 1

        await page_mobile.screenshot(
            path="/tmp/propeval_screenshots/03_mobile.png", full_page=True
        )
        await context_mobile.close()
        await browser.close()

    assert len(all_errors) == 0, f"Detected console errors: {all_errors}"
