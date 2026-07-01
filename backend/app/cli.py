"""CLI for local development — fetch TX leads without starting the API."""

from __future__ import annotations

import argparse
import json
import sys

from app.api.routes import DEFAULT_TX_SOURCES as TX_SOURCES
from app.sources.registry import get_source


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch TX distressed property leads (Phase 1)")
    parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        help="Source key (repeatable). Default: all Phase 1 TX sources.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    args = parser.parse_args(argv)

    keys = args.sources or TX_SOURCES
    output = []

    for key in keys:
        source = get_source(key)
        raw = source.fetch()
        output.append(
            {
                "source": key,
                "county": source.county,
                "count": len(raw),
                "fixture_fallback": any((r.raw_data or {}).get("fixture_fallback") for r in raw),
                "leads": [
                    {
                        "address": r.property_address,
                        "parcel_id": r.parcel_id,
                        "city": r.city,
                        "signals": r.distress_signals,
                        "raw_data": r.raw_data,
                    }
                    for r in raw[:10]
                ],
            }
        )

    if args.json:
        print(json.dumps(output, indent=2))
    else:
        for block in output:
            fb = " (fixture fallback)" if block["fixture_fallback"] else " (live)"
            print(f"\n=== {block['source']} / {block['county']}: {block['count']} leads{fb} ===")
            for lead in block["leads"]:
                print(f"  • {lead['address']}  [{lead['parcel_id']}]")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
