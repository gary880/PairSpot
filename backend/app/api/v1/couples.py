"""P3 Couples API — Profile, Update, Avatar."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import CurrentUser
from app.schemas.couple import CoupleProfileResponse, CoupleUpdateRequest
from app.services.couple_service import CoupleService

router = APIRouter()


def get_couple_service(db: Annotated[AsyncSession, Depends(get_db)]) -> CoupleService:
    return CoupleService(db)


@router.get(
    "/{couple_id}",
    response_model=CoupleProfileResponse,
    summary="取得情侶檔案（含 days_together）",
)
async def get_couple(
    couple_id: uuid.UUID,
    current_user: CurrentUser,
    service: Annotated[CoupleService, Depends(get_couple_service)],
) -> CoupleProfileResponse:
    return await service.get_couple(couple_id, current_user)


@router.patch(
    "/{couple_id}",
    response_model=CoupleProfileResponse,
    summary="更新情侶名稱或紀念日",
)
async def update_couple(
    couple_id: uuid.UUID,
    data: CoupleUpdateRequest,
    current_user: CurrentUser,
    service: Annotated[CoupleService, Depends(get_couple_service)],
) -> CoupleProfileResponse:
    return await service.update_couple(couple_id, current_user, data)


@router.put(
    "/{couple_id}/avatar",
    response_model=CoupleProfileResponse,
    summary="上傳情侶頭貼（multipart）",
)
async def upload_avatar(
    couple_id: uuid.UUID,
    current_user: CurrentUser,
    service: Annotated[CoupleService, Depends(get_couple_service)],
    file: UploadFile = File(...),
) -> CoupleProfileResponse:
    return await service.upload_avatar(couple_id, current_user, file)
