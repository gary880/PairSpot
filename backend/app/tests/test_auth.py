from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_initiate_placeholder(client: AsyncClient) -> None:
    """Test register initiate endpoint (placeholder for Phase 1)."""
    response = await client.post("/api/v1/auth/register/initiate")
    assert response.status_code == 200
    assert response.json()["status"] == "not_implemented"


@pytest.mark.asyncio
async def test_login_placeholder(client: AsyncClient) -> None:
    """Test login endpoint (placeholder for Phase 1)."""
    response = await client.post("/api/v1/auth/login")
    assert response.status_code == 200
    assert response.json()["status"] == "not_implemented"
