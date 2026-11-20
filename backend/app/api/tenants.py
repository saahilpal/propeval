from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
import asyncpg
from pydantic import BaseModel

from backend.app.api.deps import get_db_connection, get_tenant_id

router = APIRouter(prefix="/tenants", tags=["tenants"])


class TenantDeleteResponse(BaseModel):
    tenant_id: str
    status: str
    message: str


@router.delete("/{tenant_id}", response_model=TenantDeleteResponse)
async def delete_tenant(
    tenant_id: str,
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    """Cascading tenant purge under GDPR/DPDP mandates."""
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
