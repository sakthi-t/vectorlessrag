from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.session import get_db
from app.auth.tenant import TenantContext, get_tenant_context
from app.services.document_service import ensure_user_exists

router = APIRouter(prefix="/auth", tags=["auth"])


class MeOut(BaseModel):
    id: str
    email: str
    role: str


class WebhookPayload(BaseModel):
    data: dict
    type: str


@router.get("/me", response_model=MeOut)
async def get_me(
    ctx: TenantContext = Depends(get_tenant_context),
):
    return MeOut(id=str(ctx.user_id), email="", role=ctx.role)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def clerk_webhook(
    payload: WebhookPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    event_type = payload.type

    if event_type == "user.created":
        clerk_id = payload.data.get("id", "")
        email_addresses = payload.data.get("email_addresses", [])
        email = email_addresses[0]["email_address"] if email_addresses else ""
        private_meta = payload.data.get("private_metadata", {}) or {}
        role = private_meta.get("role", "user")
        if clerk_id and email:
            await ensure_user_exists(db, clerk_id, email, role)

    elif event_type == "user.deleted":
        clerk_id = payload.data.get("id", "")
        if clerk_id:
            from app.models.user import User
            from sqlalchemy import select
            user_result = await db.execute(
                select(User).where(User.clerk_id == clerk_id)
            )
            user = user_result.scalar_one_or_none()
            if user:
                await db.delete(user)
                await db.commit()

    return {"status": "ok"}
