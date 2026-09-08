"""Hotel input validation and response-shape normalization."""
from __future__ import annotations

import json
from datetime import datetime, timedelta

from ..client import TbankApiError
from .response import _flat, _https_image_url

def _hotel_children(value: str) -> list[int]:
    """Parse MCP-friendly child ages: empty, ``5,12`` or JSON ``[5, 12]``."""
    raw = str(value or "").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw) if raw.startswith("[") else raw.split(",")
    except json.JSONDecodeError:
        raise TbankApiError(
            "BAD_CHILDREN_AGES", "children_ages: передай, например, 5,12 или [5,12].")
    if not isinstance(parsed, list) or len(parsed) > 6:
        raise TbankApiError(
            "BAD_CHILDREN_AGES", "children_ages должен содержать не больше 6 возрастов.")
    ages = []
    for item in parsed:
        try:
            # Reject 5.5 instead of silently turning it into 5.
            age = int(str(item).strip())
        except (TypeError, ValueError):
            raise TbankApiError(
                "BAD_CHILDREN_AGES", f"Возраст ребёнка должен быть целым числом: {item!r}.")
        if str(item).strip() not in (str(age), f"{age}.0") or not 0 <= age <= 17:
            raise TbankApiError(
                "BAD_CHILDREN_AGES", f"Возраст ребёнка должен быть от 0 до 17: {item!r}.")
        ages.append(age)
    return ages

def _hotel_date(value: str, field: str):
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        raise TbankApiError("BAD_DATE", f"{field}: нужна дата YYYY-MM-DD, пришло {value!r}.")

def _hotel_search_window(checkin_date: str, checkout_date: str) -> int:
    """Validate the date window shared by Hotels Search API methods."""
    start = _hotel_date(checkin_date, "checkin_date")
    end = _hotel_date(checkout_date, "checkout_date")
    today = datetime.now().date()
    if start < today or start > today + timedelta(days=730):
        raise TbankApiError(
            "BAD_CHECKIN_DATE",
            "checkin_date должен быть от сегодняшней даты до сегодня + 730 дней.")
    nights = (end - start).days
    if not 1 <= nights <= 30:
        raise TbankApiError(
            "BAD_CHECKOUT_DATE", "checkout_date должен быть через 1–30 ночей после заезда.")
    return nights

def _hotel_search_guests(adults: int, children_ages: list[int] | None) -> list[int]:
    if isinstance(adults, bool) or not isinstance(adults, int) or not 1 <= adults <= 6:
        raise TbankApiError("BAD_GUESTS", "adults должен быть целым числом от 1 до 6.")
    ages = _hotel_children(children_ages or [])
    if len(ages) > 4:
        raise TbankApiError(
            "BAD_CHILDREN_AGES", "children_ages должен содержать не больше 4 возрастов.")
    return ages

def _hotel_positive_ids(values, field: str, *, required: bool,
                        max_count: int | None = None) -> list[int]:
    if values is None:
        values = []
    if not isinstance(values, list):
        raise TbankApiError("BAD_HOTEL_IDS", f"{field} должен быть JSON-массивом id.")
    if required and not values:
        raise TbankApiError("BAD_HOTEL_IDS", f"{field} должен содержать хотя бы один id.")
    if max_count is not None and len(values) > max_count:
        raise TbankApiError(
            "BAD_HOTEL_IDS", f"{field} должен содержать не больше {max_count} id.")
    normalized = []
    seen = set()
    for index, value in enumerate(values):
        if isinstance(value, bool):
            raise TbankApiError(
                "BAD_HOTEL_IDS", f"{field}[{index}] должен быть положительным целым id.")
        try:
            hotel_id = int(value)
        except (TypeError, ValueError):
            raise TbankApiError(
                "BAD_HOTEL_IDS", f"{field}[{index}] должен быть положительным целым id.")
        if hotel_id <= 0 or str(value).strip() != str(hotel_id):
            raise TbankApiError(
                "BAD_HOTEL_IDS", f"{field}[{index}] должен быть положительным целым id.")
        if hotel_id not in seen:
            seen.add(hotel_id)
            normalized.append(hotel_id)
    return normalized

def _hotel_search_filters_input(filters: list[dict] | None) -> list[dict]:
    """Validate the simple filterId/value[] union used by Search API methods."""
    if filters is None:
        return []
    if not isinstance(filters, list):
        raise TbankApiError("BAD_FILTERS", "filters должен быть JSON-массивом.")
    normalized = []
    for index, item in enumerate(filters):
        if not isinstance(item, dict):
            raise TbankApiError("BAD_FILTER", f"filters[{index}] должен быть JSON-объектом.")
        filter_id = str(item.get("filterId") or "").strip()
        # The searchFilters_v3 example says `values`, while its field table and
        # getLatestHotelOffer both say `value`. Accept the documented alias from
        # MCP callers, but always put the canonical singular key on the wire.
        values = item.get("value")
        if values is None:
            values = item.get("values")
        if not filter_id or len(filter_id) > 100:
            raise TbankApiError(
                "BAD_FILTER", f"filters[{index}].filterId должен быть непустой строкой.")
        if (not isinstance(values, list) or not values or
                any(not isinstance(value, str) or not value.strip()
                    for value in values)):
            raise TbankApiError(
                "BAD_FILTER", f"filters[{index}].value должен быть непустым массивом строк.")
        normalized.append({
            "filterId": filter_id,
            "value": [value.strip() for value in values],
        })
    return normalized

