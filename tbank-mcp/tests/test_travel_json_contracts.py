"""Contract checks for the opt-in Travel Nova JSON response format only."""
import asyncio
import inspect
import json
import os
import sys
import tempfile
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_TMP = tempfile.mkdtemp(prefix="tbank-travel-json-")
os.environ["TBANK_TRACE_FILE"] = os.path.join(_TMP, "calls.jsonl")
os.environ["TBANK_ATTEMPTS"] = os.path.join(_TMP, "attempts.jsonl")
os.environ["TBANK_EVENTS"] = os.path.join(_TMP, "events.jsonl")

from src import server  # noqa: E402
from src.client import MobileSession  # noqa: E402


class Stub(MobileSession):
    def __init__(self, **answers):
        self._memo = {}
        for name, value in answers.items():
            setattr(self, name, (lambda result: (lambda *args, **kwargs: result))(value))

    def ensure_fresh(self, *args, **kwargs):
        return None

    def ensure_client_session(self, *args, **kwargs):
        return None


def call(session, function, *args, **kwargs):
    saved = server._require
    server._require = lambda: session
    try:
        out = function(*args, response_format="json", **kwargs)
        if inspect.isawaitable(out):
            out = asyncio.run(out)
        payload = json.loads(out)
    finally:
        server._require = saved
    assert payload["ok"] is True
    assert payload["source"]
    assert payload["checkedAt"].endswith("Z")
    assert isinstance(payload["warnings"], list)
    return payload["data"]


def test_profile_reads_have_stable_json_contracts():
    session = Stub(
        list_accounts=[{
            "id": "account-1", "accountType": "Current", "name": "Black",
            "moneyAmount": {"value": 1000}, "currency": {"name": "RUB"},
            "cards": [{"id": "card-1", "ucid": "ucid-1", "name": "Карта"}],
        }],
        list_operations=[{
            "id": "operation-1", "type": "Debit",
            "operationTime": {"milliseconds": 1784658904000},
            "amount": {"value": 750, "currency": {"name": "RUB"}},
            "description": "Кафе",
        }],
        spending_categories={
            "total_spent": 750, "total_earned": 0, "currency": "RUB",
            "categories": [{"category": "Рестораны", "amount": 750, "share_pct": 100}],
        },
        orders=[{
            "orderId": "order-1", "objectType": "concert", "status": "DONE",
            "amount": 1500, "created": "2026-08-01",
            "fields": {"eventName": "Рок-концерт"},
        }],
        identity_brief={"birthDate": {"value": "1994-05-20"}, "sex": {"value": "M"}},
        order_details={
            "orderInfo": {
                "orderId": "order-1", "status": "DONE", "created": "2026-08-01",
                "reserveDate": "2026-08-15T20:00:00+03:00",
                "fields": {"eventName": "Рок-концерт", "hallName": "Главный зал"},
            },
            "eventInfo": {"eventName": "Рок-концерт", "genres": ["рок", "инди"]},
            "objectInfo": {"objectName": "Клуб", "geo": {"address": "Центр"}},
            "cartInfo": {
                "amount": 3000,
                "cartElement": [{"price": 1500}, {"price": 1500}],
            },
        },
        flight_history=[{
            "searchTime": "2026-07-01", "from": {"city_name": {"ru": "Москва"}, "code": "MOW"},
            "to": {"city_name": {"ru": "Казань"}, "code": "KZN"}, "passengers": {"adults": 1},
        }],
    )

    assert call(session, server.list_accounts)["accounts"][0]["id"] == "account-1"
    assert call(session, server.list_operations, "account-1")["operations"][0]["description"] == "Кафе"
    assert call(session, server.spending_categories, "account-1")["categories"][0]["name"] == "Рестораны"
    assert call(session, server.orders)["orders"][0]["eventName"] == "Рок-концерт"
    assert call(session, server.flight_history)["searches"][0]["to"]["code"] == "KZN"
    audience = call(session, server.audience_profile)
    assert audience == {"ageBand": "25_34", "adultContentAllowed": True}
    event_order = call(session, server.order_details, "order-1")
    assert event_order["genres"] == ["рок", "инди"]
    assert event_order["seatCount"] == 2 and event_order["totalAmountRub"] == 3000
    assert "reservationCode" not in event_order and "sex" not in event_order


