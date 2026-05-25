import uuid
from datetime import datetime
from pydantic import BaseModel


class ChatMessageOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    citations: list = []
    retrieval_metadata: dict = {}
    from_cache: bool = False
    token_count: int | None = None
    evaluation: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    tenant_id: str
    document_id: uuid.UUID | None = None
    title: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionDetailOut(ChatSessionOut):
    messages: list[ChatMessageOut] = []


class CreateChatSessionIn(BaseModel):
    document_id: uuid.UUID | None = None
    title: str | None = None


class SendMessageIn(BaseModel):
    content: str
