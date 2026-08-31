"""Versioned contract and dependency-free static renderer for trip pages.

The renderer deliberately accepts a fully materialised document.  It never calls
the bank or a places provider while writing a file, which keeps a generated page
reproducible and makes the JSON sidecar the public contract between an agent and
the presentation layer.
"""
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import (AnyHttpUrl, BaseModel, ConfigDict, Field, StringConstraints,
                      field_validator, model_validator)


NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
HttpsUrl = Annotated[AnyHttpUrl, Field(description="An HTTPS URL")]


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
    travelers: int = Field(default=1, ge=1, le=20)
    subtitle: str = ""

    @model_validator(mode="after")
    def _dates_are_ordered(self):
        if self.date_to < self.date_from:
            raise ValueError("dateTo must not be earlier than dateFrom")
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
    booking_url: HttpsUrl | None = None
    notes: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("booking_url")
    @classmethod
    def _https_booking_url(cls, value):
        if value is not None and value.scheme != "https":
            raise ValueError("bookingUrl must use HTTPS")
        return value

    @model_validator(mode="after")
    def _times_are_ordered(self):
        if self.arrival_at <= self.departure_at:
            raise ValueError("arrivalAt must be later than departureAt")
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

    @field_validator("image_url", "booking_url")
    @classmethod
    def _https_urls(cls, value):
        if value is not None and value.scheme != "https":
            raise ValueError("remote URLs must use HTTPS")
        return value


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
    venue: NonEmpty
    address: NonEmpty
    coordinates: Coordinates
    starts_at: datetime
    ends_at: datetime | None = None
    price_from_rub: float | None = Field(default=None, ge=0)
    image_url: HttpsUrl | None = None
    source_url: HttpsUrl | None = None
    genres: list[str] = Field(default_factory=list, max_length=12)
    age_restriction: str = ""
    personalization_score: float = Field(default=50, ge=0, le=100)
    match_reason: NonEmpty
    personalization_basis: Literal["order_history", "no_history"]

    @field_validator("image_url", "source_url")
    @classmethod
    def _https_urls(cls, value):
        if value is not None and value.scheme != "https":
            raise ValueError("remote URLs must use HTTPS")
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
    transport: list[TransportLeg] = Field(min_length=2, max_length=8)
    transport_booking_url: HttpsUrl | None = None
    hotels: list[HotelOption] = Field(min_length=3, max_length=3)
    selected_hotel_id: NonEmpty
    budget: list[BudgetRecommendation] = Field(min_length=4, max_length=4)
    personalization: PersonalizationSummary
    events: list[EventOption] = Field(default_factory=list, max_length=12)
    venues: list[DiningVenue] = Field(min_length=4, max_length=8)
    map_points: list[MapPoint] = Field(min_length=1, max_length=32)
    plans: list[TripPlan] = Field(min_length=3, max_length=3)
    sources: list[SourceReference] = Field(min_length=1, max_length=24)
    warnings: list[str] = Field(default_factory=list, max_length=24)
    checked_at: datetime

    @field_validator("transport_booking_url")
    @classmethod
    def _https_transport_booking_url(cls, value):
        if value is not None and value.scheme != "https":
            raise ValueError("transportBookingUrl must use HTTPS")
        return value

    @model_validator(mode="after")
    def _cross_references_are_valid(self):
        if {leg.direction for leg in self.transport} != {"outbound", "return"}:
            raise ValueError("transport must include outbound and return legs")
        ids = [item.id for item in self.transport]
        ids += [item.id for item in self.hotels]
        ids += [item.id for item in self.events]
        ids += [item.id for item in self.venues]
        if len(ids) != len(set(ids)):
            raise ValueError("all entity IDs must be unique")
        hotels = {item.id for item in self.hotels}
        if self.selected_hotel_id not in hotels:
            raise ValueError("selectedHotelId must reference a hotel")
        hotel_prices = [item.total_price_rub for item in self.hotels]
        if any(right <= left for left, right in zip(hotel_prices, hotel_prices[1:])):
            raise ValueError("hotels must be ordered by strictly increasing totalPriceRub")
        if sum(item.kind == "restaurant" for item in self.venues) < 2:
            raise ValueError("at least two restaurants are required")
        if sum(item.kind == "bar" for item in self.venues) < 1:
            raise ValueError("at least one bar is required")
        budgets = {item.component: item for item in self.budget}
        expected_budgets = {"transport", "hotel", "onsite", "total"}
        if set(budgets) != expected_budgets or len(budgets) != len(self.budget):
            raise ValueError("budget must contain transport, hotel, onsite and total exactly once")
        component_values = [budgets[name].recommended_rub
                            for name in ("transport", "hotel", "onsite")]
        if all(value is not None for value in component_values):
            expected_total = sum(component_values)
            actual_total = budgets["total"].recommended_rub
            if actual_total is None or abs(actual_total - expected_total) > .01:
                raise ValueError("recommended total budget must equal its three components")

        map_kinds = {"hotel": hotels,
                     "event": {item.id for item in self.events},
                     "restaurant": {item.id for item in self.venues
                                    if item.kind == "restaurant"},
                     "bar": {item.id for item in self.venues if item.kind == "bar"}}
        if len({point.ref_id for point in self.map_points}) != len(self.map_points):
            raise ValueError("mapPoints must not repeat an entity")
        for point in self.map_points:
            if point.ref_id not in map_kinds[point.kind]:
                raise ValueError(f"map point {point.ref_id!r} has the wrong kind")
        expected_map_ids = ({self.selected_hotel_id}
                            | {item.id for item in self.events}
                            | {item.id for item in self.venues})
        actual_map_ids = {point.ref_id for point in self.map_points}
        if actual_map_ids != expected_map_ids:
            raise ValueError("mapPoints must contain the selected hotel, every event and every venue")

        expected_styles = {"balanced", "culture", "food_nightlife"}
        if {plan.style for plan in self.plans} != expected_styles:
            raise ValueError("plans must contain balanced, culture and food_nightlife")
        all_ids = set(ids)
        trip_start = max(leg.arrival_at for leg in self.transport
                         if leg.direction == "outbound")
        trip_end = min(leg.departure_at for leg in self.transport
                       if leg.direction == "return")
        events_by_id = {item.id: item for item in self.events}
        for plan in self.plans:
            for day in plan.days:
                if not self.trip.date_from <= day.date <= self.trip.date_to:
                    raise ValueError("plan day is outside the trip dates")
                for stop in day.stops:
                    if stop.ref_id not in all_ids:
                        raise ValueError(f"unknown plan stop refId {stop.ref_id!r}")
                    if stop.starts_at < trip_start or stop.ends_at > trip_end:
                        raise ValueError("plan stop falls before arrival or after departure")
                    event = events_by_id.get(stop.ref_id)
                    if event and (stop.starts_at < event.starts_at
                                  or (event.ends_at and stop.ends_at > event.ends_at)):
                        raise ValueError("event plan stop must fit the published event time")
        return self