def _hotel_map_frame(value: dict | None) -> dict | None:
    if value is None:
        return None
    if not isinstance(value, dict) or not isinstance(value.get("viewPort"), dict):
        raise TbankApiError(
            "BAD_MAP_FRAME", "map_frame_input должен содержать объект viewPort.")
    viewport = value["viewPort"]
    normalized = {}
    for corner in ("topLeft", "bottomRight"):
        point = viewport.get(corner)
        if not isinstance(point, dict):
            raise TbankApiError(
                "BAD_MAP_FRAME", f"map_frame_input.viewPort.{corner} обязателен.")
        latitude, longitude = point.get("latitude"), point.get("longitude")
        if (isinstance(latitude, bool) or isinstance(longitude, bool) or
                not isinstance(latitude, (int, float)) or
                not isinstance(longitude, (int, float)) or
                not -90 <= latitude <= 90 or not -180 <= longitude <= 180):
            raise TbankApiError(
                "BAD_MAP_FRAME",
                f"map_frame_input.viewPort.{corner}: нужны допустимые latitude/longitude.")
        normalized[corner] = {
            "latitude": float(latitude), "longitude": float(longitude),
        }
    return {"viewPort": normalized}

def _hotel_address(hotel: dict) -> str:
    """Address across the search-card and hotel-detail response shapes."""
    loc = hotel.get("hotelLocation") or hotel.get("location") or {}
    if isinstance(loc, str):
        return _flat(loc)
    if not isinstance(loc, dict):
        loc = {}
    address = (loc.get("address") or loc.get("fullAddress")
               or hotel.get("address") or hotel.get("areaLocation") or "")
    if isinstance(address, dict):
        address = address.get("name") or address.get("address") or ""
    return _flat(address)

def _hotel_amount(value) -> float:
    if isinstance(value, dict):
        value = value.get("amount") or value.get("value")
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

def cap_hotel_photos(rows: list[dict], limit: int = 3) -> list[dict]:
    """Return copies with at most ``limit`` photo URLs per hotel row."""
    collection_keys = {"images", "imageurls", "photos", "photourls"}
    single_keys = {"imageurl", "photo", "photourl"}

    def cap_one(row: dict) -> dict:
        budget = max(0, int(limit))

        def walk(value):
            nonlocal budget
            if isinstance(value, list):
                return [walk(item) for item in value]
            if isinstance(value, dict):
                out = {}
                for key, item in value.items():
                    normalized = str(key).lower()
                    if normalized in collection_keys and isinstance(item, list):
                        kept = item[:budget]
                        budget -= len(kept)
                        out[key] = kept
                    elif normalized in single_keys and item:
                        if budget > 0:
                            out[key] = item
                            budget -= 1
                    else:
                        out[key] = walk(item)
                return out
            return value

        return walk(row)

    return [cap_one(row) for row in rows]


def _hotel_coordinates(hotel: dict) -> tuple[float | None, float | None]:
    candidates = [hotel.get("coordinates"), hotel.get("geo"),
                  hotel.get("hotelLocation"), hotel.get("location")]
    for value in candidates:
        if not isinstance(value, dict):
            continue
        latitude = value.get("latitude") or value.get("lat")
        longitude = value.get("longitude") or value.get("lon") or value.get("lng")
        try:
            if latitude is not None and longitude is not None:
                return float(latitude), float(longitude)
        except (TypeError, ValueError):
            continue
    return None, None

def _hotel_image_urls(hotel: dict, limit: int) -> list[str]:
    if limit == 0:
        return []
    urls: list[str] = []
    for item in hotel.get("images") or []:
        if isinstance(item, dict):
            value = (item.get("url") or item.get("URL") or item.get("imageUrl")
                     or item.get("templateUrl"))
        else:
            value = item
        url = _https_image_url(value, size="1024x768")
        if url and url not in urls:
            urls.append(url)
        if limit > 0 and len(urls) >= limit:
            break
    return urls

_HOTEL_ARRAY_FILTERS = {
    "accommodation_types", "chains", "meal_types", "payment_places", "stars",
    "hotel_entertainments", "hotel_facilities", "room_facilities", "bed_types",
}

_HOTEL_BOOLEAN_FILTERS = {
    "free_cancellation_allowed", "payment_card_not_required", "photos_available",
}

def _hotel_id(value: str) -> str:
    hotel_id = str(value or "").strip()
    if not hotel_id.isdigit() or int(hotel_id) <= 0:
        raise TbankApiError(
            "BAD_HOTEL_ID", "hotel_id должен быть положительным числовым id отеля.")
    return hotel_id

