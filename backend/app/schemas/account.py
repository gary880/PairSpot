from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.user import UserRole


class UserAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    role: UserRole
    email_verified: bool
    created_at: datetime
    updated_at: datetime | None


class AccountUpdateRequest(BaseModel):
    display_name: str | None = None
