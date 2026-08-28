"""Privacy-safe aggregation for trip budgets and event preferences."""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from statistics import median
from typing import Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field

from .client import ms_for_period
from .endpoints import VERTICALS


class ProfileModel(BaseModel):
    model_config = ConfigDict(alias_generator=lambda value: "".join(
        [value.split("_")[0], *[part.title() for part in value.split("_")[1:]]]),
        populate_by_name=True, extra="forbid")


class BudgetEvidence(ProfileModel):
    recommended_rub: float | None = None
    range_min_rub: float | None = None
    range_max_rub: float | None = None
    basis: Literal[
        "explicit", "comparable_trips", "weekend_spend", "live_offers",
        "insufficient_data",
    ]
    sample_size: int = Field(default=0, ge=0)
    confidence: Literal["high", "medium", "low", "none"]
    explanation: str


class EventPreferences(ProfileModel):
    personalization_basis: Literal["order_history", "no_history"]
    sample_size: int = Field(default=0, ge=0)
    top_genres: list[str] = Field(default_factory=list)
    top_kinds: list[str] = Field(default_factory=list)
    preferred_venues: list[str] = Field(default_factory=list)
    preferred_dayparts: list[str] = Field(default_factory=list)
    preferred_weekdays: list[int] = Field(default_factory=list)
    median_ticket_order_rub: float | None = None
    scoring_weights: dict[str, float] = Field(default_factory=lambda: {
        "genres": 0.40, "kind": 0.25, "venue": 0.15,
        "daypartAndWeekday": 0.10, "price": 0.10,
    })


class TripPersonalizationProfile(ProfileModel):
    travel_lookback_months: int
    spending_lookback_days: int
    transport: BudgetEvidence
    hotel_per_night: BudgetEvidence
    onsite: BudgetEvidence
    event_preferences: EventPreferences
    warnings: list[str] = Field(default_factory=list)
    privacy: str = "Only aggregates are returned; account IDs, balances and operations are omitted."


_AFISHA_TYPE_TO_KIND = {
    order_type: kind for kind, vertical in VERTICALS.items()
    for order_type in vertical.get("order_types", ())
}
_AFISHA_TYPES = set(_AFISHA_TYPE_TO_KIND) | set(VERTICALS)
_TRAVEL_TYPES = {"avia_ticket", "trains_ticket", "hotelBooking"}
_SUCCESS = {"DONE", "COMPLETED", "COMPLETE", "PAID", "SUCCESS", "FULFILLED"}
_BAD_STATUS = ("CANCEL", "REFUND", "FAILED", "REJECT", "EXPIRED")
_EXCLUDED_SPEND = re.compile(
    r"перевод|между счет|наличн|снятие|ипотек|аренд|жкх|коммун|налог|штраф|кредит|инвест",
    re.IGNORECASE,
)


def _successful(order: dict) -> bool:
    status = str(order.get("status") or "").upper()
    if any(marker in status for marker in _BAD_STATUS):
        return False
    return status in _SUCCESS


def _parse_datetime(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time(), tzinfo=timezone.utc)
    if isinstance(value, dict):
        value = value.get("milliseconds") or value.get("value")
    try:
        if isinstance(value, (int, float)) or str(value).isdigit():
            number = float(value)
            if number > 10_000_000_000:
                number /= 1000
            return datetime.fromtimestamp(number, tz=timezone.utc)
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError, OSError):
        return None


def _amount(value) -> float | None:
    if isinstance(value, dict):
        value = value.get("value", value.get("amount"))
    try:
        number = float(value)
        return number if math.isfinite(number) and number >= 0 else None
    except (TypeError, ValueError):
        return None


def _percentile(values: Iterable[float], percentile: float) -> float | None:
    rows = sorted(float(value) for value in values if value is not None)
    if not rows:
        return None
    if len(rows) == 1:
        return rows[0]
    point = (len(rows) - 1) * percentile
    lower = math.floor(point)
    upper = math.ceil(point)
    if lower == upper:
        return rows[lower]
    return rows[lower] + (rows[upper] - rows[lower]) * (point - lower)


