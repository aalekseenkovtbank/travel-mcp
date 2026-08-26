"""Mock contracts for Nominatim, Overpass and Open-Meteo."""
import asyncio
from datetime import date
import json
import os
import sys

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src import nearby, server, weather  # noqa: E402
from src.client import TbankApiError  # noqa: E402


class Response:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status

    def raise_for_status(self):
        if self.status >= 400:
            raise requests.HTTPError(f"HTTP {self.status}")

    def json(self):
        return self.payload


class NearbyRequester:
    def __init__(self, geocode=None, elements=None, failure=None):
        self.geocode = geocode if geocode is not None else []
        self.elements = elements if elements is not None else []
        self.failure = failure
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        assert "Cookie" not in kwargs.get("headers", {})
        assert "Authorization" not in kwargs.get("headers", {})
        if self.failure:
            raise self.failure
        return Response(self.geocode)

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        assert "Cookie" not in kwargs.get("headers", {})
        assert "Authorization" not in kwargs.get("headers", {})
        if self.failure:
            raise self.failure
        return Response({"elements": self.elements})


def test_nearby_success_and_exact_contract():
    requester = NearbyRequester(elements=[
        {"type": "node", "id": 1, "lat": 55.751, "lon": 37.611,
         "tags": {"name": "Кафе", "amenity": "cafe", "cuisine": "coffee_shop",
                  "addr:street": "Тверская", "addr:housenumber": "1",
                  "opening_hours": "Mo-Su 09:00-22:00"}},
        {"type": "way", "id": 2, "center": {"lat": 55.752, "lon": 37.612},
         "tags": {"name": "Музей", "tourism": "museum"}},
        {"type": "node", "id": 3, "lat": 70.0, "lon": 37.0,
         "tags": {"name": "Слишком далеко", "amenity": "restaurant"}},
    ])
    result = nearby.search_nearby(
        city="Москва", latitude=55.75, longitude=37.61,
        include_poi=True, place_kinds="culture", requester=requester)
    assert result["source"] == "OpenStreetMap" and result["complete"] is True
    assert [item["name"] for item in result["data"]["places"]] == ["Кафе", "Музей"]
    row = result["data"]["places"][0]
    assert set(row) == {
        "osmId", "type", "name", "latitude", "longitude", "address",
        "cuisine", "category", "openingHours", "distanceMeters", "source",
        "sourceUrl",
    }
    assert row["osmId"] == "node:1" and row["distanceMeters"] < 1800
    assert requester.calls[0][0] == "POST"
    assert "museum" in requester.calls[0][2]["data"]["data"]


def test_nominatim_empty_timeout_and_validation():
    nearby._last_geocode_at = 0
    empty = NearbyRequester(geocode=[])
    try:
        nearby.search_nearby(city="Москва", address="несуществующий адрес", requester=empty)
        raise AssertionError("empty geocoder response must fail")
    except TbankApiError as exc:
        assert exc.result_code == "LOCATION_NOT_FOUND"

    timed_out = NearbyRequester(failure=requests.Timeout())
    try:
        nearby.search_nearby(
            city="Москва", latitude=55.75, longitude=37.61, requester=timed_out)
        raise AssertionError("timeout must fail")
    except TbankApiError as exc:
        assert exc.result_code == "SOURCE_TIMEOUT"

    try:
        nearby.search_nearby(city="Москва", latitude=55.75, requester=empty)
        raise AssertionError("half a coordinate pair must fail")
    except TbankApiError as exc:
        assert exc.result_code == "BAD_COORDINATES"


def forecast_payload(*days):
    return {
        "daily": {
            "time": list(days),
            "temperature_2m_min": [10] * len(days),
            "temperature_2m_max": [20] * len(days),
            "precipitation_probability_max": [30] * len(days),
            "weather_code": [2] * len(days),
        }
    }


def archive_payload(month_day="09-10"):
    dates = [f"{year}-{month_day}" for year in (1991, 2000, 2010, 2020)]
    return {
        "daily": {
            "time": dates,
            "temperature_2m_min": [4, 6, 8, 10],
            "temperature_2m_max": [14, 16, 18, 20],
            "precipitation_sum": [0, 2, 0, 3],
        }
    }


