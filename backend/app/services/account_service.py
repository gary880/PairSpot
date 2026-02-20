"""P3 Account Service — Get, Update, Soft Delete, Restore."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.couple import Couple, CoupleStatus
from app.models.user import User
from app.schemas.account import AccountUpdateRequest, UserAccountResponse

_RESTORE_WINDOW_DAYS = 30


class AccountService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_account(self, current_user: User) -> UserAccountResponse:
        return UserAccountResponse.model_validate(current_user)

    async def update_account(
        self, current_user: User, data: AccountUpdateRequest
    ) -> UserAccountResponse:
        if data.display_name is not None:
            current_user.display_name = data.display_name
        await self.db.commit()
        await self.db.refresh(current_user)
        return UserAccountResponse.model_validate(current_user)

    async def delete_account(self, current_user: User) -> None:
        current_user.deleted_at = datetime.now(timezone.utc)

        if current_user.couple_id is not None:
            couple = await self.db.get(Couple, current_user.couple_id)
            if couple is not None and couple.status == CoupleStatus.ACTIVE:
                couple.status = CoupleStatus.SINGLE

        await self.db.commit()

    async def restore_account(self, current_user: User) -> UserAccountResponse:
        if current_user.deleted_at is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account is not deleted",
            )

        deleted_at = current_user.deleted_at
        if deleted_at.tzinfo is None:
            deleted_at = deleted_at.replace(tzinfo=timezone.utc)

        delta = datetime.now(timezone.utc) - deleted_at
        if delta.days > _RESTORE_WINDOW_DAYS:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Restoration window expired (>30 days)",
            )

        current_user.deleted_at = None

        # Restore couple status if partner is still active
        if current_user.couple_id is not None:
            couple = await self.db.get(Couple, current_user.couple_id)
            if couple is not None and couple.status == CoupleStatus.SINGLE:
                # Check if partner is also not deleted
                partner = (
                    await self.db.execute(
                        select(User).where(
                            User.couple_id == current_user.couple_id,
                            User.id != current_user.id,
                            User.deleted_at.is_(None),
                        )
                    )
                ).scalar_one_or_none()
                if partner is not None:
                    couple.status = CoupleStatus.ACTIVE

        await self.db.commit()
        await self.db.refresh(current_user)
        return UserAccountResponse.model_validate(current_user)