def _evidence(values: list[float], basis: str, explanation: str) -> BudgetEvidence:
    if not values:
        return BudgetEvidence(
            basis="insufficient_data", sample_size=0, confidence="none",
            explanation=explanation,
        )
    sample = len(values)
    confidence = "high" if sample >= 5 else "medium" if sample >= 2 else "low"
    return BudgetEvidence(
        recommended_rub=round(float(median(values)), 2),
        range_min_rub=round(float(_percentile(values, .25)), 2),
        range_max_rub=round(float(_percentile(values, .75)), 2),
        basis=basis, sample_size=sample, confidence=confidence,
        explanation=explanation,
    )


def _explicit(value: float | None, explanation: str) -> BudgetEvidence | None:
    if value is None:
        return None
    if value < 0:
        raise ValueError("explicit budgets must not be negative")
    return BudgetEvidence(
        recommended_rub=value, range_min_rub=value, range_max_rub=value,
        basis="explicit", sample_size=1, confidence="high", explanation=explanation,
    )


def _order_dates(order: dict) -> tuple[datetime | None, datetime | None]:
    fields = order.get("fields") or {}
    starts = (fields.get("startDate") or fields.get("dateFrom")
              or fields.get("departureDate") or fields.get("beginDate"))
    ends = (fields.get("endDate") or fields.get("dateTo")
            or fields.get("returnDate") or fields.get("finishDate"))
    return _parse_datetime(starts), _parse_datetime(ends)


def _comparable_transport(order: dict, mode: str, trip_nights: int) -> bool:
    expected = "avia_ticket" if mode == "flight" else "trains_ticket"
    if order.get("objectType") != expected or not _successful(order):
        return False
    starts, ends = _order_dates(order)
    if starts and ends:
        duration = max(0, (ends.date() - starts.date()).days)
        return abs(duration - trip_nights) <= 1
    # The mobile order feed often has no return date for transport. It remains
    # useful evidence for the whole-order amount, but confidence will be bounded by
    # sample size and the explanation never claims per-passenger normalisation.
    return True


def _hotel_nightly_values(session, orders: list[dict], trip_nights: int,
                          warnings: list[str]) -> list[float]:
    values = []
    for order in orders:
        if order.get("objectType") != "hotelBooking" or not _successful(order):
            continue
        amount = _amount(order.get("amount"))
        if not amount:
            continue
        try:
            booking = session.hotel_booking(str(order.get("orderId") or "")) or {}
        except Exception:
            warnings.append("Some historical hotel bookings could not be detailed.")
            continue
        checkin = _parse_datetime(booking.get("checkInDate"))
        checkout = _parse_datetime(booking.get("checkOutDate"))
        if not checkin or not checkout:
            continue
        nights = (checkout.date() - checkin.date()).days
        if nights <= 0 or abs(nights - trip_nights) > 1:
            continue
        values.append(amount / nights)
    return values


def _operation_day(operation: dict) -> date | None:
    when = operation.get("operationTime") or operation.get("debitingTime")
    parsed = _parse_datetime(when)
    return parsed.date() if parsed else None


def _is_discretionary_debit(operation: dict) -> bool:
    if str(operation.get("type") or "").lower() not in {"debit", "debiting", "expense"}:
        return False
    amount = operation.get("amount") or {}
    currency = amount.get("currency") or {}
    currency_name = currency.get("name") if isinstance(currency, dict) else currency
    if currency_name and str(currency_name).upper() != "RUB":
        return False
    category = operation.get("category") or {}
    category_name = category.get("name") if isinstance(category, dict) else category
    haystack = f"{category_name or ''} {operation.get('description') or ''}"
    return not _EXCLUDED_SPEND.search(haystack)


def _weekend_totals(operations: list[dict], today: date, days: int) -> list[float]:
    start = today - timedelta(days=days)
    # Last fully completed Sunday. If today is Sunday, today's weekend is not full.
    last_sunday = today - timedelta(days=(today.weekday() + 1) % 7 or 7)
    first_saturday = start + timedelta(days=(5 - start.weekday()) % 7)
    weekends: dict[date, float] = {}
    cursor = first_saturday
    while cursor + timedelta(days=1) <= last_sunday:
        weekends[cursor] = 0.0
        cursor += timedelta(days=7)
    for operation in operations:
        day = _operation_day(operation)
        if day is None or day.weekday() not in {5, 6} or not _is_discretionary_debit(operation):
            continue
        saturday = day if day.weekday() == 5 else day - timedelta(days=1)
        if saturday not in weekends:
            continue
        amount = _amount(operation.get("amount"))
        if amount is not None:
            weekends[saturday] += amount
    return list(weekends.values())


