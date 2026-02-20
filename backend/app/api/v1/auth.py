from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.auth import (
    AppleLoginRequest,
    LoginRequest,
    LoginResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RegisterCompleteRequest,
    RegisterCompleteResponse,
    RegisterInitiateRequest,
    RegisterInitiateResponse,
    RegisterVerifyRequest,
    RegisterVerifyResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
)
from app.services.auth_service import AuthService
from app.services.email.base import EmailProvider
from app.services.email.console_provider import ConsoleEmailProvider
from app.services.email.resend_provider import ResendProvider

router = APIRouter()


def get_email_provider() -> EmailProvider:
    from app.config import get_settings

    settings = get_settings()
    if settings.ENV == "development":
        return ConsoleEmailProvider()
    return ResendProvider()


async def get_auth_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    email_provider: Annotated[EmailProvider, Depends(get_email_provider)],
) -> AuthService:
    return AuthService(db=db, email_provider=email_provider)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


@router.post(
    "/register/initiate",
    response_model=RegisterInitiateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Step 1 — 建立情侶帳號並寄送雙方驗證信",
)
async def register_initiate(
    data: RegisterInitiateRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> RegisterInitiateResponse:
    return await service.register_initiate(data)


@router.post(
    "/register/verify",
    response_model=RegisterVerifyResponse,
    summary="Step 2 — 點擊驗證連結，標記 email 已驗證",
)
async def register_verify(
    data: RegisterVerifyRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> RegisterVerifyResponse:
    return await service.register_verify(data.token)


@router.post(
    "/register/complete",
    response_model=RegisterCompleteResponse,
    summary="Step 3 — 雙方驗證完成後設定密碼，啟動帳號",
)
async def register_complete(
    data: RegisterCompleteRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> RegisterCompleteResponse:
    return await service.register_complete(data)


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="以 Email + 密碼登入，取得 JWT",
)
async def login(
    data: LoginRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> LoginResponse:
    return await service.login(data)


@router.post(
    "/token/refresh",
    response_model=TokenRefreshResponse,
    summary="以 Refresh Token 換取新 Access Token（Token Rotation）",
)
async def token_refresh(
    data: TokenRefreshRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenRefreshResponse:
    return await service.refresh_token(data)


# ---------------------------------------------------------------------------
# Apple Sign In
# ---------------------------------------------------------------------------


@router.post(
    "/apple/login",
    response_model=LoginResponse,
    summary="Apple Sign In — 驗證 Apple ID Token，取得 JWT",
)
async def apple_login(
    data: AppleLoginRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> LoginResponse:
    return await service.apple_login(data)


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------


@router.post(
    "/password/reset",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="請求重設密碼（寄送重設信）",
)
async def password_reset(
    data: PasswordResetRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    await service.request_password_reset(str(data.email))


@router.post(
    "/password/reset/confirm",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="以重設 Token + 新密碼完成重設",
)
async def password_reset_confirm(
    data: PasswordResetConfirmRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> None:
    await service.confirm_password_reset(data)
