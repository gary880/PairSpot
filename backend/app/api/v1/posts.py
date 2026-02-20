"""P2 Posts API — CRUD, Feed, Like, Report."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import CurrentUser
from app.models.post import PostVisibility
from app.schemas.post import (
    FeedResponse,
    LikeResponse,
    PostResponse,
    PostUpdateRequest,
    ReportRequest,
)
from app.services.post_service import PostService

router = APIRouter()


def get_post_service(db: Annotated[AsyncSession, Depends(get_db)]) -> PostService:
    return PostService(db)


# ---------------------------------------------------------------------------
# Feed
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=FeedResponse,
    summary="取得 Feed（分頁，promoted 優先）",
)
async def get_feed(
    current_user: CurrentUser,
    service: Annotated[PostService, Depends(get_post_service)],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> FeedResponse:
    return await service.get_feed(current_user, offset, limit)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="建立貼文（multipart: 圖片+文字）",
)
async def create_post(
    current_user: CurrentUser,
    service: Annotated[PostService, Depends(get_post_service)],
    content: str | None = Form(default=None),
    visibility: PostVisibility = Form(default=PostVisibility.PUBLIC),
    images: list[UploadFile] = File(default=[]),
) -> PostResponse:
    return await service.create_post(current_user, content, visibility, images)


# ---------------------------------------------------------------------------
# Get / Update / Delete
# ---------------------------------------------------------------------------


@router.get(
    "/{post_id}",
    response_model=PostResponse,
    summary="取得單篇貼文",
)
async def get_post(
    post_id: uuid.UUID,
    current_user: CurrentUser,
    service: Annotated[PostService, Depends(get_post_service)],
) -> PostResponse:
    return await service.get_post(post_id, current_user)


@router.patch(
    "/{post_id}",
    response_model=PostResponse,
    summary="編輯貼文（僅 author）",
)
async def update_post(
    post_id: uuid.UUID,
    data: PostUpdateRequest,
    current_user: CurrentUser,
    service: Annotated[PostService, Depends(get_post_service)],
) -> PostResponse:
    return await service.update_post(post_id, current_user, data)


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="刪除貼文（soft delete）",
)
async def delete_post(
    post_id: uuid.UUID,
    current_user: CurrentUser,
    service: Annotated[PostService, Depends(get_post_service)],
) -> None:
    await service.delete_post(post_id, current_user)


# ---------------------------------------------------------------------------
# Like / Unlike
# ---------------------------------------------------------------------------


@router.post(
    "/{post_id}/like",
    response_model=LikeResponse,
    summary="按讚",
)
async def like_post(
    post_id: uuid.UUID,
    current_user: CurrentUser,
    service: Annotated[PostService, Depends(get_post_service)],
) -> LikeResponse:
    return await service.like_post(post_id, current_user)


@router.delete(
    "/{post_id}/like",
    response_model=LikeResponse,
    summary="取消讚",
)
async def unlike_post(
    post_id: uuid.UUID,
    current_user: CurrentUser,
    service: Annotated[PostService, Depends(get_post_service)],
) -> LikeResponse:
    return await service.unlike_post(post_id, current_user)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


@router.post(
    "/{post_id}/report",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="檢舉貼文",
)
async def report_post(
    post_id: uuid.UUID,
    data: ReportRequest,
    current_user: CurrentUser,
    service: Annotated[PostService, Depends(get_post_service)],
) -> None:
    await service.report_post(post_id, current_user, data.reason, data.description)
