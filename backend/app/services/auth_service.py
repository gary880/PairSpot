"""P1 Authentication Service — 情侶雙帳號驗證 + Apple Sign In + JWT."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.apple_auth import verify_apple_id_token
from app.core.security import create_access_token, hash_password, verify_password
from app.models import Couple, User
from app.models.auth import RefreshToken
from app.models.couple import CoupleStatus
from app.models.user import UserRole
from app.schemas.auth import (
    AppleLoginRequest,
    LoginRequest,
    LoginResponse,
    PasswordResetConfirmRequest,
    RegisterCompleteRequest,
    RegisterCompleteResponse,
    RegisterInitiateRequest,
    RegisterInitiateResponse,
    RegisterVerifyResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
)
from app.services.email.base import EmailProvider

settings = get_settings()

_VERIFICATION_TOKEN_TTL_HOURS = 24
_PASSWORD_RESET_TOKEN_TTL_HOURS = 2


def _hash_token(token: str) -> str:
    """SHA-256 hash of an opaque token for safe DB storage."""
    return hashlib.sha256(token.encode()).hexdigest()


class AuthService:
    def __init__(self, db: AsyncSession, email_provider: EmailProvider) -> None:
        self.db = db
        self.email_provider = email_provider

    # ------------------------------------------------------------------
    # Registration flow
    # ------------------------------------------------------------------

    async def register_initiate(self, data: RegisterInitiateRequest) -> RegisterInitiateResponse:
        """Step 1: Create couple + two unverified users, send verification emails."""
        email_a = str(data.email_a)
        email_b = str(data.email_b)

        if email_a == email_b:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Partner emails must be different",
            )

        # Reject already-registered emails
        for email in (email_a, email_b):
            result = await self.db.execute(
                select(User).where(User.email == email, User.deleted_at.is_(None))
            )
            if result.scalar_one_or_none() is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Email {email} is already registered",
                )

        # Create couple (status: pending)
        couple = Couple(
            couple_name=data.couple_name,
            anniversary_date=data.anniversary_date,
            status=CoupleStatus.PENDING,
        )
        self.db.add(couple)
        await self.db.flush()  # obtain couple.id

        token_a = secrets.token_urlsafe(32)
        token_b = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=_VERIFICATION_TOKEN_TTL_HOURS)

        user_a = User(
            couple_id=couple.id,
            email=email_a,
            display_name=email_a.split("@")[0],
            email_verified=False,
            role=UserRole.PARTNER_A,
            verification_token=token_a,
            verification_token_expires_at=expires_at,
        )
        user_b = User(
            couple_id=couple.id,
            email=email_b,
            display_name=email_b.split("@")[0],
            email_verified=False,
            role=UserRole.PARTNER_B,
            verification_token=token_b,
            verification_token_expires_at=expires_at,
        )
        self.db.add(user_a)
        self.db.add(user_b)
        await self.db.commit()

        # Send verification emails (failures are logged, not fatal)
        await self.email_provider.send_verification(
            to=email_a, code=token_a, couple_name=data.couple_name
        )
        await self.email_provider.send_verification(
            to=email_b, code=token_b, couple_name=data.couple_name
        )

        return RegisterInitiateResponse(
            couple_id=str(couple.id),
            message="Verification emails sent to both partners",
        )

    async def register_verify(self, token: str) -> RegisterVerifyResponse:
        """Step 2: Mark one user's email as verified."""
        result = await self.db.execute(
            select(User).where(
                User.verification_token == token,
                User.deleted_at.is_(None),
            )
        )
        user = result.scalar_one_or_none()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid verification token",
            )

        if user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already verified",
            )

        if (
            user.verification_token_expires_at is not None
            and user.verification_token_expires_at < datetime.now(timezone.utc)
        ):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Verification token has expired",
            )

        user.email_verified = True
        user.verification_token = None
        user.verification_token_expires_at = None
        await self.db.commit()

        # Check if the partner is also verified
        result = await self.db.execute(
            select(User).where(
                User.couple_id == user.couple_id,
                User.id != user.id,
                User.deleted_at.is_(None),
            )
        )
        partner = result.scalar_one_or_none()
        both_verified = partner is not None and partner.email_verified

        return RegisterVerifyResponse(
            email=user.email,
            verified=True,
            both_verified=both_verified,
        )

    async def register_complete(self, data: RegisterCompleteRequest) -> RegisterCompleteResponse:
        """Step 3: Set passwords + display names, activate couple."""
        try:
            couple_uuid = uuid.UUID(data.couple_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid couple_id format",
            ) from exc

        result = await self.db.execute(
            select(Couple).where(
                Couple.id == couple_uuid,
                Couple.status == CoupleStatus.PENDING,
                Couple.deleted_at.is_(None),
            )
        )
        couple = result.scalar_one_or_none()
        if couple is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Couple not found or already activated",
            )

        result = await self.db.execute(
            select(User).where(
                User.couple_id == couple.id,
                User.deleted_at.is_(None),
            )
        )
        users = result.scalars().all()

        user_a = next((u for u in users if u.role == UserRole.PARTNER_A), None)
        user_b = next((u for u in users if u.role == UserRole.PARTNER_B), None)

        if user_a is None or user_b is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Couple users not found",
            )

        if not user_a.email_verified or not user_b.email_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both partners must verify their email first",
            )

        user_a.password_hash = hash_password(data.password_a)
        user_a.display_name = data.display_name_a
        user_b.password_hash = hash_password(data.password_b)
        user_b.display_name = data.display_name_b
        couple.status = CoupleStatus.ACTIVE
        await self.db.commit()

        return RegisterCompleteResponse(
            couple_id=str(couple.id),
            message="Registration complete. You can now log in.",
        )

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    async def login(self, data: LoginRequest) -> LoginResponse:
        result = await self.db.execute(
            select(User).where(User.email == str(data.email), User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()

        # Use a generic error to prevent user enumeration
        _invalid = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

        if user is None or user.password_hash is None:
            raise _invalid

        if not verify_password(data.password, user.password_hash):
            raise _invalid

        if not user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not verified. Please check your inbox.",
            )

        await self._assert_couple_active(user.couple_id)
        return await self._issue_tokens(user)

    # ------------------------------------------------------------------
    # Token refresh
    # ------------------------------------------------------------------

    async def refresh_token(self, data: TokenRefreshRequest) -> TokenRefreshResponse:
        token_hash = _hash_token(data.refresh_token)

        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
        )
        stored = result.scalar_one_or_none()

        if stored is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked refresh token",
            )

        if stored.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired",
            )

        result = await self.db.execute(
            select(User).where(
                User.id == stored.user_id,
                User.deleted_at.is_(None),
            )
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        # Rotate: revoke the old token, issue new pair
        stored.revoked_at = datetime.now(timezone.utc)
        await self.db.flush()

        tokens = await self._issue_tokens(user)
        return TokenRefreshResponse(
            access_token=tokens.access_token,
            token_type=tokens.token_type,
        )

    # ------------------------------------------------------------------
    # Apple Sign In
    # ------------------------------------------------------------------

    async def apple_login(self, data: AppleLoginRequest) -> LoginResponse:
        """Verify Apple ID token; find or link the matching User."""
        try:
            payload = await verify_apple_id_token(data.identity_token, settings.APPLE_APP_BUNDLE_ID)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Apple ID token: {exc}",
            ) from exc

        apple_sub: str | None = payload.get("sub")
        apple_email: str | None = payload.get("email")

        if not apple_sub:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Apple token: missing sub claim",
            )

        # 1. Find by apple_sub
        result = await self.db.execute(
            select(User).where(User.apple_sub == apple_sub, User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()

        # 2. Fallback: find by email, then link the sub
        if user is None and apple_email:
            result = await self.db.execute(
                select(User).where(User.email == apple_email, User.deleted_at.is_(None))
            )
            user = result.scalar_one_or_none()
            if user is not None:
                user.apple_sub = apple_sub
                await self.db.flush()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No account found for this Apple ID. Please register first.",
            )

        await self._assert_couple_active(user.couple_id)
        return await self._issue_tokens(user)

    # ------------------------------------------------------------------
    # Password reset
    # ------------------------------------------------------------------

    async def request_password_reset(self, email: str) -> None:
        result = await self.db.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()

        # Always return success to avoid user enumeration
        if user is None:
            return

        reset_token = secrets.token_urlsafe(32)
        user.password_reset_token = reset_token
        user.password_reset_expires_at = datetime.now(timezone.utc) + timedelta(
            hours=_PASSWORD_RESET_TOKEN_TTL_HOURS
        )
        await self.db.commit()
        await self.email_provider.send_password_reset(to=email, code=reset_token)

    async def confirm_password_reset(self, data: PasswordResetConfirmRequest) -> None:
        result = await self.db.execute(
            select(User).where(
                User.password_reset_token == data.token,
                User.deleted_at.is_(None),
            )
        )
        user = result.scalar_one_or_none()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid password reset token",
            )

        if user.password_reset_expires_at is None or user.password_reset_expires_at < datetime.now(
            timezone.utc
        ):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Password reset token has expired",
            )

        user.password_hash = hash_password(data.new_password)
        user.password_reset_token = None
        user.password_reset_expires_at = None
        await self.db.commit()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _assert_couple_active(self, couple_id: uuid.UUID) -> None:
        result = await self.db.execute(select(Couple).where(Couple.id == couple_id))
        couple = result.scalar_one_or_none()
        if couple is None or couple.status != CoupleStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account not fully activated",
            )

    async def _issue_tokens(self, user: User) -> LoginResponse:
        """Create an access token (JWT) + opaque refresh token (stored as hash)."""
        token_data = {
            "sub": str(user.id),
            "couple_id": str(user.couple_id),
            "role": user.role.value,
        }
        access_token = create_access_token(token_data)

        raw_refresh = secrets.token_urlsafe(32)
        refresh_record = RefreshToken(
            user_id=user.id,
            token_hash=_hash_token(raw_refresh),
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        self.db.add(refresh_record)
        await self.db.commit()

        return LoginResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            token_type="bearer",
        )
