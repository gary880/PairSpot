from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.couple import Couple
    from app.models.post import Like, Post
    from app.models.wallet import CoinTransaction, UserWallet


class UserRole(str, enum.Enum):
    PARTNER_A = "partner_a"
    PARTNER_B = "partner_b"


class User(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    couple_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("couples.id"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)

    # Email verification token (for registration flow)
    verification_token: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    couple: Mapped[Couple] = relationship("Couple", back_populates="users")
    posts: Mapped[list[Post]] = relationship("Post", back_populates="author")
    likes: Mapped[list[Like]] = relationship("Like", back_populates="user")
    wallet: Mapped[UserWallet | None] = relationship(
        "UserWallet", back_populates="user", uselist=False
    )
    transactions: Mapped[list[CoinTransaction]] = relationship(
        "CoinTransaction", back_populates="user"
    )
