"""Phase 4 — business entity (LLC / corp) lookups.

Detects whether an owner-of-record is an entity and, where possible, resolves it
to officers / registered agent so outreach can target a real person.

- MockEntityLookup: deterministic, offline. Flags synthetic officer data.
- OpenCorporatesLookup: real API when OPENCORPORATES_API_KEY is set.
"""

from __future__ import annotations

import logging
import re

from app.adapters.interfaces import EntityLookupProvider, EntityRecord
from app.config import get_settings

logger = logging.getLogger(__name__)

_ENTITY_TOKENS = (" LLC", " L.L.C", " INC", " CORP", " CO.", " LP", " LLP", " TRUST", " COMPANY")


def is_entity_name(name: str | None) -> bool:
    if not name:
        return False
    upper = f" {name.upper()} "
    return any(tok in upper for tok in _ENTITY_TOKENS)


class MockEntityLookup(EntityLookupProvider):
    name = "mock"

    def lookup(self, entity_name: str, state: str) -> EntityRecord:
        if not is_entity_name(entity_name):
            return EntityRecord(is_entity=False, provider=self.name)

        # Derive a plausible managing-member name from the entity name (synthetic).
        core = re.sub(r"[^A-Za-z ]", " ", entity_name)
        for tok in _ENTITY_TOKENS:
            core = core.upper().replace(tok.strip(), "")
        core = " ".join(core.title().split())
        agent = f"{core} Management".strip() or "Registered Agent"

        return EntityRecord(
            is_entity=True,
            entity_name=entity_name,
            officers=[{"name": f"{core} (Managing Member)", "role": "member"}] if core else [],
            registered_agent=agent,
            status="active",
            provider=self.name,
            raw_response={"synthetic": True, "note": "MOCK entity lookup — verify with state registry"},
        )


class OpenCorporatesLookup(EntityLookupProvider):
    name = "opencorporates"

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._fallback = MockEntityLookup()

    def lookup(self, entity_name: str, state: str) -> EntityRecord:
        if not is_entity_name(entity_name):
            return EntityRecord(is_entity=False, provider=self.name)
        try:
            import httpx
        except ImportError:
            return self._fallback.lookup(entity_name, state)

        try:
            resp = httpx.get(
                "https://api.opencorporates.com/v0.4/companies/search",
                params={
                    "q": entity_name,
                    "jurisdiction_code": f"us_{state.lower()}",
                    "api_token": self._api_key,
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            companies = (data.get("results") or {}).get("companies") or []
            if not companies:
                return self._fallback.lookup(entity_name, state)
            company = companies[0]["company"]
            officers = [
                {"name": o["officer"].get("name"), "role": o["officer"].get("position")}
                for o in company.get("officers", []) or []
            ]
            return EntityRecord(
                is_entity=True,
                entity_name=company.get("name", entity_name),
                officers=officers,
                registered_agent=company.get("registered_agent_name"),
                status=company.get("current_status"),
                provider=self.name,
                raw_response=company,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("OpenCorporates lookup failed (%s); using mock", exc)
            return self._fallback.lookup(entity_name, state)


def get_entity_lookup() -> EntityLookupProvider:
    settings = get_settings()
    if settings.opencorporates_api_key:
        return OpenCorporatesLookup(settings.opencorporates_api_key)
    return MockEntityLookup()
