import uuid
import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException

from app.services.admin_service import delete_user_from_clerk
from app.models.user import User


class TestAdminService:
    @pytest.mark.asyncio
    async def test_delete_user_from_clerk_no_secret(self):
        with patch("app.services.admin_service.settings") as mock_settings:
            mock_settings.CLERK_SECRET_KEY = ""
            result = await delete_user_from_clerk("clerk_123")
            assert result is False

    @pytest.mark.asyncio
    async def test_delete_user_from_clerk_success(self):
        with patch("app.services.admin_service.settings") as mock_settings:
            with patch("app.services.admin_service.httpx.AsyncClient") as mock_client:
                mock_settings.CLERK_SECRET_KEY = "sk_test"
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_client.return_value.__aenter__.return_value.delete.return_value = mock_response
                result = await delete_user_from_clerk("clerk_123")
                assert result is True

    @pytest.mark.asyncio
    async def test_delete_user_from_clerk_failure(self):
        with patch("app.services.admin_service.settings") as mock_settings:
            with patch("app.services.admin_service.httpx.AsyncClient") as mock_client:
                mock_settings.CLERK_SECRET_KEY = "sk_test"
                mock_response = AsyncMock()
                mock_response.status_code = 404
                mock_client.return_value.__aenter__.return_value.delete.return_value = mock_response
                result = await delete_user_from_clerk("clerk_does_not_exist")
                assert result is False

    @pytest.mark.asyncio
    async def test_admin_delete_user_not_found(self):
        from app.services.admin_service import admin_delete_user
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)
        result = await admin_delete_user(mock_db, uuid.uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_admin_delete_user_success(self):
        from unittest.mock import MagicMock
        from app.services.admin_service import admin_delete_user
        uid = uuid.uuid4()
        mock_user = MagicMock(spec=User)
        mock_user.id = uid
        mock_user.clerk_id = "clerk_test_123"
        mock_user.email = "test@example.com"
        mock_user.tenant_id = "test-tenant"
        mock_user.role = "user"

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=mock_user)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.delete = AsyncMock()

        with patch("app.services.admin_service.delete_user_from_clerk", new_callable=AsyncMock) as mock_clerk:
            mock_clerk.return_value = True
            result = await admin_delete_user(mock_db, uid)
            assert result is True
            mock_clerk.assert_called_once_with("clerk_test_123")


class TestAdminAPI:
    def test_admin_stats_requires_admin_role(self, mock_tenant_context):
        from app.api.admin import _require_admin
        with pytest.raises(HTTPException) as exc_info:
            _require_admin(mock_tenant_context)
        assert exc_info.value.status_code == 403

    def test_admin_list_users_requires_admin(self, mock_tenant_context):
        from app.api.admin import _require_admin
        with pytest.raises(HTTPException) as exc_info:
            _require_admin(mock_tenant_context)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_delete_self_blocked(self, mock_admin_context):
        from app.api.admin import admin_delete_user_endpoint
        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await admin_delete_user_endpoint(
                str(mock_admin_context.user_id),
                mock_admin_context,
                mock_db,
            )
        assert exc_info.value.status_code == 400
        assert "Cannot delete yourself" in exc_info.value.detail
