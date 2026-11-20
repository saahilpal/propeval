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