def test_hotel_order_details_json_drops_guest_identity():
    session = Stub(
        orders=[{
            "orderId": "hotel-1", "objectType": "hotelBooking", "status": "DONE",
            "amount": 24000, "created": "2026-07-01",
            "fields": {"hotelName": "Отель", "destination": "Казань"},
        }],
        hotel_booking={
            "checkInDate": "2026-07-10", "checkOutDate": "2026-07-13",
            "hotelData": {
                "hotelName": "Отель", "starRating": 4,
                "areaLocation": {"destinationName": "Казань"},
            },
            "rateData": {"rooms": [{
                "mealName": "Завтрак",
                "guests": [{"firstName": "Секрет", "lastName": "Пользователь"}],
            }]},
            "contactData": {"email": "user@example.com", "phone": "+79991234567"},
        },
    )
    detail = call(session, server.travel_order_details, "hotel-1")
    assert detail["hotelStars"] == 4 and detail["mealTypes"] == ["Завтрак"]
    assert detail["guestCount"] == 1 and detail["roomCount"] == 1
    serialized = json.dumps(detail, ensure_ascii=False)
    assert "Секрет" not in serialized and "user@example.com" not in serialized


def test_travel_searches_have_stable_json_contracts():
    session = Stub(
        flight_search={
            "searchId": "search-1", "complete": True, "batches": 1,
            "info": {"carrierNames": {"SU": "Аэрофлот"}},
            "flights": [{
                "duration": 90,
                "flightSegments": [{
                    "departure": {"airport": "LED", "time": "2026-09-18T08:00:00+03:00"},
                    "arrival": {"airport": "SVO", "time": "2026-09-18T09:30:00+03:00"},
                    "carriers": {"marketing": "SU"},
                }],
            }],
            "offers": [{
                "offerId": "offer-1", "vendor": "Tinkoff", "flights": [0],
                "price": {"amount": "5400", "currency": "RUB"},
                "withBaggage": True, "refundable": False,
            }],
        },
        hotel_autocomplete={
            "locations": [{"id": 10, "name": "Москва", "signature": "Россия", "type": {"name": "city"}}],
            "hotels": [],
        },
        hotel_search={
            "filteredHotelsCount": 2, "isLoadingCompleted": True,
            "hotels": [{
                "hotelId": 20, "hotelName": "Отель", "starRating": 4,
                "images": [
                    "http://unsafe.example.test/hotel.jpg",
                    "https://cdn.tbank.ru/hotels/{size}/hotel.jpg",
                ],
                "hotelLocation": {"address": "Тверская улица", "latitude": 55.75, "longitude": 37.61},
                "review": {"rating": 8.8},
                "rateForHotelsFeed": {
                    "shownPrice": {"amount": 12000, "currency": "RUB"},
                    "mealName": "Завтрак", "availableRoomsCount": 2,
                },
            }, {
                "hotelId": 21, "hotelName": "Отель без фото", "starRating": 3,
                "images": ["", "http://unsafe.example.test/only.jpg"],
                "hotelLocation": {"address": "Арбат", "latitude": 55.74, "longitude": 37.59},
                "rateForHotelsFeed": {
                    "shownPrice": {"amount": 9000, "currency": "RUB"},
                },
            }],
        },
        hotel_search_filters={
            "filters": {
                "stars_4": {
                    "filterId": "stars", "filterType": "array",
                    "isSelected": True, "isAvailable": True,
                    "arrayValue": {"value": "4"},
                },
                "price": {
                    "filterId": "price", "filterType": "range",
                    "isSelected": False, "isAvailable": True,
                    "rangeValue": {"min": 5000, "max": 30000, "unit": "RUB"},
                },
            },
            "configurationParams": {
                "allFilters": ["stars", "price"], "quickFilters": ["stars"],
            },
            "filteredHotelsCount": 37,
            "isLoadingCompleted": True,
        },
        hotel_latest_offers={
            "hotels": [{
                "hotelId": 20,
                "offerDetails": {
                    "availableRoomsCount": 2,
                    "freeCancellationUntil": "2026-09-16",
                    "cardRequired": True,
                    "paymentPlace": "now",
                    "mealType": {"id": 1, "code": "BB", "name": "Завтрак"},
                    "price": {"amount": 14900, "currency": "RUB", "isFinalPrice": True},
                    "badgeSlugs": ["best-price"],
                },
            }, {
                "hotelId": 21,
                "offerDetails": {
                    "price": {"amount": 9000, "currency": "RUB", "isFinalPrice": False},
                },
            }],
        },
        hotel_details={
            "hotelId": 20, "hotelName": "Отель", "starRating": 4,
            "location": {"address": "Тверская улица", "lat": 55.75, "lon": 37.61},
            "facilitiesGroups": [{"name": "Общее", "facilities": [{"name": "Wi-Fi"}]}],
        },
        hotel_rates={
            "searchId": "rates-search-1", "isExtraServicesShown": True,
            "availableFilters": [{"filterId": "meal_types", "filterType": "array"}],
            "rates": [{
                "roomId": "room-1", "bookHash": "now-rate-1",
                "shownPrice": {"amount": 15000, "currency": "RUB"},
                "paymentPlace": "now", "mealName": "Завтрак",
                "availableRoomsCount": 2,
            }],
            "otherRates": [],
            "rooms": [{"roomId": "room-1", "roomName": "Делюкс", "roomSize": 28}],
        },
        hotel_reviews={
            "reviews": [{
                "masterHotelId": 20, "feedbackId": 501, "sourceType": "ostrovok",
                "review": {
                    "author": "Анна", "rating": 9.2,
                    "bookingInfo": {
                        "roomName": "Делюкс", "travelerType": "couple",
                        "nights": 3, "createdDate": "2026-08-10T00:00:00Z",
                    },
                    "reviewTextPlus": "Очень чисто",
                    "reviewTextMinus": "Шумно",
                    "photos": [{
                        "url": "https://cdn.tbank.ru/hotels/{size}/review.jpg",
                        "categories": ["room"],
                    }],
                },
                "likesCount": 4, "isLiked": False,
            }],
            "cursor": "reviews-next",
        },
    )

    flight = call(session, server.flight_search, "LED", "MOW", "2026-09-18")["offers"][0]
    assert flight["offerId"] == "offer-1" and flight["price"] == 5400
    assert call(session, server.hotel_autocomplete, "Москва")["suggestions"][0]["kind"] == "location"
    hotels = call(session, server.hotel_search, 10, "2026-09-18", "2026-09-21")["hotels"]
    hotel = hotels[0]
    assert hotel["hotelId"] == "20" and hotel["latitude"] == 55.75
    assert hotel["imageUrl"] == "https://cdn.tbank.ru/hotels/1024x768/hotel.jpg"
    assert "imageUrl" not in hotels[1]
    search_filters = call(
        session, server.hotel_search_filters, 10, "2026-09-18", "2026-09-21",
        adults=2, children_ages=[5],
        filters=[{"filterId": "stars", "values": ["4"]}])
    assert search_filters["filteredHotelsCount"] == 37
    assert search_filters["selectedFilters"] == [
        {"filterId": "stars", "value": ["4"]}]
    assert search_filters["configurationParams"]["quickFilters"] == ["stars"]
    latest = call(
        session, server.hotel_latest_offers, [20, 21],
        "2026-09-18", "2026-09-21", location_id=10, adults=2,
        children_ages=[5])
    assert latest["hotels"][0]["offerDetails"]["price"]["amount"] == 14900
    assert latest["hotels"][1]["offerDetails"]["price"]["isFinalPrice"] is False
    assert call(session, server.hotel_details, "20")["facilities"] == ["Общее: Wi-Fi"]
    rates = call(
        session, server.hotel_rates, "20", "2026-09-18", "2026-09-21",
        filters=[{
            "$objectType": "boolean",
            "filterId": "free_cancellation_allowed",
            "value": True,
        }])
    assert rates["searchId"] == "rates-search-1"
    assert rates["rates"][0]["bookHash"] == "now-rate-1"
    assert rates["rooms"][0]["roomName"] == "Делюкс"
    reviews = call(
        session, server.hotel_reviews, "20", sort="rating", page_size=5)
    assert reviews["cursor"] == "reviews-next"
    assert reviews["reviews"][0]["reviewPlus"] == "Очень чисто"
    assert reviews["reviews"][0]["likeCount"] == 4
    assert reviews["reviews"][0]["photos"][0]["url"].endswith(
        "/1024x768/review.jpg")


