from __future__ import annotations

from typing import Any, AsyncGenerator
import asyncpg
from fastapi import Header, HTTPException

from backend.app.config import settings
from backend.app.storage.db import get_pool


async def get_tenant_id(
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
) -> str:
    """Extract tenant_id from header or default."""
    if x_tenant_id and len(x_tenant_id) == 36:
        return x_tenant_id
    return settings.default_tenant_id


async def get_db_connection(
    req_tenant_id: str = Header(default=settings.default_tenant_id, alias="X-Tenant-ID"),
) -> AsyncGenerator[Any, None]:
    """Provide a connection from the pool with RLS tenant context set."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Set tenant_id for RLS
        await conn.execute("SELECT set_config('app.current_tenant_id', $1::text, true)", req_tenant_id)
        yield conn