class RenderTripPageResult(ContractModel):
    html_path: str
    json_path: str
    title: str
    warnings: list[str]
    sources: list[str]


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
    leg_urls = {str(leg.booking_url) for leg in document.transport if leg.booking_url}
    return next(iter(leg_urls)) if len(leg_urls) == 1 else None


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
    cards = []
    labels = {"outbound": "Туда", "return": "Обратно"}
    icons = {"flight": "✈", "train": "▰"}
    route_checkout = _transport_checkout_url(document)
    for leg in sorted(document.transport, key=lambda item: item.departure_at):
        notes = "".join(f'<span>{_e(note)}</span>' for note in leg.notes)
        seller = f'<small>Продавец: {_e(leg.seller)}</small>' if leg.seller else ""
        leg_action = "" if route_checkout else _link(
            leg.booking_url,
            "Оформить билет туда" if leg.direction == "outbound" else "Оформить билет обратно",
            "button button-primary",
        )
        cards.append(f"""
        <article class="transport-card" id="entity-{_e(leg.id)}">
          <div class="eyebrow">{_e(labels[leg.direction])} · {_e(leg.mode)}</div>
          <div class="route"><span>{_e(leg.origin)}</span><b>{icons[leg.mode]}</b><span>{_e(leg.destination)}</span></div>
          <div class="times"><strong>{_e(_dt(leg.departure_at))}</strong><span>→</span><strong>{_e(_dt(leg.arrival_at))}</strong></div>
          <p>{_e(leg.carrier)}{(' · ' + _e(leg.service_number)) if leg.service_number else ''}</p>
          {seller}
          {f'<div class="transport-notes">{notes}</div>' if notes else ''}
          <div class="price">{_rub(leg.price_rub)}</div>
          {leg_action}
        </article>""")
    return "".join(cards)


