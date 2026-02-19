from __future__ import annotations

import asyncio

from app.services.email.resend_provider import ResendProvider
from app.tasks import celery_app


@celery_app.task(name="send_verification_email")
def send_verification_email(to: str, code: str, couple_name: str) -> bool:
    """Send verification email task."""
    provider = ResendProvider()
    return asyncio.run(provider.send_verification(to, code, couple_name))


@celery_app.task(name="send_password_reset_email")
def send_password_reset_email(to: str, code: str) -> bool:
    """Send password reset email task."""
    provider = ResendProvider()
    return asyncio.run(provider.send_password_reset(to, code))