def test_travel_search_tools_do_not_block_each_other():
    class ConcurrentSession(Stub):
        def __init__(self):
            super().__init__()
            self.barrier = threading.Barrier(2)
            self.lock = threading.Lock()
            self.active = 0
            self.max_active = 0

        def flight_search(self, *args, **kwargs):
            with self.lock:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
            try:
                self.barrier.wait(timeout=1)
                return {
                    "searchId": "search", "complete": True, "batches": 1,
                    "info": {}, "flights": [], "offers": [],
                }
            finally:
                with self.lock:
                    self.active -= 1

    session = ConcurrentSession()
    saved = server._require
    server._require = lambda: session
    try:
        async def search_both():
            return await asyncio.gather(
                server.flight_search("LED", "MOW", "2026-09-18", response_format="json"),
                server.flight_search("MOW", "LED", "2026-09-21", response_format="json"),
            )

        responses = asyncio.run(search_both())
    finally:
        server._require = saved

    assert session.max_active == 2
    assert all(json.loads(response)["ok"] is True for response in responses)


def test_current_hotel_v2_transport_is_normalized_for_the_json_tool():
    class HotelV2Session(MobileSession):
        def __init__(self):
            self.calls = []

        def _call_read(self, name, **kwargs):
            self.calls.append((name, kwargs))
            if name == "hotel_search_points":
                return {
                    "searchId": "search-v2",
                    "isLoadingCompleted": False,
                    "hotelDetails": [{
                        "hotelId": 20,
                        "offerDetails": {
                            "price": {"amount": 12345, "currency": "RUB"},
                            "isFinalPrice": False,
                        },
                    }],
                    "hotelList": {
                        "filteredHotelsCount": 1,
                        "hotels": [{"hotelId": 20}],
                    },
                }
            if name == "hotel_static_info":
                return {"hotels": [{
                    "hotelId": 20,
                    "hotelName": "Отель v2",
                    "starRating": 4,
                    "location": {
                        "hotelAddress": "Морская улица",
                        "hotelCoordinates": {"latitude": 43.58, "longitude": 39.72},
                    },
                    "review": {"rating": 9.1},
                }]}
            raise AssertionError(f"unexpected endpoint: {name}")

    session = HotelV2Session()
    hotel = call(session, server.hotel_search, 88519,
                 "2026-08-30", "2026-09-02")["hotels"][0]
    assert hotel["name"] == "Отель v2"
    assert hotel["price"] == 12345
    assert hotel["address"] == "Морская улица"
    assert hotel["latitude"] == 43.58
    assert [name for name, _ in session.calls] == [
        "hotel_search_points", "hotel_static_info"]


