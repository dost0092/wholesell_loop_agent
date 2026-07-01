"""
Hillsborough County FL — tax deed sale / lands available list.

Public source: Hillsborough County Clerk of Circuit Court
https://hillsclerk.com/taxdeeds
https://publicaccess.hillsclerk.com/TD/
"""

from __future__ import annotations

import re
from datetime import date, datetime

from app.adapters.interfaces import LeadSource, RawLead
from app.sources.http import fetch_text, load_fixture

TAX_DEED_PAGE = "https://hillsclerk.com/taxdeeds"

ROW_RE = re.compile(
    r"Certificate\s*(?P<cert>[\w-]+)\s+Parcel\s*(?P<parcel>[\w-]+)\s+"
    r"(?:Address\s*)?(?P<address>[\d\w\s,.-]+?)\s+(?:Bid|Amount)\s*\$?(?P<amount>[\d,]+\.\d{2})",
    re.I,
)

TABLE_ROW_RE = re.compile(
    r"<tr[^>]*>\s*"
    r"<td[^>]*>(?P<cert>[^<]+)</td>\s*"
    r"<td[^>]*>(?P<parcel>[^<]+)</td>\s*"
    r"<td[^>]*>(?P<address>[^<]+)</td>\s*"
    r"<td[^>]*>\$?(?P<amount>[\d,]+\.\d{2})</td>",
    re.I | re.S,
)


def _split_fl_address(address: str) -> tuple[str, str | None, str | None]:
    address = re.sub(r"\s+", " ", address.strip())
    m = re.search(r"FL\s+(\d{5}(?:-\d{4})?)", address, re.I)
    zip_code = m.group(1) if m else None
    city = None
    if m:
        left = address[: m.start()].strip()
        parts = left.rsplit(" ", 1)
        if len(parts) == 2 and parts[1].isalpha():
            city = parts[1]
    return address, city, zip_code


def parse_hillsborough_tax_deed_html(html: str) -> list[RawLead]:
    leads: list[RawLead] = []
    seen: set[str] = set()

    for pattern in (TABLE_ROW_RE, ROW_RE):
        for match in pattern.finditer(html):
            parcel = match.group("parcel").strip()
            if parcel in seen:
                continue
            seen.add(parcel)
            cert = match.group("cert").strip()
            address_raw = match.group("address").strip()
            amount = float(match.group("amount").replace(",", ""))
            full_address, city, zip_code = _split_fl_address(address_raw)

            leads.append(
                RawLead(
                    state="FL",
                    county="Hillsborough",
                    source_module="fl.hillsborough.tax_deed",
                    property_address=full_address,
                    city=city or "Tampa",
                    zip_code=zip_code,
                    parcel_id=parcel,
                    distress_signals=["tax_delinquent", "tax_deed_scheduled"],
                    raw_data={
                        "certificate_number": cert,
                        "opening_bid": amount,
                        "parcel_lookup": "https://www.hcpafl.org/",
                    },
                    fetched_at=datetime.utcnow(),
                )
            )
    return leads


class HillsboroughTaxDeedSource(LeadSource):
    name = "Hillsborough County Tax Deed Sale List"
    state = "FL"
    county = "Hillsborough"
    description = "Tax deed sale list from Hillsborough Clerk public records"

    def fetch(self, since_date: date | None = None) -> list[RawLead]:
        errors: list[str] = []
        try:
            html = fetch_text(TAX_DEED_PAGE, timeout=45.0)
            leads = parse_hillsborough_tax_deed_html(html)
            if leads:
                return leads
        except Exception as exc:
            errors.append(str(exc))

        html = load_fixture("hillsborough_tax_deed_list.html")
        leads = parse_hillsborough_tax_deed_html(html)
        if not leads:
            raise RuntimeError(
                "Hillsborough parser returned 0 leads; " + "; ".join(errors)
            )
        for lead in leads:
            lead.raw_data["fixture_fallback"] = True
            lead.raw_data["live_fetch_errors"] = errors
        return leads
