"""Deterministic normalization and comparison contracts for travel tools.

The language model chooses the scenario and constraints.  This module owns the
mechanical work that should not be delegated to it: normalizing provider payloads,
stable sorting and exact price deltas.  It intentionally contains no network or
session code so the same functions can be used by atomic and composite MCP tools.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator


def _camel(name: str) -> str:
    first, *rest = name.split("_")
    return first + "".join(part[:1].upper() + part[1:] for part in rest)


class OutputModel(BaseModel):
    """MCP-facing models use the camelCase convention of existing JSON tools."""

    model_config = ConfigDict(
        alias_generator=_camel,
        populate_by_name=True,
        extra="forbid",
    )


class StayWindow(BaseModel):
    """One exact hotel stay supplied to a comparison tool."""

    model_config = ConfigDict(extra="forbid")

    checkin_date: str
    checkout_date: str

    @model_validator(mode="after")
    def validate_window(self) -> "StayWindow":
        try:
            start = date.fromisoformat(self.checkin_date)
            end = date.fromisoformat(self.checkout_date)
        except ValueError as exc:
            raise ValueError("checkin_date и checkout_date должны быть YYYY-MM-DD") from exc
        nights = (end - start).days
        if not 1 <= nights <= 30:
            raise ValueError("окно проживания должно содержать от 1 до 30 ночей")
        return self

    @property
    def nights(self) -> int:
        return (date.fromisoformat(self.checkout_date) - date.fromisoformat(self.checkin_date)).days

    @property
    def key(self) -> str:
        return f"{self.checkin_date}/{self.checkout_date}"


class WindowValue(OutputModel):
    key: str
    checkin_date: str
    checkout_date: str
    nights: int


class ComparisonFailure(OutputModel):
    scope: str
    code: str
    message: str


class ComparisonError(OutputModel):
    code: str
    message: str


class ComparisonGroup(OutputModel):
    key: str
    label: str
    status: Literal["complete", "partial", "empty", "failed"]
    result_count: int = 0
    best_observed_price_rub: float | None = None
    price_rank: int | None = None
    delta_rub_from_baseline: float | None = None
    delta_pct_from_baseline: float | None = None
    delta_rub_from_lowest_observed: float | None = None
    delta_pct_from_lowest_observed: float | None = None


class ComparisonMeta(OutputModel):
    complete: bool
    requested_searches: int
    succeeded_searches: int
    failed_searches: int
    incomplete_searches: int
    baseline_key: str
    currency: str = "RUB"


class FlightComparisonItem(OutputModel):
    rank: int
    group_key: str
    date: str
    offer_id: str
    price_rub: float
    delta_rub_from_lowest_observed: float
    delta_pct_from_lowest_observed: float
    summary: str
    departure_at: str
    arrival_at: str
    duration_minutes: int
    stops: int
    with_baggage: bool
    refundable: bool
    vendor: str
    source: str
    checked_at: str


class TrainComparisonItem(OutputModel):
    rank: int
    group_key: str
    date: str
    train_number: str
    name: str
    origin_name: str
    destination_name: str
    departure_at: str
    arrival_at: str
    duration_minutes: int
    min_fare_rub: float
    available_seats: int
    car_types: list[str]
    delta_rub_from_lowest_observed: float
    delta_pct_from_lowest_observed: float
    source: str
    checked_at: str


class HotelComparisonItem(OutputModel):
    rank: int
    group_key: str
    checkin_date: str
    checkout_date: str
    nights: int
    hotel_id: str
    name: str
    stars: int
    rating: float | None = None
    address: str
    meal: str
    total_price_rub: float
    nightly_price_rub: float
    delta_rub_from_lowest_observed: float
    delta_pct_from_lowest_observed: float
    source: str
    checked_at: str


class FlightHotelComparisonItem(OutputModel):
    rank: int
    group_key: str
    checkin_date: str
    checkout_date: str
    nights: int
    outbound_offer_id: str
    outbound_summary: str
    return_offer_id: str
    return_summary: str
    hotel_id: str
    hotel_name: str
    hotel_stars: int
    hotel_rating: float | None = None
    outbound_flight_rub: float
    return_flight_rub: float
    hotel_rub: float
    bundle_total_rub: float
    delta_to_budget_rub: float | None = None
    delta_rub_from_lowest_observed: float
    delta_pct_from_lowest_observed: float
    source: str
    checked_at: str


class FlightComparisonData(OutputModel):
    from_code: str
    to_code: str
    dates: list[str]
    sort_by: str
    groups: list[ComparisonGroup]
    items: list[FlightComparisonItem]
    failures: list[ComparisonFailure]


class TrainComparisonData(OutputModel):
    origin: str
    destination: str
    dates: list[str]
    sort_by: str
    groups: list[ComparisonGroup]
    items: list[TrainComparisonItem]
    failures: list[ComparisonFailure]


class HotelComparisonData(OutputModel):
    destination_id: int
    windows: list[WindowValue]
    sort_by: str
    groups: list[ComparisonGroup]
    items: list[HotelComparisonItem]
    failures: list[ComparisonFailure]


class FlightHotelComparisonData(OutputModel):
    from_code: str
    to_code: str
    hotel_destination_id: int
    windows: list[WindowValue]
    priced_components: list[str]
    groups: list[ComparisonGroup]
    items: list[FlightHotelComparisonItem]
    failures: list[ComparisonFailure]


class FlightComparisonResponse(OutputModel):
    ok: bool
    data: FlightComparisonData | None
    source: str
    checked_at: str
    warnings: list[str]
    meta: ComparisonMeta
    error: ComparisonError | None = None


class TrainComparisonResponse(OutputModel):
    ok: bool
    data: TrainComparisonData | None
    source: str
    checked_at: str
    warnings: list[str]
    meta: ComparisonMeta
    error: ComparisonError | None = None


class HotelComparisonResponse(OutputModel):
    ok: bool
    data: HotelComparisonData | None
    source: str
    checked_at: str
    warnings: list[str]
    meta: ComparisonMeta
    error: ComparisonError | None = None


class FlightHotelComparisonResponse(OutputModel):
    ok: bool
    data: FlightHotelComparisonData | None
    source: str
    checked_at: str
    warnings: list[str]
    meta: ComparisonMeta
    error: ComparisonError | None = None


@dataclass
class ObservedGroup:
    key: str
    label: str
    status: Literal["complete", "partial", "empty", "failed"]
    prices: list[Decimal] = field(default_factory=list)


def decimal_amount(value: Any) -> Decimal:
    """A non-negative provider amount, or zero for a missing/invalid value."""
    if isinstance(value, dict):
        value = value.get("amount") or value.get("value") or value.get("price")
    try:
        amount = Decimal(str(value or "0"))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")
    return amount if amount.is_finite() and amount > 0 else Decimal("0")


def rub_number(value: Decimal | Any) -> float:
    amount = value if isinstance(value, Decimal) else decimal_amount(value)
    return float(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def price_delta(value: Decimal | Any, baseline: Decimal | Any) -> tuple[float | None, float | None]:
    """Return signed RUB and percentage deltas using decimal arithmetic."""
    current = value if isinstance(value, Decimal) else decimal_amount(value)
    reference = baseline if isinstance(baseline, Decimal) else decimal_amount(baseline)
    if current <= 0 or reference <= 0:
        return None, None
    delta = current - reference
    percentage = (delta / reference * Decimal("100")).quantize(
        Decimal("0.1"), rounding=ROUND_HALF_UP)
    return rub_number(delta), float(percentage)


def comparison_groups(groups: list[ObservedGroup]) -> tuple[list[ComparisonGroup], Decimal, Decimal]:
    """Add ranks and deltas without pretending partial data is globally cheapest."""
    best_by_key = {
        group.key: min((price for price in group.prices if price > 0), default=Decimal("0"))
        for group in groups
    }
    baseline = best_by_key.get(groups[0].key, Decimal("0")) if groups else Decimal("0")
    observed = [price for price in best_by_key.values() if price > 0]
    lowest = min(observed, default=Decimal("0"))
    ranked_keys = [
        key for key, _ in sorted(
            ((key, price) for key, price in best_by_key.items() if price > 0),
            key=lambda item: (item[1], item[0]),
        )
    ]
    ranks = {key: index + 1 for index, key in enumerate(ranked_keys)}
    out: list[ComparisonGroup] = []
    for group in groups:
        best = best_by_key[group.key]
        baseline_rub, baseline_pct = price_delta(best, baseline)
        lowest_rub, lowest_pct = price_delta(best, lowest)
        out.append(ComparisonGroup(
            key=group.key,
            label=group.label,
            status=group.status,
            result_count=len(group.prices),
            best_observed_price_rub=rub_number(best) if best > 0 else None,
            price_rank=ranks.get(group.key),
            delta_rub_from_baseline=baseline_rub,
            delta_pct_from_baseline=baseline_pct,
            delta_rub_from_lowest_observed=lowest_rub,
            delta_pct_from_lowest_observed=lowest_pct,
        ))
    return out, baseline, lowest


def _flat(value: Any) -> str:
    return " ".join(str(value or "").split())


def _https_image_url(value: Any, *, size: str = "") -> str:
    url = str(value or "").strip()
    if size:
        url = url.replace("{size}", size)
    return url if url.lower().startswith("https://") else ""


def _hotel_address(hotel: dict[str, Any]) -> str:
    location = hotel.get("hotelLocation") or hotel.get("location") or {}
    if isinstance(location, str):
        return _flat(location)
    if not isinstance(location, dict):
        location = {}
    address = (location.get("address") or location.get("fullAddress")
               or hotel.get("address") or hotel.get("areaLocation") or "")
    if isinstance(address, dict):
        address = address.get("name") or address.get("address") or ""
    return _flat(address)


def _hotel_coordinates(hotel: dict[str, Any]) -> tuple[float | None, float | None]:
    for value in (hotel.get("coordinates"), hotel.get("geo"),
                  hotel.get("hotelLocation"), hotel.get("location")):
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


def normalize_flight_inventory(result: dict[str, Any], *, only_bookable: bool) -> list[dict[str, Any]]:
    """Normalize T-Bank Avia's separate flight/offer arrays into flat offers."""
    flights = result.get("flights") or []
    offers = result.get("offers") or []
    if only_bookable:
        offers = [offer for offer in offers if str(offer.get("vendor")) == "Tinkoff"]
    names = ((result.get("info") or {}).get("carrierNames") or {})

    def leg_data(index: Any) -> dict[str, Any] | None:
        try:
            flight = flights[int(index)] if 0 <= int(index) < len(flights) else {}
        except (TypeError, ValueError):
            flight = {}
        segments = flight.get("flightSegments") or []
        if not segments:
            return None
        departure = segments[0].get("departure") or {}
        arrival = segments[-1].get("arrival") or {}
        carrier = (segments[0].get("carriers") or {}).get("marketing") or ""
        hops = []
        for seg in segments:
            dep = seg.get("departure") or {}
            arr = seg.get("arrival") or {}
            hops.append({
                "departureAt": str(dep.get("time") or ""),
                "arrivalAt": str(arr.get("time") or ""),
                "fromAirport": str(dep.get("airport") or ""),
                "toAirport": str(arr.get("airport") or ""),
                "marketingCode": str((seg.get("carriers") or {}).get("marketing") or ""),
                "flightNumber": str(seg.get("number") or ""),
            })
        return {
            "carrier": str(names.get(carrier, carrier) or ""),
            "marketingCode": str(carrier or ""),
            "flightNumber": str(segments[0].get("number") or ""),
            "fromAirport": str(departure.get("airport") or ""),
            "toAirport": str(arrival.get("airport") or ""),
            "departureAt": str(departure.get("time") or ""),
            "arrivalAt": str(arrival.get("time") or ""),
            "durationMinutes": int(flight.get("duration") or 0),
            "stops": max(0, len(segments) - 1),
            "hops": hops,
        }

    rows: list[dict[str, Any]] = []
    for offer in offers:
        price = decimal_amount(offer.get("price") or {})
        if price <= 0:
            continue
        legs = [leg_data(index) for index in (offer.get("flights") or [])]
        legs = [leg for leg in legs if leg]
        first, last = (legs[0] if legs else {}), (legs[-1] if legs else {})
        summary = " / ".join(
            f"{leg['carrier']} {leg['fromAirport']}→{leg['toAirport']} "
            f"{str(leg['departureAt'])[11:16]}" for leg in legs)
        rows.append({
            "offerId": str(offer.get("offerId") or ""),
            "price": rub_number(price),
            "priceDecimal": price,
            "currency": str((offer.get("price") or {}).get("currency") or "RUB"),
            "summary": summary,
            "departureAt": str(first.get("departureAt") or ""),
            "arrivalAt": str(last.get("arrivalAt") or ""),
            "durationMinutes": sum(int(leg.get("durationMinutes") or 0) for leg in legs),
            "stops": sum(int(leg.get("stops") or 0) for leg in legs),
            "withBaggage": bool(offer.get("withBaggage")),
            "refundable": bool(offer.get("refundable")),
            "vendor": str(offer.get("vendor") or ""),
            "candidateUrl": str(offer.get("tbankUrl") or offer.get("webUrl")
                                or offer.get("bookingUrl") or offer.get("url") or ""),
            "legs": legs,
        })
    return rows


