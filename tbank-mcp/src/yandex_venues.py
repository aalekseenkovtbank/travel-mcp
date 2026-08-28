"""Contract-gated Yandex venue adapter.

The public Organization Search schema does not promise photos or review metrics.
This adapter therefore fails closed unless the commercial response contains every
field required by the trip-page contract.  It never fabricates or substitutes a
generic image.
"""
from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

import requests
from pydantic import BaseModel, ConfigDict, Field

from .trip_page import Coordinates, DiningVenue, VenuePhoto


class YandexVenueError(RuntimeError):
    pass


class VenueSearchResult(BaseModel):
    model_config = ConfigDict(alias_generator=lambda value: "".join(
        [value.split("_")[0], *[part.title() for part in value.split("_")[1:]]]),
        populate_by_name=True, extra="forbid")
    venues: list[DiningVenue]
    rejected_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    source: str = "Yandex Maps commercial venue API"


def _first(mapping: dict, *keys: str):
    for key in keys:
        value = mapping.get(key)
        if value not in (None, "", []):
            return value
    return None


def _float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _categories(meta: dict, raw: dict) -> list[str]:
    values = _first(raw, "categories", "Categories") or _first(meta, "categories", "Categories") or []
    out = []
    for value in values:
        name = value.get("name") if isinstance(value, dict) else value
        if name and str(name) not in out:
            out.append(str(name))
    return out[:12]


def _kind(raw: dict, categories: list[str]) -> str:
    declared = str(_first(raw, "kind", "venueType", "type") or "").lower()
    haystack = " ".join([declared, *categories]).lower()
    if any(word in haystack for word in ("бар", "bar", "pub", "паб", "cocktail")):
        return "bar"
    return "restaurant"


def _photo_rows(raw: dict, meta: dict, maps_url: str) -> list[VenuePhoto]:
    values = (_first(raw, "photos", "Photos", "images", "Images")
              or _first(meta, "photos", "Photos", "images", "Images") or [])
    if isinstance(values, dict):
        values = values.get("items") or values.get("results") or []
    photos = []
    for value in values:
        if isinstance(value, str):
            url, attribution, source_url = value, "Яндекс Карты", maps_url
        elif isinstance(value, dict):
            url = _first(value, "url", "imageUrl", "href", "originalUrl")
            attribution = _first(value, "attribution", "author", "source") or "Яндекс Карты"
            source_url = _first(value, "sourceUrl", "source_url", "pageUrl") or maps_url
        else:
            continue
        try:
            photos.append(VenuePhoto(url=url, attribution=str(attribution), source_url=source_url))
        except Exception:
            continue
    return photos[:8]


def _normalise(raw: dict) -> DiningVenue:
    properties = raw.get("properties") if isinstance(raw.get("properties"), dict) else {}
    meta = (_first(properties, "CompanyMetaData", "companyMetaData")
            or _first(raw, "CompanyMetaData", "companyMetaData", "company") or {})
    if not isinstance(meta, dict):
        meta = {}
    venue_id = str(_first(raw, "id", "venueId") or _first(meta, "id") or "")
    name = str(_first(raw, "name") or _first(properties, "name") or _first(meta, "name") or "")
    address = str(_first(raw, "address") or _first(meta, "address")
                  or _first(properties, "description") or "")
    geometry = raw.get("geometry") or {}
    coordinate_row = (_first(raw, "coordinates", "location")
                      or geometry.get("coordinates") or {})
    if isinstance(coordinate_row, dict):
        latitude = _float(_first(coordinate_row, "latitude", "lat"))
        longitude = _float(_first(coordinate_row, "longitude", "lon", "lng"))
    elif isinstance(coordinate_row, (list, tuple)) and len(coordinate_row) >= 2:
        longitude, latitude = _float(coordinate_row[0]), _float(coordinate_row[1])
    else:
        latitude = longitude = None
    rating = _float(_first(raw, "rating") or _first(meta, "rating", "Rating"))
    rating_scale = _float(_first(raw, "ratingScale") or _first(meta, "ratingScale")) or 5
    review_count = _int(_first(raw, "reviewCount", "reviewsCount", "ratingCount")
                        or _first(meta, "reviewCount", "reviewsCount", "ratingCount"))
    maps_url = str(_first(raw, "yandexMapsUrl", "mapsUrl", "url") or "")
    if not maps_url.startswith("https://yandex.ru/") and venue_id:
        maps_url = f"https://yandex.ru/maps/org/{venue_id}"
    categories = _categories(meta, raw)
    photos = _photo_rows(raw, meta, maps_url)
    hours = _first(raw, "openingHours") or _first(meta, "openingHours")
    if not hours:
        hours_block = _first(meta, "Hours", "hours") or {}
        if isinstance(hours_block, dict):
            hours = _first(hours_block, "text")
    return DiningVenue(
        id=venue_id, kind=_kind(raw, categories), name=name, address=address,
        coordinates=Coordinates(latitude=latitude, longitude=longitude),
        photos=photos, rating=rating, rating_scale=rating_scale,
        review_count=review_count, yandex_maps_url=maps_url,
        categories=categories, opening_hours=str(hours or ""),
        price_level=str(_first(raw, "priceLevel") or _first(meta, "priceLevel") or ""),
    )


class YandexVenueProvider:
    def __init__(self, *, api_key: str | None = None, endpoint: str | None = None,
                 timeout: float = 15):
        self.api_key = api_key or os.environ.get("YANDEX_MAPS_API_KEY", "")
        self.endpoint = endpoint or os.environ.get(
            "YANDEX_VENUE_API_URL", "https://search-maps.yandex.ru/v1/")
        self.timeout = timeout

    def search(self, city: str, query: str, limit: int = 8) -> VenueSearchResult:
        if os.environ.get("YANDEX_VENUE_STORAGE_ALLOWED", "").lower() not in {"1", "true", "yes"}:
            raise YandexVenueError(
                "YANDEX_VENUE_STORAGE_ALLOWED=1 is required after confirming the commercial storage rights")
        if not self.api_key:
            raise YandexVenueError("YANDEX_MAPS_API_KEY is not configured")
        if urlparse(self.endpoint).scheme != "https":
            raise YandexVenueError("YANDEX_VENUE_API_URL must use HTTPS")
        if not city.strip() or not query.strip():
            raise YandexVenueError("city and query are required")
        limit = max(1, min(int(limit), 20))
        try:
            response = requests.get(
                self.endpoint,
                params={"apikey": self.api_key, "text": f"{city}, {query}",
                        "type": "biz", "lang": "ru_RU", "results": limit},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            # requests includes the query string (and therefore the key) in its
            # exception text. Never propagate that string to MCP or a trace.
            raise YandexVenueError(
                f"Yandex venue request failed ({type(exc).__name__})") from None
        rows = payload.get("results") or payload.get("venues") or payload.get("features") or []
        venues, rejected = [], 0
        for row in rows:
            if not isinstance(row, dict):
                rejected += 1
                continue
            try:
                venues.append(_normalise(row))
            except Exception:
                rejected += 1
        warnings = []
        if rejected:
            warnings.append(
                f"Отклонено карточек без обязательных договорных полей: {rejected}.")
        if not venues:
            warnings.append(
                "API не вернул ни одной полной карточки с фото, рейтингом и числом отзывов.")
        return VenueSearchResult(venues=venues, rejected_count=rejected, warnings=warnings)
