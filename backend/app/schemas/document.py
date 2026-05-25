import uuid
from datetime import datetime
from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    tenant_id: str
    filename: str
    b2_file_key: str
    content_type: str
    file_size_bytes: int
    status: str
    doc_metadata: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentStatusOut(BaseModel):
    id: uuid.UUID
    status: str
