import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from fastapi import UploadFile

from app.models.document import Document
from app.models.chunk import Chunk
from app.models.document_tree import DocumentTree
from app.models.bm25_index import BM25Stats
from app.models.user import User
from app.services.storage_service import storage_service


async def upload_document(
    db: AsyncSession,
    user_id: uuid.UUID,
    tenant_id: str,
    file: UploadFile,
) -> Document:
    doc_id = uuid.uuid4()
    b2_key = await storage_service.upload(tenant_id, str(doc_id), file)

    document = Document(
        id=doc_id,
        user_id=user_id,
        tenant_id=tenant_id,
        filename=file.filename or "unnamed.pdf",
        b2_file_key=b2_key,
        content_type=file.content_type or "application/pdf",
        file_size_bytes=file.size or 0,
        status="pending",
        doc_metadata={"original_filename": file.filename},
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    from app.tasks.ingestion_tasks import process_document
    process_document.delay(str(doc_id), tenant_id)

    return document


async def get_documents(
    db: AsyncSession,
    tenant_id: str,
    limit: int = 50,
    offset: int = 0,
) -> list[Document]:
    result = await db.execute(
        select(Document)
        .where(Document.tenant_id == tenant_id)
        .order_by(Document.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_document(
    db: AsyncSession,
    document_id: uuid.UUID,
    tenant_id: str,
) -> Document | None:
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def delete_document(
    db: AsyncSession,
    document_id: uuid.UUID,
    tenant_id: str,
) -> bool:
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.tenant_id == tenant_id,
        )
    )
    document = result.scalar_one_or_none()
    if not document:
        return False

    await storage_service.delete(document.b2_file_key)

    # Explicitly delete child rows in FK order (defense-in-depth alongside DB CASCADE)
    await db.execute(delete(BM25Stats).where(BM25Stats.document_id == document_id))
    await db.execute(delete(Chunk).where(Chunk.document_id == document_id))
    await db.execute(delete(DocumentTree).where(DocumentTree.document_id == document_id))

    await db.delete(document)
    await db.commit()
    return True


async def ensure_user_exists(
    db: AsyncSession,
    clerk_id: str,
    email: str,
    role: str = "user",
) -> User:
    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()
    if user:
        if user.role != role:
            user.role = role
            await db.commit()
        return user

    user = User(
        clerk_id=clerk_id,
        email=email,
        role=role,
        tenant_id=clerk_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
