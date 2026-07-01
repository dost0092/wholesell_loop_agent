"""Run county source connectors and optionally persist leads."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.schemas.api import FetchSourceResult
from app.services.lead_ingestion import ingest_raw_leads
from app.sources.registry import get_source

logger = logging.getLogger(__name__)


def run_source_fetch(
    source_keys: list[str],
    *,
    persist: bool,
    db: Session,
) -> list[FetchSourceResult]:
    results: list[FetchSourceResult] = []

    for key in source_keys:
        try:
            source = get_source(key)
        except KeyError as exc:
            results.append(
                FetchSourceResult(
                    source_key=key,
                    county="unknown",
                    leads_fetched=0,
                    error=str(exc),
                )
            )
            continue

        try:
            raw_leads = source.fetch()
            used_fixture = any(
                (r.raw_data or {}).get("fixture_fallback") for r in raw_leads
            )
            ingest_stats = None
            if persist:
                ingest_stats = ingest_raw_leads(db, raw_leads)

            sample = [
                {
                    "address": r.property_address,
                    "parcel_id": r.parcel_id,
                    "city": r.city,
                    "distress_signals": r.distress_signals,
                }
                for r in raw_leads[:5]
            ]
            results.append(
                FetchSourceResult(
                    source_key=key,
                    county=source.county,
                    leads_fetched=len(raw_leads),
                    ingest=ingest_stats,
                    sample=sample,
                    used_fixture_fallback=used_fixture,
                )
            )
        except Exception as exc:
            logger.exception("Fetch failed for source %s", key)
            results.append(
                FetchSourceResult(
                    source_key=key,
                    county=source.county,
                    leads_fetched=0,
                    error=str(exc),
                )
            )

    return results
