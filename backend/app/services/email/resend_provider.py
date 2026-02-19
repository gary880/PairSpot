from __future__ import annotations

import resend

from app.config import get_settings
from app.services.email.base import EmailProvider

settings = get_settings()


class ResendProvider(EmailProvider):
    """Email provider using Resend API."""

    def __init__(self):
        resend.api_key = settings.RESEND_API_KEY

    async def send_verification(self, to: str, code: str, couple_name: str) -> bool:
        """Send verification email via Resend."""
        try:
            resend.Emails.send({
                "from": settings.EMAIL_FROM,
                "to": to,
                "subject": f"歡迎加入 {settings.APP_NAME}！請驗證您的 Email",
                "html": f"""
                <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
                    <h1>歡迎加入 {settings.APP_NAME}！</h1>
                    <p>您的伴侶 <strong>{couple_name}</strong> 邀請您一起加入。</p>
                    <p>請點擊以下連結驗證您的 Email：</p>
                    <a href="https://pairspot.app/verify?token={code}"
                       style="display: inline-block; background: #FF6B6B; color: white;
                              padding: 12px 24px; text-decoration: none; border-radius: 8px;">
                        驗證 Email
                    </a>
                    <p style="color: #666; margin-top: 24px;">
                        或複製此連結：https://pairspot.app/verify?token={code}
                    </p>
                </div>
                """,
            })
            return True
        except Exception:
            return False

    async def send_password_reset(self, to: str, code: str) -> bool:
        """Send password reset email via Resend."""
        try:
            resend.Emails.send({
                "from": settings.EMAIL_FROM,
                "to": to,
                "subject": f"{settings.APP_NAME} 密碼重設",
                "html": f"""
                <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
                    <h1>密碼重設請求</h1>
                    <p>我們收到您的密碼重設請求。</p>
                    <p>請點擊以下連結重設密碼：</p>
                    <a href="https://pairspot.app/reset-password?token={code}"
                       style="display: inline-block; background: #FF6B6B; color: white;
                              padding: 12px 24px; text-decoration: none; border-radius: 8px;">
                        重設密碼
                    </a>
                    <p style="color: #666; margin-top: 24px;">
                        如果您沒有請求重設密碼，請忽略此郵件。
                    </p>
                </div>
                """,
            })
            return True
        except Exception:
            return False
