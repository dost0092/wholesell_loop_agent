"""Email content agent — generates unique, human-sounding outreach per lead.

Wraps the existing ``message_writer`` with additional uniqueness constraints
and anti-AI-writing guardrails for the daily automated send pipeline.
"""

from __future__ import annotations

import hashlib
import logging

from sqlalchemy.orm import Session

from app.agents.message_writer import draft_email
from app.config import get_settings
from app.db.models import Lead, Owner
from app.email.templates import ensure_signature

logger = logging.getLogger(__name__)

# Varied openers to reduce template repetition across the daily batch
_OPENERS = (
    "Hi {name},",
    "Hello {name},",
    "Good morning {name},",
    "{name},",
)

# Human tone reminders injected into Claude prompts
_HUMAN_TONE_RULES = (
    "Write like a real person sending a one-off email, not a marketing blast.",
    "Use short sentences. No bullet points. No exclamation marks.",
    "Do not use words like: leverage, synergy, exciting, opportunity, solution.",
    "Reference the specific property address naturally.",
    "Sound like a local investor, not a corporation.",
    "Vary sentence structure — do not start consecutive sentences the same way.",
)


def _first_name(owner_name: str | None) -> str:
    if not owner_name:
        return "there"
    cleaned = owner_name.strip().split(",")[0].strip()
    parts = cleaned.split()
    return parts[0].title() if parts else "there"


def _lead_context(lead: Lead, owner: Owner | None) -> tuple[dict, dict]:
    return (
        {
            "property_address": lead.property_address,
            "city": lead.city,
            "motivation_summary": lead.motivation_summary,
            "offer_strategy": lead.offer_strategy,
            "distress_signals": lead.distress_signals,
            "deal_score": lead.deal_score,
        },
        {"name": owner.name if owner else None},
    )


def _uniqueness_seed(lead_id: int) -> str:
    """Deterministic but varied seed so the same lead always gets the same opener."""
    digest = hashlib.md5(str(lead_id).encode()).hexdigest()
    return digest


def generate_personalized_email(
    lead: Lead,
    owner: Owner | None,
    *,
    prior_body_hashes: set[str] | None = None,
) -> tuple[str, str]:
    """Generate a unique subject and body for one lead.

    Args:
        lead: The distressed-property lead record.
        owner: Owner record (may be None).
        prior_body_hashes: Body hashes already used today — regenerated if collision.

    Returns:
        ``(subject, body_plain)`` with signature appended.
    """
    lead_dict, owner_dict = _lead_context(lead, owner)
    settings = get_settings()

    if settings.anthropic_api_key:
        subject, body = _claude_draft(lead_dict, owner_dict, lead.id)
    else:
        subject, body = draft_email(lead_dict, owner_dict)
        # Template path: vary opener for batch uniqueness
        name = _first_name(owner_dict.get("name"))
        seed = int(_uniqueness_seed(lead.id)[:8], 16)
        opener = _OPENERS[seed % len(_OPENERS)].format(name=name)
        lines = body.split("\n", 1)
        if lines:
            body = opener + ("\n" + lines[1] if len(lines) > 1 else "")

    body = ensure_signature(body)

    if prior_body_hashes is not None:
        from app.email.utils import hash_body

        h = hash_body(body)
        attempts = 0
        while h in prior_body_hashes and attempts < 3:
            logger.info("Body hash collision for lead %s — regenerating", lead.id)
            if settings.anthropic_api_key:
                subject, body = _claude_draft(
                    lead_dict, owner_dict, lead.id, variation=attempts + 1
                )
            else:
                body = body + f"\n\n(P.S. — happy to answer any questions about {lead.property_address}.)"
            body = ensure_signature(body)
            h = hash_body(body)
            attempts += 1

    return subject, body


def _claude_draft(
    lead: dict,
    owner: dict,
    lead_id: int,
    variation: int = 0,
) -> tuple[str, str]:
    """Claude-authored email with human-tone guardrails."""
    settings = get_settings()
    name = _first_name(owner.get("name"))
    tone_block = "\n".join(f"- {r}" for r in _HUMAN_TONE_RULES)
    variation_hint = (
        f"\nVariation seed: {variation} — make this distinctly different from prior emails."
        if variation
        else ""
    )

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        prompt = (
            "Write a short, warm, plain-text email to a property owner from a local "
            "real estate investor. Be respectful and low-pressure.\n\n"
            f"Rules:\n{tone_block}\n"
            "120 words max. No HTML. Return subject on first line as 'Subject: ...', "
            "then blank line, then body.\n\n"
            f"Owner first name: {name}\n"
            f"Property: {lead.get('property_address')} {lead.get('city') or ''}\n"
            f"Situation: {lead.get('motivation_summary') or 'owner may want to sell'}\n"
            f"Signals: {', '.join(lead.get('distress_signals') or [])}\n"
            f"Strategy: {lead.get('offer_strategy') or ''}"
            f"{variation_hint}"
        )
        resp = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in resp.content if hasattr(b, "text")).strip()
        subject = f"Question about {lead.get('property_address', 'your property')}"
        body = text
        if text.lower().startswith("subject:"):
            head, _, rest = text.partition("\n")
            subject = head.split(":", 1)[1].strip()
            body = rest.strip()
        return subject, body
    except Exception as exc:  # noqa: BLE001
        logger.warning("Claude email agent failed for lead %s: %s", lead_id, exc)
        return draft_email(lead, owner)


def generate_batch_emails(db: Session, leads: list[Lead]) -> list[tuple[Lead, str, str]]:
    """Generate unique emails for a batch of leads, avoiding duplicate body hashes."""
    from app.email.utils import hash_body

    used_hashes: set[str] = set()
    results: list[tuple[Lead, str, str]] = []

    for lead in leads:
        owner = lead.owners[0] if lead.owners else None
        subject, body = generate_personalized_email(lead, owner, prior_body_hashes=used_hashes)
        used_hashes.add(hash_body(body))
        results.append((lead, subject, body))

    return results
