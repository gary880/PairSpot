from __future__ import annotations

from abc import ABC, abstractmethod


class EmailProvider(ABC):
    """Abstract base class for email providers."""

    @abstractmethod
    async def send_verification(self, to: str, code: str, couple_name: str) -> bool:
        """Send verification email.

        Args:
            to: Recipient email address
            code: Verification code/token
            couple_name: Name of the couple for personalization

        Returns:
            True if email sent successfully, False otherwise
        """
        pass

    @abstractmethod
    async def send_password_reset(self, to: str, code: str) -> bool:
        """Send password reset email.

        Args:
            to: Recipient email address
            code: Reset code/token

        Returns:
            True if email sent successfully, False otherwise
        """
        pass
