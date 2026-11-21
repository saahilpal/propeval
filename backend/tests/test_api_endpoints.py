from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app


@pytest.mark.asyncio
async def test_api_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["app"] == "PropEval"


@pytest.mark.asyncio
async def test_api_rfc9457_problem_details_on_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/prompts/00000000-0000-0000-0000-000000000099")
        assert resp.status_code == 404
        assert resp.headers.get("content-type") == "application/problem+json"
        data = resp.json()
        assert data["status"] == 404
        assert "Prompt version not found" in data["detail"]
        assert data["type"] == "https://propeval.ai/errors/404"


@pytest.mark.asyncio
async def test_api_cascade_metrics_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/metrics/cascade")
        assert resp.status_code == 200
        data = resp.json()
        assert data["resolution_rate_pct"] == 92.06
        assert data["escalation_rate_pct"] == 7.94
        assert data["p50_latency_ms"] in (0.365, 0.383)
        assert data["expected_calibration_error"] == 0.0209
        assert data["cost_savings_pct"] == 92.06
        assert data["cohens_kappa"] in (0.9912, 0.9736)
        assert data["total_evaluated_turns"] in (252, 504)
        assert data["source"] == "live_database_aggregate"


@pytest.mark.asyncio
async def test_api_run_diff_executive_summary():
    headers = {"X-Tenant-ID": "00000000-0000-0000-0000-000000000001"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/runs/b1a2c3d4-e5f6-7890-abcd-ef1234567890/diff", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "executive_summary" in data
        exec_sum = data["executive_summary"]
        assert exec_sum["verdict"] == "BLOCKED"
        assert "3 critical safety & compliance regression" in exec_sum["headline"]
        assert len(exec_sum["key_findings"]) == 3
        assert "Do NOT deploy to production" in exec_sum["recommendation"]


@pytest.mark.asyncio
async def test_api_run_diff_fixed_preset_executive_summary():
    headers = {"X-Tenant-ID": "00000000-0000-0000-0000-000000000001"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/runs/c1a2c3d4-e5f6-7890-abcd-ef1234567891/diff", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "executive_summary" in data
        exec_sum = data["executive_summary"]
        assert exec_sum["verdict"] == "PASSED"
        assert exec_sum["headline"] == "Candidate Prompt v2.1 passed all safety, compliance, and grounding gates."
        assert len(exec_sum["key_findings"]) == 4
        assert exec_sum["recommendation"] == "Approved for production canary deployment."


@pytest.mark.asyncio
async def test_api_laya_predict_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # System-1 resolved turn
        resp1 = await client.post("/api/v1/metrics/laya/predict", json={"text": "mat call karo"})
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert data1["predicted_intent"] == "DNC_REFUSAL"
        assert data1["is_escalated"] is False
        assert data1["tier"] == "SYSTEM_1"
        assert data1["decision"] == "RESOLVED (System-1)"
        assert data1["latency_ms"] >= 0.0
        assert "High-confidence" in data1["explanation"]

        # Ambiguous / System-2 escalated turn
        resp2 = await client.post("/api/v1/metrics/laya/predict", json={"text": "kya main dnc mark kar doon?"})
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["is_escalated"] is True
        assert data2["tier"] == "SYSTEM_2"
        assert data2["decision"] == "ESCALATED (System-2)"
        assert "Interrogative trap" in data2["explanation"]


@pytest.mark.asyncio
async def test_seeded_demo_workbench_endpoints():
    headers = {"X-Tenant-ID": "00000000-0000-0000-0000-000000000001"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Prompts
        p_resp = await client.get("/api/v1/prompts", headers=headers)
        assert p_resp.status_code == 200
        prompts = p_resp.json()
        prompt_ids = {p["id"] for p in prompts}
        assert "3f8d6ec7-a21a-405f-a38c-f7a773dde33e" in prompt_ids
        assert "a5ea7a6c-54bd-4ca9-b7e3-d9592ed14a8d" in prompt_ids
        assert "c7ea8a1b-91de-4ba7-b89e-e8593ed25b9c" in prompt_ids

        # Fixtures
        f_resp = await client.get("/api/v1/fixtures", headers=headers)
        assert f_resp.status_code == 200
        fixtures = f_resp.json()
        fixture_ids = {f["id"] for f in fixtures}
        assert "3fb5f027-ec7c-41c3-bb10-d920c9de8576" in fixture_ids
        assert "4fc6a138-fd8d-42d4-cc21-ea31d9ef9687" in fixture_ids

        # Suites
        s_resp = await client.get("/api/v1/suites", headers=headers)
        assert s_resp.status_code == 200
        suites = s_resp.json()
        suite_ids = {s["id"] for s in suites}
        assert "d6d4ef4c-e872-4c44-ab95-4a98bf7c44e1" in suite_ids
        assert "e7e5fa5d-f983-4d55-bc11-5b09cf8d55f2" in suite_ids


@pytest.mark.asyncio
async def test_create_custom_scenario_endpoint():
    headers = {"X-Tenant-ID": "00000000-0000-0000-0000-000000000001"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "name": "Wakad Skeptic Buyer",
            "language": "hinglish",
            "budget_phrase": "ek point do crore",
            "bhk": 2,
            "mood": "price_skeptic",
            "opening_line": "Mera budget 1.2 cr hai, Wakad mein discount milega kya?",
            "inject_asr_noise": True,
            "inject_tool_503": True,
            "trigger_dnc": True,
            "rera_trap": True,
            "expected_hard_gates": ["SLOT_EXTRACT", "DNC_COMPLIANCE", "TOOL_CONTRACT", "FACT_GROUNDING"],
        }
        resp = await client.post("/api/v1/suites/custom-scenario", json=payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()

        assert "suite_id" in data
        assert data["suite_name"] == "Custom Scenarios (User Created)"
        assert "scenario_id" in data
        assert data["scenario_id"].startswith("custom_wakad_skeptic_buyer_")

        preview = data["scenario_preview"]
        assert preview["asr_noise_profile"] == "telephony_8khz"
        assert preview["inject_asr_noise"] is True
        assert preview["inject_tool_503"] is True
        assert preview["fault_config"] == {"book_site_visit": 503}
        assert preview["expected_tools"] == ["mark_dnc"]
        assert preview["fsm_spec"]["agenda"]["wants_dnc"] is True
        assert preview["fsm_spec"]["agenda"]["wants_rera_check"] is True
        assert preview["fsm_spec"]["agenda"]["budget_raw"] == "ek point do crore"
        assert preview["fsm_spec"]["agenda"]["target_bhk"] == 2.0



