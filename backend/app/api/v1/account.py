"""P3 Account API — Get, Update, Soft Delete, Restore."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import CurrentUser, CurrentUserAllowDeleted
from app.schemas.account import AccountUpdateRequest, UserAccountResponse
from app.services.account_service import AccountService

router = APIRouter()


def get_account_service(db: Annotated[AsyncSession, Depends(get_db)]) -> AccountService:
    return AccountService(db)


@router.get(
    "",
    response_model=UserAccountResponse,
    summary="取得我的帳號資訊",
)
async def get_account(
    current_user: CurrentUser,
    service: Annotated[AccountService, Depends(get_account_service)],
) -> UserAccountResponse:
    return await service.get_account(current_user)


@router.patch(
    "",
    response_model=UserAccountResponse,
    summary="更新 display_name",
)
async def update_account(
    data: AccountUpdateRequest,
    current_user: CurrentUser,
    service: Annotated[AccountService, Depends(get_account_service)],
) -> UserAccountResponse:
    return await service.update_account(current_user, data)


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="軟刪除帳號（+ couple 降為 SINGLE）",
)
async def delete_account(
    current_user: CurrentUser,
    service: Annotated[AccountService, Depends(get_account_service)],
) -> None:
    await service.delete_account(current_user)


@router.post(
    "/restore",
    response_model=UserAccountResponse,
    summary="30 天內恢復帳號",
)
async def restore_account(
    current_user: CurrentUserAllowDeleted,
    service: Annotated[AccountService, Depends(get_account_service)],
) -> UserAccountResponse:
    return await service.restore_account(current_user)
