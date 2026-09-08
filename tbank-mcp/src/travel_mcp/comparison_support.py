"""Validation and bounded inventory calls used by compare tools."""
from __future__ import annotations

import threading
from datetime import datetime
from decimal import Decimal

from ..client import MobileSession, TbankApiError
from ..observability import redact_text
from ..railways import search_trains as _search_trains
from ..travel_compare import (
    ComparisonFailure, ComparisonMeta, StayWindow, WindowValue,
    normalize_flight_inventory, normalize_hotel_inventory, normalize_train_inventory,
    rub_number,
)
from .response import _checked_at

_COMPARE_FLIGHT_SLOTS = threading.BoundedSemaphore(4)

_COMPARE_HOTEL_SLOTS = threading.BoundedSemaphore(3)

_COMPARE_TRAIN_SLOTS = threading.BoundedSemaphore(3)

def _unique_strings(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(value or "").strip() for value in values))

def _comparison_dates(values: list[str], *, maximum: int) -> tuple[list[str], list[str]]:
    if not isinstance(values, list) or not values:
        raise TbankApiError("BAD_DATES", "Передай хотя бы одну дату YYYY-MM-DD.")
    dates = _unique_strings(values)
    if "" in dates:
        raise TbankApiError("BAD_DATE", "Пустая дата недопустима; нужна YYYY-MM-DD.")
    if len(dates) > maximum:
        raise TbankApiError(
            "TOO_MANY_DATES", f"За один вызов можно сравнить не больше {maximum} дат.")
    for value in dates:
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            raise TbankApiError("BAD_DATE", f"Нужна дата YYYY-MM-DD, пришло {value!r}.")
    warnings = ([] if len(dates) == len(values) else
                ["Повторяющиеся даты выполнены один раз."])
    return dates, warnings

def _comparison_windows(values: list[StayWindow], *, maximum: int) -> tuple[list[StayWindow], list[str]]:
    if not isinstance(values, list) or not values:
        raise TbankApiError("BAD_WINDOWS", "Передай хотя бы одно окно проживания.")
    unique: list[StayWindow] = []
    seen: set[str] = set()
    for value in values:
        window = value if isinstance(value, StayWindow) else StayWindow.model_validate(value)
        if window.key in seen:
            continue
        seen.add(window.key)
        unique.append(window)
    if len(unique) > maximum:
        raise TbankApiError(
            "TOO_MANY_WINDOWS", f"За один вызов можно сравнить не больше {maximum} окон.")
    warnings = ([] if len(unique) == len(values) else
                ["Повторяющиеся окна проживания выполнены один раз."])
    return unique, warnings

def _comparison_limit(limit: int, maximum: int = 50) -> int:
    if not 1 <= int(limit) <= maximum:
        raise TbankApiError("BAD_LIMIT", f"limit должен быть от 1 до {maximum}.")
    return int(limit)

def _flight_passengers(adults: int, children: int, infants: int) -> None:
    if not 1 <= int(adults) <= 9 or not 0 <= int(children) <= 9 or not 0 <= int(infants) <= 9:
        raise TbankApiError("BAD_PASSENGERS", "adults: 1..9; children/infants: 0..9.")
    if int(adults) + int(children) + int(infants) > 9:
        raise TbankApiError("BAD_PASSENGERS", "Всего должно быть не больше 9 пассажиров.")

def _hotel_guests(adults: int, children_ages: list[int] | None) -> list[int]:
    if not 1 <= int(adults) <= 6:
        raise TbankApiError("BAD_GUESTS", "adults должен быть от 1 до 6.")
    ages = list(children_ages or [])
    if len(ages) > 6 or any(isinstance(age, bool) or not isinstance(age, int)
                            or not 0 <= age <= 17 for age in ages):
        raise TbankApiError(
            "BAD_CHILDREN_AGES", "children_ages: не больше 6 целых возрастов от 0 до 17.")
    return ages

def _failure(scope: str, error: BaseException) -> ComparisonFailure:
    code = str(getattr(error, "result_code", type(error).__name__))
    raw = getattr(error, "message", None) or str(error) or type(error).__name__
    return ComparisonFailure(scope=scope, code=code, message=redact_text(str(raw)))

def _window_value(window: StayWindow) -> WindowValue:
    return WindowValue(
        key=window.key,
        checkin_date=window.checkin_date,
        checkout_date=window.checkout_date,
        nights=window.nights,
    )

def _comparison_meta(*, complete: bool, requested: int, succeeded: int,
                     failed: int, incomplete: int, baseline_key: str) -> ComparisonMeta:
    return ComparisonMeta(
        complete=complete,
        requested_searches=requested,
        succeeded_searches=succeeded,
        failed_searches=failed,
        incomplete_searches=incomplete,
        baseline_key=baseline_key,
    )

def _comparison_status(rows: list[dict], complete: bool) -> str:
    if not complete:
        return "partial"
    return "complete" if rows else "empty"

def _comparison_warnings(warnings: list[str], *, complete: bool,
                         shown: int, total: int) -> list[str]:
    out = list(dict.fromkeys(str(item) for item in warnings if item))
    if not complete:
        out.append(
            "Сравнение неполное: lowest observed относится только к полученным результатам.")
    if shown < total:
        out.append(f"Показано {shown} из {total} сравнимых вариантов.")
    return list(dict.fromkeys(out))

