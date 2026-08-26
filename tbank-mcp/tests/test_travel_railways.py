"""Public railway contracts used by the travel-only MCP."""
import asyncio
import json

import requests

from src import railways, server
from src.client import TbankApiError


class Response:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


class Requester:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return self.response


def fulltext_payload():
    return {"payload": {"hitsCount": 1, "sortedByScoreObjects": [{
        "id": "16596", "score": 11716.163,
        "objectSource": {
            "id": "16596", "type": "City", "searchCode": "2000000",
            "addressRu": {
                "station": "МОСКВА", "city": "Москва",
                "region": "Москва Город", "country": "Российская Федерация",
            },
            "popularity": 257.0,
        },
    }]}}


def train_payload(ways=None):
    return {
        "directions": [{"ways": ways if ways is not None else [{"segments": [{
            "origin": {"stationName": "МОСКВА ОКТЯБРЬСКАЯ", "stationCode": "2006004"},
            "destination": {"stationName": "САНКТ-ПЕТЕРБУРГ-ГЛАВН.",
                            "stationCode": "2004001"},
            "departureDateTime": "2026-08-26T08:00:00+03:00",
            "arrivalDateTime": "2026-08-26T12:00:00+03:00",
            "displayTrainNumber": "001А", "name": "Сапсан", "rideMin": 240,
            "carGroups": [{
                "refundablePrice": {"price": 3200.0},
                "places": {"total": 24}, "carTypeName": "СИДЯЧИЙ",
            }],
        }]}]}],
        "trainSearchId": "public-search-id",
    }


def test_station_resolver_returns_search_code_and_no_credentials():
    requester = Requester(Response(fulltext_payload()))
    result = railways.station_suggestions(
        search_text="Москва", limit=10, requester=requester)
    station = result["data"]["stations"][0]
    assert station["searchCode"] == "2000000"
    assert station["type"] == "City"
    url, kwargs = requester.calls[0]
    assert url == railways.STATIONS_URL
    assert kwargs["json"] == {
        "searchTypes": ["railway_stations"], "text": "Москва",
        "maxObjectsCount": 10,
    }
    assert not ({"Authorization", "Cookie"} & set(kwargs["headers"]))


def test_search_uses_exact_public_payload_and_no_credentials():
    requester = Requester(Response(train_payload()))
    result = railways.search_trains(
        origin="2000000", destination="2004000",
        departure_date="2026-08-26", adults=1, children=0,
        requester=requester)
    assert len(result["data"]["ways"]) == 1
    url, kwargs = requester.calls[0]
    assert url == railways.SEARCH_URL
    assert kwargs["json"] == {
        "directions": [{
            "origin": "2000000", "destination": "2004000",
            "departureDate": "2026-08-26",
        }],
        "adultsCount": 1, "childrenCount": 0,
    }
    assert not ({"Authorization", "Cookie"} & set(kwargs["headers"]))


def test_empty_search_is_a_successful_empty_result():
    requester = Requester(Response(train_payload(ways=[])))
    result = railways.search_trains(
        origin="2000000", destination="2004000",
        departure_date="2026-08-26", requester=requester)
    assert result["data"]["ways"] == []
    assert result["complete"] is True


def test_timeout_and_bad_station_code_are_explicit():
    try:
        railways.station_suggestions(
            search_text="Москва", requester=Requester(error=requests.Timeout()))
        raise AssertionError("station timeout must raise TbankApiError")
    except TbankApiError as exc:
        assert exc.result_code == "SOURCE_TIMEOUT"
    try:
        railways.search_trains(
            origin="moskva", destination="2004000",
            departure_date="2026-08-26", requester=Requester())
        raise AssertionError("a slug must not be accepted as a station code")
    except TbankApiError as exc:
        assert exc.result_code == "BAD_STATION_CODE"


def test_mcp_json_envelope_normalizes_prices_and_seats():
    saved = server._search_trains
    server._search_trains = lambda **kwargs: {
        "data": {
            "origin": kwargs["origin"], "destination": kwargs["destination"],
            "date": kwargs["departure_date"], "adults": kwargs["adults"],
            "children": kwargs["children"],
            "ways": train_payload()["directions"][0]["ways"],
        },
        "warnings": [], "source": railways.SOURCE, "complete": True,
    }
    try:
        out = json.loads(asyncio.run(server.train_search(
            "2000000", "2004000", "2026-08-26", response_format="json")))
    finally:
        server._search_trains = saved
    assert out["ok"] is True
    train = out["data"]["trains"][0]
    assert train["trainNumber"] == "001А"
    assert train["minPrice"] == 3200.0
    assert train["availableSeats"] == 24
    assert out["source"] == railways.SOURCE


if __name__ == "__main__":
    test_station_resolver_returns_search_code_and_no_credentials()
    test_search_uses_exact_public_payload_and_no_credentials()
    test_empty_search_is_a_successful_empty_result()
    test_timeout_and_bad_station_code_are_explicit()
    test_mcp_json_envelope_normalizes_prices_and_seats()
    print("travel railways: resolver, search, empty, timeout, security and JSON envelope OK")
