"""Shared HTTP helpers for county connectors."""

from pathlib import Path

import httpx

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; TXFLLeadGen/0.1; +https://localhost) "
        "Research bot for public county records"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def fetch_text(url: str, timeout: float = 45.0) -> str:
    with httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=timeout) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def fetch_bytes(url: str, timeout: float = 120.0) -> bytes:
    with httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=timeout) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.content


def load_fixture(name: str) -> str:
    path = FIXTURES_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Fixture not found: {path}")
    return path.read_text(encoding="utf-8", errors="replace")
