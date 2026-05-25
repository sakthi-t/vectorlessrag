import uuid
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.config import settings
from app.models.user import User
from app.models.document import Document
from app.models.chunk import Chunk
from app.models.document_tree import DocumentTree
from app.models.bm25_index import BM25Stats
from app.models.chat import ChatSession, ChatMessage
from app.services.storage_service import storage_service


async def delete_user_from_clerk(clerk_id: str) -> bool:
    if not settings.CLERK_SECRET_KEY:
        return False

    url = f"https://api.clerk.com/v1/users/{clerk_id}"
    headers = {
        "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.delete(url, headers=headers)
        return resp.status_code == 200


async def admin_delete_user(
    db: AsyncSession,
    target_user_id: uuid.UUID,
) -> bool:
    user = await db.get(User, target_user_id)
    if not user:
        return False

    doc_result = await db.execute(
        select(Document).where(Document.user_id == target_user_id)
    )
    documents = doc_result.scalars().all()

    for doc in documents:
        await storage_service.delete(doc.b2_file_key)
        doc_id = doc.id
        await db.execute(delete(BM25Stats).where(BM25Stats.document_id == doc_id))
        await db.execute(delete(Chunk).where(Chunk.document_id == doc_id))
        await db.execute(delete(DocumentTree).where(DocumentTree.document_id == doc_id))
        await db.execute(delete(Document).where(Document.id == doc_id))

    session_result = await db.execute(
        select(ChatSession).where(ChatSession.user_id == target_user_id)
    )
    sessions = session_result.scalars().all()

    for session in sessions:
        await db.execute(
            delete(ChatMessage).where(ChatMessage.session_id == session.id)
        )
        await db.execute(delete(ChatSession).where(ChatSession.id == session.id))

    clerk_id = user.clerk_id
    await db.delete(user)
    await db.commit()

    if clerk_id:
        await delete_user_from_clerk(clerk_id)

    return True


async def list_all_users(
    db: AsyncSession,
    tenant_id: str,
) -> list[dict]:
    result = await db.execute(
        select(User).where(User.tenant_id == tenant_id)
    )
    return [{
        "id": str(u.id),
        "email": u.email,
        "role": u.role,
        "clerk_id": u.clerk_id,
        "created_at": u.created_at.isoformat(),
    } for u in result.scalars().all()]
