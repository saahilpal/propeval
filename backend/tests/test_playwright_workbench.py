from __future__ import annotations

import os

import httpx
import pytest
from playwright.async_api import Page, async_playwright


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

    # 1. Ensure a valid completed run exists in backend
    async with httpx.AsyncClient(base_url="http://localhost:8001") as client:
        runs_res = await client.get("/api/v1/runs")
        runs = runs_res.json()
        assert len(runs) > 0, "Expected at least one eval run in DB"
        valid_runs = [r for r in runs if r.get("status") in ("PASSED", "REGRESSED", "COMPLETED")]
        latest_run_id = valid_runs[0]["id"] if valid_runs else runs[0]["id"]

    all_errors: list[str] = []

    viewports = [
        {"name": "1440x900", "width": 1440, "height": 900},
        {"name": "1024x768", "width": 1024, "height": 768},
        {"name": "768x1024", "width": 768, "height": 1024},
        {"name": "390x844", "width": 390, "height": 844},
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for vp in viewports:
            # 1. Workbench Page
            page_wb = await browser.new_page(viewport={"width": vp["width"], "height": vp["height"]})
            attach_error_tracker(page_wb, all_errors)
            await page_wb.goto("http://localhost:3000/", wait_until="networkidle")
            await page_wb.wait_for_selector("text=PropEval")
            await page_wb.wait_for_selector("text=Scenario Triage")
            await page_wb.wait_for_selector("text=Laya System-1 Cascade")
            await page_wb.wait_for_selector("text=92.06%")
            await page_wb.screenshot(path=f"web/screenshots/workbench_{vp['name']}.png", full_page=True)
            if vp["name"] == "1440x900":
                await page_wb.screenshot(path="web/screenshots/hero_diff.png", full_page=True)
            await page_wb.close()

            # 2. Registry Page
            page_reg = await browser.new_page(viewport={"width": vp["width"], "height": vp["height"]})
            attach_error_tracker(page_reg, all_errors)
            await page_reg.goto("http://localhost:3000/registry", wait_until="networkidle")
            await page_reg.wait_for_selector("text=Prompt & RERA Project Registry")
            await page_reg.screenshot(path=f"web/screenshots/registry_{vp['name']}.png", full_page=True)
            await page_reg.close()

            # 3. Scenario Inspector Page
            page_scen = await browser.new_page(viewport={"width": vp["width"], "height": vp["height"]})
            attach_error_tracker(page_scen, all_errors)
            await page_scen.goto(
                f"http://localhost:3000/runs/{latest_run_id}/scenarios/smoke_01_std_lodha_2bhk",
                wait_until="networkidle",
            )
            await page_scen.wait_for_selector("text=smoke_01_std_lodha_2bhk")
            await page_scen.wait_for_selector("text=RESOLVED (S1)")
            await page_scen.wait_for_selector("text=ESCALATED (S2)")
            await page_scen.screenshot(path=f"web/screenshots/scenario_inspector_{vp['name']}.png", full_page=True)
            if vp["name"] == "1440x900":
                await page_scen.screenshot(path="web/screenshots/turn_inspector.png", full_page=True)
            await page_scen.close()

        await browser.close()

    assert len(all_errors) == 0, f"Found browser console/hydration errors: {all_errors}"

    # Verify canonical desktop hero artifacts exist
    assert os.path.exists("web/screenshots/hero_diff.png"), "Missing hero_diff.png"
    assert os.path.getsize("web/screenshots/hero_diff.png") > 10000, "hero_diff.png is too small"
    assert os.path.exists("web/screenshots/turn_inspector.png"), "Missing turn_inspector.png"
    assert os.path.getsize("web/screenshots/turn_inspector.png") > 10000, "turn_inspector.png is too small"

    # Verify screenshots exist and are non-empty for all viewports
    for vp in viewports:
        for prefix in ["workbench", "registry", "scenario_inspector"]:
            shot = f"web/screenshots/{prefix}_{vp['name']}.png"
            assert os.path.exists(shot), f"Missing screenshot {shot}"
            assert os.path.getsize(shot) > 1000, f"Screenshot {shot} is empty"
