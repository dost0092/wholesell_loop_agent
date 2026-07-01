"""
Dallas County TX — delinquent accounts from the free public Tax Roll (TRW) file.

Public source: Dallas County Tax Office
https://www.dallascounty.org/departments/tax/tax-roll.php

The TRW unpaid summary report (tcs404p) lists accounts with outstanding balances.
Full flat404 fixed-width parsing is Phase 1b; we start with the summary report format.
"""

from __future__ import annotations

import io
import re
import zipfile
from datetime import date, datetime

from app.adapters.interfaces import LeadSource, RawLead
from app.sources.http import fetch_bytes, load_fixture

# Official sample + production zip paths (Dallas County Tax Office public downloads)
TRW_SAMPLE_ZIP = "https://www.dallascounty.org/Assets/uploads/docs/tax/trw/TRWFILE_SAMPLE.zip"
TRW_FULL_ZIP = "https://www.dallascounty.org/Assets/uploads/docs/tax/trw/TRWFILE.zip"

# Unpaid summary lines: ACCOUNT  OWNER ...  AMOUNT (simplified parser for tcs404p text export)
UNPAID_LINE_RE = re.compile(
    r"^(?P<account>[A-Z0-9]{6,})\s+(?P<owner>.{5,40}?)\s{2,}(?P<address>.{5,50}?)\s{2,}"
    r"(?P<amount>\d+\.\d{2})\s*$"
)


def parse_dallas_unpaid_summary(text: str, max_rows: int = 500) -> list[RawLead]:
    leads: list[RawLead] = []
    for line in text.splitlines():
        line = line.rstrip()
        if not line or line.startswith("-") or "ACCOUNT" in line.upper():
            continue
        m = UNPAID_LINE_RE.match(line)
        if not m:
            continue
        account = m.group("account").strip()
        owner = m.group("owner").strip()
        address = m.group("address").strip()
        amount = float(m.group("amount"))

        leads.append(
            RawLead(
                state="TX",
                county="Dallas",
                source_module="tx.dallas.trw",
                property_address=address,
                city="Dallas",
                zip_code=None,
                parcel_id=account,
                distress_signals=["tax_delinquent"],
                raw_data={
                    "owner_of_record": owner,
                    "delinquent_amount": amount,
                    "source_file": "tcs404p_unpaid_summary",
                },
                fetched_at=datetime.utcnow(),
            )
        )
        if len(leads) >= max_rows:
            break
    return leads


def _extract_unpaid_summary_from_zip(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for name in zf.namelist():
            if "tcs404p" in name.lower() or "unpaid" in name.lower():
                return zf.read(name).decode("latin-1", errors="replace")
        # fallback: first .txt-like member
        for name in zf.namelist():
            if not name.endswith("/"):
                return zf.read(name).decode("latin-1", errors="replace")
    raise ValueError("No readable file in TRW zip archive")


class DallasTrwSource(LeadSource):
    name = "Dallas County TRW Delinquent Roll"
    state = "TX"
    county = "Dallas"
    description = "Free weekly TRW tax roll — unpaid/delinquent accounts (dallascounty.org)"

    def __init__(self, use_full_file: bool = False, max_rows: int = 200):
        self.use_full_file = use_full_file
        self.max_rows = max_rows

    def fetch(self, since_date: date | None = None) -> list[RawLead]:
        errors: list[str] = []
        for label, url in (("sample", TRW_SAMPLE_ZIP), ("full", TRW_FULL_ZIP)):
            if label == "full" and not self.use_full_file:
                continue
            try:
                data = fetch_bytes(url)
                text = _extract_unpaid_summary_from_zip(data)
                leads = parse_dallas_unpaid_summary(text, max_rows=self.max_rows)
                if leads:
                    return leads
            except Exception as exc:
                errors.append(f"{label}: {exc}")

        text = load_fixture("dallas_trw_unpaid_sample.txt")
        leads = parse_dallas_unpaid_summary(text, max_rows=self.max_rows)
        if not leads:
            raise RuntimeError("Dallas TRW parser returned 0 leads; " + "; ".join(errors))
        for lead in leads:
            lead.raw_data["fixture_fallback"] = True
            lead.raw_data["live_fetch_errors"] = errors
        return leads
