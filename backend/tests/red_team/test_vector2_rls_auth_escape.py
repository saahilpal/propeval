from __future__ import annotations

import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.config import settings
from backend.app.main import app
from backend.app.storage.db import get_pool


TENANT_A = "00000000-0000-0000-0000-000000000001"
TENANT_B = "00000000-0000-0000-0000-000000000002"


@pytest.fixture(autouse=True)
async def ensure_tenants_exist():
    """Ensure both test tenants exist in DB."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO tenants (id, name, data_region, encrypted_dek)
            VALUES
                ($1::uuid, 'Test Tenant A', 'ap-south-1', '\\x01020304'),
                ($2::uuid, 'Test Tenant B', 'ap-south-1', '\\x05060708')
            ON CONFLICT (id) DO NOTHING
            """,
            TENANT_A,
            TENANT_B,
        )


@pytest.mark.asyncio
async def test_rls_session_variable_isolation_and_cleanup():
    """Verify set_config applies across queries on the connection and resets upon release."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Set tenant session variable
        await conn.execute("SELECT set_config('app.current_tenant_id', $1::text, false)", TENANT_A)
        val = await conn.fetchval("SELECT current_setting('app.current_tenant_id', true)")
        assert val == TENANT_A

        # Cleanly reset
        await conn.execute("SELECT set_config('app.current_tenant_id', '', false)")
        val_reset = await conn.fetchval("SELECT current_setting('app.current_tenant_id', true)")
        assert val_reset == ""


@pytest.mark.asyncio
async def test_cross_tenant_select_isolation():
    """Tenant B must never be able to read Tenant A's prompt versions or fixtures."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Tenant A creates a prompt version
        unique_name = f"RedTeam Prompt {uuid.uuid4().hex[:6]}"
        prompt_payload = {
            "name": unique_name,
            "version_tag": "v1.0.0",
            "system_prompt": "You are a luxury real estate advisor in South Mumbai.",
            "model_provider": "deterministic",
            "model_id": "deterministic-v1",
            "temperature": 0.3,
        }
        create_resp = await client.post(
            "/api/v1/prompts",
            json=prompt_payload,
            headers={"X-Tenant-ID": TENANT_A},
        )
        assert create_resp.status_code == 200
        prompt_id = create_resp.json()["id"]

        # 2. Tenant A can read it
        get_a = await client.get(
            f"/api/v1/prompts/{prompt_id}",
            headers={"X-Tenant-ID": TENANT_A},
        )
        assert get_a.status_code == 200

        # 3. Tenant B querying the same ID must get 404 (Row Level Security blocked)
        get_b = await client.get(
            f"/api/v1/prompts/{prompt_id}",
            headers={"X-Tenant-ID": TENANT_B},
        )
        assert get_b.status_code == 404
        assert "not found" in get_b.json()["detail"].lower()


@pytest.mark.asyncio
async def test_invalid_tenant_id_header_format_rejected():
    """Malformed UUIDs, SQL injection payloads in X-Tenant-ID must return HTTP 400."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        bad_headers = [
            "malicious-string-not-uuid",
            "'; DROP TABLE tenants; --",
            "12345",
            "00000000-0000-0000-0000-00000000000z",
        ]
        for bh in bad_headers:
            resp = await client.get("/api/v1/prompts", headers={"X-Tenant-ID": bh})
            assert resp.status_code == 400
            assert "Invalid X-Tenant-ID UUID format" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_unauthorized_tenant_deletion_blocked():
    """DELETE /api/v1/tenants/{tenant_id} must require valid X-Admin-Key header."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. No admin key -> 403 Forbidden
        resp_no_key = await client.delete(f"/api/v1/tenants/{TENANT_B}")
        assert resp_no_key.status_code == 403
        assert "Forbidden" in resp_no_key.json()["detail"]

        # 2. Invalid admin key -> 403 Forbidden
        resp_bad_key = await client.delete(
            f"/api/v1/tenants/{TENANT_B}",
            headers={"X-Admin-Key": "attacker_fake_secret"},
        )
        assert resp_bad_key.status_code == 403

        # 3. Valid admin key -> succeeds
        resp_valid = await client.delete(
            f"/api/v1/tenants/{TENANT_B}",
            headers={"X-Admin-Key": settings.admin_api_key},
        )
        assert resp_valid.status_code == 200
        assert resp_valid.json()["status"] == "purged"
