"""
Harris County TX — delinquent tax sale property list.

Public source: Harris County Tax Office monthly tax sale listing
https://www.hctax.net/Property/listings/taxsalelisting/image?id={listing_id}

Referenced from the official Tax Sales page as the "List of Sale Properties".
"""

from __future__ import annotations

import re
from datetime import date, datetime

from app.adapters.interfaces import LeadSource, RawLead
from app.sources.http import fetch_text, load_fixture

# Listing id rotates monthly; we try the live index redirect first, then a recent known id.
LISTING_URL_TEMPLATE = "https://www.hctax.net/Property/listings/taxsalelisting/image?id={listing_id}"
FALLBACK_LISTING_ID = "29765"

ADDRESS_RE = re.compile(
    r"###\s+(.+?)\s*\n+####\s+Precinct.*?Account#:\s*(\d+)\s*\n+Cause#:\s*(\d+)\s*\n+"
    r"Adjudged Value:\s*\$([\d,]+\.\d{2})\s*\n+Minimum Bid:\s*\$([\d,]+\.\d{2})",
    re.DOTALL,
)


def parse_harris_tax_sale_html(html: str) -> list[RawLead]:
    leads: list[RawLead] = []
    for match in ADDRESS_RE.finditer(html):
        full_address = match.group(1).strip()
        account = match.group(2)
        cause = match.group(3)
        adjudged = match.group(4).replace(",", "")
        min_bid = match.group(5).replace(",", "")

        city, state, zip_code = _split_tx_address(full_address)

        leads.append(
            RawLead(
                state="TX",
                county="Harris",
                source_module="tx.harris.tax_sale",
                property_address=full_address,
                city=city,
                zip_code=zip_code,
                parcel_id=account,
                distress_signals=["tax_delinquent", "tax_sale_scheduled"],
                raw_data={
                    "account_number": account,
                    "cause_number": cause,
                    "adjudged_value": float(adjudged),
                    "minimum_bid": float(min_bid),
                    "sale_type": "constable_tax_sale",
                },
                fetched_at=datetime.utcnow(),
            )
        )
    return leads


def _split_tx_address(full: str) -> tuple[str | None, str | None, str | None]:
    # e.g. "231 LA FONDA DR HOUSTON TX 77060"
    m = re.match(r"^(.+?)\s+TX\s+(\d{5}(?:-\d{4})?)$", full, re.I)
    if not m:
        return None, None, None
    left, zip_code = m.group(1), m.group(2)
    parts = left.rsplit(" ", 1)
    if len(parts) == 2:
        return parts[1], "TX", zip_code
    return left, "TX", zip_code


class HarrisTaxSaleSource(LeadSource):
    name = "Harris County Tax Sale List"
    state = "TX"
    county = "Harris"
    description = "Monthly delinquent tax sale properties from hctax.net (public listing)"

    def fetch(self, since_date: date | None = None) -> list[RawLead]:
        errors: list[str] = []
        for listing_id in (self._resolve_listing_id(), FALLBACK_LISTING_ID):
            try:
                url = LISTING_URL_TEMPLATE.format(listing_id=listing_id)
                html = fetch_text(url)
                leads = parse_harris_tax_sale_html(html)
                if leads:
                    return leads
            except Exception as exc:
                errors.append(f"id={listing_id}: {exc}")

        # Offline / blocked network: use captured public listing snapshot
        html = load_fixture("harris_tax_sale_listing.html")
        leads = parse_harris_tax_sale_html(html)
        if not leads:
            raise RuntimeError("Harris parser returned 0 leads; " + "; ".join(errors))
        for lead in leads:
            lead.raw_data["fixture_fallback"] = True
            lead.raw_data["live_fetch_errors"] = errors
        return leads

    def _resolve_listing_id(self) -> str:
        # Tax sales index often embeds the current listing id in links.
        try:
            html = fetch_text("https://www.hctax.net/Property/TaxSales/Index")
            m = re.search(r"taxsalelisting/image\?id=(\d+)", html)
            if m:
                return m.group(1)
        except Exception:
            pass
        return FALLBACK_LISTING_ID
