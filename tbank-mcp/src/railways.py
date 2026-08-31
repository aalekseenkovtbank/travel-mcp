"""Public, read-only T-Bank Railways primitives for T-Bank MCP."""
from __future__ import annotations

import os
import re
from datetime import date
from typing import Any

import requests

from . import tls
from .client import TbankApiError

STATIONS_URL = os.environ.get(
    "TBANK_TRAINS_STATIONS_URL",
    "https://search.tbank.ru/search/fulltext?context=api",
)
SEARCH_URL = os.environ.get(
    "TBANK_TRAINS_SEARCH_URL", "https://trains.tbank.ru/api/search/trains")
TIMEOUT_SECONDS = max(
    1.0, float(os.environ.get("TRAVEL_PROVIDER_TIMEOUT_SECONDS", "20")))
SEARCH_TIMEOUT_SECONDS = max(
    TIMEOUT_SECONDS,
    float(os.environ.get("TRAVEL_RAIL_SEARCH_TIMEOUT_SECONDS", "60")),
)
USER_AGENT = os.environ.get(
    "TBANK_MCP_HTTP_USER_AGENT", "tbank-mcp/0.2 (travel search)")
SOURCE = "T-Bank Railways"


def _verify_bundle() -> str:
    if not os.path.exists(tls.BUNDLE):
        tls.rebuild_bundle()
    return tls.BUNDLE


def _payload(response: Any, source: str) -> Any:
    try:
        response.raise_for_status()
        payload = response.json()
    except requests.Timeout as exc:
        raise TbankApiError("SOURCE_TIMEOUT", f"{source} не ответил вовремя.") from exc
    except requests.RequestException as exc:
        message = ""
        try:
            body = response.json()
            if isinstance(body, dict):
                message = str(body.get("errorMessage") or body.get("message") or "").strip()
        except (TypeError, ValueError):
            pass
        suffix = f": {message}" if message else "."
        raise TbankApiError("SOURCE_UNAVAILABLE", f"{source} отклонил запрос{suffix}") from exc
    except (TypeError, ValueError) as exc:
        raise TbankApiError(
            "BAD_SOURCE_RESPONSE", f"{source} вернул невалидный JSON.") from exc
    return payload


def station_suggestions(
    *,
    search_text: str,
    limit: int = 20,
    requester: Any = requests,
) -> dict[str, Any]:
    """Resolve a station name to search codes accepted by train search."""
    query = str(search_text or "").strip()
    if not query:
        raise TbankApiError("BAD_QUERY", "Передай search_text с названием города или станции.")
    if limit < 1 or limit > 50:
        raise TbankApiError("BAD_LIMIT", "limit должен быть от 1 до 50.")

    try:
        response = requester.post(
            STATIONS_URL,
            json={
                "searchTypes": ["railway_stations"],
                "text": query,
                "maxObjectsCount": limit,
            },
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=TIMEOUT_SECONDS,
            verify=_verify_bundle(),
        )
    except requests.Timeout as exc:
        raise TbankApiError("SOURCE_TIMEOUT", f"{SOURCE} не ответил вовремя.") from exc
    except requests.RequestException as exc:
        raise TbankApiError("SOURCE_UNAVAILABLE", f"{SOURCE} недоступен: {exc}") from exc
    body = _payload(response, SOURCE)
    payload = body.get("payload") if isinstance(body, dict) else None
    rows = payload.get("sortedByScoreObjects") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise TbankApiError(
            "BAD_SOURCE_RESPONSE",
            f"{SOURCE} не вернул payload.sortedByScoreObjects[].")

    stations = []
    for row in rows[:limit]:
        if not isinstance(row, dict):
            continue
        source = row.get("objectSource")
        if not isinstance(source, dict):
            continue
        address = source.get("addressRu")
        address = address if isinstance(address, dict) else {}
        search_code = str(source.get("searchCode") or "")
        if not re.fullmatch(r"\d{6,10}", search_code):
            continue
        stations.append({
            "id": str(source.get("id") or row.get("id") or ""),
            "type": str(source.get("type") or ""),
            "searchCode": search_code,
            "station": str(address.get("station") or ""),
            "city": str(address.get("city") or ""),
            "region": str(address.get("region") or ""),
            "country": str(address.get("country") or ""),
            "popularity": source.get("popularity"),
            "score": row.get("score"),
        })
    hits = int(payload.get("hitsCount") or len(rows))
    return {
        "data": {
            "query": query,
            "total": hits,
            "stations": stations,
            "codeCompatibility": "searchCode is accepted by train_search",
        },
        "warnings": ([] if len(stations) >= hits else
                     [f"Показано {len(stations)} из {hits} станций."]),
        "source": SOURCE,
        "complete": len(stations) >= hits,
    }


def search_trains(
    *,
    origin: str,
    destination: str,
    departure_date: str,
    adults: int = 1,
    children: int = 0,
    requester: Any = requests,
) -> dict[str, Any]:
    origin = str(origin or "").strip()
    destination = str(destination or "").strip()
    if not re.fullmatch(r"\d{6,10}", origin) or not re.fullmatch(r"\d{6,10}", destination):
        raise TbankApiError(
            "BAD_STATION_CODE",
            "origin и destination должны быть числовыми РЖД-кодами, например "
            "2000000 и 2004000; используй searchCode из train_stations.",
        )
    try:
        parsed_date = date.fromisoformat(str(departure_date or ""))
    except ValueError as exc:
        raise TbankApiError("BAD_DATE", "date должен быть YYYY-MM-DD.") from exc
    if not 1 <= int(adults) <= 9 or not 0 <= int(children) <= 9:
        raise TbankApiError("BAD_PASSENGERS", "adults: 1..9, children: 0..9.")
    if int(adults) + int(children) > 9:
        raise TbankApiError("BAD_PASSENGERS", "Всего должно быть не больше 9 пассажиров.")

    request_body = {
        "directions": [{
            "origin": origin,
            "destination": destination,
            "departureDate": parsed_date.isoformat(),
        }],
        "adultsCount": int(adults),
        "childrenCount": int(children),
    }
    try:
        response = requester.post(
            SEARCH_URL,
            json=request_body,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=SEARCH_TIMEOUT_SECONDS,
            verify=_verify_bundle(),
        )
    except requests.Timeout as exc:
        raise TbankApiError("SOURCE_TIMEOUT", f"{SOURCE} не ответил вовремя.") from exc
    except requests.RequestException as exc:
        raise TbankApiError("SOURCE_UNAVAILABLE", f"{SOURCE} недоступен: {exc}") from exc
    body = _payload(response, SOURCE)
    directions = body.get("directions") if isinstance(body, dict) else None
    if not isinstance(directions, list):
        raise TbankApiError("BAD_SOURCE_RESPONSE", f"{SOURCE} не вернул directions[].")
    ways: list[dict[str, Any]] = []
    for direction in directions:
        if isinstance(direction, dict) and isinstance(direction.get("ways"), list):
            ways.extend(item for item in direction["ways"] if isinstance(item, dict))
    return {
        "data": {
            "origin": origin,
            "destination": destination,
            "date": parsed_date.isoformat(),
            "adults": int(adults),
            "children": int(children),
            "ways": ways,
        },
        "warnings": [],
        "source": SOURCE,
        "complete": True,
    }