def _hotel_rate_filters(filters: list[dict] | None) -> list[dict]:
    """Validate and copy the getRates_v3 discriminated filter union."""
    if filters is None:
        return []
    if not isinstance(filters, list) or len(filters) > 30:
        raise TbankApiError(
            "BAD_FILTERS", "filters должен быть массивом максимум из 30 фильтров.")
    normalized = []
    for index, item in enumerate(filters):
        if not isinstance(item, dict):
            raise TbankApiError(
                "BAD_FILTER", f"filters[{index}] должен быть JSON-объектом.")
        kind = str(item.get("$objectType") or item.get("objectType") or "").strip()
        filter_id = str(item.get("filterId") or "").strip()
        prefix = f"filters[{index}]"
        if kind == "array":
            values = item.get("values")
            if filter_id not in _HOTEL_ARRAY_FILTERS:
                raise TbankApiError(
                    "BAD_FILTER", f"{prefix}: filterId={filter_id!r} не поддерживает array.")
            if (not isinstance(values, list) or not values or
                    any(not isinstance(value, str) or not value.strip()
                        for value in values)):
                raise TbankApiError(
                    "BAD_FILTER", f"{prefix}.values должен быть непустым массивом строк.")
            normalized.append({
                "$objectType": "array", "filterId": filter_id,
                "values": [value.strip() for value in values],
            })
        elif kind == "range":
            if filter_id != "price":
                raise TbankApiError(
                    "BAD_FILTER", f"{prefix}: range поддерживается только для price.")
            minimum, maximum = item.get("min"), item.get("max")
            if (isinstance(minimum, bool) or isinstance(maximum, bool) or
                    not isinstance(minimum, (int, float)) or
                    not isinstance(maximum, (int, float)) or minimum > maximum):
                raise TbankApiError(
                    "BAD_FILTER", f"{prefix}: нужны числовые min <= max.")
            normalized.append({
                "$objectType": "range", "filterId": "price",
                "min": minimum, "max": maximum,
            })
        elif kind == "boolean":
            value = item.get("value")
            if filter_id not in _HOTEL_BOOLEAN_FILTERS or not isinstance(value, bool):
                raise TbankApiError(
                    "BAD_FILTER", f"{prefix}: нужен boolean value и допустимый filterId.")
            normalized.append({
                "$objectType": "boolean", "filterId": filter_id, "value": value,
            })
        elif kind == "radio":
            value = item.get("value")
            if (filter_id != "review_rating" or not isinstance(value, str)
                    or not value.strip()):
                raise TbankApiError(
                    "BAD_FILTER", f"{prefix}: radio поддерживается только для review_rating.")
            normalized.append({
                "$objectType": "radio", "filterId": "review_rating",
                "value": value.strip(),
            })
        else:
            raise TbankApiError(
                "BAD_FILTER",
                f"{prefix}.$objectType должен быть array, range, boolean или radio.")
    return normalized

def _hotel_review_item(item: dict, fallback_hotel_id: str) -> dict:
    review = item.get("review") or {}
    if not isinstance(review, dict):
        review = {}
    booking = review.get("bookingInfo") or {}
    if not isinstance(booking, dict):
        booking = {}
    photos = []
    for photo in review.get("photos") or []:
        if isinstance(photo, str):
            url, categories = photo, []
        elif isinstance(photo, dict):
            url = photo.get("url") or photo.get("URL")
            categories = photo.get("categories") or []
        else:
            continue
        if not isinstance(categories, list):
            categories = []
        safe_url = _https_image_url(url, size="1024x768")
        if safe_url:
            photos.append({
                "url": safe_url,
                "categories": [str(value) for value in categories
                               if isinstance(value, (str, int, float))],
            })
    like_count = item.get("likeCount")
    if like_count is None:
        like_count = item.get("likesCount", 0)
    return {
        "hotelId": str(item.get("hotelId") or item.get("masterHotelId")
                       or fallback_hotel_id),
        "feedbackId": str(item.get("feedbackId") or ""),
        "sourceType": str(item.get("sourceType") or ""),
        "author": _flat(review.get("author") or ""),
        "rating": review.get("rating"),
        "bookingInfo": {
            "roomName": _flat(booking.get("roomName") or ""),
            "travelerType": str(booking.get("travelerType") or ""),
            "nights": str(booking.get("nights") or ""),
            "createdDate": str(booking.get("createdDate") or ""),
        },
        # Both spellings exist: the attached contract says reviewPlus/reviewMinus,
        # while the live v2 response uses reviewTextPlus/reviewTextMinus.
        "reviewPlus": _flat(review.get("reviewPlus") or review.get("reviewTextPlus") or ""),
        "reviewMinus": _flat(review.get("reviewMinus") or review.get("reviewTextMinus") or ""),
        "photos": photos,
        "likeCount": int(like_count or 0),
        "isLiked": item.get("isLiked") is True,
        "replyInfo": item.get("replyInfo"),
    }
