"""Provider-agnostic email interfaces.

Business logic depends on ``EmailProvider``, not Gmail directly, so the
backend can swap to Google Workspace, Brevo, Mailgun, SES, etc. later.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.adapters.interfaces import OutboundEmail


@dataclass(frozen=True)
class SendResult:
    """Outcome of a single send attempt."""

    success: bool
    provider_message_id: str | None = None
    error_message: str | None = None
    is_retryable: bool = False


class EmailProvider(ABC):
    """Abstract email transport — implement per provider."""

    name: str = "email_provider"

    @abstractmethod
    def send(self, email: OutboundEmail) -> SendResult:
        """Send one plain-text email. Must not raise on transient failures."""
        ...
