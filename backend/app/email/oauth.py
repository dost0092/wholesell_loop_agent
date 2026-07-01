"""Gmail OAuth 2.0 credential management with automatic token refresh.

Credentials are loaded from environment variables and optionally persisted
in the ``oauth_tokens`` table so refreshed access tokens survive restarts.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.models import OAuthToken

logger = logging.getLogger(__name__)

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
PROVIDER_KEY = "gmail"


class OAuthError(Exception):
    """Raised when OAuth credentials are missing or invalid."""


def _credentials_from_settings(settings: Settings) -> Credentials:
    return Credentials(
        token=None,
        refresh_token=settings.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=GMAIL_SCOPES,
    )


def _load_stored_token(db: Session) -> OAuthToken | None:
    return db.query(OAuthToken).filter(OAuthToken.provider == PROVIDER_KEY).first()


def _save_token(db: Session, creds: Credentials, refresh_token: str) -> None:
    stored = _load_stored_token(db)
    expiry = creds.expiry
    if expiry and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    if stored is None:
        stored = OAuthToken(
            provider=PROVIDER_KEY,
            access_token=creds.token,
            refresh_token=refresh_token,
            token_expiry=expiry,
            scopes=",".join(creds.scopes or GMAIL_SCOPES),
        )
        db.add(stored)
    else:
        stored.access_token = creds.token
        stored.refresh_token = refresh_token or stored.refresh_token
        stored.token_expiry = expiry
    db.commit()


def get_gmail_credentials(db: Session | None = None) -> Credentials:
    """Return valid Gmail API credentials, refreshing the access token if needed.

    Priority:
    1. DB-stored token (refreshed access token from a prior session)
    2. Environment ``GOOGLE_REFRESH_TOKEN``

    Raises ``OAuthError`` when credentials cannot be obtained.
    """
    settings = get_settings()
    if not settings.gmail_api_configured:
        raise OAuthError(
            "Gmail API not configured. Set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, "
            "GOOGLE_REFRESH_TOKEN, and SENDER_EMAIL."
        )

    creds: Credentials | None = None
    refresh_token = settings.google_refresh_token

    if db is not None:
        stored = _load_stored_token(db)
        if stored and stored.refresh_token:
            refresh_token = stored.refresh_token
            creds = Credentials(
                token=stored.access_token,
                refresh_token=stored.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
                scopes=GMAIL_SCOPES,
            )
            if stored.token_expiry:
                creds.expiry = stored.token_expiry.replace(tzinfo=None)

    if creds is None:
        creds = _credentials_from_settings(settings)

    if creds.expired or not creds.token:
        if not creds.refresh_token:
            raise OAuthError(
                "Access token expired and no refresh token available. "
                "Re-run scripts/gmail_authorize.py to re-authorize."
            )
        try:
            creds.refresh(Request())
            logger.info("Gmail access token refreshed successfully")
        except Exception as exc:  # noqa: BLE001
            raise OAuthError(f"Token refresh failed: {exc}") from exc

        if db is not None:
            _save_token(db, creds, refresh_token)

    return creds