def _daypart(value: datetime | None) -> str:
    if value is None:
        return "unknown"
    hour = value.hour
    if hour < 12:
        return "morning"
    if hour < 17:
        return "afternoon"
    if hour < 22:
        return "evening"
    return "night"


def _event_preferences(session, orders: list[dict], since: datetime,
                       warnings: list[str]) -> EventPreferences:
    genre_counts, kind_counts = Counter(), Counter()
    venue_counts, daypart_counts, weekday_counts = Counter(), Counter(), Counter()
    prices: list[float] = []
    samples = 0
    for order in orders:
        created = _parse_datetime(order.get("created"))
        if (order.get("objectType") not in _AFISHA_TYPES or not _successful(order)
                or (created and created < since)):
            continue
        try:
            detail = session.order_details(str(order.get("orderId") or "")) or {}
        except Exception:
            warnings.append("Some event orders could not be detailed.")
            continue
        info = detail.get("orderInfo") or {}
        event = detail.get("eventInfo") or {}
        place = detail.get("objectInfo") or {}
        cart = detail.get("cartInfo") or {}
        samples += 1
        raw_kind = str(order.get("objectType") or "other")
        kind_counts[_AFISHA_TYPE_TO_KIND.get(raw_kind, raw_kind)] += 1
        genre_counts.update(str(item).strip().lower() for item in (event.get("genres") or []) if item)
        venue = str(place.get("objectName") or "").strip()
        if venue:
            venue_counts[venue] += 1
        starts = _parse_datetime(info.get("reserveDate"))
        daypart_counts[_daypart(starts)] += 1
        if starts:
            weekday_counts[starts.weekday()] += 1
        amount = _amount(cart.get("amount") or info.get("amount") or order.get("amount"))
        if amount is not None:
            prices.append(amount)
    if not samples:
        return EventPreferences(personalization_basis="no_history")
    return EventPreferences(
        personalization_basis="order_history", sample_size=samples,
        top_genres=[name for name, _ in genre_counts.most_common(6)],
        top_kinds=[name for name, _ in kind_counts.most_common(4)],
        # A single venue would disclose an individual order, so venue affinity is
        # exposed only after the preference appears at least twice.
        preferred_venues=[name for name, count in venue_counts.most_common(4) if count >= 2],
        preferred_dayparts=[name for name, _ in daypart_counts.most_common(3) if name != "unknown"],
        preferred_weekdays=[name for name, _ in weekday_counts.most_common(4)],
        median_ticket_order_rub=round(float(median(prices)), 2) if prices else None,
    )


def score_event_candidate(candidate: dict, preferences: EventPreferences) -> tuple[float, str]:
    """Apply the public 40/25/15/10/10 weighting to one candidate."""
    if preferences.personalization_basis == "no_history":
        return 50.0, "Нет истории заказов: нейтральная рекомендация."
    genres = {str(item).strip().lower() for item in candidate.get("genres", [])}
    preferred_genres = set(preferences.top_genres)
    genre_score = len(genres & preferred_genres) / max(1, len(genres))
    kind_score = 1.0 if str(candidate.get("kind") or "") in preferences.top_kinds else 0.0
    venue_score = 1.0 if str(candidate.get("venue") or "") in preferences.preferred_venues else 0.0
    starts = _parse_datetime(candidate.get("startsAt") or candidate.get("starts_at"))
    temporal = 0.0
    if starts:
        temporal = (float(_daypart(starts) in preferences.preferred_dayparts)
                    + float(starts.weekday() in preferences.preferred_weekdays)) / 2
    candidate_price = _amount(candidate.get("priceFromRub") or candidate.get("price_from_rub"))
    price_score = 0.0
    if candidate_price is not None and preferences.median_ticket_order_rub:
        price_score = max(0.0, 1 - abs(candidate_price - preferences.median_ticket_order_rub)
                          / max(preferences.median_ticket_order_rub, 1))
    score = 100 * (genre_score * .40 + kind_score * .25 + venue_score * .15
                   + temporal * .10 + price_score * .10)
    matched = []
    if genre_score:
        matched.append("жанр")
    if kind_score:
        matched.append("тип события")
    if venue_score:
        matched.append("площадка")
    if temporal:
        matched.append("привычное время")
    if price_score >= .5:
        matched.append("цена")
    reason = "Совпало: " + ", ".join(matched) if matched else "Новых совпадений с историей мало."
    return round(score, 1), reason


