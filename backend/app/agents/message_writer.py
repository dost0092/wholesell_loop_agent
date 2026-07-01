"""Phase 5 — outreach email drafting.

Plain-text, CAN-SPAM-aware messages. Template-based by default (no key needed);
Claude-authored when ANTHROPIC_API_KEY is set, with fallback to the template.
"""

from __future__ import annotations

import logging

from app.config import get_settings

logger = logging.getLogger(__name__)


def _first_name(owner_name: str | None) -> str:
    if not owner_name:
        return "there"
    cleaned = owner_name.strip().split(",")[0].strip()
    parts = cleaned.split()
    return parts[0].title() if parts else "there"


def _canspam_footer() -> str:
    settings = get_settings()
    addr = settings.canspam_physical_address or "[Your mailing address]"
    name = settings.smtp_from_name or "Our team"
    return (
        f"\n\n---\n{name}\n{addr}\n"
        "If you'd prefer not to receive messages about your property, just reply "
        '"STOP" and we will not contact you again.'
    )


def _template_draft(lead: dict, owner: dict) -> tuple[str, str]:
    name = _first_name(owner.get("name"))
    address = lead.get("property_address", "your property")
    city = lead.get("city") or ""
    loc = f" in {city}" if city else ""

    subject = f"Quick question about {address}"
    body = (
        f"Hi {name},\n\n"
        f"I'm reaching out about the property at {address}{loc}. "
        "I work with local buyers who purchase homes directly, as-is, and can close "
        "on your timeline without repairs, showings, or agent fees.\n\n"
        "If you've thought about selling — even down the road — I'd love to share a "
        "no-obligation cash offer. Would a quick call this week work?\n\n"
        "Either way, I hope you're doing well."
    )
    return subject, body + _canspam_footer()


def draft_email(lead: dict, owner: dict) -> tuple[str, str]:
    """Return (subject, body_plain)."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        return _template_draft(lead, owner)

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        prompt = (
            "Write a short, warm, plain-text cold outreach email to a distressed-property "
            "owner from a real estate investor. Be respectful and low-pressure. No HTML, no "
            "images, no hype. 120 words max. Return the subject on the first line prefixed "
            "with 'Subject: ', then a blank line, then the body.\n\n"
            f"Owner first name: {_first_name(owner.get('name'))}\n"
            f"Property: {lead.get('property_address')} {lead.get('city') or ''}\n"
            f"Situation: {lead.get('motivation_summary') or 'distressed property'}\n"
            f"Offer strategy: {lead.get('offer_strategy') or ''}"
        )
        resp = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in resp.content if hasattr(b, "text")).strip()
        subject = "Quick question about your property"
        body = text
        if text.lower().startswith("subject:"):
            head, _, rest = text.partition("\n")
            subject = head.split(":", 1)[1].strip()
            body = rest.strip()
        return subject, body + _canspam_footer()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Claude drafting failed (%s); using template", exc)
        return _template_draft(lead, owner)