def _render_transport_overview(document: TripPageDocumentV1) -> str:
    checkout = _transport_checkout_url(document)
    total = sum(leg.price_rub for leg in document.transport)
    has_separate_links = any(leg.booking_url for leg in document.transport)
    if checkout:
        action = _checkout_action(
            checkout, "Оформить перелёт", "Checkout перелёта не получен")
    elif has_separate_links:
        action = '<span class="checkout-note">Оформление — в карточках рейсов</span>'
    else:
        action = _checkout_action(
            None, "Оформить перелёт", "Checkout перелёта пока недоступен")
    return f"""
      <aside class="transport-overview">
        <div><span>Выбранный маршрут</span><strong>{len(document.transport)} сегм.</strong></div>
        <div><span>Полная цена</span><strong>{_rub(total)}</strong></div>
        {action}
      </aside>"""


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


def _render_hotels(document: TripPageDocumentV1) -> str:
    cards = []
    tier_labels = ("Выгодный", "Сбалансированный", "Больше комфорта")
    for index, hotel in enumerate(document.hotels):
        selected = hotel.id == document.selected_hotel_id
        facts = [
            ("Номер", hotel.room),
            ("Питание", hotel.meal),
            ("Отмена", hotel.cancellation),
            ("Оплата", hotel.payment),
        ]
        conditions = "".join(
            f'<li><span>{_e(label)}</span><strong>{_e(value)}</strong></li>'
            for label, value in facts if value
        )
        rating = (
            f'Рейтинг {_e(hotel.rating)}'
            f'{(" · " + _e(hotel.review_count) + " отзывов") if hotel.review_count is not None else ""}'
            if hotel.rating is not None else "Рейтинг не указан"
        )
        cards.append(f"""
        <article class="hotel-card {'selected' if selected else ''}" id="entity-{_e(hotel.id)}">
          <div class="card-media">{_image(hotel.image_url, hotel.name)}<span class="card-rank">0{index + 1}</span><span class="hotel-tier">{_e(tier_labels[index])}</span></div>
          <div class="card-body">
            <div class="eyebrow">{'Рекомендуем · ' if selected else ''}{'★' * hotel.stars}</div>
            <h3>{_e(hotel.name)}</h3><p>{_e(hotel.address)}</p>
            <div class="hotel-metrics"><span>{rating}</span><span>{_rub(hotel.nightly_price_rub)} за ночь</span></div>
            {f'<ul class="hotel-conditions">{conditions}</ul>' if conditions else '<p class="muted-note">Условия тарифа нужно уточнить перед оформлением.</p>'}
            {f'<blockquote class="hotel-review">{_e(hotel.review_summary)}</blockquote>' if hotel.review_summary else ''}
            <div class="price">{_rub(hotel.total_price_rub)} <small>за всю поездку</small></div>
            {_checkout_action(hotel.booking_url, 'Оформить отель', 'Checkout отеля пока недоступен')}
          </div>
        </article>""")
    return "".join(cards)


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
          {_checkout_action(item.source_url, 'Открыть в Афише', 'Ссылка Афиши не опубликована')}
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