class WeatherRequester:
    def __init__(self, forecast=None, archive=None, forecast_error=None, archive_error=None):
        self.forecast = forecast
        self.archive = archive
        self.forecast_error = forecast_error
        self.archive_error = archive_error
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        assert "headers" not in kwargs or "Authorization" not in kwargs["headers"]
        if url == weather.FORECAST_URL:
            if self.forecast_error:
                raise self.forecast_error
            return Response(self.forecast)
        if self.archive_error:
            raise self.archive_error
        return Response(self.archive)


def test_weather_forecast_climate_and_partial_results():
    current = date(2026, 8, 24)
    mixed = WeatherRequester(
        forecast=forecast_payload("2026-08-24"),
        archive=archive_payload("09-10"))
    result = weather.weather_report(
        city="Москва", latitude=55.75, longitude=37.61,
        date_from="2026-08-24", date_to="2026-09-10",
        requester=mixed, today=current)
    assert {day["kind"] for day in result["data"]["days"]} == {"forecast", "climate"}
    assert result["source"] == "Open-Meteo Forecast + ERA5"
    assert result["complete"] is False  # mocks intentionally omit intermediate days.

    partial = WeatherRequester(
        forecast=forecast_payload("2026-08-24"),
        archive_error=requests.Timeout())
    result = weather.weather_report(
        city="Москва", latitude=55.75, longitude=37.61,
        date_from="2026-08-24", date_to="2026-09-10",
        requester=partial, today=current)
    assert [day["kind"] for day in result["data"]["days"]] == ["forecast"]
    assert result["complete"] is False and result["warnings"]

    fallback = WeatherRequester(
        forecast_error=requests.Timeout(), archive=archive_payload("08-24"))
    result = weather.weather_report(
        city="Москва", latitude=55.75, longitude=37.61,
        date_from="2026-08-24", date_to="2026-08-24",
        requester=fallback, today=current)
    assert result["data"]["days"][0]["kind"] == "climate"
    assert result["warnings"] and result["complete"] is True


def test_weather_validation_and_server_json_envelopes():
    try:
        weather.weather_report(
            city="Москва", latitude=55.75, longitude=37.61,
            date_from="2026-08-01", date_to="2026-09-01")
        raise AssertionError("range over 30 days must fail before HTTP")
    except TbankApiError as exc:
        assert exc.result_code == "BAD_DATES"

    saved_nearby, saved_weather = server._search_nearby, server._weather_report
    server._search_nearby = lambda **kwargs: {
        "data": {"places": [], "anchor": {"name": "Центр"}, "radiusMeters": 1800},
        "warnings": ["partial"], "source": "OpenStreetMap", "complete": False,
    }
    server._weather_report = lambda **kwargs: {
        "data": {"city": "Москва", "days": [{"date": "2026-08-24", "kind": "forecast"}]},
        "warnings": [], "source": "Open-Meteo Forecast", "complete": True,
    }
    try:
        nearby_json = json.loads(asyncio.run(server.nearby_search(
            "Москва", latitude=55.75, longitude=37.61, response_format="json")))
        weather_json = json.loads(asyncio.run(server.weather(
            "Москва", 55.75, 37.61, "2026-08-24", "2026-08-24",
            response_format="json")))
    finally:
        server._search_nearby, server._weather_report = saved_nearby, saved_weather
    for payload in (nearby_json, weather_json):
        assert set(payload) == {
            "ok", "data", "source", "checkedAt", "warnings", "meta"}
        assert payload["ok"] is True and "token" not in json.dumps(payload).lower()


if __name__ == "__main__":
    test_nearby_success_and_exact_contract()
    test_nominatim_empty_timeout_and_validation()
    test_weather_forecast_climate_and_partial_results()
    test_weather_validation_and_server_json_envelopes()
    print("travel public sources: success, empty, timeout, partial and envelopes OK")
