import pytest
import pytest_asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.auth.tenant import TenantContext
from app.config import settings


@pytest.fixture
def mock_tenant_context():
    return TenantContext(
        user_id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        role="user",
    )


@pytest.fixture
def mock_admin_context():
    return TenantContext(
        user_id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        role="admin",
    )
