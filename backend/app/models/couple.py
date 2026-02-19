from __future__ import annotations

import enum
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.post import Post
    from app.models.user import User


class CoupleStatus(str, enum.Enum):
    PENDING = "pending"  # 等待双方验证
    ACTIVE = "active"  # 双方已验证，正常状态
    SUSPENDED = "suspended"  # 被暂停
    SINGLE = "single"  # 解绑后（一方离开）


class Couple(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "couples"

    couple_name: Mapped[str] = mapped_column(String(100), nullable=False)
    anniversary_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[CoupleStatus] = mapped_column(
        Enum(CoupleStatus),
        default=CoupleStatus.PENDING,
        nullable=False,
    )

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="couple")
    posts: Mapped[list["Post"]] = relationship("Post", back_populates="couple")
