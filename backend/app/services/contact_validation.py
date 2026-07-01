"""Phase 5 — contact validation: email syntax + MX, phone normalization/type, DNC scrub."""

from __future__ import annotations

import logging
import re

from sqlalchemy.orm import Session

from app.adapters.interfaces import ContactValidationResult
from app.compliance.gates import is_on_dnc_list
from app.db.models import Contact, Lead, LeadStatus

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# In-process MX cache to avoid repeat DNS lookups for the same domain.
_mx_cache: dict[str, bool] = {}


def _domain_has_mx(domain: str) -> bool | None:
    """True/False if resolvable, None if DNS unavailable (can't determine)."""
    if domain in _mx_cache:
        return _mx_cache[domain]
    try:
        import dns.resolver  # type: ignore
    except ImportError:
        return None
    try:
        answers = dns.resolver.resolve(domain, "MX")
        result = len(answers) > 0
    except Exception:  # noqa: BLE001 — NXDOMAIN, no MX, timeout, etc.
        result = False
    _mx_cache[domain] = result
    return result


def validate_email(value: str) -> ContactValidationResult:
    value = value.strip().lower()
    if not _EMAIL_RE.match(value):
        return ContactValidationResult(is_valid=False, confidence=0.0, details={"reason": "bad_syntax"})

    domain = value.rsplit("@", 1)[-1]
    # Test/synthetic domains are syntactically valid but never deliverable.
    if domain.endswith((".test", ".invalid", ".example")):
        return ContactValidationResult(
            is_valid=False, confidence=0.1, details={"reason": "non_deliverable_domain", "domain": domain}
        )

    mx = _domain_has_mx(domain)
    if mx is None:
        return ContactValidationResult(
            is_valid=True, confidence=0.5, details={"mx": "unknown", "domain": domain}
        )
    if mx:
        return ContactValidationResult(
            is_valid=True, confidence=0.85, details={"mx": True, "domain": domain}
        )
    return ContactValidationResult(
        is_valid=False, confidence=0.1, details={"mx": False, "domain": domain}
    )


def validate_phone(value: str, hint: str | None = None) -> ContactValidationResult:
    digits = re.sub(r"\D", "", value)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return ContactValidationResult(is_valid=False, confidence=0.0, details={"reason": "bad_length"})

    area = digits[:3]
    if area[0] in "01":
        return ContactValidationResult(is_valid=False, confidence=0.0, details={"reason": "invalid_area_code"})

    line_type = (hint or "unknown").lower()
    if line_type not in ("mobile", "landline", "voip"):
        line_type = "unknown"

    return ContactValidationResult(
        is_valid=True,
        line_type=line_type,
        confidence=0.7,
        details={"normalized": f"+1{digits}", "area_code": area},
    )


def validate_contact(db: Session, contact: Contact) -> Contact:
    if is_on_dnc_list(db, contact.value):
        contact.validated = False
        contact.validation_details = {"reason": "on_dnc_list"}
        contact.confidence_score = 0.0
        return contact

    if contact.contact_type == "email":
        result = validate_email(contact.value)
    else:
        result = validate_phone(contact.value, contact.line_type)
        if result.line_type:
            contact.line_type = result.line_type
        if result.details.get("normalized"):
            contact.value = result.details["normalized"]

    contact.validated = result.is_valid
    contact.validation_details = result.details
    contact.confidence_score = result.confidence
    return contact


def validate_lead_contacts(db: Session, lead: Lead) -> dict:
    valid = 0
    invalid = 0
    for owner in lead.owners:
        for contact in owner.contacts:
            validate_contact(db, contact)
            if contact.validated:
                valid += 1
            else:
                invalid += 1

    if valid > 0 and lead.status == LeadStatus.TRACED:
        lead.status = LeadStatus.VALIDATED

    db.commit()
    logger.info("Validated contacts for lead %s: valid=%s invalid=%s", lead.id, valid, invalid)
    return {"valid": valid, "invalid": invalid}
