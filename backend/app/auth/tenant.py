from pydantic import BaseModel
from fastapi import Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.db.session import get_db
from app.models.user import User
from app.auth.clerk import verify_clerk_jwt


class TenantContext(BaseModel):
    user_id: str
    tenant_id: str
    role: str


async def get_tenant_context(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TenantContext:
    claims = await verify_clerk_jwt(request)
    clerk_id = claims["sub"]

    # Extract role from Clerk private_metadata or ADMIN_CLERK_IDS env var
    private_meta = claims.get("private_metadata", {}) or {}
    public_meta = claims.get("public_metadata", {}) or {}
    clerk_role = private_meta.get("role") or public_meta.get("role")

    admin_ids = {id_.strip() for id_ in settings.ADMIN_CLERK_IDS.split(",") if id_.strip()}
    if not clerk_role and clerk_id in admin_ids:
        clerk_role = "admin"

    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()

    if not user:
        email_addresses = claims.get("email_addresses", []) or []
        email = ""
        if isinstance(email_addresses, list) and len(email_addresses) > 0:
            email = email_addresses[0].get("email_address", "")
        if not email:
            email = claims.get("email", "")

        user = User(
            clerk_id=clerk_id,
            email=email,
            role=clerk_role or "user",
            tenant_id=clerk_id,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    elif clerk_role and user.role != clerk_role:
        user.role = clerk_role
        await db.commit()

    return TenantContext(
        user_id=str(user.id),
        tenant_id=user.tenant_id,
        role=user.role,
    )
