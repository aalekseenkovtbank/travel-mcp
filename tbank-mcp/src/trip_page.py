"""Versioned contract and dependency-free static renderer for trip pages.

The renderer deliberately accepts a fully materialised document.  It never calls
the bank or a places provider while rendering, which keeps a generated page
reproducible. MCP tools return HTML and Markdown in memory; the CLI may still
write a JSON sidecar for local inspection.
"""
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import tempfile
import types
from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import (AnyHttpUrl, BaseModel, ConfigDict, Field, StringConstraints,
                      ValidationError, field_validator, model_validator)

from .tbank_urls import (avia_checkout_url, avia_share_url, hotel_details_url,
                         safe_public_https_url, safe_tbank_url)


NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
HttpsUrl = Annotated[AnyHttpUrl, Field(description="An HTTPS URL")]


def _require_tbank_url(value, field_name: str):
    if value is not None and not safe_tbank_url(value):
        raise ValueError(f"{field_name} must be a safe public T-Bank HTTPS URL")
    return value


class ContractModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=lambda value: "".join(
            [value.split("_")[0], *[part.title() for part in value.split("_")[1:]]]
        ),
        populate_by_name=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    @field_validator("*", mode="before")
    @classmethod
    def _reject_control_characters(cls, value):
        if isinstance(value, str) and any(ord(char) < 9 for char in value):
            raise ValueError("control characters are not allowed")
        return value

    @field_validator("*")
    @classmethod
    def _require_datetime_timezone(cls, value):
        if isinstance(value, datetime) and value.tzinfo is None:
            raise ValueError("datetimes must include a timezone offset")
        return value


