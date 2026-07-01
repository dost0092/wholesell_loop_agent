"""Miami-Dade County FL — delinquent real estate property tax notice.

Public source: Miami-Dade County Tax Collector legal advertisements
https://www.miamidade.gov/resources/legal-ads/

Monthly delinquent real estate lists are published as PDF notices.
"""

from __future__ import annotations

import io
import re
from datetime import date, datetime

from app.adapters.interfaces import LeadSource, RawLead
from app.sources.http import fetch_bytes, fetch_text, load_fixture

LEGAL_ADS_INDEX = "https://www.miamidade.gov/resources/legal-ads/"
KNOWN_DELINQUENT_PDF = (
    "https://www.miamidade.gov/resources/legal-ads/2025/"
    "2025-05-28-delinquent-real-estate-property-taxes.pdf"
)

# 000000001 01 01010401020 J E J PROPERTIES INC........................ $17135.47
DELINQUENT_LINE_RE = re.compile(
    r"^\d+\s+(?P<muni>\d{2})\s+(?P<folio>\d{11})\s+"
    r"(?P<owner>.+?)\s*\.{2,}\s+\$(?P<amount>[\d,]+\.\d{2})\s*$"
)


def parse_miami_dade_delinquent_text(text: str, max_rows: int = 500) -> list[RawLead]:
    leads: list[RawLead] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("CITY OF") or "PUBLIC NOTICE" in line.upper():
            continue
        match = DELINQUENT_LINE_RE.match(line)
        if not match:
            continue
        folio = match.group("folio")
        owner = re.sub(r"\s+", " ", match.group("owner").strip())
        amount = float(match.group("amount").replace(",", ""))

        leads.append(
            RawLead(
                state="FL",
                county="Miami-Dade",
                source_module="fl.miami_dade.delinquent",
                property_address=f"Miami-Dade County FL (folio {folio})",
                city="Miami",
                zip_code=None,
                parcel_id=folio,
                distress_signals=["tax_delinquent"],
                raw_data={
                    "owner_of_record": owner,
                    "delinquent_amount": amount,
                    "municipality_code": match.group("muni"),
                    "folio_lookup": "https://www.miamidade.gov/Apps/PA/propertysearch/",
                },
                fetched_at=datetime.utcnow(),
            )
        )
        if len(leads) >= max_rows:
            break
    return leads


def _extract_pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf is required for Miami-Dade PDF parsing") from exc

    reader = PdfReader(io.BytesIO(data))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


def _resolve_delinquent_pdf_url() -> str | None:
    try:
        html = fetch_text(LEGAL_ADS_INDEX, timeout=30.0)
        matches = re.findall(
            r'href="([^"]+delinquent-real-estate-property-taxes\.pdf)"',
            html,
            re.I,
        )
        if matches:
            url = matches[0]
            if url.startswith("/"):
                return "https://www.miamidade.gov" + url
            return url
    except Exception:
        pass
    return None


class MiamiDadeDelinquentSource(LeadSource):
    name = "Miami-Dade Delinquent Real Estate Taxes"
    state = "FL"
    county = "Miami-Dade"
    description = (
        "Monthly delinquent real estate tax notice from miamidade.gov legal advertisements"
    )

    def __init__(self, max_rows: int = 200):
        self.max_rows = max_rows

    def fetch(self, since_date: date | None = None) -> list[RawLead]:
        errors: list[str] = []
        for label, url in (
            ("index", _resolve_delinquent_pdf_url()),
            ("known", KNOWN_DELINQUENT_PDF),
        ):
            if not url:
                continue
            try:
                data = fetch_bytes(url, timeout=90.0)
                text = _extract_pdf_text(data)
                leads = parse_miami_dade_delinquent_text(text, max_rows=self.max_rows)
                if leads:
                    return leads
            except Exception as exc:
                errors.append(f"{label}: {exc}")

        text = load_fixture("miami_dade_delinquent_sample.txt")
        leads = parse_miami_dade_delinquent_text(text, max_rows=self.max_rows)
        if not leads:
            raise RuntimeError(
                "Miami-Dade parser returned 0 leads; " + "; ".join(errors)
            )
        for lead in leads:
            lead.raw_data["fixture_fallback"] = True
            lead.raw_data["live_fetch_errors"] = errors
        return leads
