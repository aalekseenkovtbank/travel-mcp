"""Contracts and deterministic behavior of the four scenario comparison tools."""
import asyncio
import json
import os
import sys
import tempfile
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_TMP = tempfile.mkdtemp(prefix="tbank-travel-comparisons-")
os.environ["TBANK_TRACE_FILE"] = os.path.join(_TMP, "calls.jsonl")
os.environ["TBANK_ATTEMPTS"] = os.path.join(_TMP, "attempts.jsonl")
os.environ["TBANK_EVENTS"] = os.path.join(_TMP, "events.jsonl")

from src import server  # noqa: E402
from src.client import TbankApiError  # noqa: E402
from src.travel_compare import price_delta  # noqa: E402


def flight_result(price, date, *, offer_id="offer", duration=90, stops=0,
                  complete=True, baggage=True, refundable=False):
    segments = []
    for index in range(stops + 1):
        segments.append({
            "departure": {
                "airport": "LED" if index == 0 else f"X{index}",
                "time": f"{date}T0{8 + index}:00:00+03:00",
            },
            "arrival": {
                "airport": "MOW" if index == stops else f"X{index + 1}",
                "time": f"{date}T{10 + index}:00:00+03:00",
            },
            "carriers": {"marketing": "SU"},
        })
    return {
        "searchId": f"search-{date}", "complete": complete,
        "batches": 1 if complete else 8,
        "info": {"carrierNames": {"SU": "Аэрофлот"}},
        "flights": [{"duration": duration, "flightSegments": segments}],
        "offers": [{
            "offerId": offer_id, "vendor": "Tinkoff", "flights": [0],
            "price": {"amount": str(price), "currency": "RUB"},
            "withBaggage": baggage, "refundable": refundable,
        }],
    }


def hotel_result(hotel_id, name, price, *, complete=True, stars=4, rating=8.5):
    return {
        "filteredHotelsCount": 1,
        "isLoadingCompleted": complete,
        "hotels": [{
            "hotelId": hotel_id, "hotelName": name, "starRating": stars,
            "hotelLocation": {"address": "Центр", "latitude": 55.7, "longitude": 37.6},
            "review": {"rating": rating},
            "rateForHotelsFeed": {
                "shownPrice": {"amount": price, "currency": "RUB"},
                "mealName": "Завтрак", "availableRoomsCount": 2,
            },
        }],
    }


def train_result(price, date, *, number="001", duration=240):
    return {
        "data": {
            "origin": "2000000", "destination": "2004000", "date": date,
            "adults": 1, "children": 0,
            "ways": [{"segments": [{
                "displayTrainNumber": number, "name": "Экспресс",
                "origin": {"stationName": "Москва", "stationCode": "2000000"},
                "destination": {"stationName": "Петербург", "stationCode": "2004000"},
                "departureDateTime": f"{date}T08:00:00+03:00",
                "arrivalDateTime": f"{date}T12:00:00+03:00",
                "rideMin": duration, "rideKm": 650,
                "carGroups": [{
                    "carTypeName": "Сидячий",
                    "refundablePrice": {"price": price},
                    "places": {"total": 12},
                }],
            }]}],
        },
        "warnings": [], "source": "T-Bank Railways", "complete": True,
    }


class StubSession:
    def __init__(self, *, flights=None, hotels=None):
        self.flights = flights or {}
        self.hotels = hotels or {}
        self.hotel_calls = {}

    def ensure_fresh(self):
        return None

    def flight_search(self, from_code, to_code, date, **kwargs):
        value = self.flights[(from_code, to_code, date)]
        if isinstance(value, BaseException):
            raise value
        return value

    def hotel_search(self, destination_id, checkin_date, checkout_date, **kwargs):
        key = (checkin_date, checkout_date)
        call = self.hotel_calls.get(key, 0)
        self.hotel_calls[key] = call + 1
        values = self.hotels[key]
        value = values[min(call, len(values) - 1)] if isinstance(values, list) else values
        if isinstance(value, BaseException):
            raise value
        return value


def with_session(session, function, *args, **kwargs):
    saved = server._require
    server._require = lambda: session
    try:
        return asyncio.run(function(*args, **kwargs))
    finally:
        server._require = saved


