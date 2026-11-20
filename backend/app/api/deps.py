from __future__ import annotations

from typing import Any, AsyncGenerator
import uuid
import asyncpg
from fastapi import Depends, Header, HTTPException

from backend.app.config import settings
from backend.app.storage.db import get_pool


async def get_tenant_id(
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
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
