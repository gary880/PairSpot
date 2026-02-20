"""P3 Couple Service — Profile, Update, Avatar."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.storage import delete_file, upload_file
from app.models.couple import Couple
from app.models.user import User
from app.schemas.couple import CoupleProfileResponse, CoupleUpdateRequest

settings = get_settings()


class CoupleService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_couple(self, couple_id: uuid.UUID, current_user: User) -> CoupleProfileResponse:
        couple = await self._get_couple_or_404(couple_id)
        self._assert_member(couple, current_user)
        return self._to_response(couple)

    async def update_couple(
        self, couple_id: uuid.UUID, current_user: User, data: CoupleUpdateRequest
    ) -> CoupleProfileResponse:
        couple = await self._get_couple_or_404(couple_id)
        self._assert_member(couple, current_user)

        if data.couple_name is not None:
            couple.couple_name = data.couple_name
        if data.anniversary_date is not None:
            couple.anniversary_date = data.anniversary_date

        await self.db.commit()
        await self.db.refresh(couple)
        return self._to_response(couple)

    async def upload_avatar(
        self, couple_id: uuid.UUID, current_user: User, file: UploadFile
    ) -> CoupleProfileResponse:
        couple = await self._get_couple_or_404(couple_id)
        self._assert_member(couple, current_user)

        # Delete old avatar if exists
        if couple.avatar_url:
            prefix = f"{settings.S3_ENDPOINT_URL}/{settings.S3_BUCKET_NAME}/"
            if couple.avatar_url.startswith(prefix):
                old_key = couple.avatar_url[len(prefix):]
                try:
                    await delete_file(old_key)
                except Exception:
                    pass  # Don't fail upload if old file deletion fails

        data = await file.read()
        content_type = file.content_type or "image/jpeg"
        key = f"couples/{couple_id}/avatar/{uuid.uuid4()}.jpg"
        avatar_url = await upload_file(data, key, content_type)

        couple.avatar_url = avatar_url
        await self.db.commit()
        await self.db.refresh(couple)
        return self._to_response(couple)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get_couple_or_404(self, couple_id: uuid.UUID) -> Couple:
        couple = (
            await self.db.execute(
                select(Couple).where(Couple.id == couple_id, Couple.deleted_at.is_(None))
            )
        ).scalar_one_or_none()
        if couple is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Couple not found")
        return couple

    def _assert_member(self, couple: Couple, current_user: User) -> None:
        if current_user.couple_id != couple.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this couple",
            )

    def _days_together(self, anniversary_date: date | None) -> int:
        if not anniversary_date:
            return 0
        return max(0, (date.today() - anniversary_date).days)

    def _to_response(self, couple: Couple) -> CoupleProfileResponse:
        return CoupleProfileResponse(
            id=couple.id,
            couple_name=couple.couple_name,
            anniversary_date=couple.anniversary_date,
            avatar_url=couple.avatar_url,
            status=couple.status,
            days_together=self._days_together(couple.anniversary_date),
            created_at=couple.created_at,
            updated_at=couple.updated_at,
        )
