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
        assert data["total_evaluated_turns"] == 252
        assert data["source"] == "live_database_aggregate"

