import pytest
from fastapi import HTTPException

from app.auth.tenant import TenantContext


class TestTenantContext:
    def test_tenant_context_creation(self):
        ctx = TenantContext(user_id="user-1", tenant_id="tenant-1", role="user")
        assert ctx.user_id == "user-1"
        assert ctx.tenant_id == "tenant-1"
        assert ctx.role == "user"

    def test_tenant_context_admin(self):
        ctx = TenantContext(user_id="admin-1", tenant_id="admin-1", role="admin")
        assert ctx.role == "admin"
        assert ctx.tenant_id == "admin-1"


class TestRBAC:
    def test_admin_can_access(self, mock_admin_context):
        from app.auth.rbac import require_role
        dep = require_role("admin")
        result = dep(mock_admin_context)
        assert result.role == "admin"

    def test_user_cannot_access_admin(self, mock_tenant_context):
        from app.auth.rbac import require_role
        dep = require_role("admin")
        with pytest.raises(HTTPException) as exc_info:
            dep(mock_tenant_context)
        assert exc_info.value.status_code == 403
        assert "Admin access required" in exc_info.value.detail

    def test_non_admin_role_not_checked(self, mock_tenant_context):
        from app.auth.rbac import require_role
        dep = require_role("user")
        result = dep(mock_tenant_context)
        assert result.role == "user"