def payload(model):
    return model.model_dump(mode="json", by_alias=True)


def test_decimal_delta_is_signed_and_rounded():
    assert price_delta("8000", "10000") == (-2000.0, -20.0)
    assert price_delta("10001", "10000") == (1.0, 0.0)
    assert price_delta("1", "0") == (None, None)


def test_flights_are_fanned_out_ranked_and_partial_failures_survive():
    dates = ["2026-09-18", "2026-09-19", "2026-09-20"]
    session = StubSession(flights={
        ("LED", "MOW", dates[0]): flight_result(10_000, dates[0], offer_id="a"),
        ("LED", "MOW", dates[1]): flight_result(8_000, dates[1], offer_id="b", duration=110),
        ("LED", "MOW", dates[2]): TbankApiError("SOURCE_TIMEOUT", "Источник не ответил"),
    })
    result = payload(with_session(
        session, server.compare_flight_prices, "LED", "MOW", dates, limit=10))
    assert result["ok"] is True
    assert result["meta"] == {
        "complete": False, "requestedSearches": 3, "succeededSearches": 2,
        "failedSearches": 1, "incompleteSearches": 0,
        "baselineKey": dates[0], "currency": "RUB",
    }
    assert [item["offerId"] for item in result["data"]["items"]] == ["b", "a"]
    assert result["data"]["groups"][1]["deltaRubFromBaseline"] == -2000.0
    assert result["data"]["groups"][1]["deltaPctFromBaseline"] == -20.0
    assert result["data"]["groups"][2]["status"] == "failed"
    assert result["data"]["failures"][0]["code"] == "SOURCE_TIMEOUT"
    assert any("lowest observed" in warning for warning in result["warnings"])


def test_flight_fanout_reaches_but_does_not_exceed_four_workers():
    dates = [f"2026-10-{day:02d}" for day in range(1, 5)]

    class Concurrent(StubSession):
        def __init__(self):
            super().__init__()
            self.barrier = threading.Barrier(4)
            self.lock = threading.Lock()
            self.active = 0
            self.maximum = 0

        def flight_search(self, from_code, to_code, date, **kwargs):
            with self.lock:
                self.active += 1
                self.maximum = max(self.maximum, self.active)
            try:
                self.barrier.wait(timeout=2)
                return flight_result(10_000, date, offer_id=date)
            finally:
                with self.lock:
                    self.active -= 1

    session = Concurrent()
    result = with_session(session, server.compare_flight_prices, "LED", "MOW", dates)
    assert result.ok is True
    assert session.maximum == 4


def test_hotel_polling_nightly_prices_and_window_delta():
    windows = [
        {"checkin_date": "2026-09-18", "checkout_date": "2026-09-20"},
        {"checkin_date": "2026-09-19", "checkout_date": "2026-09-21"},
    ]
    session = StubSession(hotels={
        ("2026-09-18", "2026-09-20"): [
            hotel_result("20", "Отель", 20_000, complete=False),
            hotel_result("20", "Отель", 20_000, complete=True),
        ],
        ("2026-09-19", "2026-09-21"): [
            hotel_result("20", "Отель", 16_000, complete=False),
            hotel_result("20", "Отель", 16_000, complete=True),
        ],
    })
    result = payload(with_session(
        session, server.compare_hotel_prices, 10, windows,
        hotel_ids=["20"], sort_by="nightly_price"))
    assert result["ok"] is True and result["meta"]["complete"] is True
    assert session.hotel_calls == {
        ("2026-09-18", "2026-09-20"): 2,
        ("2026-09-19", "2026-09-21"): 2,
    }
    assert result["data"]["items"][0]["nightlyPriceRub"] == 8000.0
    assert result["data"]["groups"][1]["deltaRubFromBaseline"] == -4000.0
    assert result["data"]["groups"][1]["deltaPctFromBaseline"] == -20.0


