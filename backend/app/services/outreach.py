"""Phase 5 — outreach: draft emails, human approval queue, compliant send."""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.adapters.email import get_email_sender
from app.adapters.interfaces import OutboundEmail
from app.agents.message_writer import draft_email
from app.compliance.gates import can_send_message, is_on_dnc_list
from app.core.exceptions import AppError
from app.db.models import (
    ApprovalQueueItem,
    ApprovalStatus,
    Contact,
    Lead,
    LeadStatus,
    Message,
    MessageChannel,
    MessageDirection,
    MessageStatus,
    Owner,
)

logger = logging.getLogger(__name__)


def _best_email_contact(lead: Lead) -> Contact | None:
    best: Contact | None = None
    for owner in lead.owners:
        for contact in owner.contacts:
            if contact.contact_type != "email" or not contact.validated:
                continue
            if best is None or contact.confidence_score > best.confidence_score:
                best = contact
    return best


def _owner_for_contact(lead: Lead, contact: Contact) -> Owner | None:
    for owner in lead.owners:
        if any(c.id == contact.id for c in owner.contacts):
            return owner
    return None


def generate_drafts(db: Session, lead: Lead) -> ApprovalQueueItem:
    """Create a draft email + approval-queue item for a lead's best email contact."""
    contact = _best_email_contact(lead)
    if contact is None:
        raise AppError(
            "No validated email contact for this lead. Run trace + validation first.",
            status_code=422,
            code="no_valid_contact",
        )
    if is_on_dnc_list(db, contact.value):
        raise AppError("Contact is on the Do Not Contact list.", status_code=422, code="on_dnc")

    owner = _owner_for_contact(lead, contact)
    subject, body = draft_email(
        lead={
            "property_address": lead.property_address,
            "city": lead.city,
            "motivation_summary": lead.motivation_summary,
            "offer_strategy": lead.offer_strategy,
        },
        owner={"name": owner.name if owner else None},
    )

    message = Message(
        lead_id=lead.id,
        contact_id=contact.id,
        channel=MessageChannel.EMAIL,
        direction=MessageDirection.OUTBOUND,
        subject=subject,
        body=body,
        status=MessageStatus.PENDING_APPROVAL,
    )
    db.add(message)
    db.flush()

    item = ApprovalQueueItem(
        message_id=message.id,
        lead_id=lead.id,
        channel=MessageChannel.EMAIL,
        draft_subject=subject,
        draft_body=body,
        status=ApprovalStatus.PENDING,
    )
    db.add(item)

    if lead.status in (LeadStatus.VALIDATED, LeadStatus.TRACED, LeadStatus.SCORED):
        lead.status = LeadStatus.OUTREACH_PENDING

    db.commit()
    db.refresh(item)
    logger.info("Drafted outreach for lead %s (approval item %s)", lead.id, item.id)
    return item


def approve_item(
    db: Session,
    item: ApprovalQueueItem,
    reviewer: str,
    edited_subject: str | None = None,
    edited_body: str | None = None,
) -> ApprovalQueueItem:
    message = item.message
    edited = False
    if edited_subject is not None and edited_subject != item.draft_subject:
        item.draft_subject = edited_subject
        message.subject = edited_subject
        edited = True
    if edited_body is not None and edited_body != item.draft_body:
        item.draft_body = edited_body
        message.body = edited_body
        edited = True

    item.status = ApprovalStatus.EDITED if edited else ApprovalStatus.APPROVED
    item.reviewed_by = reviewer
    item.reviewed_at = datetime.utcnow()

    message.status = MessageStatus.APPROVED
    message.compliance_checked = True
    message.compliance_notes = "Approved by human reviewer"

    db.commit()
    db.refresh(item)
    return item


def reject_item(db: Session, item: ApprovalQueueItem, reviewer: str, notes: str | None) -> ApprovalQueueItem:
    item.status = ApprovalStatus.REJECTED
    item.reviewed_by = reviewer
    item.reviewed_at = datetime.utcnow()
    item.notes = notes
    if item.message:
        item.message.status = MessageStatus.REJECTED
    db.commit()
    db.refresh(item)
    return item


def send_item(db: Session, item: ApprovalQueueItem) -> Message:
    """Send an approved message. Compliance gate is enforced here — no bypass."""
    message = item.message
    if message is None:
        raise AppError("Approval item has no message", status_code=422, code="no_message")

    contact = db.get(Contact, message.contact_id) if message.contact_id else None
    if contact is None:
        raise AppError("Message has no contact to send to", status_code=422, code="no_contact")

    allowed, reason = can_send_message(db, message, contact.value)
    if not allowed:
        raise AppError(f"Send blocked: {reason}", status_code=422, code="send_blocked")

    sender = get_email_sender()
    ok = sender.send(
        OutboundEmail(
            to_email=contact.value,
            subject=message.subject or "",
            body_plain=message.body,
            lead_id=message.lead_id,
            message_id=message.id,
        )
    )

    if ok:
        message.status = MessageStatus.SENT
        message.sent_at = datetime.utcnow()
        lead = db.get(Lead, message.lead_id)
        if lead and lead.status == LeadStatus.OUTREACH_PENDING:
            lead.status = LeadStatus.CONTACTED
    else:
        message.status = MessageStatus.FAILED

    db.commit()
    db.refresh(message)
    logger.info("Send attempt for message %s: status=%s", message.id, message.status.value)
    return message
