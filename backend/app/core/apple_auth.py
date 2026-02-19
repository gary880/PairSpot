"""Apple Sign In — 驗證 Apple ID Token (JWT / JWKS)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
from jose import JWTError, jwt

APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"
_JWKS_CACHE_TTL_SECONDS = 3600  # 1 hour

_jwks_cache: dict[str, Any] | None = None
_jwks_cached_at: datetime | None = None


async def _get_apple_jwks() -> dict[str, Any]:
    """Fetch (and cache) Apple's public JWKS."""
    global _jwks_cache, _jwks_cached_at

    now = datetime.now(timezone.utc)
    if (
        _jwks_cache is not None
        and _jwks_cached_at is not None
        and (now - _jwks_cached_at).total_seconds() < _JWKS_CACHE_TTL_SECONDS
    ):
        return _jwks_cache

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(APPLE_JWKS_URL)
        response.raise_for_status()
        _jwks_cache = response.json()
        _jwks_cached_at = now

    return _jwks_cache


async def verify_apple_id_token(identity_token: str, client_id: str) -> dict[str, Any]:
    """Verify an Apple Sign In identity token.

    Args:
        identity_token: JWT issued by Apple after Sign In with Apple.
        client_id: Your app's bundle ID (e.g. "com.example.pairspot").

    Returns:
        Decoded JWT payload containing at minimum ``sub`` and optionally ``email``.

    Raises:
        ValueError: If the token is malformed, expired, or fails signature verification.
    """
    try:
        header = jwt.get_unverified_header(identity_token)
    except JWTError as exc:
        raise ValueError(f"Cannot parse Apple token header: {exc}") from exc

    jwks = await _get_apple_jwks()

    key_data = next(
        (k for k in jwks.get("keys", []) if k.get("kid") == header.get("kid")),
        None,
    )
    if key_data is None:
        raise ValueError(f"No matching Apple public key found for kid={header.get('kid')}")

    try:
        payload: dict[str, Any] = jwt.decode(
            identity_token,
            key_data,
            algorithms=["RS256"],
            audience=client_id,
            issuer=APPLE_ISSUER,
        )
    except JWTError as exc:
        raise ValueError(f"Apple token verification failed: {exc}") from exc

    return payload