def test_train_comparison_uses_server_side_price_delta():
    dates = ["2026-09-18", "2026-09-19"]
    answers = {
        dates[0]: train_result(5000, dates[0], number="001"),
        dates[1]: train_result(4500, dates[1], number="002"),
    }
    saved = server._search_trains
    server._search_trains = lambda **kwargs: answers[kwargs["departure_date"]]
    try:
        result = payload(asyncio.run(server.compare_train_prices(
            "2000000", "2004000", dates)))
    finally:
        server._search_trains = saved
    assert result["ok"] is True
    assert result["data"]["items"][0]["trainNumber"] == "002"
    assert result["data"]["groups"][1]["deltaRubFromBaseline"] == -500.0
    assert result["data"]["groups"][1]["deltaPctFromBaseline"] == -10.0


def test_flight_hotel_bundle_names_components_and_budget_delta():
    windows = [
        {"checkin_date": "2026-09-18", "checkout_date": "2026-09-20"},
        {"checkin_date": "2026-09-19", "checkout_date": "2026-09-21"},
    ]
    session = StubSession(
        flights={
            ("LED", "MOW", "2026-09-18"): flight_result(5000, "2026-09-18", offer_id="o1"),
            ("MOW", "LED", "2026-09-20"): flight_result(6000, "2026-09-20", offer_id="r1"),
            ("LED", "MOW", "2026-09-19"): flight_result(4000, "2026-09-19", offer_id="o2"),
            ("MOW", "LED", "2026-09-21"): flight_result(5000, "2026-09-21", offer_id="r2"),
        },
        hotels={
            ("2026-09-18", "2026-09-20"): hotel_result("20", "Первый", 20_000),
            ("2026-09-19", "2026-09-21"): hotel_result("21", "Второй", 18_000),
        },
    )
    result = payload(with_session(
        session, server.compare_flight_hotel_prices,
        "LED", "MOW", 10, windows, budget_rub=28_000))
    assert result["ok"] is True
    assert result["data"]["pricedComponents"] == [
        "outboundFlight", "returnFlight", "hotel"]
    cheapest = result["data"]["items"][0]
    assert cheapest["bundleTotalRub"] == 27_000.0
    assert cheapest["deltaToBudgetRub"] == -1000.0
    assert result["data"]["groups"][1]["deltaRubFromBaseline"] == -4000.0
    assert result["data"]["groups"][1]["deltaPctFromBaseline"] == -12.9
    assert any("только перелёт" in warning for warning in result["warnings"])


def test_tool_contracts_publish_output_schema_and_json_text_fallback():
    names = {
        "compare_flight_prices", "compare_train_prices", "compare_hotel_prices",
        "compare_flight_hotel_prices",
    }
    registered = {tool.name: tool for tool in server.mcp._tool_manager.list_tools()}
    assert all(registered[name].output_schema for name in names)
    assert all(registered[name].annotations.readOnlyHint is True for name in names)

    session = StubSession(flights={
        ("LED", "MOW", "2026-09-18"): flight_result(5000, "2026-09-18"),
    })
    saved = server._require
    server._require = lambda: session
    try:
        converted = asyncio.run(server.mcp._tool_manager.call_tool(
            "compare_flight_prices",
            {"from_code": "LED", "to_code": "MOW", "dates": ["2026-09-18"]},
            convert_result=True,
        ))
    finally:
        server._require = saved
    content, structured = converted
    assert structured["ok"] is True and structured["data"]["items"]
    text = "\n".join(item.text for item in content if item.type == "text")
    assert json.loads(text)["ok"] is True


def test_too_many_dates_fails_before_any_provider_call():
    session = StubSession()
    result = payload(with_session(
        session, server.compare_flight_prices, "LED", "MOW",
        [f"2026-11-{day:02d}" for day in range(1, 9)]))
    assert result["ok"] is False
    assert result["error"]["code"] == "TOO_MANY_DATES"


if __name__ == "__main__":
    test_decimal_delta_is_signed_and_rounded()
    test_flights_are_fanned_out_ranked_and_partial_failures_survive()
    test_flight_fanout_reaches_but_does_not_exceed_four_workers()
    test_hotel_polling_nightly_prices_and_window_delta()
    test_train_comparison_uses_server_side_price_delta()
    test_flight_hotel_bundle_names_components_and_budget_delta()
    test_tool_contracts_publish_output_schema_and_json_text_fallback()
    test_too_many_dates_fails_before_any_provider_call()
    print("travel comparisons: OK")