def _flight_inventory_call(session: MobileSession, from_code: str, to_code: str,
                           departure_date: str, adults: int, children: int,
                           infants: int, only_bookable: bool) -> dict:
    with _COMPARE_FLIGHT_SLOTS:
        result = session.flight_search(
            from_code, to_code, departure_date,
            adults=adults, children=children, infants=infants,
            only_bookable=only_bookable,
        )
    return {
        "rows": normalize_flight_inventory(result, only_bookable=only_bookable),
        "complete": bool(result.get("complete")),
        "checkedAt": _checked_at(),
        "warnings": ([] if result.get("complete") else
                     [f"{from_code.upper()}→{to_code.upper()} {departure_date}: "
                      "поток прерван по таймауту, получено "
                      f"{len(result.get('offers') or [])} предложений."]),
        "source": "T-Bank Avia",
    }

def _hotel_inventory_call(session: MobileSession, destination_id: int,
                          window: StayWindow, adults: int,
                          children_ages: list[int]) -> dict:
    by_id: dict[str, dict] = {}
    complete = False
    last_data: dict = {}
    with _COMPARE_HOTEL_SLOTS:
        last_data = session.hotel_search(
            int(destination_id), window.checkin_date, window.checkout_date,
            adults=adults, children_ages=children_ages, limit=50,
        )
        for hotel in last_data.get("hotels") or []:
            if isinstance(hotel, dict):
                key = str(hotel.get("hotelId") or "")
                if key:
                    by_id[key] = hotel
        complete = last_data.get("isLoadingCompleted") is True
    return {
        "rows": normalize_hotel_inventory(list(by_id.values())),
        "complete": complete,
        "checkedAt": _checked_at(),
        "warnings": ([] if complete else
                     [f"Отели {window.key}: выдача не закрылась за ожидание поиска."]),
        "source": "T-Bank Hotels",
    }

def _train_inventory_call(origin: str, destination: str, departure_date: str,
                          adults: int, children: int) -> dict:
    with _COMPARE_TRAIN_SLOTS:
        result = _search_trains(
            origin=origin, destination=destination, departure_date=departure_date,
            adults=adults, children=children,
        )
    return {
        "rows": normalize_train_inventory(result["data"].get("ways") or []),
        "complete": bool(result.get("complete", True)),
        "checkedAt": _checked_at(),
        "warnings": list(result.get("warnings") or []),
        "source": str(result.get("source") or "T-Bank Railways"),
    }

def _eligible_flights(rows: list[dict], *, max_stops: int | None,
                      max_duration_minutes: int | None,
                      baggage_required: bool, refundable_required: bool) -> tuple[list[dict], list[str]]:
    if max_stops is not None and int(max_stops) < 0:
        raise TbankApiError("BAD_FILTER", "max_stops должен быть неотрицательным.")
    if max_duration_minutes is not None and int(max_duration_minutes) <= 0:
        raise TbankApiError("BAD_FILTER", "max_duration_minutes должен быть положительным.")
    out, skipped_currency = [], 0
    seen: set[tuple] = set()
    for row in rows:
        if str(row.get("currency") or "RUB").upper() != "RUB":
            skipped_currency += 1
            continue
        if row.get("priceDecimal", Decimal("0")) <= 0:
            continue
        if max_stops is not None and int(row.get("stops") or 0) > int(max_stops):
            continue
        if (max_duration_minutes is not None and
                int(row.get("durationMinutes") or 0) > int(max_duration_minutes)):
            continue
        if baggage_required and not row.get("withBaggage"):
            continue
        if refundable_required and not row.get("refundable"):
            continue
        key = (row.get("offerId") or "", row.get("departureAt") or "",
               row.get("priceDecimal"))
        if key in seen:
            continue
        seen.add(key); out.append(row)
    warnings = ([f"Исключено предложений не в RUB: {skipped_currency}."]
                if skipped_currency else [])
    return out, warnings

def _eligible_hotels(rows: list[dict], *, nights: int,
                     hotel_ids: set[str], min_stars: int, min_rating: float,
                     max_total_price_rub: float | None) -> tuple[list[dict], list[str]]:
    if not 0 <= int(min_stars) <= 5:
        raise TbankApiError("BAD_FILTER", "min_stars должен быть от 0 до 5.")
    if not 0 <= float(min_rating) <= 10:
        raise TbankApiError("BAD_FILTER", "min_rating должен быть от 0 до 10.")
    maximum = (Decimal(str(max_total_price_rub))
               if max_total_price_rub is not None else None)
    if maximum is not None and maximum <= 0:
        raise TbankApiError("BAD_FILTER", "max_total_price_rub должен быть положительным.")
    out, skipped_currency = [], 0
    seen: set[str] = set()
    for original in rows:
        row = dict(original)
        hotel_id = str(row.get("hotelId") or "")
        if not hotel_id or hotel_id in seen:
            continue
        seen.add(hotel_id)
        if str(row.get("currency") or "RUB").upper() != "RUB":
            skipped_currency += 1
            continue
        price = row.get("priceDecimal", Decimal("0"))
        if price <= 0 or (maximum is not None and price > maximum):
            continue
        if hotel_ids and hotel_id not in hotel_ids:
            continue
        if int(row.get("stars") or 0) < int(min_stars):
            continue
        if float(row.get("rating") or 0) < float(min_rating):
            continue
        row["nightlyPriceDecimal"] = price / Decimal(nights)
        row["nightlyPrice"] = rub_number(row["nightlyPriceDecimal"])
        out.append(row)
    warnings = ([f"Исключено отелей не в RUB: {skipped_currency}."]
                if skipped_currency else [])
    return out, warnings
