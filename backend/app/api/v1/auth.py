from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.post("/register/initiate")
async def register_initiate() -> dict[str, str]:
    """
    Phase 1: Initiate couple registration.
    Creates couple and two users, sends verification emails.
    """
    # TODO: Implement in Phase 1
    return {"status": "not_implemented"}


@router.post("/register/verify")
async def register_verify() -> dict[str, str]:
    """Verify email token."""
    # TODO: Implement in Phase 1
    return {"status": "not_implemented"}


@router.post("/register/complete")
async def register_complete() -> dict[str, str]:
    """Complete registration after both emails verified."""
    # TODO: Implement in Phase 1
    return {"status": "not_implemented"}


@router.post("/login")
async def login() -> dict[str, str]:
    """Login with email and password."""
    # TODO: Implement in Phase 1
    return {"status": "not_implemented"}


@router.post("/token/refresh")
async def token_refresh() -> dict[str, str]:
    """Refresh access token."""
    # TODO: Implement in Phase 1
    return {"status": "not_implemented"}
