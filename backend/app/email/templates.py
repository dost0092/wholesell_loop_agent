"""Email signature and formatting helpers."""

from __future__ import annotations

from app.config import get_settings


def build_signature() -> str:
    """Professional plain-text signature block appended to outbound emails."""
    settings = get_settings()
    name = settings.email_sender_name or settings.smtp_from_name or "Our team"
    email = settings.sender_email or settings.smtp_from_email or settings.smtp_user
    addr = settings.canspam_physical_address or "[Your mailing address]"

    lines = [f"\n\n---", name]
    if email:
        lines.append(email)
    lines.append(addr)
    lines.append(
        'If you prefer not to hear from us again, reply "STOP" and we will remove you.'
    )
    return "\n".join(lines)


def ensure_signature(body: str) -> str:
    """Append the signature if the body does not already contain the footer marker."""
    if "---" in body and "STOP" in body:
        return body
    return body.rstrip() + build_signature()
