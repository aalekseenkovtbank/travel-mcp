"""Public, credential-free restaurant search backed by Yandex Maps pages.

The endpoint is the same server-rendered public search page a browser opens.
Results stay in memory and are returned with direct Yandex Maps organization
links; no bank session, cookies, API keys, booking, or payment are involved.
"""
from __future__ import annotations

import json
import math
import os
from html.parser import HTMLParser
from typing import Any
from urllib.parse import quote

import requests

from . import tls
from .client import TbankApiError

YANDEX_MAPS_URL = os.environ.get("YANDEX_MAPS_URL", "https://yandex.ru/maps/")
TIMEOUT_SECONDS = max(
    1.0, float(os.environ.get("TRAVEL_PROVIDER_TIMEOUT_SECONDS", "15")))
USER_AGENT = os.environ.get(
    "TBANK_MCP_HTTP_USER_AGENT",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "Chrome/140.0 Safari/537.36 TravelNova/0.3",
)
MAX_PAGE_BYTES = 8 * 1024 * 1024


class _JsonScriptParser(HTMLParser):
    """Collect large JSON hydration scripts without parsing page markup."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._collecting = False
        self._chunks: list[str] = []
        self.payloads: list[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script" and dict(attrs).get("type") == "application/json":
            self._collecting = True
            self._chunks = []

    def handle_data(self, data: str) -> None:
        if self._collecting:
            self._chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "script" or not self._collecting:
            return
        raw = "".join(self._chunks).strip()
        self._collecting = False
        self._chunks = []
        if len(raw) < 100:
            return
        try:
            value = json.loads(raw)
        except (TypeError, ValueError):
            return
        if isinstance(value, dict):
            self.payloads.append(value)


def _trusted_requester() -> requests.Session:
    tls.rebuild_bundle()
    session = requests.Session()
    session.mount("https://", tls.RobustTLSAdapter())
    session.verify = tls.BUNDLE
    return session


def _coordinates(
    latitude: float | None, longitude: float | None,
) -> tuple[float, float] | None:
    if (latitude is None) != (longitude is None):
        raise TbankApiError(
            "BAD_COORDINATES", "latitude и longitude нужно передавать вместе.")
    if latitude is None or longitude is None:
        return None
    try:
        lat, lon = float(latitude), float(longitude)
    except (TypeError, ValueError) as exc:
        raise TbankApiError(
            "BAD_COORDINATES", "Координаты должны быть числами.") from exc
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise TbankApiError(
            "BAD_COORDINATES",
            "latitude должен быть -90..90, longitude -180..180.",
        )
    return lat, lon


def _distance(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    radius = 6_371_000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    value = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return round(radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value)))


def _result_block(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    for payload in sorted(payloads, key=lambda item: len(json.dumps(item)), reverse=True):
        stack = payload.get("stack")
        if not isinstance(stack, list):
            continue
        for panel in stack:
            results = panel.get("results") if isinstance(panel, dict) else None
            if isinstance(results, dict) and isinstance(results.get("items"), list):
                return results
    raise TbankApiError(
        "BAD_SOURCE_RESPONSE",
        "Яндекс Карты не вернули список организаций на публичной странице поиска.",
    )


def _photo_url(template: Any) -> str:
    value = str(template or "").strip()
    if value.startswith("//"):
        value = "https:" + value
    if "%s" in value:
        value = value.replace("%s", "orig")
    return value if value.startswith("https://") else ""


def _price_label(item: dict[str, Any]) -> str:
    subtitles = item.get("subtitleItems")
    if isinstance(subtitles, list):
        for subtitle in subtitles:
            if not isinstance(subtitle, dict):
                continue
            if subtitle.get("type") == "average_bill2":
                return str(subtitle.get("text") or "").strip()
    features = item.get("features")
    if isinstance(features, list):
        for feature in features:
            if isinstance(feature, dict) and feature.get("id") == "average_bill2":
                return str(feature.get("value") or "").strip()
    return ""


def _venue_url(item: dict[str, Any], business_id: str) -> str:
    slug = str(item.get("seoname") or "").strip()
    if slug:
        return f"https://yandex.ru/maps/org/{quote(slug, safe='')}/{business_id}/"
    return f"https://yandex.ru/maps/?oid={business_id}"


def _restaurant_card(
    item: dict[str, Any], anchor: tuple[float, float] | None,
) -> dict[str, Any] | None:
    if item.get("type") != "business":
        return None
    business_id = str(item.get("id") or "").strip()
    name = str(item.get("title") or item.get("shortTitle") or "").strip()
    raw_coordinates = item.get("coordinates")
    if not business_id or not name or not isinstance(raw_coordinates, list):
        return None
    try:
        lon, lat = float(raw_coordinates[0]), float(raw_coordinates[1])
    except (IndexError, TypeError, ValueError):
        return None
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        return None

    raw_categories = item.get("categories")
    categories = [
        str(category.get("name") or "").strip()
        for category in (raw_categories if isinstance(raw_categories, list) else [])
        if isinstance(category, dict) and str(category.get("name") or "").strip()
    ][:12]
    category_classes = {
        str(category.get("class") or "").strip()
        for category in (raw_categories if isinstance(raw_categories, list) else [])
        if isinstance(category, dict)
    }
    if not category_classes.intersection({"restaurants", "cafe", "bars"}):
        return None
    kind = "bar" if category_classes <= {"bars"} else "restaurant"

    rating_data = item.get("ratingData")
    rating = review_count = None
    if isinstance(rating_data, dict):
        try:
            rating = float(rating_data["ratingValue"])
        except (KeyError, TypeError, ValueError):
            rating = None
        try:
            review_count = int(rating_data["reviewCount"])
        except (KeyError, TypeError, ValueError):
            review_count = None

    source_url = _venue_url(item, business_id)
    photos: list[dict[str, str]] = []
    photo_data = item.get("photos")
    photo_items = photo_data.get("items") if isinstance(photo_data, dict) else None
    for photo in photo_items if isinstance(photo_items, list) else []:
        url = _photo_url(photo.get("urlTemplate") if isinstance(photo, dict) else "")
        if url and url not in {row["url"] for row in photos}:
            photos.append({
                "url": url,
                "attribution": "Фото: Яндекс Карты",
                "sourceUrl": source_url,
            })
        if len(photos) == 3:
            break

    card: dict[str, Any] = {
        "id": f"yandex-{business_id}",
        "kind": kind,
        "name": name,
        "address": str(item.get("fullAddress") or item.get("address") or "").strip(),
        "coordinates": {"latitude": lat, "longitude": lon},
        "photos": photos,
        "rating": rating,
        "ratingScale": 5 if rating is not None else None,
        "reviewCount": review_count,
        "sourceUrl": source_url,
        "source": "Yandex Maps",
        "categories": categories,
        "openingHours": str(item.get("workingTimeText") or "").strip(),
        "priceLevel": _price_label(item),
    }
    if anchor is not None:
        card["distanceMeters"] = _distance(anchor[0], anchor[1], lat, lon)
    return card


def search_yandex_restaurants(
    *,
    city: str,
    anchor_name: str = "",
    address: str = "",
    latitude: float | None = None,
    longitude: float | None = None,
    radius_meters: int = 1_800,
    limit: int = 5,
    requester: Any | None = None,
) -> dict[str, Any]:
    """Return report-ready restaurant cards from a public Yandex Maps search."""
    city = str(city or "").strip()
    anchor_name = str(anchor_name or "").strip()
    address = str(address or "").strip()
    if not city:
        raise TbankApiError("BAD_CITY", "Передай city.")
    if not 1 <= int(limit) <= 20:
        raise TbankApiError("BAD_LIMIT", "limit должен быть от 1 до 20.")
    if not 250 <= int(radius_meters) <= 10_000:
        raise TbankApiError(
            "BAD_RADIUS", "radius_meters должен быть от 250 до 10000.")
    anchor = _coordinates(latitude, longitude)
    query_parts = ["рестораны"]
    if anchor is None:
        query_parts.extend(value for value in (address or anchor_name, city) if value)
    query = ", ".join(query_parts)
    params: dict[str, str | int] = {
        "mode": "search",
        "text": query,
        "type": "biz",
    }
    if anchor is not None:
        lat, lon = anchor
        lon_span = 2 * int(radius_meters) / (
            111_320 * max(0.2, math.cos(math.radians(lat))))
        lat_span = 2 * int(radius_meters) / 110_540
        params.update({
            "ll": f"{lon:.6f},{lat:.6f}",
            "sll": f"{lon:.6f},{lat:.6f}",
            "sspn": f"{lon_span:.6f},{lat_span:.6f}",
            "z": "15",
        })

    requester = requester or _trusted_requester()
    try:
        response = requester.get(
            YANDEX_MAPS_URL,
            params=params,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "ru-RU,ru;q=0.9",
            },
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.Timeout as exc:
        raise TbankApiError(
            "SOURCE_TIMEOUT", "Яндекс Карты не ответили вовремя.") from exc
    except requests.RequestException as exc:
        raise TbankApiError(
            "SOURCE_UNAVAILABLE", f"Яндекс Карты недоступны: {exc}") from exc
    content = response.content
    if not content or len(content) > MAX_PAGE_BYTES:
        raise TbankApiError(
            "BAD_SOURCE_RESPONSE", "Яндекс Карты вернули страницу неожиданного размера.")
    parser = _JsonScriptParser()
    try:
        parser.feed(response.text)
        results = _result_block(parser.payloads)
    except TbankApiError:
        raise
    except Exception as exc:
        raise TbankApiError(
            "BAD_SOURCE_RESPONSE", "Не удалось прочитать ответ Яндекс.Карт.") from exc

    candidates: list[dict[str, Any]] = []
    for item in results.get("items") or []:
        if not isinstance(item, dict):
            continue
        card = _restaurant_card(item, anchor)
        if card is None:
            continue
        if anchor is not None and card.get("distanceMeters", 0) > int(radius_meters):
            continue
        candidates.append(card)
    candidates.sort(key=lambda card: (
        card.get("distanceMeters", 0) if anchor is not None else 0,
        -(card.get("rating") or 0),
        card["name"].lower(),
    ))
    shown = candidates[: int(limit)]
    if not shown:
        raise TbankApiError(
            "NO_RESTAURANTS",
            f"Яндекс Карты не нашли рестораны рядом с {anchor_name or address or city}.",
        )
    total = int(results.get("totalResultCount") or len(candidates))
    warnings = []
    if len(shown) < min(int(limit), total):
        warnings.append(
            f"В заданном радиусе найдено только {len(shown)} ресторанов из запрошенных {limit}.")
    return {
        "data": {
            "city": city,
            "anchor": {
                "name": anchor_name or address or city,
                "latitude": anchor[0] if anchor is not None else None,
                "longitude": anchor[1] if anchor is not None else None,
            },
            "radiusMeters": int(radius_meters) if anchor is not None else None,
            "total": total,
            "restaurants": shown,
        },
        "warnings": warnings,
        "source": "Yandex Maps",
        "complete": len(shown) >= min(int(limit), total),
    }
