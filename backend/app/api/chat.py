from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from datetime import datetime, timezone

from app.db.session import get_db
from app.auth.tenant import TenantContext, get_tenant_context
from app.schemas.chat import (
    ChatSessionOut,
    ChatSessionDetailOut,
    ChatMessageOut,
    CreateChatSessionIn,
    SendMessageIn,
)
from app.models.chat import ChatSession, ChatMessage
from app.models.document import Document
from app.services.chat_service import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


def _message_to_out(msg: ChatMessage) -> ChatMessageOut:
    citations = msg.citations if isinstance(msg.citations, list) else []
    retrieval_meta = msg.retrieval_metadata if isinstance(msg.retrieval_metadata, dict) else {}
    evaluation = msg.evaluation if isinstance(msg.evaluation, dict) else None
    return ChatMessageOut(
        id=msg.id,
        session_id=msg.session_id,
        role=msg.role,
        content=msg.content,
        citations=citations,
        retrieval_metadata=retrieval_meta,
        from_cache=bool(msg.from_cache),
        token_count=msg.token_count,
        evaluation=evaluation,
        created_at=msg.created_at,
    )


@router.post("/sessions", response_model=ChatSessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: CreateChatSessionIn,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    if body.document_id:
        result = await db.execute(
            select(Document).where(
                Document.id == body.document_id,
                Document.tenant_id == ctx.tenant_id,
            )
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

    session = ChatSession(
        user_id=ctx.user_id,
        tenant_id=ctx.tenant_id,
        document_id=body.document_id,
        title=body.title,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/sessions", response_model=list[ChatSessionOut])
async def list_sessions(
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.tenant_id == ctx.tenant_id)
        .order_by(ChatSession.updated_at.desc())
    )
    return list(result.scalars().all())


@router.get("/sessions/{session_id}", response_model=ChatSessionDetailOut)
async def get_session(
    session_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid session ID")

    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == sid,
            ChatSession.tenant_id == ctx.tenant_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    messages_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == sid)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = list(messages_result.scalars().all())

    return ChatSessionDetailOut(
        id=session.id,
        user_id=session.user_id,
        tenant_id=session.tenant_id,
        document_id=session.document_id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[_message_to_out(m) for m in messages],
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid session ID")

    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == sid,
            ChatSession.tenant_id == ctx.tenant_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    msg_result = await db.execute(
        select(ChatMessage).where(ChatMessage.session_id == sid)
    )
    for msg in msg_result.scalars().all():
        await db.delete(msg)

    await db.delete(session)
    await db.commit()


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageOut)
async def send_message(
    session_id: str,
    body: SendMessageIn,
    ctx: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid session ID")

    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == sid,
            ChatSession.tenant_id == ctx.tenant_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if not session.document_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This session is not associated with a document",
        )

    doc_result = await db.execute(
        select(Document).where(
            Document.id == session.document_id,
            Document.tenant_id == ctx.tenant_id,
        )
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Associated document not found")
    if document.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document is not ready for chat (status: {document.status})",
        )

    assistant_msg = await chat_service.handle_message(
        db=db,
        session_id=sid,
        user_message_content=body.content,
        document_id=session.document_id,
        tenant_id=ctx.tenant_id,
    )

    session.updated_at = assistant_msg.created_at
    await db.commit()

    return _message_to_out(assistant_msg)
