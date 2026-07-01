"""Phase 4 — skip trace providers.

- MockSkipTraceProvider: deterministic synthetic contacts, no API key. Clearly
  flags results as synthetic so they are never mistaken for real PII.
- BatchDataProvider: real BatchData skip-trace API when SKIP_TRACE_API_KEY is set.

The factory chooses BatchData when a key is configured, else the mock.
"""

from __future__ import annotations

import hashlib
import logging
import re

from app.adapters.interfaces import ContactRecord, SkipTraceProvider
from app.config import get_settings

logger = logging.getLogger(__name__)


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", ".", (name or "owner").lower()).strip(".") or "owner"


class MockSkipTraceProvider(SkipTraceProvider):
    """Synthetic contacts for offline development and demos."""

    name = "mock"

    def trace(self, owner_name: str, property_address: str, city: str, state: str) -> ContactRecord:
        seed = hashlib.md5(f"{owner_name}|{property_address}".encode()).hexdigest()
        digits = re.sub(r"\D", "", seed)[:10].ljust(10, "0")
        area = "713" if state.upper() == "TX" else "305"
        phone = f"+1{area}{digits[3:10]}"
        local = _slug(owner_name)
        email = f"{local}@example-skiptrace.test"

        return ContactRecord(
            name=owner_name,
            mailing_address=property_address,
            emails=[{"value": email, "source": "mock", "confidence": 0.5}],
            phones=[{"value": phone, "line_type": "mobile", "source": "mock", "confidence": 0.5}],
            provider=self.name,
            raw_response={"synthetic": True, "note": "MOCK skip trace — not real contact data"},
        )


class BatchDataProvider(SkipTraceProvider):
    name = "batchdata"

    def __init__(self, api_key: str, api_url: str):
        self._api_key = api_key
        self._api_url = api_url
        self._fallback = MockSkipTraceProvider()

    def trace(self, owner_name: str, property_address: str, city: str, state: str) -> ContactRecord:
        try:
            import httpx
        except ImportError:
            logger.warning("httpx not installed; using mock skip trace")
            return self._fallback.trace(owner_name, property_address, city, state)

        payload = {
            "requests": [
                {
                    "name": {"full": owner_name},
                    "propertyAddress": {"street": property_address, "city": city, "state": state},
                }
            ]
        }
        try:
            resp = httpx.post(
                self._api_url,
                json=payload,
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return self._parse(owner_name, property_address, data)
        except Exception as exc:  # noqa: BLE001
            logger.warning("BatchData skip trace failed (%s); using mock", exc)
            return self._fallback.trace(owner_name, property_address, city, state)

    def _parse(self, owner_name: str, property_address: str, data: dict) -> ContactRecord:
        emails: list[dict] = []
        phones: list[dict] = []
        results = (data.get("results") or {}).get("persons") or []
        for person in results:
            for em in person.get("emails", []) or []:
                val = em.get("email") if isinstance(em, dict) else em
                if val:
                    emails.append({"value": val, "source": self.name, "confidence": 0.8})
            for ph in person.get("phoneNumbers", []) or []:
                if isinstance(ph, dict):
                    phones.append(
                        {
                            "value": ph.get("number"),
                            "line_type": (ph.get("type") or "unknown").lower(),
                            "source": self.name,
                            "confidence": 0.8,
                        }
                    )
        return ContactRecord(
            name=owner_name,
            mailing_address=property_address,
            emails=emails,
            phones=[p for p in phones if p.get("value")],
            provider=self.name,
            raw_response=data,
        )


def get_skip_trace_provider() -> SkipTraceProvider:
    settings = get_settings()
    if settings.skip_trace_api_key and settings.skip_trace_provider == "batchdata":
        return BatchDataProvider(settings.skip_trace_api_key, settings.skip_trace_api_url)
    return MockSkipTraceProvider()
