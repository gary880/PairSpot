from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.post import PostVisibility, ReportReason


class PostImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    image_url: str
    thumbnail_url: str | None
    sort_order: int
    width: int | None
    height: int | None


class PostAuthorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    display_name: str
    role: str


class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    couple_id: uuid.UUID
    author_id: uuid.UUID
    author: PostAuthorResponse
    content: str | None
    visibility: PostVisibility
    is_promoted: bool
    promoted_until: datetime | None
    like_count: int
    liked_by_me: bool = False
    images: list[PostImageResponse]
    created_at: datetime
    updated_at: datetime | None


class PostUpdateRequest(BaseModel):
    content: str | None = None
    visibility: PostVisibility | None = None


class FeedResponse(BaseModel):
    items: list[PostResponse]
    total: int
    offset: int
    limit: int


class LikeResponse(BaseModel):
    liked: bool
    like_count: int


class ReportRequest(BaseModel):
    reason: ReportReason
    description: str | None = None