def test_afisha_reads_have_stable_json_contracts():
    event = {
        "eventId": "event-1", "eventName": "Концерт", "genres": ["рок"],
        "fields": {"ageRestriction": "12+", "rating": {"value": 8.5}},
        "posters": {
            "landscape": {"url": "https://kassa.rambler.ru/landscape.jpg"},
            "main": {"url": "https://kassa.rambler.ru/main.jpg"},
        },
        "slots": [{"startDateTime": "2026-09-19T19:00:00+03:00", "slotId": "slot-1",
                   "prices": {"min": 2000, "max": 5000}}],
    }
    fallback_event = {
        **event,
        "eventId": "event-2",
        "eventName": "Спектакль",
        "posters": {
            "landscape": {"url": "http://unsafe.example.test/landscape.jpg"},
            "main": {"url": "https://kassa.rambler.ru/main-fallback.jpg"},
        },
    }
    session = Stub(
        afisha_catalog=([event, fallback_event], 2, 2),
        afisha_places=([{"id": "venue-1", "name": "Клуб", "address": "Центр", "subways": []}], 1),
        event_showings=[{
            "info": {"objectId": "venue-1", "objectName": "Клуб",
                     "geo": {"address": "Центр", "latitude": 55.75, "longitude": 37.61}},
            "events": [{"slots": [{"startDateTime": "2026-09-19T19:00:00+03:00",
                                     "slotId": "slot-1", "prices": {"min": 2000}}]}],
        }],
    )

    catalog = call(session, server.afisha_catalog, kind="концерт", city="Москва",
                   date_from="2026-09-18", date_to="2026-09-21")["events"]
    catalog_event = catalog[0]
    assert catalog_event["eventId"] == "event-1"
    assert catalog_event["imageUrl"] == "https://kassa.rambler.ru/landscape.jpg"
    assert catalog[1]["imageUrl"] == "https://kassa.rambler.ru/main-fallback.jpg"
    assert server._https_image_url("http://unsafe.example.test/poster.jpg") == ""
    assert call(session, server.afisha_places, kind="концерт", city="Москва")["places"][0]["objectId"] == "venue-1"
    showing = call(session, server.concert_schedule, "event-1", kind="концерт")["showings"][0]
    assert showing["venue"] == "Клуб" and showing["priceMin"] == 2000


if __name__ == "__main__":
    test_profile_reads_have_stable_json_contracts()
    test_hotel_order_details_json_drops_guest_identity()
    test_travel_searches_have_stable_json_contracts()
    test_travel_search_tools_do_not_block_each_other()
    test_current_hotel_v2_transport_is_normalized_for_the_json_tool()
    test_afisha_reads_have_stable_json_contracts()
    print("travel JSON contracts: OK")
