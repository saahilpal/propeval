from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from backend.app.api.deps import get_db_connection
from backend.app.config import settings

router = APIRouter(prefix="/tenants", tags=["tenants"])


class TenantDeleteResponse(BaseModel):
    tenant_id: str
    status: str
    message: str


@router.delete("/{tenant_id}", response_model=TenantDeleteResponse)
async def delete_tenant(
    tenant_id: str,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    """Cascading tenant purge under GDPR/DPDP mandates."""
    if not x_admin_key or x_admin_key != settings.admin_api_key:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Valid X-Admin-Key required for tenant deletion",
        )

    res = await conn.execute(
        """
        DELETE FROM tenants
        WHERE id = $1::uuid
        """,
        tenant_id,
    )
    if res == "DELETE 0":
        raise HTTPException(status_code=404, detail="Tenant not found")

    return TenantDeleteResponse(
        tenant_id=tenant_id,
        status="purged",
        message="Tenant and all associated runs, jobs, turns, and credentials purged successfully",
    )
