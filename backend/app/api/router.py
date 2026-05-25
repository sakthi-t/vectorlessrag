from fastapi import APIRouter

from app.api import documents, chat, users, admin

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(documents.router)
api_router.include_router(chat.router)
api_router.include_router(users.router)
api_router.include_router(admin.router)