def render_html(document: TripPageDocumentV1) -> str:
    """Render one self-contained page, except for remote images and OSM tiles."""
    leaflet_css = _asset("leaflet-1.9.4.css.txt")
    leaflet_js = _asset("leaflet-1.9.4.js.txt")
    app_js = _asset("trip-page.js.txt")
    entities = _entity_index(document)
    map_ids = list(dict.fromkeys(
        [hotel.id for hotel in document.hotels]
        + [point.ref_id for point in document.map_points]
    ))
    map_rows = [entities[entity_id] for entity_id in map_ids]
    map_json = json.dumps(map_rows, ensure_ascii=False, separators=(",", ":"))
    map_json = map_json.replace("<", "\\u003c").replace(">", "\\u003e")
    script_hashes = []
    for source in (leaflet_js, app_js):
        digest = base64.b64encode(hashlib.sha256(source.encode()).digest()).decode()
        script_hashes.append(f"'sha256-{digest}'")
    csp = ("default-src 'none'; img-src https: data:; style-src 'unsafe-inline'; "
           f"script-src {' '.join(script_hashes)}; connect-src https:; "
           "base-uri 'none'; form-action 'none'; object-src 'none'")
    warnings = "".join(f"<li>{_e(item)}</li>" for item in document.warnings)
    sources = "".join(
        f'<li>{_link(item.url, item.name, "source-link") if item.url else _e(item.name)}'
        f'<small>{_e(_dt(item.checked_at))}</small></li>' for item in document.sources)
    entity_labels = {key: {"label": value["label"]} for key, value in entities.items()}
    # Transport is valid for a plan reference too, even though it is not mapped.
    entity_labels.update({leg.id: {"label": f"{leg.origin} → {leg.destination}"}
                          for leg in document.transport})
    total_budget = next(item for item in document.budget if item.component == "total")
    outbound = min(
        (leg for leg in document.transport if leg.direction == "outbound"),
        key=lambda leg: leg.departure_at,
    )
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{_e(csp)}">
<title>{_e(document.trip.title)}</title>
<style>{leaflet_css}</style><style>{_asset('trip-page.css.txt')}</style></head>
<body><header class="site-header"><a class="brand" href="#top"><span class="logo-mark">TN</span><strong>travel nova</strong></a><nav class="site-nav" aria-label="Разделы поездки"><a href="#route">Дорога</a><a href="#hotels">Отели</a><a href="#events">Афиша</a><a href="#places">Места</a><a href="#plans">Планы</a></nav><div class="header-meta"><span>{_e(document.trip.destination)}</span><span>{_e(document.trip.date_from.strftime('%d.%m'))}–{_e(document.trip.date_to.strftime('%d.%m.%Y'))}</span></div></header>
<main>
<section class="hero" id="top"><div class="hero-copy"><p class="hero-kicker">Персональный план поездки</p><h1>{_e(document.trip.title)}</h1><p class="hero-lede">{_e(document.trip.subtitle)}</p><div class="hero-meta"><span>{_e(outbound.origin)} → {_e(outbound.destination)}</span><span>{_e(document.trip.date_from.strftime('%d.%m'))} — {_e(document.trip.date_to.strftime('%d.%m.%Y'))}</span><span>{document.trip.travelers} чел.</span><span>Проверено {_e(_dt(document.checked_at))}</span></div></div>
<aside class="trip-profile"><span>Комфортный ориентир</span><strong>{_rub(total_budget.recommended_rub)}</strong><small>{_rub(total_budget.range_min_rub)} — {_rub(total_budget.range_max_rub)}</small><div><b>{document.personalization.travel_sample_size}</b><small>поездок в основе</small></div><div><b>{document.personalization.event_sample_size}</b><small>заказов Афиши</small></div></aside></section>
<section class="budget-section" id="budget"><div class="section-head"><div><span>01</span><h2>Бюджет поездки</h2></div><p>{_e(document.personalization.explanation)}</p></div><div class="budget-grid">{_render_budget(document)}</div></section>
<section class="route-section" id="route"><div class="section-head"><div><span>02</span><h2>Дорога туда и обратно</h2></div><p>Выбранные сегменты собраны в один маршрут. Checkout открывается отдельно и не означает покупку.</p></div>{_render_transport_overview(document)}<div class="transport-grid">{_render_transport(document)}</div></section>
<section class="hotels-section" id="hotels"><div class="section-head"><div><span>03</span><h2>Где остановиться</h2></div><p>Три уровня цены с конкретным номером, условиями тарифа, отзывами и ссылкой на оформление.</p></div><div class="hotels">{_render_hotels(document)}</div></section>
<section class="events-section" id="events"><div class="section-head"><div><span>04</span><h2>Что посмотреть</h2></div><p>События ранжируются по безопасному профилю интересов без раскрытия истории покупок.</p></div><div class="card-grid events">{_render_events(document)}</div></section>
<section class="venues-section" id="places"><div class="section-head"><div><span>05</span><h2>Рестораны и бары</h2></div><p>Заведения, категории и часы работы получены из OpenStreetMap через Travel MCP.</p></div><div class="card-grid venues">{_render_venues(document)}</div></section>
<section class="map-section" id="map"><div class="section-head"><div><span>06</span><h2>Всё на карте</h2></div><p>Все три отеля, мероприятия и заведения. Нажмите маркер, чтобы перейти к карточке.</p></div><div id="trip-map" aria-label="Карта поездки OpenStreetMap"><div class="map-fallback">Карта появится при подключении к интернету.</div></div><div class="map-legend"><span class="hotel">Отели</span><span class="event">События</span><span class="restaurant">Рестораны</span><span class="bar">Бары</span></div></section>
<section class="plans-section" id="plans"><div class="section-head"><div><span>07</span><h2>Три сценария поездки</h2></div><p>Выберите темп: сбалансированный, культурный или с акцентом на еду и вечернюю жизнь.</p></div><div class="plans">{_render_plans(document, entity_labels)}</div></section>
<section class="fine-print"><div><h2>Источники</h2><ul class="sources">{sources}</ul></div><div><h2>Важно знать</h2><ul>{warnings or '<li>Цены и доступность могут измениться до оформления.</li>'}</ul></div></section>
</main><footer><b>travel nova</b><span>Страница не является подтверждением бронирования или оплаты.</span></footer>
<script id="trip-map-data" type="application/json">{map_json}</script>
<script>{leaflet_js}</script><script>{app_js}</script></body></html>"""


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


def render_trip_page_files(document: TripPageDocumentV1, *, output_dir: str = "",
                           basename: str = "", overwrite: bool = False,
                           explicit_html_path: str = "") -> RenderTripPageResult:
    """Validate, render and atomically write the HTML/JSON pair."""
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
    payload = document.model_dump_json(by_alias=True, indent=2)
    rendered = render_html(document)
    if "apikey=" in payload.lower() or "apikey=" in rendered.lower():
        raise ValueError("generated artifacts contain an API credential")
    _atomic_write(json_path, payload + "\n", overwrite)
    try:
        _atomic_write(html_path, rendered, overwrite)
    except Exception:
        # Do not leave a new orphan sidecar when HTML creation failed.  Never remove
        # a pre-existing sidecar from an explicit overwrite operation.
        if not overwrite:
            json_path.unlink(missing_ok=True)
        raise
    return RenderTripPageResult(
        html_path=str(html_path), json_path=str(json_path), title=document.trip.title,
        warnings=document.warnings,
        sources=[source.name for source in document.sources],
    )


def trip_page_json_schema() -> dict:
    return TripPageDocumentV1.model_json_schema(by_alias=True)
