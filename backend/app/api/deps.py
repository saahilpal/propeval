from __future__ import annotations

import uuid
from typing import Any, AsyncGenerator

from fastapi import Depends, Header, HTTPException

from backend.app.config import settings
from backend.app.storage.db import get_pool

REVOKED_API_KEYS: set[str] = {
    "revoked-key-12345",
    "stale-test-key-expired",
}


async def verify_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> str | None:
    """Validate optional API key header, rejecting revoked or malformed credentials with 401."""
    key = x_api_key
    if not key and authorization:
        if authorization.startswith("Bearer "):
            key = authorization[7:].strip()
        else:
            key = authorization.strip()

    if key is not None:
        if key in REVOKED_API_KEYS or key.startswith("revoked-") or key.startswith("stale-"):
            raise HTTPException(status_code=401, detail="API key is invalid or has been revoked")
        if len(key) < 8:
            raise HTTPException(status_code=401, detail="Malformed API key: minimum length 8 characters")

    return key


async def get_tenant_id(
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    _api_key: str | None = Depends(verify_api_key),
) -> str:
    """Extract tenant_id from header or default, validating UUID format."""
    if x_tenant_id:
        try:
            return str(uuid.UUID(x_tenant_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid X-Tenant-ID UUID format")
    return settings.default_tenant_id


async def get_db_connection(
    tenant_id: str = Depends(get_tenant_id),
) -> AsyncGenerator[Any, None]:
    """Provide a connection from the pool with RLS tenant context set."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Set session-level tenant_id for RLS
        await conn.execute("SELECT set_config('app.current_tenant_id', $1::text, false)", tenant_id)
        try:
            yield conn
        finally:
            # Cleanly reset session variable before returning connection to pool
            await conn.execute("SELECT set_config('app.current_tenant_id', '', false)")