def normalize_train_inventory(ways: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for way in ways:
        segment = (way.get("segments") or [{}])[0]
        origin = segment.get("origin") or {}
        destination = segment.get("destination") or {}
        cars: list[tuple[dict[str, Any], Decimal]] = []
        for car in segment.get("carGroups") or []:
            price = decimal_amount((car.get("refundablePrice") or {}).get("price"))
            if price > 0:
                cars.append((car, price))
        best = min(cars, key=lambda item: item[1], default=None)
        seats = sum(int((car.get("places") or {}).get("total") or 0) for car, _ in cars)
        rows.append({
            "trainNumber": str(segment.get("displayTrainNumber") or segment.get("number") or ""),
            "name": _flat(segment.get("name") or segment.get("brandName") or segment.get("description")),
            "origin": {"name": _flat(origin.get("stationName")),
                       "code": str(origin.get("stationCode") or "")},
            "destination": {"name": _flat(destination.get("stationName")),
                            "code": str(destination.get("stationCode") or "")},
            "departureAt": str(segment.get("departureDateTime") or ""),
            "arrivalAt": str(segment.get("arrivalDateTime") or ""),
            "durationMinutes": int(segment.get("rideMin") or 0),
            "distanceKm": int(segment.get("rideKm") or 0),
            "minPrice": rub_number(best[1]) if best else None,
            "priceDecimal": best[1] if best else Decimal("0"),
            "currency": "RUB",
            "availableSeats": seats,
            "carTypes": sorted({
                str(car.get("carTypeName") or car.get("carType") or "")
                for car, _ in cars if car.get("carTypeName") or car.get("carType")
            }),
            "candidateUrl": str(way.get("tbankUrl") or way.get("webUrl")
                                or way.get("bookingUrl") or way.get("url") or ""),
        })
    return rows


def normalize_hotel_inventory(hotels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for hotel in hotels:
        rate = hotel.get("rateForHotelsFeed") or {}
        shown_price = rate.get("shownPrice") or {}
        price = decimal_amount(shown_price)
        review = hotel.get("review") or {}
        rating_value = ((review.get("rating") or review.get("score"))
                        if isinstance(review, dict) else None)
        latitude, longitude = _hotel_coordinates(hotel)
        image_url = next((
            normalized for value in (hotel.get("images") or [])
            if (normalized := _https_image_url(value, size="1024x768"))
        ), "")
        row = {
            "hotelId": str(hotel.get("hotelId") or ""),
            "name": _flat(hotel.get("hotelName") or ""),
            "stars": int(hotel.get("starRating") or 0),
            "price": rub_number(price),
            "priceDecimal": price,
            "currency": (str(shown_price.get("currency") or "RUB")
                         if isinstance(shown_price, dict) else "RUB"),
            "address": _hotel_address(hotel),
            "rating": (rub_number(decimal_amount(rating_value))
                       if rating_value is not None else None),
            "meal": _flat(rate.get("mealName") or rate.get("mealType") or ""),
            "availableRooms": (rub_number(decimal_amount(rate.get("availableRoomsCount")))
                               if rate.get("availableRoomsCount") is not None else None),
            "latitude": latitude,
            "longitude": longitude,
            "isFinalPrice": rate.get("isFinalPrice") is True,
        }
        if image_url:
            row["imageUrl"] = image_url
        rows.append(row)
    return rows


def sort_flights(rows: list[dict[str, Any]], sort_by: str) -> list[dict[str, Any]]:
    if sort_by == "duration":
        key = lambda row: (int(row.get("durationMinutes") or 10**9),
                           row["priceDecimal"], row.get("departureAt") or "~",
                           row.get("offerId") or "")
    elif sort_by == "departure_time":
        key = lambda row: (row.get("departureAt") or "~", row["priceDecimal"],
                           int(row.get("durationMinutes") or 10**9), row.get("offerId") or "")
    else:
        key = lambda row: (row["priceDecimal"], int(row.get("durationMinutes") or 10**9),
                           row.get("departureAt") or "~", row.get("offerId") or "")
    return sorted(rows, key=key)


def sort_trains(rows: list[dict[str, Any]], sort_by: str) -> list[dict[str, Any]]:
    if sort_by == "duration":
        key = lambda row: (int(row.get("durationMinutes") or 10**9),
                           row["priceDecimal"], row.get("departureAt") or "~",
                           row.get("trainNumber") or "")
    elif sort_by == "departure_time":
        key = lambda row: (row.get("departureAt") or "~", row["priceDecimal"],
                           row.get("trainNumber") or "")
    else:
        key = lambda row: (row["priceDecimal"], int(row.get("durationMinutes") or 10**9),
                           row.get("departureAt") or "~", row.get("trainNumber") or "")
    return sorted(rows, key=key)


def sort_hotels(rows: list[dict[str, Any]], sort_by: str) -> list[dict[str, Any]]:
    if sort_by == "nightly_price":
        key = lambda row: (row["nightlyPriceDecimal"], row["priceDecimal"],
                           -(row.get("rating") or 0), row.get("hotelId") or "")
    elif sort_by == "rating":
        key = lambda row: (-(row.get("rating") or 0), row["priceDecimal"],
                           -(row.get("stars") or 0), row.get("hotelId") or "")
    else:
        key = lambda row: (row["priceDecimal"], row["nightlyPriceDecimal"],
                           -(row.get("rating") or 0), row.get("hotelId") or "")
    return sorted(rows, key=key)
