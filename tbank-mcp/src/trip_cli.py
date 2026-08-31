"""CLI for rendering and inspecting the trip-page contract."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from .trip_page import (TripPageDocumentV1, render_trip_page_files,
                        trip_page_json_schema)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tbank-mcp")
    commands = parser.add_subparsers(dest="command", required=True)
    render = commands.add_parser("render-trip", help="render trip JSON to a static HTML page")
    render.add_argument("document", help="path to trip-page/v1 JSON")
    render.add_argument("-o", "--output", help="output .html path")
    render.add_argument("--overwrite", action="store_true", help="replace an existing HTML/JSON pair")
    commands.add_parser("trip-page-schema", help="print the trip-page/v1 JSON Schema")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "trip-page-schema":
        print(json.dumps(trip_page_json_schema(), ensure_ascii=False, indent=2))
        return 0
    try:
        source = Path(args.document).expanduser()
        document = TripPageDocumentV1.model_validate_json(source.read_text(encoding="utf-8"))
        result = render_trip_page_files(
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
