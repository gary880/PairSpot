"""P1 Authentication — comprehensive test suite.

Test coverage:
  - Registration: initiate → verify → complete (happy path + all error cases)
  - Login: success + wrong password + unverified + inactive couple
  - Token refresh: success + invalid + expired + rotation
  - Password reset: request + confirm + expired + invalid token
  - Apple Sign In: success (by sub / by email) + unknown user + bad token
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models import Couple, User
from app.models.auth import RefreshToken
from app.models.couple import CoupleStatus
from app.models.user import UserRole
from app.tests.conftest import MockEmailProvider

BASE = "/api/v1/auth"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _initiate_payload(**kwargs: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "email_a": "alice@example.com",
        "email_b": "bob@example.com",
        "couple_name": "Alice & Bob",
        "anniversary_date": "2024-02-14",
    }
    defaults.update(kwargs)
    return defaults


async def _create_active_couple(
    db: AsyncSession,
    email_a: str = "alice@example.com",
    email_b: str = "bob@example.com",
    password_a: str = "securepass1",
    password_b: str = "securepass2",
    couple_name: str = "Test Couple",
) -> tuple[Couple, User, User]:
    """Directly insert an active couple into the DB (bypasses API)."""
    couple = Couple(
        couple_name=couple_name,
        status=CoupleStatus.ACTIVE,
    )
    db.add(couple)
    await db.flush()

    user_a = User(
        couple_id=couple.id,
        email=email_a,
        display_name="Alice",
        email_verified=True,
        role=UserRole.PARTNER_A,
        password_hash=hash_password(password_a),
    )
    user_b = User(
        couple_id=couple.id,
        email=email_b,
        display_name="Bob",
        email_verified=True,
        role=UserRole.PARTNER_B,
        password_hash=hash_password(password_b),
    )
    db.add(user_a)
    db.add(user_b)
    await db.commit()
    return couple, user_a, user_b


# ===========================================================================
# Registration — Initiate
# ===========================================================================


async def test_register_initiate_success(
    client: AsyncClient, mock_email: MockEmailProvider
) -> None:
    resp = await client.post(BASE + "/register/initiate", json=_initiate_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert "couple_id" in body
    # Two verification emails must have been sent
    assert len(mock_email.sent_verification) == 2
    recipients = {e["to"] for e in mock_email.sent_verification}
    assert recipients == {"alice@example.com", "bob@example.com"}


async def test_register_initiate_same_email_rejected(client: AsyncClient) -> None:
    resp = await client.post(
        BASE + "/register/initiate",
        json=_initiate_payload(email_b="alice@example.com"),
    )
    assert resp.status_code == 400
    assert "different" in resp.json()["detail"]


async def test_register_initiate_duplicate_email(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    # Pre-create a user with email_a
    couple = Couple(couple_name="Existing", status=CoupleStatus.ACTIVE)
    db_session.add(couple)
    await db_session.flush()
    existing = User(
        couple_id=couple.id,
        email="alice@example.com",
        display_name="Alice",
        email_verified=True,
        role=UserRole.PARTNER_A,
    )
    db_session.add(existing)
    await db_session.commit()

    resp = await client.post(BASE + "/register/initiate", json=_initiate_payload())
    assert resp.status_code == 409
    assert "alice@example.com" in resp.json()["detail"]


async def test_register_initiate_empty_couple_name(client: AsyncClient) -> None:
    resp = await client.post(
        BASE + "/register/initiate", json=_initiate_payload(couple_name="   ")
    )
    assert resp.status_code == 422


# ===========================================================================
# Registration — Verify
# ===========================================================================


async def test_register_verify_success(
    client: AsyncClient, mock_email: MockEmailProvider
) -> None:
    # Initiate first
    resp = await client.post(BASE + "/register/initiate", json=_initiate_payload())
    assert resp.status_code == 201

    # Verify user_a
    token_a = mock_email.sent_verification[0]["code"]
    resp = await client.post(BASE + "/register/verify", json={"token": token_a})
    assert resp.status_code == 200
    body = resp.json()
    assert body["verified"] is True
    assert body["both_verified"] is False  # user_b not yet verified

    # Verify user_b
    token_b = mock_email.sent_verification[1]["code"]
    resp = await client.post(BASE + "/register/verify", json={"token": token_b})
    assert resp.status_code == 200
    body = resp.json()
    assert body["verified"] is True
    assert body["both_verified"] is True


async def test_register_verify_invalid_token(client: AsyncClient) -> None:
    resp = await client.post(
        BASE + "/register/verify", json={"token": "totally_invalid_token"}
    )
    assert resp.status_code == 404


async def test_register_verify_already_verified(
    client: AsyncClient, mock_email: MockEmailProvider
) -> None:
    await client.post(BASE + "/register/initiate", json=_initiate_payload())
    token_a = mock_email.sent_verification[0]["code"]

    # First verify — should succeed
    resp = await client.post(BASE + "/register/verify", json={"token": token_a})
    assert resp.status_code == 200

    # Second verify — same token, should be gone
    resp = await client.post(BASE + "/register/verify", json={"token": token_a})
    assert resp.status_code == 404  # token was cleared


async def test_register_verify_expired_token(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    couple = Couple(couple_name="Exp Couple", status=CoupleStatus.PENDING)
    db_session.add(couple)
    await db_session.flush()

    expired_token = secrets.token_urlsafe(32)
    user = User(
        couple_id=couple.id,
        email="expire@example.com",
        display_name="Expire",
        email_verified=False,
        role=UserRole.PARTNER_A,
        verification_token=expired_token,
        verification_token_expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    db_session.add(user)
    await db_session.commit()

    resp = await client.post(BASE + "/register/verify", json={"token": expired_token})
    assert resp.status_code == 410


# ===========================================================================
# Registration — Complete
# ===========================================================================


async def _full_register(
    client: AsyncClient, mock_email: MockEmailProvider
) -> dict[str, Any]:
    """Run the full initiate → verify → complete flow, return complete response."""
    init_resp = await client.post(BASE + "/register/initiate", json=_initiate_payload())
    assert init_resp.status_code == 201
    couple_id = init_resp.json()["couple_id"]

    for email_record in mock_email.sent_verification:
        resp = await client.post(
            BASE + "/register/verify", json={"token": email_record["code"]}
        )
        assert resp.status_code == 200

    complete_resp = await client.post(
        BASE + "/register/complete",
        json={
            "couple_id": couple_id,
            "password_a": "password_alice_1",
            "password_b": "password_bob_1",
            "display_name_a": "Alice",
            "display_name_b": "Bob",
        },
    )
    return complete_resp.json() | {"couple_id": couple_id}


async def test_register_complete_success(
    client: AsyncClient, mock_email: MockEmailProvider
) -> None:
    result = await _full_register(client, mock_email)
    # complete endpoint returns 200 with message
    assert "couple_id" in result
    assert "message" in result


async def test_register_complete_not_both_verified(
    client: AsyncClient, mock_email: MockEmailProvider
) -> None:
    init_resp = await client.post(BASE + "/register/initiate", json=_initiate_payload())
    couple_id = init_resp.json()["couple_id"]

    # Only verify one partner
    token_a = mock_email.sent_verification[0]["code"]
    await client.post(BASE + "/register/verify", json={"token": token_a})

    resp = await client.post(
        BASE + "/register/complete",
        json={
            "couple_id": couple_id,
            "password_a": "password123",
            "password_b": "password456",
            "display_name_a": "Alice",
            "display_name_b": "Bob",
        },
    )
    assert resp.status_code == 400
    assert "verify" in resp.json()["detail"].lower()


async def test_register_complete_invalid_couple_id(client: AsyncClient) -> None:
    resp = await client.post(
        BASE + "/register/complete",
        json={
            "couple_id": "not-a-uuid",
            "password_a": "password123",
            "password_b": "password456",
            "display_name_a": "A",
            "display_name_b": "B",
        },
    )
    assert resp.status_code == 400


async def test_register_complete_unknown_couple_id(client: AsyncClient) -> None:
    import uuid

    resp = await client.post(
        BASE + "/register/complete",
        json={
            "couple_id": str(uuid.uuid4()),
            "password_a": "password123",
            "password_b": "password456",
            "display_name_a": "A",
            "display_name_b": "B",
        },
    )
    assert resp.status_code == 404


async def test_register_complete_password_too_short(
    client: AsyncClient, mock_email: MockEmailProvider
) -> None:
    init_resp = await client.post(BASE + "/register/initiate", json=_initiate_payload())
    couple_id = init_resp.json()["couple_id"]
    for e in mock_email.sent_verification:
        await client.post(BASE + "/register/verify", json={"token": e["code"]})

    resp = await client.post(
        BASE + "/register/complete",
        json={
            "couple_id": couple_id,
            "password_a": "short",  # < 8 chars
            "password_b": "password456",
            "display_name_a": "A",
            "display_name_b": "B",
        },
    )
    assert resp.status_code == 422


# ===========================================================================
# Login
# ===========================================================================


async def test_login_success(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_active_couple(db_session)
    resp = await client.post(
        BASE + "/login", json={"email": "alice@example.com", "password": "securepass1"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


async def test_login_wrong_password(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_active_couple(db_session)
    resp = await client.post(
        BASE + "/login", json={"email": "alice@example.com", "password": "wrong_pass"}
    )
    assert resp.status_code == 401


async def test_login_unknown_email(client: AsyncClient) -> None:
    resp = await client.post(
        BASE + "/login", json={"email": "nobody@example.com", "password": "password123"}
    )
    assert resp.status_code == 401
    # Must NOT reveal whether the email exists
    assert resp.json()["detail"] == "Invalid email or password"


async def test_login_email_not_verified(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    couple = Couple(couple_name="Unverified", status=CoupleStatus.PENDING)
    db_session.add(couple)
    await db_session.flush()
    user = User(
        couple_id=couple.id,
        email="unverified@example.com",
        display_name="UV",
        email_verified=False,
        role=UserRole.PARTNER_A,
        password_hash=hash_password("password123"),
    )
    db_session.add(user)
    await db_session.commit()

    resp = await client.post(
        BASE + "/login",
        json={"email": "unverified@example.com", "password": "password123"},
    )
    assert resp.status_code == 403
    assert "verif" in resp.json()["detail"].lower()


async def test_login_couple_not_active(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    couple = Couple(couple_name="Pending Couple", status=CoupleStatus.PENDING)
    db_session.add(couple)
    await db_session.flush()
    user = User(
        couple_id=couple.id,
        email="pending@example.com",
        display_name="P",
        email_verified=True,
        role=UserRole.PARTNER_A,
        password_hash=hash_password("password123"),
    )
    db_session.add(user)
    await db_session.commit()

    resp = await client.post(
        BASE + "/login",
        json={"email": "pending@example.com", "password": "password123"},
    )
    assert resp.status_code == 403


# ===========================================================================
# Token Refresh
# ===========================================================================


async def test_token_refresh_success(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_active_couple(db_session)
    login_resp = await client.post(
        BASE + "/login", json={"email": "alice@example.com", "password": "securepass1"}
    )
    assert login_resp.status_code == 200
    refresh_token = login_resp.json()["refresh_token"]

    resp = await client.post(
        BASE + "/token/refresh", json={"refresh_token": refresh_token}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


async def test_token_refresh_invalid_token(client: AsyncClient) -> None:
    resp = await client.post(
        BASE + "/token/refresh", json={"refresh_token": "invalid_random_token"}
    )
    assert resp.status_code == 401


async def test_token_refresh_rotation(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """After refreshing, the old refresh token must be revoked."""
    await _create_active_couple(db_session)
    login_resp = await client.post(
        BASE + "/login", json={"email": "alice@example.com", "password": "securepass1"}
    )
    old_refresh = login_resp.json()["refresh_token"]

    # Use the token once
    resp = await client.post(
        BASE + "/token/refresh", json={"refresh_token": old_refresh}
    )
    assert resp.status_code == 200

    # Re-use the old token — must be rejected
    resp2 = await client.post(
        BASE + "/token/refresh", json={"refresh_token": old_refresh}
    )
    assert resp2.status_code == 401


async def test_token_refresh_expired(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """An expired refresh token must return 401."""
    _, user_a, _ = await _create_active_couple(db_session)

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expired_record = RefreshToken(
        user_id=user_a.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(expired_record)
    await db_session.commit()

    resp = await client.post(
        BASE + "/token/refresh", json={"refresh_token": raw_token}
    )
    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"].lower()


# ===========================================================================
# Password Reset
# ===========================================================================


async def test_password_reset_request_success(
    client: AsyncClient, db_session: AsyncSession, mock_email: MockEmailProvider
) -> None:
    await _create_active_couple(db_session)
    resp = await client.post(
        BASE + "/password/reset", json={"email": "alice@example.com"}
    )
    assert resp.status_code == 204
    assert len(mock_email.sent_reset) == 1
    assert mock_email.sent_reset[0]["to"] == "alice@example.com"


async def test_password_reset_request_unknown_email(
    client: AsyncClient, mock_email: MockEmailProvider
) -> None:
    # Must return 204 even for unknown emails (no enumeration)
    resp = await client.post(
        BASE + "/password/reset", json={"email": "nobody@example.com"}
    )
    assert resp.status_code == 204
    assert len(mock_email.sent_reset) == 0


async def test_password_reset_confirm_success(
    client: AsyncClient, db_session: AsyncSession, mock_email: MockEmailProvider
) -> None:
    await _create_active_couple(db_session)
    # Request reset
    await client.post(BASE + "/password/reset", json={"email": "alice@example.com"})
    reset_token = mock_email.sent_reset[0]["code"]

    # Confirm reset
    resp = await client.post(
        BASE + "/password/reset/confirm",
        json={"token": reset_token, "new_password": "new_secure_pass"},
    )
    assert resp.status_code == 204

    # Login with new password should succeed
    login_resp = await client.post(
        BASE + "/login",
        json={"email": "alice@example.com", "password": "new_secure_pass"},
    )
    assert login_resp.status_code == 200


async def test_password_reset_confirm_invalid_token(client: AsyncClient) -> None:
    resp = await client.post(
        BASE + "/password/reset/confirm",
        json={"token": "bad_token", "new_password": "new_password123"},
    )
    assert resp.status_code == 404


async def test_password_reset_confirm_expired_token(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, user_a, _ = await _create_active_couple(db_session)
    expired_token = secrets.token_urlsafe(32)
    user_a.password_reset_token = expired_token
    user_a.password_reset_expires_at = datetime.now(timezone.utc) - timedelta(hours=3)
    await db_session.commit()

    resp = await client.post(
        BASE + "/password/reset/confirm",
        json={"token": expired_token, "new_password": "new_password123"},
    )
    assert resp.status_code == 410


async def test_password_reset_confirm_password_too_short(
    client: AsyncClient, db_session: AsyncSession, mock_email: MockEmailProvider
) -> None:
    await _create_active_couple(db_session)
    await client.post(BASE + "/password/reset", json={"email": "alice@example.com"})
    reset_token = mock_email.sent_reset[0]["code"]

    resp = await client.post(
        BASE + "/password/reset/confirm",
        json={"token": reset_token, "new_password": "short"},
    )
    assert resp.status_code == 422


# ===========================================================================
# Apple Sign In
# ===========================================================================


@pytest.fixture
def mock_apple_verify():
    """Patch verify_apple_id_token at the service import location."""
    with patch(
        "app.services.auth_service.verify_apple_id_token",
        new_callable=AsyncMock,
    ) as m:
        yield m


# Patch is applied inside the method via local import — patch at module level.
# We need to patch at the point of USE, so patch the core module.
@pytest.fixture
def mock_apple_core():
    with patch(
        "app.core.apple_auth.verify_apple_id_token",
        new_callable=AsyncMock,
    ) as m:
        yield m


async def test_apple_login_existing_user_by_apple_sub(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, user_a, _ = await _create_active_couple(db_session)
    user_a.apple_sub = "apple_sub_abc123"
    await db_session.commit()

    with patch(
        "app.services.auth_service.verify_apple_id_token",
        new_callable=AsyncMock,
        return_value={"sub": "apple_sub_abc123", "email": "alice@example.com"},
    ):
        resp = await client.post(
            BASE + "/apple/login", json={"identity_token": "fake_token"}
        )

    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_apple_login_existing_user_by_email(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """If no apple_sub match, fall back to email and auto-link the sub."""
    await _create_active_couple(db_session)

    with patch(
        "app.services.auth_service.verify_apple_id_token",
        new_callable=AsyncMock,
        return_value={"sub": "new_apple_sub_xyz", "email": "alice@example.com"},
    ):
        resp = await client.post(
            BASE + "/apple/login", json={"identity_token": "fake_token"}
        )

    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_apple_login_user_not_found(client: AsyncClient) -> None:
    with patch(
        "app.services.auth_service.verify_apple_id_token",
        new_callable=AsyncMock,
        return_value={"sub": "unknown_sub", "email": "nobody@example.com"},
    ):
        resp = await client.post(
            BASE + "/apple/login", json={"identity_token": "fake_token"}
        )

    assert resp.status_code == 404
    assert "register" in resp.json()["detail"].lower()


async def test_apple_login_invalid_token(client: AsyncClient) -> None:
    with patch(
        "app.services.auth_service.verify_apple_id_token",
        new_callable=AsyncMock,
        side_effect=ValueError("bad signature"),
    ):
        resp = await client.post(
            BASE + "/apple/login", json={"identity_token": "bad_token"}
        )

    assert resp.status_code == 401
    assert "Apple" in resp.json()["detail"]


# ===========================================================================
# Full end-to-end flow
# ===========================================================================


async def test_full_registration_and_login_flow(
    client: AsyncClient, mock_email: MockEmailProvider
) -> None:
    """Complete happy-path: initiate → verify both → complete → login → refresh."""
    # 1. Initiate
    init_resp = await client.post(BASE + "/register/initiate", json=_initiate_payload())
    assert init_resp.status_code == 201
    couple_id = init_resp.json()["couple_id"]
    assert len(mock_email.sent_verification) == 2

    # 2. Verify both
    for record in mock_email.sent_verification:
        v = await client.post(BASE + "/register/verify", json={"token": record["code"]})
        assert v.status_code == 200
    assert v.json()["both_verified"] is True  # type: ignore[possibly-undefined]

    # 3. Complete
    complete_resp = await client.post(
        BASE + "/register/complete",
        json={
            "couple_id": couple_id,
            "password_a": "alice_pass_123",
            "password_b": "bob_pass_456",
            "display_name_a": "Alice",
            "display_name_b": "Bob",
        },
    )
    assert complete_resp.status_code == 200

    # 4. Login
    login_resp = await client.post(
        BASE + "/login",
        json={"email": "alice@example.com", "password": "alice_pass_123"},
    )
    assert login_resp.status_code == 200
    tokens = login_resp.json()

    # 5. Refresh
    refresh_resp = await client.post(
        BASE + "/token/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()
