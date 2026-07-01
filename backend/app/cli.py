"""CLI for local development — fetch leads without starting the API."""

from __future__ import annotations

import argparse
import json
import sys

from app.sources.registry import (
    DEFAULT_ALL_SOURCES,
    DEFAULT_FL_SOURCES,
    DEFAULT_TX_SOURCES,
    get_source,
)


def _resolve_sources(state: str | None, explicit: list[str] | None) -> list[str]:
    if explicit:
        return explicit
    if state == "tx":
        return DEFAULT_TX_SOURCES
    if state == "fl":
        return DEFAULT_FL_SOURCES
    return DEFAULT_ALL_SOURCES


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch distressed property leads")
    parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        help="Source key (repeatable).",
    )
    parser.add_argument(
        "--state",
        choices=["tx", "fl", "all"],
        default="all",
        help="Fetch all sources for a state (default: all).",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    args = parser.parse_args(argv)

    state = None if args.state == "all" else args.state
    keys = _resolve_sources(state, args.sources)
    output = []

    for key in keys:
        source = get_source(key)
        raw = source.fetch()
        output.append(
            {
                "source": key,
                "county": source.county,
                "state": source.state,
                "count": len(raw),
                "fixture_fallback": any(
                    (r.raw_data or {}).get("fixture_fallback") for r in raw
                ),
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
            print(
                f"\n=== {block['source']} / {block['county']}, {block['state']}: "
                f"{block['count']} leads{fb} ==="
            )
            for lead in block["leads"]:
                print(f"  • {lead['address']}  [{lead['parcel_id']}]")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
