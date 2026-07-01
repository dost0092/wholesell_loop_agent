"""
Broward County FL — tax deed sale property list.

Public sources:
- Broward County Records, Taxes & Treasury tax deed information
- Legal notices advertising scheduled tax deed sales
https://www.broward.org/RecordsTaxesTreasury/
"""

from __future__ import annotations

import re
from datetime import date, datetime

from app.adapters.interfaces import LeadSource, RawLead
from app.sources.http import fetch_text, load_fixture

TAX_DEED_INFO_URL = (
    "https://www.broward.org/RecordsTaxesTreasury/Pages/TaxDeedSaleInformation.aspx"
)

# HTML row: tax deed cert, parcel id, owner name, opening bid
ROW_RE = re.compile(
    r"Tax\s*Deed\s*(?P<cert>[\w-]+)\s+Parcel\s*(?P<parcel>[\d-]+)\s+"
    r"Owner\s*(?P<owner>[\w\s,'.&-]+?)\s+(?:Bid|Amount)\s*\$?(?P<amount>[\d,]+\.\d{2})",
    re.I,
)

TABLE_ROW_RE = re.compile(
    r"<tr[^>]*>\s*"
    r"<td[^>]*>(?P<cert>[^<]+)</td>\s*"
    r"<td[^>]*>(?P<parcel>[^<]+)</td>\s*"
    r"<td[^>]*>(?P<owner>[^<]+)</td>\s*"
    r"<td[^>]*>\$?(?P<amount>[\d,]+\.\d{2})</td>",
    re.I | re.S,
)


def parse_broward_tax_deed_html(html: str) -> list[RawLead]:
    leads: list[RawLead] = []
    seen: set[str] = set()

    for pattern in (TABLE_ROW_RE, ROW_RE):
        for match in pattern.finditer(html):
            parcel = match.group("parcel").strip()
            if parcel in seen:
                continue
            seen.add(parcel)
            cert = match.group("cert").strip()
            owner = match.group("owner").strip()
            amount = float(match.group("amount").replace(",", ""))

            leads.append(
                RawLead(
                    state="FL",
                    county="Broward",
                    source_module="fl.broward.tax_deed",
                    property_address=f"Broward County FL (parcel {parcel})",
                    city="Fort Lauderdale",
                    zip_code=None,
                    parcel_id=parcel,
                    distress_signals=["tax_delinquent", "tax_deed_scheduled"],
                    raw_data={
                        "tax_deed_certificate": cert,
                        "owner_of_record": owner,
                        "opening_bid": amount,
                        "parcel_lookup": "https://county-taxes.net/broward/broward",
                    },
                    fetched_at=datetime.utcnow(),
                )
            )
    return leads


class BrowardTaxDeedSource(LeadSource):
    name = "Broward County Tax Deed Sale List"
    state = "FL"
    county = "Broward"
    description = "Tax deed sale properties from Broward County public notices"

    def fetch(self, since_date: date | None = None) -> list[RawLead]:
        errors: list[str] = []
        try:
            html = fetch_text(TAX_DEED_INFO_URL, timeout=45.0)
            leads = parse_broward_tax_deed_html(html)
            if leads:
                return leads
        except Exception as exc:
            errors.append(str(exc))

        html = load_fixture("broward_tax_deed_list.html")
        leads = parse_broward_tax_deed_html(html)
        if not leads:
            raise RuntimeError("Broward parser returned 0 leads; " + "; ".join(errors))
        for lead in leads:
            lead.raw_data["fixture_fallback"] = True
            lead.raw_data["live_fetch_errors"] = errors
        return leads
