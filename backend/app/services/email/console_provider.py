from __future__ import annotations

from app.services.email.base import EmailProvider


class ConsoleEmailProvider(EmailProvider):
    """Development-only email provider — prints tokens to stdout instead of sending real emails."""

    async def send_verification(self, to: str, code: str, couple_name: str) -> bool:
        print(
            f"\n{'=' * 60}\n"
            f"[DEV] Verification Email\n"
            f"  To:          {to}\n"
            f"  Couple:      {couple_name}\n"
            f"  Token:       {code}\n"
            f"  Verify URL:  http://localhost:3000/verify?token={code}\n"
            f"{'=' * 60}\n",
            flush=True,
        )
        return True

    async def send_password_reset(self, to: str, code: str) -> bool:
        print(
            f"\n{'=' * 60}\n"
            f"[DEV] Password Reset Email\n"
            f"  To:         {to}\n"
            f"  Token:      {code}\n"
            f"{'=' * 60}\n",
            flush=True,
        )
        return True
