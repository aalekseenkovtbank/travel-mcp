"""Public OpenStreetMap/Nominatim primitives for the travel-only MCP surface."""
from __future__ import annotations

import math
import os
import threading
import time
from typing import Any

import requests

from . import tls
from .client import TbankApiError

RADIUS_METERS = 1_800
OVERPASS_URL = os.environ.get(
    "OVERPASS_URL", "https://maps.mail.ru/osm/tools/overpass/api/interpreter")
NOMINATIM_URL = os.environ.get(
    "NOMINATIM_URL", "https://nominatim.openstreetmap.org")
TIMEOUT_SECONDS = max(1.0, float(os.environ.get("TRAVEL_PROVIDER_TIMEOUT_SECONDS", "15")))
USER_AGENT = os.environ.get(
    "TRAVEL_HTTP_USER_AGENT", "tbank-travel-mcp/0.1 (local read-only travel assistant)")

_geocode_lock = threading.Lock()
_last_geocode_at = 0.0


def _trusted_requester() -> requests.Session:
    """Create a credential-free session using the project's explicit CA bundle."""
    tls.rebuild_bundle()
    session = requests.Session()
    session.mount("https://", tls.RobustTLSAdapter())
    session.verify = tls.BUNDLE
    return session


def _coordinates(latitude: float | None, longitude: float | None) -> tuple[float, float] | None:
    if (latitude is None) != (longitude is None):
        raise TbankApiError(
            "BAD_COORDINATES", "latitude и longitude нужно передавать вместе.")
    if latitude is None or longitude is None:
        return None
    try:
        lat, lon = float(latitude), float(longitude)
    except (TypeError, ValueError) as exc:
        raise TbankApiError("BAD_COORDINATES", "Координаты должны быть числами.") from exc
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise TbankApiError(
            "BAD_COORDINATES", "latitude должен быть -90..90, longitude -180..180.")
    return lat, lon


def _json(response: Any, source: str) -> Any:
    try:
        response.raise_for_status()
        payload = response.json()
    except requests.Timeout as exc:
        raise TbankApiError("SOURCE_TIMEOUT", f"{source} не ответил вовремя.") from exc
    except requests.RequestException as exc:
        raise TbankApiError("SOURCE_UNAVAILABLE", f"{source} недоступен: {exc}") from exc
    except (TypeError, ValueError) as exc:
        raise TbankApiError("BAD_SOURCE_RESPONSE", f"{source} вернул невалидный JSON.") from exc
    return payload


def _geocode(query: str, requester: Any) -> tuple[float, float] | None:
    global _last_geocode_at
    # Nominatim's public service asks clients not to exceed one request per second.
    with _geocode_lock:
        delay = 1.0 - (time.monotonic() - _last_geocode_at)
        if delay > 0:
            time.sleep(delay)
        try:
            response = requester.get(
                f"{NOMINATIM_URL.rstrip('/')}/search",
                params={"q": query, "format": "jsonv2", "limit": 1},
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                timeout=TIMEOUT_SECONDS,
            )
        except requests.Timeout as exc:
            raise TbankApiError("SOURCE_TIMEOUT", "Nominatim не ответил вовремя.") from exc
        except requests.RequestException as exc:
            raise TbankApiError("SOURCE_UNAVAILABLE", f"Nominatim недоступен: {exc}") from exc
        finally:
            _last_geocode_at = time.monotonic()
    payload = _json(response, "Nominatim")
    if not isinstance(payload, list) or not payload:
        return None
    row = payload[0] if isinstance(payload[0], dict) else {}
    try:
        return float(row["lat"]), float(row["lon"])
    except (KeyError, TypeError, ValueError):
        return None


