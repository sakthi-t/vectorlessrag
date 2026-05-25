from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import uuid

from app.db.session import get_db
from app.auth.tenant import TenantContext, get_tenant_context
from app.schemas.admin import AdminStatsOut, AdminUserOut
from app.services.admin_service import admin_delete_user
from app.models.user import User
from app.models.document import Document

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(ctx: TenantContext) -> None:
    if ctx.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")


@router.get("/stats", response_model=AdminStatsOut)
async def admin_stats(
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(ctx)

    users_count = await db.scalar(
        select(func.count(User.id))
    )
    docs_count = await db.scalar(
        select(func.count(Document.id))
    )
    storage = await db.scalar(
        select(func.coalesce(func.sum(Document.file_size_bytes), 0))
    )

    return AdminStatsOut(
        total_users=users_count or 0,
        total_documents=docs_count or 0,
        total_storage_bytes=storage or 0,
    )


@router.get("/users", response_model=list[AdminUserOut])
async def admin_list_users(
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(ctx)

    subq = (
        select(
            Document.user_id,
            func.count(Document.id).label("doc_count"),
        )
        .group_by(Document.user_id)
        .subquery()
    )

    query = (
        select(
            User.id,
            User.email,
            User.role,
            func.coalesce(subq.c.doc_count, 0).label("document_count"),
            User.created_at,
        )
        .outerjoin(subq, User.id == subq.c.user_id)
    )

    result = await db.execute(query)
    rows = result.all()

    return [
        AdminUserOut(
            id=row.id,
            email=row.email,
            role=row.role,
            document_count=row.document_count,
            created_at=row.created_at.isoformat(),
        )
        for row in rows
    ]


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_user_endpoint(
    user_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(ctx)

    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID")

    if str(uid) == str(ctx.user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )

    deleted = await admin_delete_user(db, uid)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
