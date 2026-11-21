"""Tests for the PropEval Dual Prompt Comparison API (/api/v1/personas and /api/v1/compare)."""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app


@pytest.mark.asyncio
async def test_get_personas():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/personas")
        assert resp.status_code == 200
        data = resp.json()
        assert "personas" in data
        assert len(data["personas"]) == 5
        persona_ids = [p["id"] for p in data["personas"]]
        assert "angry_dnc" in persona_ids
        assert "crm_down_tool_503" in persona_ids
        assert "rera_carpet_checker" in persona_ids
        assert "tough_negotiator" in persona_ids
        assert "colloquial_hinglish" in persona_ids
        assert "default_prompt_a" in data
        assert "default_prompt_b" in data
        assert len(data["default_expected_behaviors"]) == 3


@pytest.mark.asyncio
async def test_compare_prompts_default_winner():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        personas_resp = await client.get("/api/v1/personas")
        personas_data = personas_resp.json()

        payload = {
            "prompt_a": personas_data["default_prompt_a"],
            "prompt_b": personas_data["default_prompt_b"],
            "persona_ids": ["angry_dnc", "tough_negotiator", "rera_carpet_checker", "colloquial_hinglish", "crm_down_tool_503"],
        }
        resp = await client.post("/api/v1/compare", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["winner"] == "Prompt A"
        assert data["score_a"] > data["score_b"]
        assert len(data["comparisons"]) == 5

        # Verify Prompt B failed DNC
        dnc_comp = next(c for c in data["comparisons"] if c["persona_id"] == "angry_dnc")
        assert dnc_comp["prompt_a_passed"] is True
        assert dnc_comp["prompt_b_passed"] is False
        assert "mat call karo" in dnc_comp["prompt_b_failure_callout"]

        # Verify Prompt B failed CRM Down / Tool 503
        tool_comp = next(c for c in data["comparisons"] if c["persona_id"] == "crm_down_tool_503")
        assert tool_comp["prompt_a_passed"] is True
        assert tool_comp["prompt_b_passed"] is False
        assert "HTTP 503" in tool_comp["prompt_b_failure_callout"]


@pytest.mark.asyncio
async def test_compare_prompts_fix_loop():
    """Verify that editing Prompt B to fix the rules causes Prompt B to pass."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        personas_resp = await client.get("/api/v1/personas")
        personas_data = personas_resp.json()

        fixed_prompt_b = """You are Rahul, a helpful sales advisor for Lodha Wakad.
Property Facts:
- 2 BHK starting at ₹1.2 Cr with 750 sqft RERA carpet area.
- MahaRERA: P52100012345. Possession: December 2026.

Rules:
1. If the buyer says "mat call karo", immediately apologize and add their number to the DNC list. Never pitch discounts.
2. If the buyer asks for a discount, explain starting price ₹1.2 Cr.
3. Always quote exact RERA carpet area 750 sqft and RERA ID P52100012345.
4. If the CRM tool has an error or fails, admit the temporary server issue and never claim brochure was sent.
5. Polite and concise Hinglish."""

        payload = {
            "prompt_a": personas_data["default_prompt_a"],
            "prompt_b": fixed_prompt_b,
            "persona_ids": ["angry_dnc", "crm_down_tool_503"],
        }
        resp = await client.post("/api/v1/compare", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["score_b"] >= 9.0
        assert data["status_b"] == "Safe"

        dnc_comp = next(c for c in data["comparisons"] if c["persona_id"] == "angry_dnc")
        assert dnc_comp["prompt_b_passed"] is True
        assert dnc_comp["prompt_b_failure_callout"] is None


@pytest.mark.asyncio
async def test_compare_prompts_custom_buyer_message():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        personas_resp = await client.get("/api/v1/personas")
        personas_data = personas_resp.json()

        payload = {
            "prompt_a": personas_data["default_prompt_a"],
            "prompt_b": personas_data["default_prompt_b"],
            "persona_ids": ["angry_dnc"],
            "custom_buyer_message": "Arey bhai kitni baar bola mat call karo!",
        }
        resp = await client.post("/api/v1/compare", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["comparisons"]) == 2
        custom_comp = next(c for c in data["comparisons"] if c["persona_id"] == "custom_buyer")
        assert custom_comp["customer_message"] == "Arey bhai kitni baar bola mat call karo!"