def _distance(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    radius = 6_371_000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    return round(radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def _address(tags: dict[str, Any]) -> str:
    street = str(tags.get("addr:street") or "").strip()
    number = str(tags.get("addr:housenumber") or "").strip()
    city = str(tags.get("addr:city") or "").strip()
    first = " ".join(value for value in (street, number) if value)
    return ", ".join(value for value in (first, city) if value)


def _category(tags: dict[str, Any]) -> str:
    return str(
        tags.get("amenity") or tags.get("tourism") or tags.get("historic") or
        tags.get("leisure") or tags.get("natural") or "place")


def search_nearby(
    *,
    city: str,
    anchor_name: str = "",
    address: str = "",
    latitude: float | None = None,
    longitude: float | None = None,
    include_poi: bool = False,
    place_kinds: str = "culture",
    limit: int = 20,
    requester: Any | None = None,
) -> dict[str, Any]:
    city = str(city or "").strip()
    anchor_name = str(anchor_name or "").strip()
    address = str(address or "").strip()
    if not city:
        raise TbankApiError("BAD_CITY", "Передай city.")
    if limit < 0 or limit > 100:
        raise TbankApiError("BAD_LIMIT", "limit должен быть от 0 до 100.")
    requester = requester or _trusted_requester()

    resolved = _coordinates(latitude, longitude)
    geocoded = False
    if resolved is None:
        target = address or anchor_name
        if not target:
            raise TbankApiError(
                "BAD_ANCHOR", "Передай координаты, address или anchor_name.")
        resolved = _geocode(f"{target}, {city}, Россия", requester)
        geocoded = True
    if resolved is None:
        raise TbankApiError(
            "LOCATION_NOT_FOUND", f"Nominatim не нашёл «{address or anchor_name}» в городе {city}.")
    anchor_lat, anchor_lon = resolved

    allowed_kinds = {"culture", "nature", "nightlife"}
    requested_kinds = {value.strip().lower() for value in str(place_kinds or "").split(",") if value.strip()}
    unknown = requested_kinds - allowed_kinds
    if unknown:
        raise TbankApiError(
            "BAD_PLACE_KIND", "place_kinds: culture, nature и/или nightlife через запятую.")
    requested_kinds = requested_kinds or {"culture"}
    poi_queries: list[str] = []
    if include_poi and "culture" in requested_kinds:
        poi_queries.extend([
            'nwr[tourism~"museum|attraction|gallery"]', "nwr[historic]",
        ])
    if include_poi and "nature" in requested_kinds:
        poi_queries.extend([
            'nwr[tourism="viewpoint"]', 'nwr[leisure~"park|nature_reserve|garden"]',
            'nwr[natural~"beach|wood"]',
        ])
    if include_poi and "nightlife" in requested_kinds:
        poi_queries.append('nwr[amenity~"bar|pub|nightclub|music_venue"]')
    selectors = ['nwr[amenity~"restaurant|cafe|fast_food|food_court"]', *poi_queries]
    body = "\n".join(
        f"  {selector}(around:{RADIUS_METERS},{anchor_lat},{anchor_lon});"
        for selector in selectors)
    query = f"[out:json][timeout:12];(\n{body}\n);out center tags;"
    try:
        response = requester.post(
            OVERPASS_URL,
            data={"data": query},
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=TIMEOUT_SECONDS,
        )
    except requests.Timeout as exc:
        raise TbankApiError("SOURCE_TIMEOUT", "Overpass не ответил вовремя.") from exc
    except requests.RequestException as exc:
        raise TbankApiError("SOURCE_UNAVAILABLE", f"Overpass недоступен: {exc}") from exc
    payload = _json(response, "Overpass")
    elements = payload.get("elements") if isinstance(payload, dict) else None
    if not isinstance(elements, list):
        raise TbankApiError("BAD_SOURCE_RESPONSE", "Overpass не вернул elements[].")

    places: list[dict[str, Any]] = []
    seen: set[str] = set()
    for element in elements:
        if not isinstance(element, dict):
            continue
        tags = element.get("tags") if isinstance(element.get("tags"), dict) else {}
        name = str(tags.get("name") or tags.get("brand") or "").strip()
        if not name:
            continue
        center = element.get("center") if isinstance(element.get("center"), dict) else {}
        try:
            lat = float(element.get("lat", center.get("lat")))
            lon = float(element.get("lon", center.get("lon")))
        except (TypeError, ValueError):
            continue
        distance = _distance(anchor_lat, anchor_lon, lat, lon)
        if distance > RADIUS_METERS:
            continue
        osm_type = str(element.get("type") or "node")
        osm_id = str(element.get("id") or "")
        key = f"{osm_type}:{osm_id}"
        if not osm_id or key in seen:
            continue
        seen.add(key)
        amenity = str(tags.get("amenity") or "")
        kind = "restaurant" if amenity in {"restaurant", "cafe", "fast_food", "food_court"} else "poi"
        places.append({
            "osmId": key,
            "type": kind,
            "name": name,
            "latitude": lat,
            "longitude": lon,
            "address": _address(tags),
            "cuisine": str(tags.get("cuisine") or ""),
            "category": _category(tags),
            "openingHours": str(tags.get("opening_hours") or ""),
            "distanceMeters": distance,
            "source": "OpenStreetMap",
            "sourceUrl": f"https://www.openstreetmap.org/{osm_type}/{osm_id}",
        })
    places.sort(key=lambda item: (item["distanceMeters"], item["name"].lower()))
    shown = places[:limit] if limit > 0 else places
    warnings = [] if len(shown) == len(places) else [f"Показано {len(shown)} из {len(places)} мест."]
    return {
        "data": {
            "city": city,
            "anchor": {
                "name": anchor_name or address or city,
                "latitude": anchor_lat,
                "longitude": anchor_lon,
                "geocoded": geocoded,
            },
            "radiusMeters": RADIUS_METERS,
            "total": len(places),
            "places": shown,
        },
        "warnings": warnings,
        "source": "OpenStreetMap",
        "complete": len(shown) == len(places),
    }
