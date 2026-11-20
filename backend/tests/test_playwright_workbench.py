from __future__ import annotations

import os
import pytest
from playwright.async_api import async_playwright, Page
import httpx


def attach_error_tracker(page: Page, errors_list: list[str]) -> None:
    page.on(
        "console",
        lambda msg: errors_list.append(f"[{msg.type}] {msg.text}")
        if msg.type == "error" or "hydration" in msg.text.lower()
        else None,
    )
    page.on("pageerror", lambda exc: errors_list.append(f"[pageerror] {exc}"))


@pytest.mark.asyncio
async def test_playwright_visual_proof_loop():
    os.makedirs("web/screenshots", exist_ok=True)

    # 1. Ensure a run exists in backend
    async with httpx.AsyncClient(base_url="http://localhost:8001") as client:
        runs_res = await client.get("/api/v1/runs")
        runs = runs_res.json()
        assert len(runs) > 0, "Expected at least one eval run in DB"
        latest_run_id = runs[0]["id"]

    all_errors: list[str] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # -------------------------------------------------------------
        # Test 1: Desktop 1440x900 Workbench
        # -------------------------------------------------------------
        page_desktop = await browser.new_page(viewport={"width": 1440, "height": 900})
        attach_error_tracker(page_desktop, all_errors)
        await page_desktop.goto("http://localhost:3000/", wait_until="networkidle")
        await page_desktop.wait_for_selector("text=PropEval")
        await page_desktop.wait_for_selector("text=Scenario Triage")
        await page_desktop.screenshot(path="web/screenshots/workbench_1440x900.png", full_page=True)
        await page_desktop.close()

        # -------------------------------------------------------------
        # Test 2: Tablet 768x1024 Workbench
        # -------------------------------------------------------------
        page_tablet = await browser.new_page(viewport={"width": 768, "height": 1024})
        attach_error_tracker(page_tablet, all_errors)
        await page_tablet.goto("http://localhost:3000/", wait_until="networkidle")
        await page_tablet.wait_for_selector("text=PropEval")
        await page_tablet.screenshot(path="web/screenshots/workbench_768x1024.png", full_page=True)
        await page_tablet.close()

        # -------------------------------------------------------------
        # Test 3: Desktop 1440x900 Registry View
        # -------------------------------------------------------------
        page_reg_desktop = await browser.new_page(viewport={"width": 1440, "height": 900})
        attach_error_tracker(page_reg_desktop, all_errors)
        await page_reg_desktop.goto("http://localhost:3000/registry", wait_until="networkidle")
        await page_reg_desktop.wait_for_selector("text=Prompt & RERA Project Registry")
        await page_reg_desktop.screenshot(path="web/screenshots/registry_1440x900.png", full_page=True)
        await page_reg_desktop.close()

        # -------------------------------------------------------------
        # Test 4: Tablet 768x1024 Registry View
        # -------------------------------------------------------------
        page_reg_tablet = await browser.new_page(viewport={"width": 768, "height": 1024})
        attach_error_tracker(page_reg_tablet, all_errors)
        await page_reg_tablet.goto("http://localhost:3000/registry", wait_until="networkidle")
        await page_reg_tablet.wait_for_selector("text=Prompt & RERA Project Registry")
        await page_reg_tablet.screenshot(path="web/screenshots/registry_768x1024.png", full_page=True)
        await page_reg_tablet.close()

        # -------------------------------------------------------------
        # Test 5: Desktop 1440x900 Scenario Inspector
        # -------------------------------------------------------------
        page_scenario_desktop = await browser.new_page(viewport={"width": 1440, "height": 900})
        attach_error_tracker(page_scenario_desktop, all_errors)
        await page_scenario_desktop.goto(
            f"http://localhost:3000/runs/{latest_run_id}/scenarios/smoke_01_std_lodha_2bhk",
            wait_until="networkidle",
        )
        await page_scenario_desktop.wait_for_selector("text=smoke_01_std_lodha_2bhk")
        await page_scenario_desktop.screenshot(path="web/screenshots/scenario_inspector_1440x900.png", full_page=True)
        await page_scenario_desktop.close()

        # -------------------------------------------------------------
        # Test 6: Tablet 768x1024 Scenario Inspector
        # -------------------------------------------------------------
        page_scenario_tablet = await browser.new_page(viewport={"width": 768, "height": 1024})
        attach_error_tracker(page_scenario_tablet, all_errors)
        await page_scenario_tablet.goto(
            f"http://localhost:3000/runs/{latest_run_id}/scenarios/smoke_01_std_lodha_2bhk",
            wait_until="networkidle",
        )
        await page_scenario_tablet.wait_for_selector("text=smoke_01_std_lodha_2bhk")
        await page_scenario_tablet.screenshot(path="web/screenshots/scenario_inspector_768x1024.png", full_page=True)
        await page_scenario_tablet.close()

        await browser.close()

    assert len(all_errors) == 0, f"Found browser console/hydration errors: {all_errors}"

    # Verify screenshots exist and are non-empty
    expected_screenshots = [
        "web/screenshots/workbench_1440x900.png",
        "web/screenshots/workbench_768x1024.png",
        "web/screenshots/registry_1440x900.png",
        "web/screenshots/registry_768x1024.png",
        "web/screenshots/scenario_inspector_1440x900.png",
        "web/screenshots/scenario_inspector_768x1024.png",
    ]
    for shot in expected_screenshots:
        assert os.path.exists(shot), f"Missing screenshot {shot}"
        assert os.path.getsize(shot) > 10000, f"Screenshot {shot} is smaller than 10KB"
