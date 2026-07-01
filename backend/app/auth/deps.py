"""API key authentication for protected endpoints."""

from __future__ import annotations

from fastapi import Depends, Security
from fastapi.security import APIKeyHeader

from app.config import get_settings
from app.core.exceptions import AppError

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str | None = Security(_api_key_header)) -> str:
    settings = get_settings()
    if not settings.api_key:
        return "dev-open"
    if not api_key or api_key != settings.api_key:
        raise AppError("Invalid or missing API key", status_code=401, code="unauthorized")
    return api_key
