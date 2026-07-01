"""
Tarrant County TX — constable delinquent tax sale property lists.

Public source: Tarrant County Constable Precinct 3
https://www.tarrantcountytx.gov/en/constables/constable-3/delinquent-tax-sales.html

Monthly sale lists link cause numbers + tax account numbers (public).
Physical addresses are resolved via Tarrant Tax Office / TAD lookup in Phase 4.
"""

from __future__ import annotations

import re
from datetime import date, datetime

from app.adapters.interfaces import LeadSource, RawLead
from app.sources.http import fetch_text, load_fixture

SALE_PAGE_URL = (
    "https://www.tarrantcountytx.gov/en/constables/constable-3/delinquent-tax-sales.html"
)

# Rows like: Cause 2019-12345  Account 12345678  Attorney LGBS
ROW_RE = re.compile(
    r"Cause\s*(?P<cause>[\w-]+)\s+Account\s*(?P<account>\d{6,})\s*(?:Attorney\s*(?P<attorney>[A-Z]+))?",
    re.I,
)


def parse_tarrant_sale_html(html: str) -> list[RawLead]:
    leads: list[RawLead] = []
    seen: set[str] = set()

    for match in ROW_RE.finditer(html):
        account = match.group("account")
        if account in seen:
            continue
        seen.add(account)
        cause = match.group("cause")
        attorney = (match.group("attorney") or "").strip()

        leads.append(
            RawLead(
                state="TX",
                county="Tarrant",
                source_module="tx.tarrant.tax_sale",
                property_address=f"Tarrant County TX (account {account})",
                city="Fort Worth",
                zip_code=None,
                parcel_id=account,
                distress_signals=["tax_delinquent", "tax_sale_scheduled"],
                raw_data={
                    "cause_number": cause,
                    "attorney": attorney,
                    "address_lookup": "https://taxonline.tarrantcounty.com/taxweb/accountsearch.asp",
                    "tad_lookup": "https://www.tad.org/property-search/",
                },
                fetched_at=datetime.utcnow(),
            )
        )
    return leads


class TarrantTaxSaleSource(LeadSource):
    name = "Tarrant County Constable Tax Sale List"
    state = "TX"
    county = "Tarrant"
    description = "Monthly constable tax sale list (cause + account numbers, public)"

    def fetch(self, since_date: date | None = None) -> list[RawLead]:
        errors: list[str] = []
        try:
            html = fetch_text(SALE_PAGE_URL)
            # Follow first monthly list link if present
            link_match = re.search(
                r'href="([^"]+delinquent[^"]*\.(?:html|htm|pdf))"',
                html,
                re.I,
            )
            if link_match:
                list_url = link_match.group(1)
                if list_url.startswith("/"):
                    list_url = "https://www.tarrantcountytx.gov" + list_url
                html = fetch_text(list_url)
            leads = parse_tarrant_sale_html(html)
            if leads:
                return leads
        except Exception as exc:
            errors.append(str(exc))

        html = load_fixture("tarrant_tax_sale_list.html")
        leads = parse_tarrant_sale_html(html)
        if not leads:
            raise RuntimeError("Tarrant parser returned 0 leads; " + "; ".join(errors))
        for lead in leads:
            lead.raw_data["fixture_fallback"] = True
            lead.raw_data["live_fetch_errors"] = errors
        return leads