class Coordinates(ContractModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class TripSummary(ContractModel):
    title: NonEmpty
    destination: NonEmpty
    date_from: date
    date_to: date
    # Состав поездки: и транспорт, и отель ищутся/показываются для этого числа
    # взрослых. Отдельные счётчики transportAdults/hotelAdults убраны: цены в
    # документе уже итоговые для этого состава, поэтому рендер не путает 1+2.
    travelers: int = Field(default=2, ge=1, le=20)
    subtitle: str = ""

    @model_validator(mode="after")
    def _dates_are_ordered(self):
        if self.date_to < self.date_from:
            raise ValueError("dateTo must not be earlier than dateFrom")
        return self


class FlightSegment(ContractModel):
    """Один реальный сегмент перелёта (для маршрутов с пересадками)."""
    departure_at: datetime
    arrival_at: datetime
    from_code: str = ""
    to_code: str = ""
    carrier_code: str = ""
    flight_number: str = ""

    @field_validator("from_code", "to_code")
    @classmethod
    def _three_letter_code(cls, value, info):
        value = str(value or "").strip().upper()
        if value and not __import__("re").fullmatch(r"[A-Z]{3}", value):
            raise ValueError(f"{info.field_name} must be a 3-letter code")
        return value

    @field_validator("carrier_code")
    @classmethod
    def _carrier_code(cls, value):
        value = str(value or "").strip().upper()
        if value and not __import__("re").fullmatch(r"[A-Z0-9]{1,3}", value):
            raise ValueError("carrierCode must be a 1-3 char airline code")
        return value

    @field_validator("flight_number")
    @classmethod
    def _flight_number(cls, value):
        value = str(value or "").strip().upper()
        if value and not __import__("re").fullmatch(r"[0-9]{1,5}[A-Z]?", value):
            raise ValueError("flightNumber must look like a flight number")
        return value

    @model_validator(mode="after")
    def _times_are_ordered(self):
        if self.arrival_at <= self.departure_at:
            raise ValueError("segment arrivalAt must be later than departureAt")
        return self


class TransportLeg(ContractModel):
    id: NonEmpty
    direction: Literal["outbound", "return"]
    mode: Literal["flight", "train"]
    origin: NonEmpty
    destination: NonEmpty
    departure_at: datetime
    arrival_at: datetime
    carrier: NonEmpty
    service_number: str = ""
    seller: str = ""
    price_rub: float = Field(ge=0)
    tbank_url: HttpsUrl | None = None
    booking_url: HttpsUrl | None = None
    notes: list[str] = Field(default_factory=list, max_length=8)
    # Source-verified fields used to build the T-Bank avia „share“ deep link
    # (renderer assembles it only from these; no UTM, nothing guessed).
    origin_code: str = ""
    destination_code: str = ""
    carrier_code: str = ""
    flight_number: str = ""
    # Реальные сегменты перелёта (для пересадок). Если заданы — share-ссылка и
    # детали строятся по ним, а не по одиночному flightNumber выше.
    hops: list[FlightSegment] = Field(default_factory=list, max_length=8)
    # Идентификаторы выбранного оффера из flight_search (для трассировки и на
    # случай, если upstream начнёт отдавать canonical URL оффера — тогда его
    # клади в tbankUrl, а эти поля остаются справочными).
    search_id: str = ""
    offer_id: str = ""

    @field_validator("search_id", "offer_id")
    @classmethod
    def _short_id(cls, value, info):
        value = str(value or "").strip()
        if len(value) > 128:
            raise ValueError(f"{info.field_name} is too long")
        return value

    @field_validator("origin_code", "destination_code")
    @classmethod
    def _three_letter_code(cls, value, info):
        value = str(value or "").strip().upper()
        if value and not __import__("re").fullmatch(r"[A-Z]{3}", value):
            raise ValueError(f"{info.field_name} must be a 3-letter code")
        return value

    @field_validator("carrier_code")
    @classmethod
    def _carrier_code(cls, value):
        value = str(value or "").strip().upper()
        if value and not __import__("re").fullmatch(r"[A-Z0-9]{1,3}", value):
            raise ValueError("carrierCode must be a 1-3 char airline code")
        return value

    @field_validator("flight_number")
    @classmethod
    def _flight_number(cls, value):
        value = str(value or "").strip().upper()
        if value and not __import__("re").fullmatch(r"[0-9]{1,5}[A-Z]?", value):
            raise ValueError("flightNumber must look like a flight number")
        return value

    @field_validator("tbank_url")
    @classmethod
    def _tbank_object_url(cls, value):
        return _require_tbank_url(value, "tbankUrl")

    @field_validator("booking_url")
    @classmethod
    def _tbank_booking_url(cls, value):
        return _require_tbank_url(value, "bookingUrl")

    @model_validator(mode="after")
    def _times_are_ordered(self):
        if self.arrival_at <= self.departure_at:
            raise ValueError("arrivalAt must be later than departureAt")
        return self


class CombinedFlight(ContractModel):
    """Единый round-trip оффер (туда+обратно в одном поиске): одна цена за
    оба перелёта и один checkout-URL. Рендер показывает Дорогу одной карточкой.
    """

    price_rub: float = Field(ge=0)
    checkout_url: str = ""

    @field_validator("checkout_url")
    @classmethod
    def _tbank_checkout(cls, value):
        if value and not safe_tbank_url(value):
            raise ValueError("combinedFlight.checkoutUrl must be a safe T-Bank HTTPS URL")
        return str(value or "")


class FlightOption(ContractModel):
    """Альтернативный вариант перелёта, который предлагает агент.

    Модель сама объясняет (comment), почему вариант подходит (цена, время,
    пересадки, «±1 день», риск). directions — плечи этого варианта
    (TransportLeg: outbound и return), каждый со своими offerId/hops и
    ссылками; рендер показывает их отдельным блоком «Варианты перелёта».
    """

    id: NonEmpty
    comment: NonEmpty
    label: str = ""
    price_rub: float | None = Field(default=None, ge=0)
    checkout_url: str = ""
    directions: list[TransportLeg] = Field(min_length=2, max_length=8)

    @field_validator("checkout_url")
    @classmethod
    def _tbank_checkout(cls, value):
        if value and not safe_tbank_url(value):
            raise ValueError("flight option checkoutUrl must be a safe T-Bank HTTPS URL")
        return str(value or "")

    @model_validator(mode="after")
    def _directions_are_valid(self):
        dirs = {leg.direction for leg in self.directions}
        if dirs != {"outbound", "return"}:
            raise ValueError("flight option directions must include outbound and return")
        return self


class HotelOption(ContractModel):
    id: NonEmpty
    name: NonEmpty
    address: NonEmpty
    coordinates: Coordinates
    stars: int = Field(default=0, ge=0, le=5)
    rating: float | None = Field(default=None, ge=0, le=10)
    review_count: int | None = Field(default=None, ge=0)
    image_url: HttpsUrl | None = None
    nightly_price_rub: float = Field(ge=0)
    total_price_rub: float = Field(ge=0)
    meal: str = ""
    room: str = ""
    cancellation: str = ""
    payment: str = ""
    review_summary: str = ""
    booking_url: HttpsUrl | None = None

    @field_validator("image_url")
    @classmethod
    def _https_image_url(cls, value):
        if value is not None and value.scheme != "https":
            raise ValueError("remote URLs must use HTTPS")
        return value

    @field_validator("booking_url")
    @classmethod
    def _tbank_booking_url(cls, value):
        return _require_tbank_url(value, "bookingUrl")


class HotelPhoto(ContractModel):
    url: HttpsUrl
    kind: Literal["official", "guest"] = "official"
    attribution: str = ""
    source_url: HttpsUrl | None = None

    @field_validator("url", "source_url")
    @classmethod
    def _https_urls(cls, value):
        if value is not None and value.scheme != "https":
            raise ValueError("photo URLs must use HTTPS")
        return value


class HotelReviewDigest(ContractModel):
    sample_size: int = Field(default=0, ge=0, le=50)
    sort: Literal["date", "rating"] = "date"
    sort_type: Literal["asc", "desc"] = "desc"
    date_from: date | None = None
    date_to: date | None = None
    pros: list[str] = Field(default_factory=list, max_length=5)
    cons: list[str] = Field(default_factory=list, max_length=5)
    suitable_for: str = ""
    summary: str = ""

    @model_validator(mode="after")
    def _dates_are_ordered(self):
        if (self.date_from is not None and self.date_to is not None
                and self.date_to < self.date_from):
            raise ValueError("review digest dateTo must not be earlier than dateFrom")
        return self


class HotelOptionV2(HotelOption):
    photos: list[HotelPhoto] = Field(default_factory=list, max_length=3)
    description: str = ""
    check_in_time: str = ""
    check_out_time: str = ""
    facilities: list[str] = Field(default_factory=list, max_length=12)
    location_summary: str = ""
    details_url: HttpsUrl | None = None
    review_digest: HotelReviewDigest | None = None

    @model_validator(mode="before")
    @classmethod
    def _derive_details_url(cls, value):
        if not isinstance(value, dict) or value.get("details_url") or value.get("detailsUrl"):
            return value
        details_url = hotel_details_url(value.get("id"))
        return {**value, "details_url": details_url} if details_url else value

    @field_validator("details_url")
    @classmethod
    def _https_details_url(cls, value):
        return _require_tbank_url(value, "detailsUrl")

    @model_validator(mode="after")
    def _photos_are_unique(self):
        urls = [str(item.url) for item in self.photos]
        if len(urls) != len(set(urls)):
            raise ValueError("hotel photos must have unique URLs")
        kinds = [item.kind for item in self.photos]
        if "guest" in kinds and "official" in kinds[kinds.index("guest"):]:
            raise ValueError("official hotel photos must be listed before guest photos")
        return self


class BudgetRecommendation(ContractModel):
    component: Literal["transport", "hotel", "onsite", "total"]
    recommended_rub: float | None = Field(default=None, ge=0)
    range_min_rub: float | None = Field(default=None, ge=0)
    range_max_rub: float | None = Field(default=None, ge=0)
    basis: Literal[
        "explicit", "comparable_trips", "weekend_spend", "live_offers",
        "mixed", "insufficient_data",
    ]
    sample_size: int = Field(default=0, ge=0)
    confidence: Literal["high", "medium", "low", "none"]
    explanation: NonEmpty

    @model_validator(mode="after")
    def _range_is_ordered(self):
        values = (self.range_min_rub, self.recommended_rub, self.range_max_rub)
        present = [value for value in values if value is not None]
        if len(present) == 3 and not present[0] <= present[1] <= present[2]:
            raise ValueError("budget range must contain the recommended amount")
        return self


class PersonalizationSummary(ContractModel):
    budget_basis: NonEmpty
    event_basis: Literal["order_history", "no_history"]
    explanation: NonEmpty
    travel_sample_size: int = Field(default=0, ge=0)
    event_sample_size: int = Field(default=0, ge=0)


class EventOption(ContractModel):
    id: NonEmpty
    name: NonEmpty
    kind: NonEmpty
    venue: str = ""
    address: str = ""
    coordinates: Coordinates | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    price_from_rub: float | None = Field(default=None, ge=0)
    image_url: HttpsUrl | None = None
    source_url: HttpsUrl | None = None
    genres: list[str] = Field(default_factory=list, max_length=12)
    age_restriction: str = ""
    personalization_score: float = Field(default=50, ge=0, le=100)
    match_reason: str = ""
    personalization_basis: Literal["order_history", "no_history"] = "no_history"

    @field_validator("image_url")
    @classmethod
    def _https_image_url(cls, value):
        if value is not None and value.scheme != "https":
            raise ValueError("remote URLs must use HTTPS")
        return value

    @field_validator("source_url")
    @classmethod
    def _public_source_url(cls, value):
        # Events may point to an external public page (e.g. the league site)
        # when there is no T-Bank Afisha card. Hotels and avia links stay
        # T-Bank-only via safe_tbank_url elsewhere.
        if value is not None and not safe_public_https_url(value):
            raise ValueError("sourceUrl must be a public HTTPS URL")
        return value

    @model_validator(mode="after")
    def _event_times_are_ordered(self):
        if self.ends_at is not None and self.ends_at <= self.starts_at:
            raise ValueError("endsAt must be later than startsAt")
        return self


class VenuePhoto(ContractModel):
    url: HttpsUrl
    attribution: NonEmpty
    source_url: HttpsUrl

    @field_validator("url", "source_url")
    @classmethod
    def _https_urls(cls, value):
        if value.scheme != "https":
            raise ValueError("photo URLs must use HTTPS")
        return value


class DiningVenue(ContractModel):
    id: NonEmpty
    kind: Literal["restaurant", "bar"]
    name: NonEmpty
    address: str = ""
    coordinates: Coordinates
    photos: list[VenuePhoto] = Field(default_factory=list, max_length=8)
    rating: float | None = Field(default=None, ge=0)
    rating_scale: float | None = Field(default=None, gt=0)
    review_count: int | None = Field(default=None, ge=0)
    openstreetmap_url: HttpsUrl
    source: Literal["OpenStreetMap"] = "OpenStreetMap"
    categories: list[str] = Field(default_factory=list, max_length=12)
    opening_hours: str = ""
    price_level: str = ""

    @field_validator("openstreetmap_url")
    @classmethod
    def _openstreetmap_https_url(cls, value):
        host = str(value.host or "").lower()
        if value.scheme != "https" or not (
            host == "openstreetmap.org" or host.endswith(".openstreetmap.org")
        ):
            raise ValueError(
                "openstreetmapUrl must be an HTTPS openstreetmap.org URL")
        return value

    @model_validator(mode="after")
    def _rating_fits_scale(self):
        if (self.rating is None) != (self.rating_scale is None):
            raise ValueError("rating and ratingScale must be provided together")
        if (self.rating is not None and self.rating_scale is not None
                and self.rating > self.rating_scale):
            raise ValueError("rating must not exceed ratingScale")
        return self


class MapPoint(ContractModel):
    ref_id: NonEmpty
    kind: Literal["hotel", "event", "restaurant", "bar"]


class PlanStop(ContractModel):
    starts_at: datetime
    ends_at: datetime
    ref_id: NonEmpty
    note: str = ""

    @model_validator(mode="after")
    def _stop_times_are_ordered(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("plan stop endsAt must be later than startsAt")
        return self


class PlanDay(ContractModel):
    date: date
    title: NonEmpty
    stops: list[PlanStop] = Field(min_length=1, max_length=16)

    @model_validator(mode="after")
    def _stops_are_chronological(self):
        if any(stop.starts_at.date() != self.date for stop in self.stops):
            raise ValueError("every stop must start on its plan day")
        if any(right.starts_at < left.ends_at
               for left, right in zip(self.stops, self.stops[1:])):
            raise ValueError("plan stops must be chronological and non-overlapping")
        return self


class TripPlan(ContractModel):
    style: Literal["balanced", "culture", "food_nightlife"]
    title: NonEmpty
    summary: NonEmpty
    days: list[PlanDay] = Field(min_length=1, max_length=31)


class SourceReference(ContractModel):
    name: NonEmpty
    url: HttpsUrl | None = None
    checked_at: datetime

    @field_validator("url")
    @classmethod
    def _https_url(cls, value):
        if value is not None and value.scheme != "https":
            raise ValueError("source URL must use HTTPS")
        return value


class TripPageDocumentV1(ContractModel):
    schema_version: Literal["trip-page/v1"] = "trip-page/v1"
    trip: TripSummary
    transport: list[TransportLeg] = Field(default_factory=list, max_length=8)
    transport_booking_url: HttpsUrl | None = None
    # Альтернативные варианты перелёта с комментариями модели (рендерятся
    # блоком «Варианты перелёта»; выбранная пара остаётся в transport).
    flight_options: list[FlightOption] = Field(default_factory=list, max_length=8)
    combined_flight: CombinedFlight | None = None
    hotels: list[HotelOption] = Field(default_factory=list, min_length=1,
                                      max_length=8)
    selected_hotel_id: NonEmpty = ""
    budget: list[BudgetRecommendation] = Field(default_factory=list, max_length=8)
    personalization: PersonalizationSummary | None = None
    events: list[EventOption] = Field(default_factory=list, max_length=16)
    venues: list[DiningVenue] = Field(default_factory=list, max_length=16)
    map_points: list[MapPoint] = Field(default_factory=list, max_length=32)
    plans: list[TripPlan] = Field(default_factory=list, max_length=6)
    sources: list[SourceReference] = Field(min_length=1, max_length=24)
    warnings: list[str] = Field(default_factory=list, max_length=24)
    checked_at: datetime

    @field_validator("transport_booking_url")
    @classmethod
    def _https_transport_booking_url(cls, value):
        return _require_tbank_url(value, "transportBookingUrl")

    @model_validator(mode="after")
    def _cross_references_are_valid(self):
        # Optional blocks (budget, events, venues, mapPoints, plans,
        # personalization) are only checked when actually present — chat pages
        # may honestly lack Afisha/OSM/profile data.
        directions = {leg.direction for leg in self.transport}
        if not directions <= {"outbound", "return"}:
            raise ValueError("leg direction must be outbound or return")
        if len(self.transport) >= 2 and directions != {"outbound", "return"}:
            raise ValueError("with two or more legs both outbound and return are required")
        ids = [item.id for item in self.transport]
        ids += [item.id for item in self.hotels]
        ids += [item.id for item in self.events]
        ids += [item.id for item in self.venues]
        if len(ids) != len(set(ids)):
            raise ValueError("all entity IDs must be unique")
        hotel_ids = {item.id for item in self.hotels}
        if hotel_ids and self.selected_hotel_id not in hotel_ids:
            raise ValueError("selectedHotelId must reference a hotel")
        prices = [item.total_price_rub for item in self.hotels]
        if any(right <= left for left, right in zip(prices, prices[1:])):
            raise ValueError("hotels must be ordered by strictly increasing totalPriceRub")
        if self.budget:
            budgets = {item.component: item for item in self.budget}
            if not set(budgets) <= {"transport", "hotel", "onsite", "total"}:
                raise ValueError("unknown budget component")
            if len(budgets) != len(self.budget):
                raise ValueError("budget components must be unique")
            if {"transport", "hotel", "onsite", "total"} <= set(budgets):
                component_values = [budgets[name].recommended_rub
                                    for name in ("transport", "hotel", "onsite")]
                actual = budgets["total"].recommended_rub
                if (all(value is not None for value in component_values)
                        and (actual is None or abs(actual - sum(component_values)) > .01)):
                    raise ValueError(
                        "recommended total budget must equal its three components")
        map_kinds = {"hotel": hotel_ids,
                     "event": {item.id for item in self.events},
                     "restaurant": {item.id for item in self.venues
                                    if item.kind == "restaurant"},
                     "bar": {item.id for item in self.venues if item.kind == "bar"}}
        if len({point.ref_id for point in self.map_points}) != len(self.map_points):
            raise ValueError("mapPoints must not repeat an entity")
        for point in self.map_points:
            if point.ref_id not in map_kinds[point.kind]:
                raise ValueError(f"map point {point.ref_id!r} has the wrong kind")
        if any(plan.style not in {"balanced", "culture", "food_nightlife"}
               for plan in self.plans):
            raise ValueError("unknown plan style")
        all_ids = set(ids)
        events_by_id = {item.id: item for item in self.events}
        valid_plans: list[TripPlan] = []
        plan_warnings: list[str] = []
        for plan in self.plans:
            valid_days: list[PlanDay] = []
            for day in plan.days:
                if not self.trip.date_from <= day.date <= self.trip.date_to:
                    plan_warnings.append(
                        f'День {day.date.isoformat()} из плана «{plan.title}» '
                        "пропущен: он не входит в даты поездки.")
                    continue
                valid_stops: list[PlanStop] = []
                for stop in day.stops:
                    if stop.ref_id not in all_ids:
                        plan_warnings.append(
                            f'Остановка {stop.ref_id!r} из плана «{plan.title}» '
                            "пропущена: объекта нет в отчёте.")
                        continue
                    event = events_by_id.get(stop.ref_id)
                    if event and (stop.starts_at < event.starts_at
                                  or (event.ends_at and stop.ends_at > event.ends_at)):
                        plan_warnings.append(
                            f'Остановка {stop.ref_id!r} из плана «{plan.title}» '
                            "пропущена: время не совпадает с расписанием события.")
                        continue
                    valid_stops.append(stop)
                if valid_stops:
                    valid_days.append(day.model_copy(update={"stops": valid_stops}))
            if valid_days:
                valid_plans.append(plan.model_copy(update={"days": valid_days}))
        if plan_warnings:
            # Plans are optional, model-authored presentation data. A bad stop
            # must not hide otherwise valid source-backed transport and hotels.
            self.plans = valid_plans
            for warning in plan_warnings:
                if warning not in self.warnings and len(self.warnings) < 24:
                    self.warnings.append(warning)
        return self


class TripPageDocumentV2(TripPageDocumentV1):
    schema_version: Literal["trip-page/v2"] = "trip-page/v2"
    hotels: list[HotelOptionV2] = Field(default_factory=list, min_length=1,
                                        max_length=8)


class HotelSearchSummary(ContractModel):
    title: NonEmpty
    destination: NonEmpty
    date_from: date
    date_to: date
    adults: int = Field(default=2, ge=1, le=6)
    children_ages: list[int] = Field(default_factory=list, max_length=4)
    subtitle: str = ""

    @field_validator("children_ages")
    @classmethod
    def _children_ages_are_valid(cls, value):
        if any(age < 0 or age > 17 for age in value):
            raise ValueError("childrenAges must contain ages from 0 to 17")
        return value

    @model_validator(mode="after")
    def _dates_are_ordered(self):
        if self.date_to <= self.date_from:
            raise ValueError("dateTo must be later than dateFrom")
        return self


class HotelPageDocumentV1(ContractModel):
    schema_version: Literal["hotel-page/v1"] = "hotel-page/v1"
    search: HotelSearchSummary
    hotels: list[HotelOptionV2] = Field(min_length=1, max_length=5)
    selected_hotel_id: NonEmpty
    sources: list[SourceReference] = Field(min_length=1, max_length=24)
    warnings: list[str] = Field(default_factory=list, max_length=24)
    checked_at: datetime

    @model_validator(mode="after")
    def _hotel_references_are_valid(self):
        hotel_ids = [hotel.id for hotel in self.hotels]
        if len(hotel_ids) != len(set(hotel_ids)):
            raise ValueError("hotel IDs must be unique")
        if self.selected_hotel_id not in hotel_ids:
            raise ValueError("selectedHotelId must reference a hotel")
        if len(self.hotels) < 5:
            warning = (f"Найдено только {len(self.hotels)} подходящих доступных "
                       "отелей из целевых пяти.")
            if warning not in self.warnings:
                self.warnings = [*self.warnings[:23], warning]
        return self


TravelPageDocument = TripPageDocumentV2 | HotelPageDocumentV1

TBANK_LINK_MISSING = "Ссылка T-Bank недоступна"
PAGE_DISPLAY_HINT = (
    "Show `html` as a visual page without waiting for the user to ask: host "
    "artifact, canvas, or a fenced ```html block. Then paste `replyMarkdown` "
    "into the visible message so T-Bank links are clickable. Do not mention "
    "server disk paths and do not skip this because the host cannot open files."
)


class RenderPageResult(ContractModel):
    """In-memory Travel Nova page for MCP hosts (no disk paths)."""

    schema_version: Literal["trip-page/v1", "trip-page/v2", "hotel-page/v1"]
    html: str
    document_json: str
    reply_markdown: str
    display_hint: str
    title: str
    warnings: list[str]
    sources: list[str]
    advice: list[str] = Field(default_factory=list, max_length=24)


class RenderTripPageResult(ContractModel):
    """CLI-only pair of files; MCP tools do not return this."""

    html_path: str
    json_path: str
    title: str
    warnings: list[str]
    sources: list[str]


class RenderTravelPageResult(RenderTripPageResult):
    """CLI-only result of writing a current Travel Nova page contract."""


_ASSET_ROOT = Path(__file__).with_name("assets")
_SAFE_BASENAME = re.compile(r"[^A-Za-z0-9._-]+")


def _asset(name: str) -> str:
    return (_ASSET_ROOT / name).read_text(encoding="utf-8")


def _e(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def _rub(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:,.0f}".replace(",", "\u00a0") + " ₽"


def _dt(value: datetime) -> str:
    return value.strftime("%d.%m · %H:%M")


def _plural(n: int, one: str, few: str, many: str) -> str:
    """Русское склонение: _plural(3, 'ночь','ночи','ночей') → 'ночи'."""
    n = abs(int(n or 0))
    n10, n100 = n % 10, n % 100
    if n10 == 1 and n100 != 11:
        return one
    if 2 <= n10 <= 4 and not (12 <= n100 <= 14):
        return few
    return many


def _nights(n: int) -> str:
    return f"{n} {_plural(n, 'ночь', 'ночи', 'ночей')}"


def _adults(n: int) -> str:
    return f"{n} {_plural(n, 'взрослый', 'взрослых', 'взрослых')}"


def _slug(value: str) -> str:
    cleaned = _SAFE_BASENAME.sub("-", value.strip()).strip(".-")
    return cleaned[:80] or "trip"


def _image(url, alt: str, attribution: str = "") -> str:
    if not url:
        return '<div class="image-fallback">Фото появится при обновлении данных</div>'
    caption = f'<small class="credit">{_e(attribution)}</small>' if attribution else ""
    return (f'<div class="image-frame"><img class="remote-image" src="{_e(url)}" '
            f'alt="{_e(alt)}" loading="lazy" referrerpolicy="no-referrer">'
            '<div class="image-fallback">Изображение недоступно</div>'
            f'{caption}</div>')


def _link(url, label: str, css: str = "button") -> str:
    if not url:
        return ""
    return (f'<a class="{_e(css)}" href="{_e(url)}" target="_blank" '
            f'rel="noopener noreferrer">{_e(label)}</a>')


def _checkout_action(url, label: str, unavailable: str) -> str:
    if url:
        return _link(url, label, "button button-primary")
    return (f'<span class="button is-disabled" aria-disabled="true" '
            f'title="{_e(unavailable)}">{_e(unavailable)}</span>')


def _transport_checkout_url(document: TripPageDocumentV1):
    if document.transport_booking_url:
        return document.transport_booking_url
    return None


def _entity_index(document: TripPageDocumentV1) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for hotel in document.hotels:
        selected = hotel.id == document.selected_hotel_id
        index[hotel.id] = {
            "id": hotel.id, "kind": "hotel", "label": hotel.name,
            "lat": hotel.coordinates.latitude, "lon": hotel.coordinates.longitude,
            "selected": selected,
        }
    for event in document.events:
        if event.coordinates is None:
            continue
        index[event.id] = {
            "id": event.id, "kind": "event", "label": event.name,
            "lat": event.coordinates.latitude, "lon": event.coordinates.longitude,
        }
    for venue in document.venues:
        index[venue.id] = {
            "id": venue.id, "kind": venue.kind, "label": venue.name,
            "lat": venue.coordinates.latitude, "lon": venue.coordinates.longitude,
        }
    return index


def _render_transport(document: TripPageDocumentV1) -> str:
    combined = document.combined_flight
    if combined is not None:
        icons = {"flight": "✈", "train": "▰"}
        rows = []
        for leg in sorted(document.transport, key=lambda item: item.departure_at):
            origin = leg.origin_code or leg.origin
            destination = leg.destination_code or leg.destination
            notes = "".join(f'<span>{_e(note)}</span>' for note in leg.notes)
            rows.append(f"""
        <div class="eyebrow">{_e(_LEG_LABEL[leg.direction])} · {_e(leg.mode)}</div>
        <div class="route"><span>{_e(origin)}</span><b>{icons[leg.mode]}</b><span>{_e(destination)}</span></div>
        <div class="times"><strong>{_e(_dt(leg.departure_at))}</strong><span>→</span><strong>{_e(_dt(leg.arrival_at))}</strong></div>
        <p>{_e(leg.carrier)}{(' · ' + _e(leg.service_number)) if leg.service_number else ''}</p>
        {f'<div class="transport-notes">{notes}</div>' if notes else ''}""")
        action = (_link(combined.checkout_url, "Оформить оба перелёта в T-Bank", "button")
                  if combined.checkout_url
                  else '<span class="button is-disabled">Ссылка T-Bank недоступна</span>')
        return f"""
        <article class="transport-card" id="flight-combined">
          {''.join(rows)}
          <div class="price">{_rub(combined.price_rub)} <small>единый оффер: оба перелёта</small></div>
          {action}
        </article>"""
    cards = []
    labels = {"outbound": "Туда", "return": "Обратно"}
    icons = {"flight": "✈", "train": "▰"}
    for leg in sorted(document.transport, key=lambda item: item.departure_at):
        notes = "".join(f'<span>{_e(note)}</span>' for note in leg.notes)
        seller = f'<small>Продавец: {_e(leg.seller)}</small>' if leg.seller else ""
        leg_action = _checkout_action(
            leg.tbank_url,
            "Открыть билет в T-Bank",
            "Ссылка T-Bank недоступна",
        )
        booking_action = (_link(leg.booking_url, "Перейти к оформлению", "button")
                          if leg.booking_url else "")
        cards.append(f"""
        <article class="transport-card" id="entity-{_e(leg.id)}">
          <div class="eyebrow">{_e(labels[leg.direction])} · {_e(leg.mode)}</div>
          <div class="route"><span>{_e(leg.origin)}</span><b>{icons[leg.mode]}</b><span>{_e(leg.destination)}</span></div>
          <div class="times"><strong>{_e(_dt(leg.departure_at))}</strong><span>→</span><strong>{_e(_dt(leg.arrival_at))}</strong></div>
          <p>{_e(leg.carrier)}{(' · ' + _e(leg.service_number)) if leg.service_number else ''}</p>
          {seller}
          {f'<div class="transport-notes">{notes}</div>' if notes else ''}
          <div class="price">{_rub(leg.price_rub)}</div>
          <div class="transport-actions">{leg_action}{booking_action}</div>
        </article>""")
    return "".join(cards)


def _render_transport_overview(document: TripPageDocumentV1) -> str:
    combined = document.combined_flight
    if combined is not None:
        action = (_checkout_action(
            combined.checkout_url, "Оформить оба перелёта в T-Bank",
            "Checkout единого оффера не получен") if combined.checkout_url
            else '<span class="checkout-note">Единый оффер без checkout</span>')
        return f"""
      <aside class="transport-overview">
        <div><span>Маршрут</span><strong>туда и обратно</strong></div>
        <div><span>Единый оффер</span><strong>{_rub(combined.price_rub)}</strong></div>
        {action}
      </aside>"""
    checkout = _transport_checkout_url(document)
    total = sum(leg.price_rub for leg in document.transport)
    if checkout:
        action = _checkout_action(
            checkout, "Перейти к оформлению перелёта", "Checkout перелёта не получен")
    elif any(leg.booking_url for leg in document.transport):
        action = '<span class="checkout-note">Оформление — в карточках билетов</span>'
    else:
        action = '<span class="checkout-note">Оформление доступно после выбора предложения</span>'
    return f"""
      <aside class="transport-overview">
        <div><span>Выбранный маршрут</span><strong>{len(document.transport)} сегм.</strong></div>
        <div><span>Полная цена</span><strong>{_rub(total)}</strong></div>
        {action}
      </aside>"""


def _duration_label(start: datetime, end: datetime) -> str:
    minutes = max(0, int((end - start).total_seconds() // 60))
    days, minutes = divmod(minutes, 1440)
    hours, minutes = divmod(minutes, 60)
    return f"{days} д {hours} ч" if days else f"{hours} ч {minutes:02d} м"


def _road_option_html(document, legs, price, checkout_url, label, main=False) -> str:
    legs = sorted(list(legs), key=lambda item: item.departure_at)
    if not legs:
        return ""
    outbound = next((leg for leg in legs if leg.direction == "outbound"), legs[0])
    returning = next((leg for leg in legs if leg.direction == "return"), legs[-1])
    mode = "flight" if all(leg.mode == "flight" for leg in legs) else "train"
    icon = "✈" if mode == "flight" else "▰"
    icon_class = "road-icon-flight" if mode == "flight" else "road-icon-train"
    weekdays = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")
    date_text = f"{outbound.departure_at:%d.%m} → {returning.arrival_at:%d.%m}"
    week_text = f"{weekdays[outbound.departure_at.weekday()]} – {weekdays[returning.arrival_at.weekday()]}"
    duration = (f"{_duration_label(outbound.departure_at, outbound.arrival_at)} / "
                f"{_duration_label(returning.departure_at, returning.arrival_at)}")
    features = []
    for leg in legs:
        if leg.mode == "flight":
            features.append("прямой" if len(leg.hops) <= 1 else f"{len(leg.hops)-1} пересадка")
        else:
            features.append("без пересадок")
        features.extend(str(note) for note in leg.notes if str(note) not in features)
    risks = []
    if returning.arrival_at.date() > document.trip.date_to:
        risks.append("обратно прилёт +1")
    if not main and outbound.departure_at.date() != document.trip.date_from:
        risks.append("выезд на другой день")
    features_text = " · ".join(dict.fromkeys(features)) or "условия в раскрытии"
    risk_html = f'<div class="road-risk">{_e(" · ".join(dict.fromkeys(risks)))}</div>' if risks else ""
    action = (_link(checkout_url, "Оформить ↗", "road-checkout") if checkout_url
              else '<span class="road-no-link">Ссылка недоступна</span>')
    detail_rows = []
    for leg in (outbound, returning):
        kind = "АВИА" if leg.mode == "flight" else "Ж/Д"
        flights = []
        for hop in leg.hops:
            flights.append(f"{hop.carrier_code} {hop.flight_number}".strip())
        if not flights and leg.service_number:
            flights.append(leg.service_number)
        if len(leg.hops) > 1:
            middle = f"пересадка · {_e(leg.hops[0].to_code)}"
        elif leg.mode == "flight":
            middle = f"прямой · {_e(' → '.join(flights))}"
        else:
            middle = f"без пересадок · {_e(' · '.join(flights))}"
        next_day = " · прилёт на следующий день" if leg.arrival_at.date() > leg.departure_at.date() else ""
        detail_rows.append(f"""
          <div class="road-leg-detail">
            <div class="road-detail-kicker">{_e(_LEG_LABEL[leg.direction])} · {kind}<span>{_duration_label(leg.departure_at, leg.arrival_at)}{next_day}</span></div>
            <div class="road-detail-grid"><div><strong>{_e(leg.origin)}</strong><small>{_e(leg.origin_code or leg.origin)} · {_dt(leg.departure_at)}</small></div><div class="road-route-line"><b>{middle}</b></div><div><strong>{_e(leg.destination)}</strong><small>{_e(leg.destination_code or leg.destination)} · {_dt(leg.arrival_at)}</small></div></div>
            <div class="road-carrier">{_e(leg.carrier)}{f" · {_e(' → '.join(flights))}" if flights else ""}</div>
          </div>""")
    chips = "".join(f"<span>{_e(str(note))}</span>" for note in dict.fromkeys(str(n) for leg in legs for n in leg.notes))
    return f"""<details class="road-option{' road-option-main' if main else ''}"{' open' if main else ''}><summary class="road-summary"><span class="road-icon {icon_class}">{icon}</span><span class="road-dates"><strong>{date_text}</strong><small>{week_text}</small></span><span class="road-duration"><strong>{duration}</strong><small>туда / обратно</small></span><span class="road-features"><strong>{_e(features_text)}</strong>{risk_html}</span><span class="road-price"><strong>{_rub(price or 0)}</strong><small>{'единый заказ' if checkout_url else 'цена из выдачи'}</small></span><span class="road-action">{action}</span><span class="road-chevron">⌄</span></summary><div class="road-option-details">{''.join(detail_rows)}{f'<div class="road-condition-chips">{chips}</div>' if chips else ''}</div></details>"""


def _render_transport_comparison(document: TripPageDocumentV1) -> str:
    main_price = (document.combined_flight.price_rub if document.combined_flight
                  else sum(leg.price_rub for leg in document.transport))
    main_url = (document.combined_flight.checkout_url if document.combined_flight
                else _transport_checkout_url(document))
    rows = [_road_option_html(document, document.transport, main_price, main_url,
                              "Основной маршрут", main=True)]
    rows.extend(_road_option_html(document, option.directions, option.price_rub,
                                  option.checkout_url, option.label or option.id)
                for option in document.flight_options)
    return '<div class="road-compare-list">' + "".join(rows) + "</div>"


def _render_budget(document: TripPageDocumentV1) -> str:
    names = {"transport": "Дорога", "hotel": "Отель", "onsite": "На месте", "total": "Итого"}
    confidence = {"high": "Высокая точность", "medium": "Средняя точность",
                  "low": "Ориентир", "none": "Недостаточно данных"}
    basis = {
        "explicit": "Ваш бюджет", "comparable_trips": "Похожие поездки",
        "weekend_spend": "Расходы за выходные", "live_offers": "Актуальные цены",
        "mixed": "Несколько источников", "insufficient_data": "Мало данных",
    }
    return "".join(f"""
      <article class="budget-card">
        <div class="eyebrow">{_e(confidence[item.confidence])} · {item.sample_size} набл.</div>
        <h3>{_e(names[item.component])}</h3>
        <div class="price">{_rub(item.recommended_rub)}</div>
        <p class="range">{_rub(item.range_min_rub)} — {_rub(item.range_max_rub)}</p>
        <p>{_e(item.explanation)}</p>
        <span class="pill">{_e(basis[item.basis])}</span>
      </article>""" for item in document.budget)


def _hotel_gallery(hotel: HotelOption) -> str:
    photos = list(getattr(hotel, "photos", []) or [])
    if not photos and hotel.image_url:
        photos = [HotelPhoto(url=hotel.image_url)]
    if not photos:
        return '<div class="hotel-gallery is-empty"><div class="image-fallback">Фото в источнике не предоставлено</div></div>'
    images = []
    for index, photo in enumerate(photos):
        attribution = photo.attribution
        if photo.kind == "guest":
            attribution = (f"Фото гостя · {attribution}"
                           if attribution else "Фото гостя")
        images.append(
            f'<div class="hotel-gallery-item hotel-gallery-item-{index + 1}">'
            f'{_image(photo.url, f"{hotel.name}, фото {index + 1}", attribution)}</div>'
        )
    return f'<div class="hotel-gallery count-{len(images)}">{"".join(images)}</div>'


def _review_sample_label(digest: HotelReviewDigest) -> str:
    dates = ""
    if digest.date_from and digest.date_to:
        dates = (f" · {digest.date_from.strftime('%d.%m.%Y')}–"
                 f"{digest.date_to.strftime('%d.%m.%Y')}")
    elif digest.date_from or digest.date_to:
        value = digest.date_from or digest.date_to
        dates = f" · {value.strftime('%d.%m.%Y')}"
    ordering = "сначала новые" if digest.sort_type == "desc" else "сначала старые"
    return f"По {digest.sample_size} загруженным отзывам · {ordering}{dates}"


def _hotel_review_block(hotel: HotelOption) -> str:
    digest = getattr(hotel, "review_digest", None)
    if digest is None:
        summary = hotel.review_summary or "Недостаточно данных"
        return f'<blockquote class="hotel-review">{_e(summary)}</blockquote>'
    if digest.sample_size < 2:
        return (
            '<div class="hotel-review-digest">'
            f'<small>{_e(_review_sample_label(digest))}</small>'
            '<p>Недостаточно данных</p></div>'
        )
    pros = "".join(f"<li>{_e(item)}</li>" for item in digest.pros)
    cons = "".join(f"<li>{_e(item)}</li>" for item in digest.cons)
    summary = digest.summary or hotel.review_summary
    columns = ""
    if pros or cons:
        columns = (
            '<div class="review-columns">'
            f'<div><strong>Чаще хвалят</strong><ul>{pros or "<li>Недостаточно данных</li>"}</ul></div>'
            f'<div><strong>Что учитывать</strong><ul>{cons or "<li>Недостаточно данных</li>"}</ul></div>'
            '</div>'
        )
    suitable = (f'<p class="review-fit"><strong>Кому подходит:</strong> '
                f'{_e(digest.suitable_for)}</p>' if digest.suitable_for else "")
    return (
        '<div class="hotel-review-digest">'
        f'<small>{_e(_review_sample_label(digest))}</small>'
        f'{f"<p>{_e(summary)}</p>" if summary else ""}{columns}{suitable}</div>'
    )


_HOTEL_PAYMENT_LABELS = {
    "now": "Оплата сейчас",
    "hotel": "Оплата в отеле",
}


def _hotel_payment_label(value: str) -> str:
    """Humanize stable Hotels API enum values without guessing unknown ones."""
    text = str(value or "").strip()
    return _HOTEL_PAYMENT_LABELS.get(text.casefold(), text)


def _render_hotels(document: TripPageDocumentV1 | TripPageDocumentV2 | HotelPageDocumentV1) -> str:
    cards = []
    tier_labels = ("Выгодный", "Сбалансированный", "Больше комфорта")
    for index, hotel in enumerate(document.hotels):
        selected = hotel.id == document.selected_hotel_id
        label = tier_labels[index] if len(document.hotels) == 3 else f"Вариант {index + 1:02d}"
        facts = [
            ("Номер", hotel.room),
            ("Питание", hotel.meal),
            ("Отмена", hotel.cancellation),
            ("Оплата", _hotel_payment_label(hotel.payment)),
            ("Заезд", getattr(hotel, "check_in_time", "")),
            ("Выезд", getattr(hotel, "check_out_time", "")),
        ]
        conditions = "".join(
            f'<li><span>{_e(fact_label)}</span><strong>{_e(value)}</strong></li>'
            for fact_label, value in facts if value
        )
        rating = (
            f'Рейтинг {_e(hotel.rating)}'
            f'{(" · " + _e(hotel.review_count) + " отзывов") if hotel.review_count is not None else ""}'
            if hotel.rating is not None else "Рейтинг не указан"
        )
        description = getattr(hotel, "description", "")
        location = getattr(hotel, "location_summary", "")
        facilities = getattr(hotel, "facilities", []) or []
        tags = "".join(f"<span>{_e(item)}</span>" for item in facilities[:6])
        details_url = (safe_tbank_url(getattr(hotel, "details_url", None))
                       or hotel_details_url(hotel.id))
        details_action = _checkout_action(
            details_url, "Открыть отель в T-Bank", "Ссылка T-Bank недоступна")
        checkout_action = (_link(hotel.booking_url, "Перейти к оформлению", "button button-primary")
                           if hotel.booking_url else "")
        actions = (f'<div class="hotel-actions">{details_action}{checkout_action}</div>'
                   if details_action or checkout_action else "")
        cards.append(f"""
        <article class="hotel-card {'selected' if selected else ''}" id="entity-{_e(hotel.id)}">
          <div class="card-media">{_hotel_gallery(hotel)}<span class="card-rank">{index + 1:02d}</span><span class="hotel-tier">{_e(label)}</span></div>
          <div class="card-body">
            <div class="eyebrow">{'Рекомендуем · ' if selected else ''}{'★' * hotel.stars}</div>
            <h3>{_e(hotel.name)}</h3><p>{_e(location or hotel.address)}</p>
            {f'<p class="hotel-description">{_e(description)}</p>' if description else ''}
            <div class="hotel-metrics"><span>{rating}</span><span>{_rub(hotel.nightly_price_rub)} за ночь</span></div>
            {f'<div class="card-tags hotel-facilities">{tags}</div>' if tags else ''}
            {f'<ul class="hotel-conditions">{conditions}</ul>' if conditions else '<p class="muted-note">Условия тарифа нужно уточнить перед оформлением.</p>'}
            {_hotel_review_block(hotel)}
            <div class="price">{_rub(hotel.total_price_rub)} <small>за весь период</small></div>
            {actions}
          </div>
        </article>""")
    return "".join(cards)


def _comparison_list(values: list[str]) -> str:
    return "<br>".join(_e(value) for value in values) if values else "—"


def _render_hotel_comparison(
        document: TripPageDocumentV1 | TripPageDocumentV2 | HotelPageDocumentV1) -> str:
    hotels = document.hotels

    def digest(hotel):
        return getattr(hotel, "review_digest", None)

    def digest_values(hotel, field: str) -> list[str]:
        item = digest(hotel)
        if item is None or item.sample_size < 2:
            return ["Недостаточно данных"]
        values = list(getattr(item, field) or [])
        return values or ["Недостаточно данных"]

    def suitable_for(hotel) -> str:
        item = digest(hotel)
        if item is None or item.sample_size < 2 or not item.suitable_for:
            return "Недостаточно данных"
        return item.suitable_for

    rows = [
        ("Полная цена", lambda hotel: _rub(hotel.total_price_rub)),
        ("Цена за ночь", lambda hotel: _rub(hotel.nightly_price_rub)),
        ("Звёзды", lambda hotel: "★" * hotel.stars if hotel.stars else "—"),
        ("Рейтинг и отзывы", lambda hotel: (
            f"{hotel.rating:g} · {hotel.review_count} отзывов"
            if hotel.rating is not None and hotel.review_count is not None
            else (f"{hotel.rating:g}" if hotel.rating is not None else "—"))),
        ("Расположение", lambda hotel: _e(
            getattr(hotel, "location_summary", "") or hotel.address)),
        ("Номер", lambda hotel: _e(hotel.room) if hotel.room else "—"),
        ("Питание", lambda hotel: _e(hotel.meal) if hotel.meal else "—"),
        ("Отмена", lambda hotel: _e(hotel.cancellation) if hotel.cancellation else "—"),
        ("Оплата", lambda hotel: (
            _e(_hotel_payment_label(hotel.payment)) if hotel.payment else "—")),
        ("Удобства", lambda hotel: _comparison_list(
            list(getattr(hotel, "facilities", []) or [])[:6])),
        ("Плюсы по отзывам", lambda hotel: _comparison_list(
            digest_values(hotel, "pros"))),
        ("Минусы по отзывам", lambda hotel: _comparison_list(
            digest_values(hotel, "cons"))),
        ("Для кого подходит", lambda hotel: _e(suitable_for(hotel))),
    ]
    headers = "".join(
        f'<th class="{"is-selected" if hotel.id == document.selected_hotel_id else ""}">'
        f'<span>{"Рекомендуем" if hotel.id == document.selected_hotel_id else f"Вариант {index + 1}"}</span>'
        f'<strong>{_e(hotel.name)}</strong></th>'
        for index, hotel in enumerate(hotels)
    )
    body = "".join(
        f'<tr><th scope="row">{_e(label)}</th>'
        + "".join(
            f'<td class="{"is-selected" if hotel.id == document.selected_hotel_id else ""}">'
            f'{renderer(hotel)}</td>' for hotel in hotels
        ) + "</tr>"
        for label, renderer in rows
    )
    return (
        '<div class="comparison-scroll"><table class="hotel-comparison">'
        f'<thead><tr><th scope="col">Критерий</th>{headers}</tr></thead>'
        f'<tbody>{body}</tbody></table></div>'
    )


def _render_events(document: TripPageDocumentV1) -> str:
    if not document.events:
        return '<p class="empty">Подходящих мероприятий на эти даты пока нет.</p>'
    return "".join(f"""
      <article class="event-card" id="entity-{_e(item.id)}">
        <div class="card-media">{_image(item.image_url, item.name)}<span class="card-rank">{index:02d}</span><span class="card-match">{item.personalization_score:.0f}% совпадение</span></div>
        <div class="card-body">
          <div class="eyebrow">{_e(item.kind)}{(' · ' + _e(item.age_restriction)) if item.age_restriction else ''}</div>
          <h3>{_e(item.name)}</h3>
          <p><strong>{_e(_dt(item.starts_at))}</strong> · {_e(item.venue)}</p>
          <p class="event-address">{_e(item.address)}</p>
          {f'<div class="card-tags">{"".join(f"<span>{_e(genre)}</span>" for genre in item.genres)}</div>' if item.genres else ''}
          <p>{_e(item.match_reason)}</p>
          <div class="price">{('от ' + _rub(item.price_from_rub)) if item.price_from_rub is not None else 'Цена уточняется'}</div>
          {_checkout_action(item.source_url, 'Открыть событие в T-Bank', 'Ссылка T-Bank недоступна')}
        </div>
      </article>""" for index, item in enumerate(sorted(document.events,
                                         key=lambda event: -event.personalization_score), 1))


def _render_venues(document: TripPageDocumentV1) -> str:
    cards = []
    for item in document.venues:
        photo = item.photos[0] if item.photos else None
        if item.rating is not None:
            reviews = (f" · {item.review_count:n}" if item.review_count is not None else "")
            metric = f'<span class="card-match">★ {item.rating:g}{reviews}</span>'
        else:
            metric = '<span class="card-match">OpenStreetMap</span>'
        cards.append(f"""
          <article class="venue-card" id="entity-{_e(item.id)}">
            <div class="card-media">{_image(photo.url if photo else None, item.name, photo.attribution if photo else '')}{metric}</div>
            <div class="card-body">
              <div class="eyebrow">{'Ресторан' if item.kind == 'restaurant' else 'Бар'}{(' · ' + _e(item.price_level)) if item.price_level else ''}</div>
              <h3>{_e(item.name)}</h3><p>{_e(item.address)}</p>
              <p>{_e(', '.join(item.categories))}</p>
              {f'<small>{_e(item.opening_hours)}</small>' if item.opening_hours else ''}
              {_link(item.openstreetmap_url, 'Открыть в OpenStreetMap')}
            </div>
          </article>""")
    return "".join(cards)


def _render_plans(document: TripPageDocumentV1, entities: dict[str, dict]) -> str:
    blocks = []
    for index, plan in enumerate(document.plans):
        days = []
        for day in plan.days:
            stops = "".join(f"""
              <li><time>{_e(stop.starts_at.strftime('%H:%M'))}–{_e(stop.ends_at.strftime('%H:%M'))}</time>
              <div><a href="#entity-{_e(stop.ref_id)}">{_e(entities[stop.ref_id]['label'])}</a>
              {f'<p>{_e(stop.note)}</p>' if stop.note else ''}</div></li>""" for stop in day.stops)
            days.append(f'<div class="plan-day"><h4>{_e(day.date.strftime("%d.%m"))} · {_e(day.title)}</h4><ol>{stops}</ol></div>')
        blocks.append(f"""
          <details class="plan" {'open' if index == 0 else ''}>
            <summary><span class="plan-number">0{index + 1}</span><div><h3>{_e(plan.title)}</h3><p>{_e(plan.summary)}</p></div></summary>
            <div class="plan-content">{''.join(days)}</div>
          </details>""")
    return "".join(blocks)


def _content_security_policy(scripts: list[str]) -> str:
    script_hashes = []
    for source in scripts:
        digest = base64.b64encode(hashlib.sha256(source.encode()).digest()).decode()
        script_hashes.append(f"'sha256-{digest}'")
    script_src = f"script-src {' '.join(script_hashes)}; " if script_hashes else ""
    return ("default-src 'none'; img-src https: data:; style-src 'unsafe-inline'; "
            f"{script_src}connect-src https:; base-uri 'none'; form-action 'none'; "
            "object-src 'none'")


def _page_head(title: str, csp: str, extra_css: str = "") -> str:
    return (
        '<!doctype html><html lang="ru"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<meta http-equiv="Content-Security-Policy" content="{_e(csp)}">'
        f'<title>{_e(title)}</title>'
        f'{f"<style>{extra_css}</style>" if extra_css else ""}'
        f'<style>{_asset("trip-page.css.txt")}</style></head>'
    )


def _site_header(nav_items: list[tuple[str, str]], destination: str,
                 date_label: str, aria_label: str) -> str:
    links = "".join(f'<a href="#{_e(anchor)}">{_e(label)}</a>'
                    for anchor, label in nav_items)
    return (
        '<header class="site-header"><a class="brand" href="#top">'
        '<span class="logo-mark">TN</span><strong>travel nova</strong></a>'
        f'<nav class="site-nav" aria-label="{_e(aria_label)}">{links}</nav>'
        f'<div class="header-meta"><span>{_e(destination)}</span>'
        f'<span>{_e(date_label)}</span></div></header>'
    )


def _fine_print(document) -> str:
    warnings = "".join(f"<li>{_e(item)}</li>" for item in document.warnings)
    sources = "".join(
        f'<li>{_link(item.url, item.name, "source-link") if item.url else _e(item.name)}'
        f'<small>{_e(_dt(item.checked_at))}</small></li>' for item in document.sources)
    return (
        '<section class="fine-print" id="sources">'
        f'<div><h2>Источники</h2><ul class="sources">{sources}</ul></div>'
        '<div><h2>Важно знать</h2><ul>'
        f'{warnings or "<li>Цены и доступность могут измениться до оформления.</li>"}'
        '</ul></div></section>'
    )


def _page_footer() -> str:
    return ('<footer><b>travel nova</b><span>Страница не является подтверждением '
            'бронирования или оплаты.</span></footer>')


def render_html(document: TripPageDocumentV1 | TripPageDocumentV2) -> str:
    """Render one self-contained trip page, except for remote images and OSM tiles."""
    leaflet_css = _asset("leaflet-1.9.4.css.txt")
    leaflet_js = _asset("leaflet-1.9.4.js.txt")
    app_js = _asset("trip-page.js.txt")
    entities = _entity_index(document)
    map_ids = list(dict.fromkeys(
        [hotel.id for hotel in document.hotels]
        + [point.ref_id for point in document.map_points]
    ))
    map_rows = [entities[entity_id] for entity_id in map_ids if entity_id in entities]
    map_json = json.dumps(map_rows, ensure_ascii=False, separators=(",", ":"))
    map_json = map_json.replace("<", "\\u003c").replace(">", "\\u003e")
    csp = _content_security_policy([leaflet_js, app_js])
    entity_labels = {
        item.id: {"label": item.name}
        for item in [*document.hotels, *document.events, *document.venues]
    }
    # Transport is valid for a plan reference too, even though it is not mapped.
    entity_labels.update({leg.id: {"label": f"{leg.origin} → {leg.destination}"}
                          for leg in document.transport})
    total_budget = next(
        (item for item in document.budget if item.component == "total"), None)
    outbound = min(
        (leg for leg in document.transport if leg.direction == "outbound"),
        key=lambda leg: leg.departure_at,
        default=None,
    )
    if total_budget is None:
        budget_summary = (
            '<span>Ориентир не рассчитан</span><strong>—</strong>'
            '<small>Бюджет не передан</small>')
    else:
        budget_summary = (
            f'<span>Комфортный ориентир</span>'
            f'<strong>{_rub(total_budget.recommended_rub)}</strong>'
            f'<small>{_rub(total_budget.range_min_rub)} — '
            f'{_rub(total_budget.range_max_rub)}</small>')
    if document.personalization is None:
        profile_summary = (
            '<div><b>—</b><small>профиль поездок</small></div>'
            '<div><b>—</b><small>профиль Афиши</small></div>')
        budget_explanation = "Детали расчёта указаны в карточках."
    else:
        profile_summary = (
            f'<div><b>{document.personalization.travel_sample_size}</b>'
            '<small>поездок в основе</small></div>'
            f'<div><b>{document.personalization.event_sample_size}</b>'
            '<small>заказов Афиши</small></div>')
        budget_explanation = document.personalization.explanation
    route_label = (f"{outbound.origin} → {outbound.destination}"
                   if outbound is not None else document.trip.destination)
    budget_section = (
        '<section class="budget-section" id="budget"><div class="section-head">'
        '<div><span>01</span><h2>Бюджет поездки</h2></div>'
        f'<p>{_e(budget_explanation)}</p></div><div class="budget-grid">'
        f'{_render_budget(document)}</div></section>'
        if document.budget else ""
    )
    transport_section = (
        '<section class="route-section" id="route"><div class="section-head">'
        '<div><span>02</span><h2>Дорога туда и обратно</h2></div>'
        '<p>Сравните способы добраться; оформление откроется в T-Bank '
        'отдельно и не означает покупку.</p></div>'
        f'{_render_transport_comparison(document)}</section>'
        if document.transport or document.flight_options else ""
    )
    date_label = (f"{document.trip.date_from.strftime('%d.%m')}–"
                  f"{document.trip.date_to.strftime('%d.%m.%Y')}")
    head = _page_head(document.trip.title, csp, leaflet_css)
    header = _site_header(
        [("route", "Дорога"), ("hotels", "Отели"), ("comparison", "Сравнение"),
         ("events", "Афиша"), ("places", "Места"), ("plans", "Планы")],
        document.trip.destination, date_label, "Разделы поездки")
    return f"""{head}
<body>{header}
<main>
<section class="hero" id="top"><div class="hero-copy"><p class="hero-kicker">Персональный план поездки</p><h1>{_e(document.trip.title)}</h1><p class="hero-lede">{_e(document.trip.subtitle)}</p><div class="hero-meta"><span>{_e(route_label)}</span><span>{_e(document.trip.date_from.strftime('%d.%m'))} — {_e(document.trip.date_to.strftime('%d.%m.%Y'))}</span><span>{document.trip.travelers} чел.</span><span>Проверено {_e(_dt(document.checked_at))}</span></div></div>
<aside class="trip-profile">{budget_summary}{profile_summary}</aside></section>
{budget_section}
{transport_section}
<section class="hotels-section" id="hotels"><div class="section-head"><div><span>03</span><h2>Где остановиться</h2></div><p>Три уровня цены с конкретным номером, условиями тарифа, отзывами и ссылкой на карточку T-Bank.</p></div><div class="hotels">{_render_hotels(document)}</div><div class="hotel-comparison-block" id="comparison"><div class="subsection-head"><span>Сравнение</span><h3>Все условия рядом</h3><p>Резюме отзывов относится только к реально загруженной выборке.</p></div>{_render_hotel_comparison(document)}</div></section>
<section class="events-section" id="events"><div class="section-head"><div><span>04</span><h2>Что посмотреть</h2></div><p>События ранжируются по безопасному профилю интересов без раскрытия истории покупок.</p></div><div class="card-grid events">{_render_events(document)}</div></section>
<section class="venues-section" id="places"><div class="section-head"><div><span>05</span><h2>Рестораны и бары</h2></div><p>Заведения, категории и часы работы получены из OpenStreetMap через T-Bank MCP.</p></div><div class="card-grid venues">{_render_venues(document)}</div></section>
<section class="map-section" id="map"><div class="section-head"><div><span>06</span><h2>Всё на карте</h2></div><p>Все три отеля, мероприятия и заведения. Нажмите маркер, чтобы перейти к карточке.</p></div><div id="trip-map" aria-label="Карта поездки OpenStreetMap"><div class="map-fallback">Карта появится при подключении к интернету.</div></div><div class="map-legend"><span class="hotel">Отели</span><span class="event">События</span><span class="restaurant">Рестораны</span><span class="bar">Бары</span></div></section>
<section class="plans-section" id="plans"><div class="section-head"><div><span>07</span><h2>Три сценария поездки</h2></div><p>Выберите темп: сбалансированный, культурный или с акцентом на еду и вечернюю жизнь.</p></div><div class="plans">{_render_plans(document, entity_labels)}</div></section>
{_fine_print(document)}</main>{_page_footer()}
<script id="trip-map-data" type="application/json">{map_json}</script>
<script>{leaflet_js}</script><script>{app_js}</script></body></html>"""


def render_hotel_html(document: HotelPageDocumentV1) -> str:
    """Render a hotel shortlist with the same shell and design system as a trip page."""
    app_js = _asset("trip-page.js.txt")
    csp = _content_security_policy([app_js])
    date_label = (f"{document.search.date_from.strftime('%d.%m')}–"
                  f"{document.search.date_to.strftime('%d.%m.%Y')}")
    head = _page_head(document.search.title, csp)
    header = _site_header(
        [("hotels", "Отели"), ("comparison", "Сравнение"), ("sources", "Источники")],
        document.search.destination, date_label, "Разделы подборки отелей")
    selected = next(hotel for hotel in document.hotels
                    if hotel.id == document.selected_hotel_id)
    review_sample = sum(
        hotel.review_digest.sample_size for hotel in document.hotels
        if hotel.review_digest is not None)
    children = len(document.search.children_ages)
    guests = f"{document.search.adults} взр."
    if children:
        guests += f" · {children} дет."
    return f"""{head}
<body>{header}<main>
<section class="hero hotel-hero" id="top"><div class="hero-copy"><p class="hero-kicker">Подборка отелей</p><h1>{_e(document.search.title)}</h1><p class="hero-lede">{_e(document.search.subtitle)}</p><div class="hero-meta"><span>{_e(document.search.destination)}</span><span>{_e(date_label)}</span><span>{_e(guests)}</span><span>Проверено {_e(_dt(document.checked_at))}</span></div></div>
<aside class="trip-profile"><span>Рекомендуемый вариант</span><strong>{_rub(selected.total_price_rub)}</strong><small>{_e(selected.name)}</small><div><b>{len(document.hotels)}</b><small>отелей в сравнении</small></div><div><b>{review_sample}</b><small>отзывов загружено</small></div></aside></section>
<section class="hotels-section" id="hotels"><div class="section-head"><div><span>01</span><h2>Где остановиться</h2></div><p>Актуальные предложения с фотографиями, условиями тарифов и отдельными обзорами отзывов.</p></div><div class="hotels hotels-five">{_render_hotels(document)}</div></section>
<section class="comparison-section" id="comparison"><div class="section-head"><div><span>02</span><h2>Сравнение отелей</h2></div><p>Отзывы сравниваются на сопоставимых выборках; отсутствующие сведения не подменяются предположениями.</p></div>{_render_hotel_comparison(document)}</section>
{_fine_print(document)}</main>{_page_footer()}<script>{app_js}</script></body></html>"""


def render_travel_html(document: TripPageDocumentV2 | HotelPageDocumentV1) -> str:
    if isinstance(document, HotelPageDocumentV1):
        return render_hotel_html(document)
    return render_html(document)


# ---------------------------------------------------------------------------
# Chat-ready page and Markdown reply (content-only; nothing touches the disk).
# MCP hosts receive these strings directly — no htmlPath/jsonPath, no files.
# ---------------------------------------------------------------------------

_COMPACT_CSS = """
:root{--ink:#111827;--mut:#6b7280;--accent:#ffdd2d;--line:#e5e7eb;--deep:#3730a3}
*{box-sizing:border-box}
body{margin:0;font:15px/1.5 -apple-system,"Segoe UI",Roboto,Arial,sans-serif;color:var(--ink);background:#f2f3f7}
.wrap{max-width:780px;margin:0 auto;padding:20px 14px 44px}
.top{background:#fff;border:1px solid var(--line);border-radius:18px;padding:20px}
.kicker{text-transform:uppercase;letter-spacing:.09em;font-size:11px;color:var(--mut);margin:0 0 4px}
h1{font-size:25px;margin:0 0 6px;line-height:1.2}
.lede{color:var(--mut);margin:0 0 12px}
.meta{display:flex;flex-wrap:wrap;gap:6px}
.chip{background:#eef2ff;border:1px solid var(--line);border-radius:999px;padding:2px 11px;font-size:12px;color:var(--deep)}
h2{font-size:12px;letter-spacing:.09em;text-transform:uppercase;color:var(--mut);margin:20px 0 8px}
.card{background:#fff;border:1px solid var(--line);border-radius:15px;padding:14px 16px;margin-bottom:10px}
.sel{border:2px solid var(--accent)}
.sel-tag{display:inline-block;background:var(--accent);font-size:11px;font-weight:700;border-radius:6px;padding:1px 8px;margin-left:6px}
.price{font-weight:800;font-size:19px;margin-top:6px}
.price small{color:var(--mut);font-weight:400;font-size:12px}
.small{color:var(--mut);font-size:12px}
.stat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin-top:10px}
.stat{background:#f9fafb;border:1px solid var(--line);border-radius:11px;padding:8px 11px}
.stat b{display:block;font-size:16px}
.stat span{font-size:11px;color:var(--mut)}
.row{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;align-items:baseline}
.facts{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}
.fact{font-size:12px;background:#f3f4f6;border-radius:7px;padding:2px 9px}
.btn{display:inline-block;background:var(--accent);color:#111;text-decoration:none;font-weight:700;border-radius:10px;padding:7px 13px;font-size:13px;margin:4px 8px 0 0}
.btn.ghost{background:#fff;border:1px solid var(--line)}
.no{color:var(--mut);font-size:12px;margin:7px 0 0;font-style:italic}
.photo{width:100%;height:160px;object-fit:cover;border-radius:12px;margin:0 0 10px;background:#eef0f4}
.fine{color:var(--mut);font-size:12px;margin-top:16px;border-top:1px dashed #d1d5db;padding-top:10px}
.fine ul{margin:4px 0;padding-left:18px}
.li-row{display:flex;gap:12px;justify-content:space-between;align-items:baseline;padding:9px 0;border-bottom:1px solid var(--line);font-size:14px}
.li-row:last-child{border-bottom:0}
.li-date{white-space:nowrap;color:var(--mut);font-size:12px}
.li-act{margin-left:auto;padding-left:10px;white-space:nowrap}
a{color:var(--deep)}
"""


_ROUTE_ICON = {"flight": "✈", "train": "🚆"}
_LEG_LABEL = {"outbound": "Туда", "return": "Обратно"}


def _trip_share_url(document: TripPageDocumentV2) -> str:
    """T-Bank avia „share“ deep link for the whole chosen route (no UTM).

    Built only from source-verified fields on TransportLeg: per-leg hops when
    present (real segments, works for transfers), otherwise the single
    flightNumber fields. Path uses the direction city pair + its departure
    date; segments inside a direction are joined with "_" in the flights
    parameter. Passenger count mirrors the search used for flight prices.
    Empty when data is missing — callers show «Ссылка T-Bank недоступна».
    """
    legs = []
    for leg in sorted(document.transport, key=lambda item: item.departure_at):
        if leg.mode != "flight":
            return ""
        if not (leg.origin_code and leg.destination_code):
            return ""
        segments = []
        hops = list(leg.hops)
        if hops:
            for hop in hops:
                if not (hop.carrier_code and hop.flight_number):
                    return ""
                segments.append({
                    "date": hop.departure_at.date().isoformat(),
                    "carrier": hop.carrier_code,
                    "flight": hop.flight_number,
                })
        else:
            if not (leg.carrier_code and leg.flight_number):
                return ""
            segments.append({
                "date": leg.departure_at.date().isoformat(),
                "carrier": leg.carrier_code,
                "flight": leg.flight_number,
            })
        legs.append({
            "origin": leg.origin_code,
            "destination": leg.destination_code,
            "date": leg.departure_at.date().isoformat(),
            "segments": segments,
        })
    if not legs:
        return ""
    return avia_share_url(legs, adults=document.trip.travelers)


def _leg_booking_url(leg) -> str:
    """Primary T-Bank link for one flight leg: source tbankUrl, else the offer
    checkout link built from its offerId (bookable T-Bank offers). Empty when
    neither exists — show «Ссылка T-Bank недоступна»."""
    source = getattr(leg, "tbank_url", None)
    if source:
        return str(source)
    offer_id = str(getattr(leg, "offer_id", "") or "").strip()
    if offer_id:
        return avia_checkout_url(offer_id)
    return ""


def _flight_options_section(document, *, full: bool = False) -> str:
    """Блок «Варианты перелёта»: альтернативы с комментарием модели.

    Читает document.flight_options (FlightOption[]): каждый вариант — label,
    comment и directions (outbound+return TransportLeg со ссылками). Выбранная
    пара живёт в document.transport; здесь — только альтернативы.
    """
    options = getattr(document, "flight_options", None) or []
    if not options:
        return ""
    card_cls = "transport-card" if full else "card"
    btn_cls = "button" if full else "btn"
    items = []
    for option in options:
        combined_url = str(getattr(option, "checkout_url", "") or "")
        legs = sorted(option.directions, key=lambda leg: leg.departure_at)
        leg_lines = []
        for leg in legs:
            origin = leg.origin_code or leg.origin
            destination = leg.destination_code or leg.destination
            route = f"{_e(origin)} {_ROUTE_ICON.get(leg.mode, '→')} {_e(destination)}"
            when = f"{_e(_dt(leg.departure_at))} → {_e(_dt(leg.arrival_at))}"
            head = (f'<b>{_e(_LEG_LABEL[leg.direction])}</b> · {route}<br>'
                    f'<span class="small">{_e(leg.carrier)}'
                    + (f' · {_e(leg.service_number)}' if leg.service_number else '')
                    + '</span><br><span class="small">' + when + '</span>')
            if combined_url:
                leg_lines.append(f'<div class="row" style="margin-top:8px"><span>{head}</span></div>')
                continue
            url = _leg_booking_url(leg)
            action = (f'<a class="{btn_cls}" href="{_e(url)}" target="_blank" '
                      f'rel="noopener noreferrer">Оформить в T-Bank</a>' if url
                      else '<span class="no">Ссылка T-Bank недоступна</span>')
            price = f'<div class="price">{_rub(leg.price_rub)}</div>'
            leg_lines.append(f'<div class="row" style="margin-top:8px"><span>{head}</span></div>'
                             f'{price}{action}')
        total_line = ""
        combined_btn = ""
        if combined_url:
            if option.price_rub:
                total_line = (f'<div class="price">{_rub(option.price_rub)} '
                              '<small>единый оффер: оба перелёта</small></div>')
            combined_btn = (f'<a class="{btn_cls}" href="{_e(combined_url)}" target="_blank" '
                            f'rel="noopener noreferrer">Оформить оба перелёта в T-Bank</a>')
        elif option.price_rub:
            total_line = f'<div class="price">{_rub(option.price_rub)}</div>'
        items.append(
            f'<article class="{card_cls}" style="margin-bottom:10px">'
            f'<div class="row"><span><b>{_e(option.label or option.id)}</b></span></div>'
            f'<p class="small">{_e(option.comment)}</p>{total_line}'
            + "".join(leg_lines) + combined_btn + "</article>")
    return ('<section id="flight-options"><div class="section-head" style="margin-bottom:8px">'
            f'<h2>Варианты перелёта</h2></div>{"".join(items)}</section>')


def _combined_route_card(document, legs) -> str:
    """Одна карточка «туда и обратно» для единого round-trip оффера."""
    combined = getattr(document, "combined_flight", None)
    if combined is None:
        return ""
    rows = []
    for leg in sorted(legs, key=lambda leg: leg.departure_at):
        origin = leg.origin_code or leg.origin
        destination = leg.destination_code or leg.destination
        route = f"{_e(origin)} {_ROUTE_ICON.get(leg.mode, '→')} {_e(destination)}"
        rows.append(
            '<div class="row" style="margin-top:8px">'
            f'<span><b>{_e(_LEG_LABEL[leg.direction])}</b> · {route}</span>'
            f'<span class="small">{_e(leg.carrier)}</span></div>'
            f'<p class="small" style="margin:2px 0 0">{_e(_dt(leg.departure_at))} → '
            f'{_e(_dt(leg.arrival_at))}</p>')
    action = (f'<a class="btn" href="{_e(combined.checkout_url)}" target="_blank" '
              f'rel="noopener noreferrer">Оформить оба перелёта в T-Bank</a>'
              if combined.checkout_url else '<p class="no">Ссылка T-Bank недоступна</p>')
    return ('<section><h2>Дорога туда и обратно · единый оффер</h2><article class="card">'
            + "".join(rows)
            + f'<div class="price">{_rub(combined.price_rub)} '
            '<small>за обоих за оба перелёта (единый оффер)</small></div>'
            + action + "</article></section>")


def _route_section_html(document, transport_cards, legs, share_html) -> str:
    combined = _combined_route_card(document, legs)
    if combined:
        return combined
    return (('<section><h2>Дорога туда и обратно</h2>' + "".join(transport_cards)
             + share_html + "</section>") if transport_cards else "")


def _compact_actions(primary_url: str, primary_label: str,
                     secondary_url: str = "", secondary_label: str = "") -> str:
    """Primary T-Bank action plus an optional checkout link; honest when absent."""
    parts = []
    if primary_url:
        parts.append(f'<a class="btn" href="{_e(primary_url)}" target="_blank" '
                     f'rel="noopener noreferrer">{_e(primary_label)}</a>')
    else:
        parts.append(f'<p class="no">Ссылка T-Bank недоступна</p>')
    if secondary_url:
        parts.append(f'<a class="btn ghost" href="{_e(secondary_url)}" target="_blank" '
                     f'rel="noopener noreferrer">{_e(secondary_label)}</a>')
    return "".join(parts)


def _compact_hotel_card(hotel: HotelOptionV2, *, selected: bool,
                        nights: int, guests: str) -> str:
    photo = next((photo.url for photo in hotel.photos), "") or (hotel.image_url or "")
    image = (f'<img class="photo" src="{_e(photo)}" alt="{_e(hotel.name)}" '
             f'loading="lazy" referrerpolicy="no-referrer">') if photo else ""
    facts = []
    if hotel.stars:
        facts.append("★" * hotel.stars)
    if hotel.rating is not None:
        label = (f"{hotel.rating:g}/10" if hotel.rating <= 10 else f"{hotel.rating:g}")
        facts.append(f"рейтинг {label}")
    if hotel.meal:
        facts.append(_e(hotel.meal))
    if hotel.room:
        facts.append(_e(hotel.room))
    if hotel.cancellation:
        facts.append(_e(hotel.cancellation))
    if hotel.payment:
        facts.append(_e(_hotel_payment_label(hotel.payment)))
    if hotel.location_summary:
        facts.append(_e(hotel.location_summary))
    facts_html = ("".join(f'<span class="fact">{fact}</span>' for fact in facts)
                  if facts else "")
    per_night = ""
    if hotel.nightly_price_rub:
        per_night = (f'<small>≈ {_rub(hotel.nightly_price_rub)} за ночь · '
                     f'{_e(guests)}</small>')
    return f"""
<article class="card{' sel' if selected else ''}">
  {image}<div class="row"><div><b>{_e(hotel.name)}</b>{'<span class="sel-tag">Рекомендуем</span>' if selected else ''}</div></div>
  <div class="small">{_e(hotel.address)}</div>
  {f'<div class="facts">{facts_html}</div>' if facts_html else ''}
  <div class="price">{_rub(hotel.total_price_rub)} {per_night}</div>
  {_compact_actions(hotel.details_url, 'Открыть отель в T-Bank', hotel.booking_url, 'Перейти к оформлению')}
</article>"""


def _compact_trip_page(document: TripPageDocumentV2) -> str:
    trip = document.trip
    nights = (trip.date_to - trip.date_from).days
    adults = trip.travelers
    legs = sorted(document.transport, key=lambda leg: leg.departure_at)
    outbound = next((leg for leg in legs if leg.direction == "outbound"), None)
    date_label = f"{trip.date_from.strftime('%d.%m')}–{trip.date_to.strftime('%d.%m.%Y')}"
    budgets = {item.component: item for item in document.budget}
    budget_cells = []
    labels = {"transport": "Дорога", "hotel": "Отель", "onsite": "На месте", "total": "Ориентир всего"}
    basis_line = f"для {_adults(trip.travelers)}"
    for component in ("transport", "hotel", "onsite", "total"):
        item = budgets.get(component)
        if item is None:
            continue
        span = basis_line if component in ("transport", "hotel", "total") else "по оценке"
        if item.range_min_rub is not None or item.range_max_rub is not None:
            span = span + (" · " if span else "") + (
                f"{_rub(item.range_min_rub)} — {_rub(item.range_max_rub)}")
        budget_cells.append(
            f'<div class="stat"><span>{_e(labels[component])}</span>'
            f'<b>{_rub(item.recommended_rub)}</b><span>{span}</span></div>')
    budget_note_html = ""
    transport_cards = []
    for leg in legs:
        notes = "".join(f'<span class="fact">{_e(note)}</span>' for note in leg.notes)
        transport_cards.append(f"""
<article class="card">
  <div class="row"><b>{_e(_LEG_LABEL[leg.direction])} · {_e(leg.mode)}</b>
  <span>{_e(leg.origin)} {_ROUTE_ICON.get(leg.mode, '→')} {_e(leg.destination)}</span></div>
  <div class="small">{_e(leg.carrier)}{(' · ' + _e(leg.service_number)) if leg.service_number else ''}
  {' · продавец: ' + _e(leg.seller) if leg.seller else ''}</div>
  <p><b>{_e(_dt(leg.departure_at))}</b> → <b>{_e(_dt(leg.arrival_at))}</b></p>
  {f'<div class="facts">{notes}</div>' if notes else ''}
  <div class="price">{_rub(leg.price_rub)} <small>для {_adults(trip.travelers)}</small></div>
  {_compact_actions(_leg_booking_url(leg), 'Оформить в T-Bank', leg.booking_url, 'Перейти к оформлению')}
</article>""")
    hotel_cards = "".join(
        _compact_hotel_card(
            hotel, selected=hotel.id == document.selected_hotel_id,
            nights=nights, guests=_adults(trip.travelers))
        for hotel in document.hotels)
    share = _trip_share_url(document)
    share_html = (f'<div class="row" style="margin-top:6px">'
                  f'<a class="btn" href="{_e(share)}" target="_blank" '
                  f'rel="noopener noreferrer">Открыть весь маршрут в T-Bank</a>'
                  '<span class="small">Откроется поиск по этим рейсам и датам; '
                  'бронь и оплата — у банка.</span></div>' if share else "")
    event_rows = []
    for event in sorted(document.events, key=lambda item: item.starts_at):
        when = event.starts_at.strftime("%d.%m %H:%M")
        price = f"от {_rub(event.price_from_rub)}" if event.price_from_rub else ""
        extra = " · ".join(part for part in (
            event.venue, price, " ".join(event.genres)) if part)
        action = (f'<a class="li-act" href="{_e(event.source_url)}" target="_blank" '
                  f'rel="noopener noreferrer">Подробнее</a>'
                  if event.source_url else '<span class="li-act small">Ссылка недоступна</span>')
        event_rows.append(
            f'<div class="li-row"><span class="li-date">{_e(when)}</span>'
            f'<span><b>{_e(event.name)}</b><br><span class="small">{_e(extra)}</span></span>{action}</div>')
    venue_rows = []
    for venue in sorted(document.venues, key=lambda item: (item.kind, item.name)):
        rating = (f"{venue.rating:g}/{venue.rating_scale:g}" if venue.rating is not None else "")
        meta = " · ".join(part for part in (
            venue.kind, rating, venue.address, " ".join(venue.categories),
            venue.opening_hours) if part)
        venue_rows.append(
            f'<div class="li-row"><b>{_e(venue.name)}</b>'
            f'<span class="small">{_e(meta)}</span>'
            f'<a class="li-act small" href="{_e(venue.openstreetmap_url)}" target="_blank" '
            f'rel="noopener noreferrer">OpenStreetMap</a></div>')
    warnings = "".join(f"<li>{_e(item)}</li>" for item in document.warnings)
    sources = "".join(
        f"<li>{_e(item.name)}{(' · ' + _e(item.url)) if item.url else ''} · "
        f"проверено {_e(_dt(item.checked_at))}</li>" for item in document.sources)
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_e(trip.title)}</title><style>{_COMPACT_CSS}</style></head>
<body><div class="wrap">
<header class="top"><p class="kicker">Персональный план поездки · travel nova</p>
<h1>{_e(trip.title)}</h1>
<p class="lede">{_e(trip.subtitle)}</p>
<div class="meta">
<span class="chip">{_e(date_label)}</span>
<span class="chip">проверено {_e(_dt(document.checked_at))}</span>
<span class="chip">проверено {_e(_dt(document.checked_at))}</span>
</div></header>
<section><h2>Бюджет</h2><div class="stat-grid">{"".join(budget_cells)}</div>{budget_note_html}</section>
{_route_section_html(document, transport_cards, legs, share_html)}
{_flight_options_section(document) if (getattr(document, "flight_options", None) or []) else ''}
{('<section><h2>Где остановиться · ' + _nights(nights) + ' · ' + _adults(trip.travelers) + '</h2>' + hotel_cards + '</section>') if hotel_cards else ''}
{'<section><h2>Что посмотреть</h2>' + "".join(event_rows) + '</section>' if event_rows else ''}
{'<section><h2>Рестораны и бары · OpenStreetMap</h2>' + "".join(venue_rows) + '</section>' if venue_rows else ''}
<div class="fine"><b>Важно знать</b><ul>{warnings or '<li>Цены и доступность могут измениться до оформления.</li>'}</ul>
<b>Источники</b><ul>{sources}</ul>
Страница собрана Travel Nova. Переход по ссылкам T-Bank открывает оформление у банка — MCP ничего не бронирует и не оплачивает.
</div>
</div></body></html>"""


def _compact_hotel_page(document: HotelPageDocumentV1) -> str:
    search = document.search
    nights = (search.date_to - search.date_from).days
    children = len(search.children_ages)
    guests = f"{search.adults} взр." + (f" · {children} дет." if children else "")
    date_label = f"{search.date_from.strftime('%d.%m')}–{search.date_to.strftime('%d.%m.%Y')}"
    cards = "".join(
        _compact_hotel_card(
            hotel, selected=hotel.id == document.selected_hotel_id,
            nights=nights, guests=guests)
        for hotel in document.hotels)
    hotels_section = (f'<section><h2>Отели · {_nights(nights)} · {_e(guests)}</h2>{cards}</section>'
                      if cards else '')
    warnings = "".join(f"<li>{_e(item)}</li>" for item in document.warnings)
    sources = "".join(
        f"<li>{_e(item.name)}{(' · ' + _e(item.url)) if item.url else ''} · "
        f"проверено {_e(_dt(item.checked_at))}</li>" for item in document.sources)
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_e(search.title)}</title><style>{_COMPACT_CSS}</style></head>
<body><div class="wrap">
<header class="top"><p class="kicker">Подборка отелей · travel nova</p>
<h1>{_e(search.title)}</h1>
<p class="lede">{_e(search.subtitle)}</p>
<div class="meta">
<span class="chip">{_e(search.destination)}</span>
<span class="chip">{_e(date_label)}</span>
<span class="chip">{_e(guests)}</span>
<span class="chip">проверено {_e(_dt(document.checked_at))}</span>
</div></header>
{hotels_section}
<div class="fine"><b>Важно знать</b><ul>{warnings or '<li>Цены и доступность могут измениться до оформления.</li>'}</ul>
<b>Источники</b><ul>{sources}</ul>
Подборка собрана Travel Nova. Переход по ссылкам открывает оформление у банка — MCP ничего не бронирует и не оплачивает.
</div>
</div></body></html>"""


def render_travel_compact_html(
        document: TripPageDocumentV2 | HotelPageDocumentV1) -> str:
    """Return a compact, self-contained chat-ready page (no disk writes)."""
    if isinstance(document, HotelPageDocumentV1):
        return _compact_hotel_page(document)
    return _compact_trip_page(document)


def _md_tbank_link(url, label: str) -> str:
    cleaned = safe_tbank_url(url)
    if cleaned:
        return f"[{label}]({cleaned})"
    return TBANK_LINK_MISSING


def _card_title(item: dict, *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if value:
            return str(value)
    return "Без названия"


def _card_price(item: dict) -> str:
    for key in ("price", "minPrice", "totalPriceRub", "priceRub"):
        value = item.get(key)
        if value in (None, ""):
            continue
        return f"{value} ₽" if not str(value).endswith("₽") else str(value)
    return "цена не указана"


def format_inventory_reply(
        *, title: str = "", hotels=None, flights=None, trains=None,
        events=None) -> str:
    """Ready Markdown cards with a T-Bank link line after each item."""
    lines: list[str] = []
    if title.strip():
        lines.extend([f"## {title.strip()}", ""])
    sections = (
        ("Отели", hotels or [], ("name", "hotelName"), "Открыть отель в T-Bank",
         ("tbankUrl", "detailsUrl")),
        ("Авиа", flights or [], ("summary", "offerId"), "Открыть рейс в T-Bank",
         ("tbankUrl",)),
        ("Поезда", trains or [], ("name", "trainNumber"), "Открыть поезд в T-Bank",
         ("tbankUrl",)),
        ("События", events or [], ("name", "title"), "Открыть событие в T-Bank",
         ("tbankUrl", "sourceUrl")),
    )
    for heading, items, name_keys, label, url_keys in sections:
        if not items:
            continue
        lines.append(f"### {heading}")
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            name = _card_title(item, *name_keys)
            url = next((item.get(key) for key in url_keys if item.get(key)), None)
            lines.append(f"{index}. **{name}** — {_card_price(item)}")
            lines.append(_md_tbank_link(url, label))
            lines.append("")
    if len(lines) <= 2:
        lines.append("Нет карточек для оформления.")
    return "\n".join(lines).rstrip() + "\n"


def format_inventory_reply_json(
        hotels_json: str = "[]", flights_json: str = "[]",
        trains_json: str = "[]", events_json: str = "[]",
        title: str = "") -> str:
    def parse(raw: str, *list_keys: str):
        text = str(raw or "").strip()
        if not text:
            return []
        data = json.loads(text)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in list_keys:
                value = data.get(key)
                if isinstance(value, list):
                    return value
            inner = data.get("data")
            if isinstance(inner, dict):
                for key in list_keys:
                    value = inner.get(key)
                    if isinstance(value, list):
                        return value
            return [data]
        raise ValueError("expected a JSON array or object of cards")

    return format_inventory_reply(
        title=title,
        hotels=parse(hotels_json, "hotels"),
        flights=parse(flights_json, "offers", "flights"),
        trains=parse(trains_json, "trains"),
        events=parse(events_json, "events"),
    )


def format_document_reply(document) -> str:
    hotels = []
    for hotel in getattr(document, "hotels", []) or []:
        hotels.append({
            "name": hotel.name,
            "price": hotel.total_price_rub,
            "tbankUrl": str(getattr(hotel, "details_url", None)
                            or getattr(hotel, "booking_url", None) or ""),
        })
    flights = []
    trains = []
    for leg in getattr(document, "transport", []) or []:
        row = {
            "summary": f"{leg.origin} → {leg.destination}",
            "price": leg.price_rub,
            "tbankUrl": _leg_booking_url(leg),
        }
        combined_rt = getattr(document, "combined_flight", None)
        if leg.mode == "train":
            trains.append(row)
        elif combined_rt is None:
            flights.append(row)
    events = []
    for event in getattr(document, "events", []) or []:
        events.append({
            "name": event.name,
            "price": event.price_from_rub,
            "sourceUrl": str(event.source_url or ""),
        })
    title = (document.search.title if isinstance(document, HotelPageDocumentV1)
             else document.trip.title)
    reply = format_inventory_reply(
        title=title, hotels=hotels, flights=flights, trains=trains, events=events)
    combined_rt = getattr(document, "combined_flight", None)
    if combined_rt is not None:
        price = _rub(combined_rt.price_rub)
        if combined_rt.checkout_url:
            reply = (reply.rstrip() + "\n\n**Перелёт туда и обратно "
                     "(единый оффер):** " + price + " — "
                     f"[Оформить оба перелёта в T-Bank]({combined_rt.checkout_url})\n"
                     "Цена и наличие за оба рейса в одном оффере T-Bank.\n")
        else:
            reply = (reply.rstrip() + "\n\n**Перелёт туда и обратно "
                     "(единый оффер):** " + price + " · Ссылка T-Bank недоступна\n")
    share = _trip_share_url(document) if isinstance(document, TripPageDocumentV2) else ""
    if share:
        reply = (reply.rstrip() + "\n\n**Весь маршрут:** "
                 f"[Открыть перелёт в T-Bank]({share})\n"
                 "Откроется поиск по выбранным рейсам и датам; бронь и оплата — "
                 "у банка.\n")
    return reply


def _page_title(document) -> str:
    if isinstance(document, HotelPageDocumentV1):
        return document.search.title
    return document.trip.title


def prepare_report_document(
    document: TripPageDocumentV1 | TripPageDocumentV2 | HotelPageDocumentV1,
) -> tuple[TripPageDocumentV1 | TripPageDocumentV2 | HotelPageDocumentV1, list[str]]:
    """Attach visible, actionable warnings for incomplete hotel enrichment.

    External hotel sources may legitimately fail, so report generation remains
    fail-soft. Missing comparison facts must never be silent, though: callers
    receive one warning per affected hotel plus a concrete retry instruction.
    """
    if not isinstance(document, (TripPageDocumentV2, HotelPageDocumentV1)):
        return document, []

    enrichment_warnings: list[str] = []
    for hotel in document.hotels:
        missing: list[str] = []
        if hotel.review_count is None:
            missing.append("число отзывов")
        if not hotel.room:
            missing.append("номер")
        if not hotel.meal:
            missing.append("питание")
        if not hotel.cancellation:
            missing.append("отмена")
        if not hotel.payment:
            missing.append("оплата")
        if not hotel.facilities:
            missing.append("удобства")

        digest = hotel.review_digest
        if digest is None:
            missing.append("обзор отзывов")
        elif digest.sample_size < 2:
            missing.append("сопоставимая выборка отзывов")
        else:
            if not digest.pros:
                missing.append("плюсы по отзывам")
            if not digest.cons:
                missing.append("минусы по отзывам")
            if not digest.suitable_for:
                missing.append("кому подходит")
            if not digest.summary:
                missing.append("резюме отзывов")

        if missing:
            enrichment_warnings.append(
                f"Отель «{hotel.name}» ({hotel.id}): неполные данные — "
                + ", ".join(missing)
                + ". Перепроверь hotel_details, hotel_rates и hotel_reviews."
            )

    if not enrichment_warnings:
        return document, []

    warnings = list(document.warnings)
    for warning in enrichment_warnings:
        if warning not in warnings and len(warnings) < 24:
            warnings.append(warning)
    prepared = document.model_copy(update={"warnings": warnings})
    advice = [
        "До get_trip_report вызови hotel_latest_offers для shortlist, затем "
        "hotel_details, hotel_rates и hotel_reviews для каждого финального отеля; "
        "передай facilities, room, meal, cancellation, payment, reviewCount и "
        "reviewDigest в hotel item."
    ]
    return prepared, advice


def render_page_content(document) -> RenderPageResult:
    """Validate via the document model and return HTML + Markdown, no files."""
    document, advice = prepare_report_document(document)
    if isinstance(document, (TripPageDocumentV2, HotelPageDocumentV1)):
        rendered = render_travel_html(document)
    else:
        rendered = render_html(document)
    payload = document.model_dump_json(by_alias=True, indent=2)
    if "apikey=" in payload.lower() or "apikey=" in rendered.lower():
        raise ValueError("generated artifacts contain an API credential")
    return RenderPageResult(
        schema_version=document.schema_version,
        html=rendered,
        document_json=payload,
        reply_markdown=format_document_reply(document),
        display_hint=PAGE_DISPLAY_HINT,
        title=_page_title(document),
        warnings=document.warnings,
        sources=[source.name for source in document.sources],
        advice=advice,
    )


def load_tolerant_document(raw):
    """Per-part tolerant parse of a page JSON for chat rendering.

    Instead of demanding every global invariant of TripPageDocumentV2 at once
    (the usual cause of «валидация на ровном месте» in chat), validate each
    top-level block independently: a block that fails is skipped and reported
    as advice, everything that parsed is rendered. Returns a lightweight
    document namespace usable by the compact renderers, plus the advice list.
    Raises ValueError only when the page cannot be rendered at all (no trip /
    no search block).
    """
    if not isinstance(raw, dict):
        raise ValueError("document должен быть JSON-объектом поездки или отелей.")
    advice: list[str] = []

    def take(model, key: str, label: str):
        value = raw.get(key)
        if value is None:
            return None
        if isinstance(value, list):
            items = []
            for index, item in enumerate(value):
                if not isinstance(item, dict):
                    continue
                try:
                    items.append(model.model_validate(item))
                except ValidationError as exc:
                    advice.append(f"{label}[{index}]: пропущен (не хватает полей контракта).")
            return items
        try:
            return model.model_validate(value)
        except ValidationError as exc:
            advice.append(f"{label}: пропущен — {exc.errors()[0]['msg'] if exc.errors() else 'невалиден'}")
            return None

    warnings = [str(item) for item in (raw.get("warnings") or [])]
    checked = _parse_checked_at(raw.get("checkedAt"), advice)
    sources = take(SourceReference, "sources", "sources") or []

    if raw.get("schemaVersion") == "hotel-page/v1":
        search = take(HotelSearchSummary, "search", "search")
        if search is None:
            raise ValueError(
                "Для подборки отелей нужен блок search (title, destination, "
                "dateFrom, dateTo, adults). " + " ".join(advice))
        hotels = take(HotelOptionV2, "hotels", "hotels") or []
        hotel_ids = {hotel.id for hotel in hotels}
        selected = str(raw.get("selectedHotelId") or "")
        if selected not in hotel_ids:
            advice.append("selectedHotelId не совпадает с отелями — выбран первый.")
            selected = next(iter(hotel_ids), "")
        warnings += [f"Совет: {item}" for item in advice]
        doc = types.SimpleNamespace(
            search=search, hotels=hotels, selected_hotel_id=selected,
            sources=sources, warnings=warnings, checked_at=checked)
        return doc, advice

    trip = take(TripSummary, "trip", "trip")
    if trip is None:
        raise ValueError(
            "Для поездки нужен блок trip (title, destination, dateFrom, dateTo). "
            + " ".join(advice))
    transport = take(TransportLeg, "transport", "transport") or []
    hotels = take(HotelOptionV2, "hotels", "hotels") or []
    hotel_ids = {hotel.id for hotel in hotels}
    selected = str(raw.get("selectedHotelId") or "")
    if selected not in hotel_ids:
        advice.append("selectedHotelId не совпадает с отелями — выбран первый.")
        selected = next(iter(hotel_ids), "")
    budget = take(BudgetRecommendation, "budget", "budget") or []
    events = take(EventOption, "events", "events") or []
    venues = take(DiningVenue, "venues", "venues") or []
    flight_options = take(FlightOption, "flightOptions", "flightOptions") or []
    combined_flight = take(CombinedFlight, "combinedFlight", "combinedFlight")
    if not hotels:
        advice.append("Нет отелей: собери hotel_search/hotel_rates для шорт-листа "
                      "и передай hotels в документ.")
    if not transport:
        advice.append("Нет транспорта: собери flight_search туда/обратно и передай "
                      "transport (с originCode/carrierCode/flightNumber для ссылки).")
    warnings += [f"Совет: {item}" for item in advice]
    doc = types.SimpleNamespace(
        trip=trip, transport=transport, hotels=hotels,
        selected_hotel_id=selected, budget=budget, events=events,
        venues=venues, map_points=[], plans=[], sources=sources,
        flight_options=flight_options, combined_flight=combined_flight,
        warnings=warnings, checked_at=checked)
    return doc, advice


def _parse_checked_at(value, advice: list[str]) -> datetime:
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            pass
    advice.append("checkedAt отсутствует — подставлено текущее время проверки.")
    return datetime.now().astimezone()


def _atomic_write(path: Path, content: str, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"file already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def default_output_dir() -> Path:
    root = os.environ.get("XDG_DATA_HOME")
    if root:
        return Path(root).expanduser() / "tbank-mcp" / "trip-pages"
    return Path.home() / ".local" / "share" / "tbank-mcp" / "trip-pages"


def default_travel_output_dir() -> Path:
    root = os.environ.get("XDG_DATA_HOME")
    if root:
        return Path(root).expanduser() / "tbank-mcp" / "travel-pages"
    return Path.home() / ".local" / "share" / "tbank-mcp" / "travel-pages"


def render_trip_page_files(document: TripPageDocumentV1, *, output_dir: str = "",
                           basename: str = "", overwrite: bool = False,
                           explicit_html_path: str = "") -> RenderTripPageResult:
    """CLI helper: render in memory, then atomically write HTML/JSON."""
    content = render_page_content(document)
    if explicit_html_path:
        html_path = Path(explicit_html_path).expanduser().resolve()
        if html_path.suffix.lower() != ".html":
            raise ValueError("output path must end with .html")
    else:
        root = Path(output_dir).expanduser().resolve() if output_dir else default_output_dir()
        stem = _slug(basename or f"trip-{document.trip.date_from.isoformat()}")
        html_path = root / f"{stem}.html"
    json_path = html_path.with_suffix(".json")
    if html_path.exists() and not overwrite:
        raise FileExistsError(f"file already exists: {html_path}")
    if json_path.exists() and not overwrite:
        raise FileExistsError(f"file already exists: {json_path}")
    _atomic_write(json_path, content.document_json + "\n", overwrite)
    try:
        _atomic_write(html_path, content.html, overwrite)
    except Exception:
        if not overwrite:
            json_path.unlink(missing_ok=True)
        raise
    return RenderTripPageResult(
        html_path=str(html_path), json_path=str(json_path), title=content.title,
        warnings=content.warnings, sources=content.sources,
    )


def render_travel_page_files(
        document: TripPageDocumentV2 | HotelPageDocumentV1, *, output_dir: str = "",
        basename: str = "", overwrite: bool = False,
        explicit_html_path: str = "") -> RenderTravelPageResult:
    """CLI helper: render in memory, then atomically write HTML/JSON."""
    content = render_page_content(document)
    if isinstance(document, HotelPageDocumentV1):
        date_from = document.search.date_from
        prefix = "hotels"
    else:
        date_from = document.trip.date_from
        prefix = "trip"
    if explicit_html_path:
        html_path = Path(explicit_html_path).expanduser().resolve()
        if html_path.suffix.lower() != ".html":
            raise ValueError("output path must end with .html")
    else:
        root = (Path(output_dir).expanduser().resolve()
                if output_dir else default_travel_output_dir())
        stem = _slug(basename or f"{prefix}-{date_from.isoformat()}")
        html_path = root / f"{stem}.html"
    json_path = html_path.with_suffix(".json")
    if html_path.exists() and not overwrite:
        raise FileExistsError(f"file already exists: {html_path}")
    if json_path.exists() and not overwrite:
        raise FileExistsError(f"file already exists: {json_path}")
    _atomic_write(json_path, content.document_json + "\n", overwrite)
    try:
        _atomic_write(html_path, content.html, overwrite)
    except Exception:
        if not overwrite:
            json_path.unlink(missing_ok=True)
        raise
    return RenderTravelPageResult(
        html_path=str(html_path), json_path=str(json_path), title=content.title,
        warnings=content.warnings, sources=content.sources,
    )


def trip_page_json_schema() -> dict:
    return TripPageDocumentV1.model_json_schema(by_alias=True)


def travel_page_json_schema(kind: Literal["trip", "hotels"]) -> dict:
    model = TripPageDocumentV2 if kind == "trip" else HotelPageDocumentV1
    return model.model_json_schema(by_alias=True)
