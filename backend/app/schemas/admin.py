import uuid
from pydantic import BaseModel


class AdminStatsOut(BaseModel):
    total_users: int
    total_documents: int
    total_storage_bytes: int


class AdminUserOut(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    document_count: int
    created_at: str
