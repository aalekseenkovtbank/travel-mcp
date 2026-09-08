#!/usr/bin/env python3
"""Travel Nova eval runner.

Deterministic checks that the travel MCP contract behaves as expected, run as a
plain script (stdlib only, no test framework):

  * offline group — URL builders and document contract, no network;
  * live group    — the real MCP endpoint: tools/list, validation, tolerant
                    render, compact hotel_rates, flight_search bookable links,
                    instruction content.

Usage:
  ./.venv/bin/python evals/eval_live.py --offline          # no network
  ./.venv/bin/python evals/eval_live.py --url https://host/path/mcp
  ./.venv/bin/python evals/eval_live.py --url https://…/mcp --scenario   # + compose

Exit code 0 when every enabled check passed, 1 otherwise. Add --report FILE.json
to write a machine-readable report. Meant for a cron/CI hook; it never books or
pays anything (read-only calls only).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from urllib.parse import urlsplit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if os.path.isdir(SRC):
    sys.path.insert(0, SRC)

RESULTS: list[dict] = []


def check(name: str, fn, *args, **kwargs):
    ok = False
    detail = ""
    try:
        ok, detail = fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        detail = f"raised {type(exc).__name__}: {str(exc)[:240]}"
    RESULTS.append({"check": name, "ok": bool(ok), "detail": str(detail)[:400]})
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail[:160]}" if detail and not ok else ""))


# ─────────────────────────────────────────────────────────── offline ─────────
def run_offline():
    from src.tbank_urls import (avia_checkout_url, avia_share_url,
                                safe_public_https_url, safe_tbank_url)
    from src.trip_page import (EventOption, HotelOptionV2, TripPageDocumentV2,
                               travel_page_json_schema)

    def compare_url(built: str, sample: str):
        from urllib.parse import parse_qs
        bp = urlsplit(built)
        sp = urlsplit(sample)
        bq, sq = parse_qs(bp.query), parse_qs(sp.query)
        for key in ("flights", "adults", "cabin"):
            if bq.get(key) != sq.get(key):
                return False
        return bp.path == sp.path and bp.scheme == "https"

    sample_direct = ("https://www.tbank.ru/travel/flights/multi-way/OVB-MOW/10-13/MOW-OVB/11-11/"
                     "?children=0&source=share&infants=0&cabin=Y&flights=10-13-S7-2502~11-11-S7-2505&adults=1")
    built_direct = avia_share_url([
        {"origin": "OVB", "destination": "MOW", "date": "2026-10-13",
         "segments": [{"date": "2026-10-13", "carrier": "S7", "flight": "2502"}]},
        {"origin": "MOW", "destination": "OVB", "date": "2026-11-11",
         "segments": [{"date": "2026-11-11", "carrier": "S7", "flight": "2505"}]},
    ], adults=1)
    check("avia_share_url: direct sample", lambda: (compare_url(built_direct, sample_direct), ""))

    sample_xfer = ("https://www.tbank.ru/travel/flights/multi-way/OVB-KZN/10-13/KZN-OVB/11-11/"
                   "?children=0&source=share&infants=0&cabin=Y&flights=10-13-S7-7001_10-14-N4-758~11-11-N4-759_11-11-S7-5344&adults=1")
    built_xfer = avia_share_url([
        {"origin": "OVB", "destination": "KZN", "date": "2026-10-13",
         "segments": [{"date": "2026-10-13", "carrier": "S7", "flight": "7001"},
                      {"date": "2026-10-14", "carrier": "N4", "flight": "758"}]},
        {"origin": "KZN", "destination": "OVB", "date": "2026-11-11",
         "segments": [{"date": "2026-11-11", "carrier": "N4", "flight": "759"},
                      {"date": "2026-11-11", "carrier": "S7", "flight": "5344"}]},
    ], adults=1)
    check("avia_share_url: transfer sample", lambda: (compare_url(built_xfer, sample_xfer), built_xfer))

    expected = "https://www.tbank.ru/travel/flights/checkout/?offerId=b3b47df9-0424-4fe6-a26c-28d1e7c66d88.38"
    check("avia_checkout_url: sample", lambda: (
        avia_checkout_url("b3b47df9-0424-4fe6-a26c-28d1e7c66d88.38") == expected, ""))
    check("avia_checkout_url: rejects garbage",
          lambda: (avia_checkout_url("") == "" and avia_checkout_url("x&y=1") == "", ""))

    ev = {"id": "e1", "name": "Матч", "kind": "hockey", "startsAt": "2026-11-25T19:00:00+03:00",
          "sourceUrl": "https://sportmail.ru/hockey/khl/407/match/8129128/"}
    try:
        EventOption.model_validate(ev)
        event_ok = True
    except Exception:
        event_ok = False
    check("event external https source accepted", lambda: (event_ok, ""))

    bad_hotel = {"id": "h1", "name": "H", "address": "x",
                 "coordinates": {"latitude": 1, "longitude": 2}, "totalPriceRub": 1,
                 "nightlyPriceRub": 1,
                 "detailsUrl": "https://x.com/abc"}
    try:
        HotelOptionV2.model_validate(bad_hotel)
        hotel_restricted = False
    except Exception:
        hotel_restricted = True
    check("hotel detailsUrl still T-Bank-only", lambda: (hotel_restricted, ""))

    mini = {
        "schemaVersion": "trip-page/v2",
        "trip": {"title": "T", "destination": "NN", "dateFrom": "2026-11-24",
                 "dateTo": "2026-11-26", "travelers": 2},
        "transport": [
            {"id": "a", "direction": "outbound", "mode": "flight", "origin": "A",
             "destination": "B", "departureAt": "2026-11-24T10:00:00+03:00",
             "arrivalAt": "2026-11-24T12:00:00+03:00", "carrier": "X", "priceRub": 100},
            {"id": "b", "direction": "return", "mode": "flight", "origin": "B",
             "destination": "A", "departureAt": "2026-11-26T10:00:00+03:00",
             "arrivalAt": "2026-11-26T12:00:00+03:00", "carrier": "X", "priceRub": 100}],
        "hotels": [{"id": "h1", "name": "H", "address": "ул. 1",
                    "coordinates": {"latitude": 56.3, "longitude": 44.0},
                    "stars": 3, "totalPriceRub": 1000, "nightlyPriceRub": 500,
                    "detailsUrl": "https://www.tbank.ru/travel/hotels/new/hotels/123"}],
        "selectedHotelId": "h1",
        "sources": [{"name": "s", "url": "https://example.com/",
                     "checkedAt": "2026-09-04T12:00:00Z"}],
        "checkedAt": "2026-09-04T12:00:00Z",
    }
    try:
        TripPageDocumentV2.model_validate(mini)
        mini_ok = True
    except Exception as exc:
        mini_ok = False
        mini_err = str(exc)
    check("optional blocks not required (strict ok)",
          lambda: (mini_ok, "" if mini_ok else mini_err))

    schema = json.dumps(travel_page_json_schema("trip"))
    check("schema has travelers, no transportAdults",
          lambda: ('"travelers"' in schema and "transportAdults" not in schema, ""))


# ────────────────────────────────────────────────────────────── live ─────────
class LiveMCP:
    def __init__(self, url: str):
        import http.client
        sp = urlsplit(url)
        self.conn = http.client.HTTPSConnection if sp.scheme == "https" \
            else http.client.HTTPConnection
        self.host, self.path = sp.netloc, sp.path
        self.conn = self.conn(self.host, timeout=60)
        self.sid = None
        self._init()

    def _call(self, payload):
        headers = {"Content-Type": "application/json",
                   "Accept": "application/json, text/event-stream"}
        if self.sid:
            headers["mcp-session-id"] = self.sid
        self.conn.request("POST", self.path, body=json.dumps(payload), headers=headers)
        resp = self.conn.getresponse()
        body = resp.read().decode()
        if self.sid is None:
            self.sid = resp.getheader("mcp-session-id")
        data = [ln[5:].strip() for ln in body.splitlines() if ln.startswith("data:")]
        if not (data or body.strip()):
            return {}
        return json.loads(data[-1] if data else body)

    def _init(self):
        res = self._call({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                          "params": {"protocolVersion": "2025-03-26",
                                     "capabilities": {},
                                     "clientInfo": {"name": "eval", "version": "1"}}})
        self.server_info = (res or {}).get("result", {}).get("serverInfo")
        self._call({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

    def tool(self, name: str, args: dict, _id: int = 99) -> str:
        res = self._call({"jsonrpc": "2.0", "id": _id, "method": "tools/call",
                          "params": {"name": name, "arguments": args}})
        content = (res or {}).get("result", {}).get("content") or []
        return "".join(c.get("text", "") for c in content if c.get("type") == "text")

    def tools(self):
        res = self._call({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        return [(t or {}).get("name") for t in (res or {}).get("result", {}).get("tools", [])]


def run_live(url: str, scenario: bool):
    mcp = LiveMCP(url)
    check("initialize serverInfo", lambda: (bool(mcp.server_info), json.dumps(mcp.server_info)))

    def tools_ok():
        names = mcp.tools()
        need = {"render_travel_page", "format_trip_reply", "travel_page_schema",
                "validate_travel_page", "compose_travel_page", "flight_checkout_url",
                "hotel_rates", "flight_search"}
        missing = sorted(need - set(names))
        banned = "flight_history" in names
        return (len(names) >= len(need) and not missing and not banned,
                f"missing={missing} flight_history={banned} total={len(names)}")
    check("tools/list contains expected tools", tools_ok)

    mini = {"schemaVersion": "trip-page/v2",
            "trip": {"title": "T", "destination": "NN", "dateFrom": "2026-11-24",
                     "dateTo": "2026-11-26", "travelers": 2},
            "sources": [{"name": "s", "url": "https://example.com/",
                         "checkedAt": "2026-09-04T12:00:00Z"}],
            "checkedAt": "2026-09-04T12:00:00Z"}
    v = mcp.tool("validate_travel_page", {"document": mini})
    check("validate: minimal doc ok", lambda: (v.strip().startswith("ok:"), v[:200]))

    bad = json.loads(json.dumps(mini))
    bad["hotels"] = [{"id": "h1", "name": "H"}]
    vb = mcp.tool("validate_travel_page", {"document": bad})
    check("validate: broken doc reports errors/tips",
          lambda: ("ошибок" in vb or "Частые причины" in vb, vb[:200]))

    r = mcp.tool("render_travel_page", {"document": mini})
    try:
        p = json.loads(r)
        tolerant_ok = bool(p.get("html")) and (p.get("advice") is not None)
        tolerant_detail = f"html={bool(p.get('html'))} advice={len(p.get('advice') or [])}"
    except Exception:
        tolerant_ok, tolerant_detail = False, r[:200]
    check("render: tolerant partial doc -> html+advice", lambda: (tolerant_ok, tolerant_detail))

    doc = mcp.tool("read_instruction", {"slug": "trip-generation"})
    forbidden = [t for t in ("orders(", "audience_profile(", "render_trip_page",
                             "python", "render-page", "/tbank-mcp/") if t in doc]
    check("instruction trip-generation clean",
          lambda: (not forbidden, f"found={forbidden}"))

    fs = mcp.tool("flight_search", {"from_code": "OVB", "to_code": "GOJ",
                                    "date": "2026-11-24", "adults": 1,
                                    "only_bookable": True, "limit": 2,
                                    "response_format": "json"})
    try:
        offers = json.loads(fs)["data"]["offers"]
        ok_rows = offers and all(o.get("tbankUrl") and "/flights/checkout/" in o["tbankUrl"]
                                 and o.get("offerId") for o in offers)
        legs_ok = bool(offers) and any(leg.get("hops") is not None or leg.get("flightNumber")
                                       for o in offers for leg in o.get("legs") or [])
        detail = (offers[0].get("tbankUrl") if offers else "no offers")
    except Exception:
        ok_rows, legs_ok, detail = False, False, fs[:200]
    check("flight_search: bookable offers have checkout tbankUrl",
          lambda: (ok_rows and legs_ok, detail))

    rates = mcp.tool("hotel_rates", {"hotel_id": "1468883", "checkin_date": "2026-11-24",
                                     "checkout_date": "2026-11-26", "adults": 2,
                                     "response_format": "json"})
    try:
        data = json.loads(rates)["data"]
        r0 = data["rates"][0]
        keys = set(r0)
        ok_keys = {"bookHash", "price", "meal", "paymentPlace",
                   "isNonRefundable", "freeCancellationUntil"} <= keys
        compact_ok = len(rates) < 15000 and "isCreditCardDataRequired" not in keys
    except Exception:
        ok_keys, compact_ok = False, False
    check("hotel_rates: compact cards", lambda: (ok_keys and compact_ok,
                                                 f"len={len(rates)} keys={sorted(keys) if 'keys' in dir() else ''}"))

    out = mcp.tool("flight_checkout_url", {"request": {"adults": 1, "directions": [
        {"fromCode": "OVB", "toCode": "KZN", "date": "2026-10-13",
         "flights": [{"date": "2026-10-13", "carrier": "S7", "flight": "7001"},
                     {"date": "2026-10-14", "carrier": "N4", "flight": "758"}]},
        {"fromCode": "KZN", "toCode": "OVB", "date": "2026-11-11",
         "flights": [{"date": "2026-11-11", "carrier": "N4", "flight": "759"},
                     {"date": "2026-11-11", "carrier": "S7", "flight": "5344"}]}]}})
    first = out.splitlines()[0] if out else ""
    ok_url = first == ("https://www.tbank.ru/travel/flights/multi-way/OVB-KZN/10-13/KZN-OVB/11-11/"
                       "?children=0&source=share&infants=0&cabin=Y"
                       "&flights=10-13-S7-7001_10-14-N4-758~11-11-N4-759_11-11-S7-5344"
                       "&adults=1&baggage=0&composite=0")
    check("flight_checkout_url: matches transfer sample", lambda: (ok_url, first))

    if scenario:
        comp = mcp.tool("compose_travel_page", {"request": {
            "title": "Eval trip", "destination": "Нижний Новгород", "locationId": 93815,
            "dateFrom": "2026-11-24", "dateTo": "2026-11-26", "travelers": 2,
            "flights": [
                {"direction": "outbound", "fromCode": "OVB", "toCode": "GOJ",
                 "date": "2026-11-24", "carriers": ["SU 1549", "SU 6229"]},
                {"direction": "return", "fromCode": "GOJ", "toCode": "OVB",
                 "date": "2026-11-26", "carriers": ["SU 6226", "SU 1464"]}],
            "hotels": [{"hotelId": "1429902", "preferBreakfast": True}],
        }})
        try:
            p = json.loads(comp)
            ok = bool(p.get("html")) and p.get("advice") is not None
        except Exception:
            ok, p = False, None
        check("compose_travel_page end-to-end",
              lambda: (ok, (p.get("advice") if isinstance(p, dict) else comp[:200])))


def main() -> int:
    parser = argparse.ArgumentParser(description="Travel Nova eval runner")
    parser.add_argument("--offline", action="store_true", help="run only offline checks")
    parser.add_argument("--url", default=os.environ.get("TRAVEL_MCP_URL", ""),
                        help="live MCP endpoint URL (https://host/path/mcp)")
    parser.add_argument("--scenario", action="store_true",
                        help="also run the slow compose_travel_page scenario")
    parser.add_argument("--report", default="", help="write report JSON to this file")
    args = parser.parse_args()

    started = time.time()
    if args.offline or not args.url:
        print("== offline checks ==")
        run_offline()
    else:
        print(f"== live checks: {args.url} ==")
        run_live(args.url, args.scenario)

    failed = [r for r in RESULTS if not r["ok"]]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed"
          f" in {time.time() - started:.1f}s")
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            json.dump({"passed": len(RESULTS) - len(failed), "total": len(RESULTS),
                       "results": RESULTS}, fh, ensure_ascii=False, indent=1)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