def build_personalization_profile(
    session, *, transport_mode: Literal["flight", "train"] = "flight",
    trip_nights: int = 2, is_weekend: bool = False,
    travel_lookback_months: int = 24, spending_lookback_days: int = 90,
    transport_offer_prices_rub: list[float] | None = None,
    hotel_nightly_offer_prices_rub: list[float] | None = None,
    explicit_transport_budget_rub: float | None = None,
    explicit_hotel_budget_per_night_rub: float | None = None,
    explicit_onsite_budget_rub: float | None = None,
    now: datetime | None = None,
) -> TripPersonalizationProfile:
    if trip_nights < 1 or trip_nights > 60:
        raise ValueError("trip_nights must be between 1 and 60")
    if not 30 <= spending_lookback_days <= 180:
        raise ValueError("spending_lookback_days must be between 30 and 180")
    if not 1 <= travel_lookback_months <= 60:
        raise ValueError("travel_lookback_months must be between 1 and 60")
    current = now or datetime.now(timezone.utc)
    since = current - timedelta(days=travel_lookback_months * 30)
    warnings: list[str] = []

    session.ensure_fresh()
    orders = list(session.orders() or [])
    recent = [order for order in orders
              if order.get("objectType") in (_TRAVEL_TYPES | _AFISHA_TYPES)
              and _parse_datetime(order.get("created")) is not None
              and _parse_datetime(order.get("created")) >= since]
    transport_values = [_amount(order.get("amount")) for order in recent
                        if _comparable_transport(order, transport_mode, trip_nights)]
    transport_values = [value for value in transport_values if value is not None]
    hotel_values = _hotel_nightly_values(session, recent, trip_nights, warnings)

    explicit_transport = _explicit(
        explicit_transport_budget_rub, "Использован бюджет на дорогу, заданный пользователем.")
    explicit_hotel = _explicit(
        explicit_hotel_budget_per_night_rub,
        "Использован бюджет за ночь, заданный пользователем.")
    transport = explicit_transport or (
        _evidence(transport_values, "comparable_trips",
                  "Медиана стоимости завершённых сопоставимых заказов транспорта; сумма относится ко всему заказу.")
        if len(transport_values) >= 2 else
        _evidence(list(transport_offer_prices_rub or []), "live_offers",
                  "Истории недостаточно: диапазон рассчитан по актуальным найденным предложениям."))
    hotel = explicit_hotel or (
        _evidence(hotel_values, "comparable_trips",
                  "Медианная стоимость одной ночи в завершённых поездках сходной длительности.")
        if len(hotel_values) >= 2 else
        _evidence(list(hotel_nightly_offer_prices_rub or []), "live_offers",
                  "Истории отелей недостаточно: диапазон рассчитан по актуальным ценам за ночь."))

    weekend_values: list[float] = []
    if is_weekend:
        operations: list[dict] = []
        try:
            start_ms, end_ms = ms_for_period(spending_lookback_days)
            for account in session.list_accounts() or []:
                currency = account.get("currency") or {}
                name = currency.get("name") if isinstance(currency, dict) else currency
                if name and str(name).upper() != "RUB":
                    continue
                account_id = str(account.get("id") or "")
                if not account_id:
                    continue
                operations.extend(session.list_operations(account_id, start_ms, end_ms) or [])
        except Exception:
            warnings.append("Weekend spending could not be fully analysed.")
        weekend_values = _weekend_totals(operations, current.date(), spending_lookback_days)
    explicit_onsite = _explicit(
        explicit_onsite_budget_rub, "Использован бюджет на месте, заданный пользователем.")
    onsite = explicit_onsite or (
        _evidence(weekend_values, "weekend_spend",
                  "Медианные дискреционные траты за полные субботу и воскресенье; переводы и обязательные платежи исключены.")
        if is_weekend else
        BudgetEvidence(
            basis="insufficient_data", sample_size=0, confidence="none",
            explanation="Для поездки не на выходные отдельный бюджет на месте не выводился из банковских операций.",
        ))
    preferences = _event_preferences(session, recent, since, warnings)
    return TripPersonalizationProfile(
        travel_lookback_months=travel_lookback_months,
        spending_lookback_days=spending_lookback_days,
        transport=transport, hotel_per_night=hotel, onsite=onsite,
        event_preferences=preferences,
        warnings=list(dict.fromkeys(warnings)),
    )
