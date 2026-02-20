from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.couple import CoupleStatus


class CoupleProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    couple_name: str
    anniversary_date: date | None
    avatar_url: str | None
    status: CoupleStatus
    days_together: int
    created_at: datetime
    updated_at: datetime | None


class CoupleUpdateRequest(BaseModel):
    couple_name: str | None = None
    anniversary_date: date | None = None
