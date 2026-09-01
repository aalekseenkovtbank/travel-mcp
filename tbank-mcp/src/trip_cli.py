"""CLI for rendering and inspecting Travel Nova page contracts."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from .trip_page import (HotelPageDocumentV1, TripPageDocumentV1,
                        TripPageDocumentV2, render_travel_page_files,
                        render_trip_page_files, travel_page_json_schema,
                        trip_page_json_schema)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tbank-mcp")
    commands = parser.add_subparsers(dest="command", required=True)
    render = commands.add_parser("render-trip", help="render trip JSON to a static HTML page")
    render.add_argument("document", help="path to trip-page/v1 JSON")
    render.add_argument("-o", "--output", help="output .html path")
    render.add_argument("--overwrite", action="store_true", help="replace an existing HTML/JSON pair")
    commands.add_parser("trip-page-schema", help="print the trip-page/v1 JSON Schema")
    render_page = commands.add_parser(
        "render-page", help="render trip-page/v2 or hotel-page/v1 JSON")
    render_page.add_argument("document", help="path to a Travel Nova page JSON")
    render_page.add_argument("-o", "--output", help="output .html path")
    render_page.add_argument(
        "--overwrite", action="store_true", help="replace an existing HTML/JSON pair")
    schema = commands.add_parser("page-schema", help="print a current page JSON Schema")
    schema.add_argument("--kind", choices=("trip", "hotels"), required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "trip-page-schema":
        print(json.dumps(trip_page_json_schema(), ensure_ascii=False, indent=2))
        return 0
    if args.command == "page-schema":
        print(json.dumps(
            travel_page_json_schema(args.kind), ensure_ascii=False, indent=2))
        return 0
    try:
        source = Path(args.document).expanduser()
        payload = source.read_text(encoding="utf-8")
        if args.command == "render-trip":
            document = TripPageDocumentV1.model_validate_json(payload)
            result = render_trip_page_files(
                document, overwrite=args.overwrite,
                explicit_html_path=args.output or str(source.with_suffix(".html")),
            )
        else:
            raw = json.loads(payload)
            schema_version = raw.get("schemaVersion") if isinstance(raw, dict) else None
            model = {
                "trip-page/v2": TripPageDocumentV2,
                "hotel-page/v1": HotelPageDocumentV1,
            }.get(schema_version)
            if model is None:
                raise ValueError(
                    "render-page expects schemaVersion trip-page/v2 or hotel-page/v1")
            document = model.model_validate(raw)
            result = render_travel_page_files(
                document, overwrite=args.overwrite,
                explicit_html_path=args.output or str(source.with_suffix(".html")),
            )
        print(json.dumps(result.model_dump(by_alias=True), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, ValidationError) as exc:
        print(f"tbank-mcp: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
