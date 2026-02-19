"""Test configuration and fixtures.

DB isolation strategy: each test wraps its operations in an outer connection-level
transaction that is rolled back at the end. Session uses join_transaction_mode=
"create_savepoint" so that service-layer session.commit() calls emit
RELEASE SAVEPOINT instead of a real COMMIT, keeping everything inside the
outer transaction.

Requires: a running PostgreSQL with migrations applied
  docker compose up -d db
  alembic upgrade head
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.v1.auth import get_email_provider
from app.config import get_settings
from app.core.database import get_db
from app.main import app
from app.services.email.base import EmailProvider

settings = get_settings()


# ---------------------------------------------------------------------------
# Mock email provider
# ---------------------------------------------------------------------------


class MockEmailProvider(EmailProvider):
    """Captures sent emails instead of calling the real API."""

    def __init__(self) -> None:
        self.sent_verification: list[dict[str, str]] = []
        self.sent_reset: list[dict[str, str]] = []

    async def send_verification(self, to: str, code: str, couple_name: str) -> bool:
        self.sent_verification.append({"to": to, "code": code, "couple_name": couple_name})
        return True

    async def send_password_reset(self, to: str, code: str) -> bool:
        self.sent_reset.append({"to": to, "code": code})
        return True


# ---------------------------------------------------------------------------
# DB fixtures — transaction-level rollback for isolation
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, Any]:
    engine = create_async_engine(settings.DATABASE_URL, echo=False, poolclass=NullPool)
    conn = await engine.connect()
    trans = await conn.begin()

    session = AsyncSession(
        bind=conn,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    yield session

    await session.close()
    await trans.rollback()
    await conn.close()
    await engine.dispose()


# ---------------------------------------------------------------------------
# HTTP client + dependency overrides
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
def mock_email() -> MockEmailProvider:
    return MockEmailProvider()


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession, mock_email: MockEmailProvider
) -> AsyncGenerator[AsyncClient, Any]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, Any]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_email_provider] = lambda: mock_email

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
