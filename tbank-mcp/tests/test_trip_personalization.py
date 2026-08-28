"""Privacy-safe trip budget and event affinity aggregation."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.trip_personalization import (build_personalization_profile,
                                      score_event_candidate)


def milliseconds(value: str) -> int:
    return int(datetime.fromisoformat(value).timestamp() * 1000)


class Stub:
    def ensure_fresh(self):
        return None

    def orders(self):
        return [
            {"orderId": "flight-1", "objectType": "avia_ticket", "status": "DONE",
             "amount": 12000, "created": "2026-03-01",
             "fields": {"startDate": "2026-03-10", "endDate": "2026-03-12"}},
            {"orderId": "flight-2", "objectType": "avia_ticket", "status": "PAID",
             "amount": 16000, "created": "2026-05-01",
             "fields": {"startDate": "2026-05-10", "endDate": "2026-05-13"}},
            {"orderId": "flight-cancelled", "objectType": "avia_ticket", "status": "CANCELED",
             "amount": 999999, "created": "2026-06-01"},
            {"orderId": "hotel-1", "objectType": "hotelBooking", "status": "DONE",
             "amount": 18000, "created": "2026-03-01"},
            {"orderId": "hotel-2", "objectType": "hotelBooking", "status": "DONE",
             "amount": 24000, "created": "2026-05-01"},
            {"orderId": "event-1", "objectType": "concert", "status": "DONE",
             "amount": 3000, "created": "2026-06-01"},
            {"orderId": "event-2", "objectType": "concert", "status": "DONE",
             "amount": 5000, "created": "2026-07-01"},
            {"orderId": "event-cancelled", "objectType": "concert", "status": "CANCELED",
             "amount": 500000, "created": "2026-07-02"},
        ]

    def hotel_booking(self, order_id):
        return {
            "hotel-1": {"checkInDate": "2026-03-10", "checkOutDate": "2026-03-12"},
            "hotel-2": {"checkInDate": "2026-05-10", "checkOutDate": "2026-05-13"},
        }[order_id]

    def order_details(self, order_id):
        rows = {
            "event-1": ("2026-06-20T20:00:00+03:00", 3000),
            "event-2": ("2026-07-18T20:00:00+03:00", 5000),
        }
        starts, amount = rows[order_id]
        return {
            "orderInfo": {"reserveDate": starts},
            "eventInfo": {"genres": ["рок", "инди"]},
            "objectInfo": {"objectName": "Тестовый клуб"},
            "cartInfo": {"amount": amount},
        }

    def list_accounts(self):
        # Balance and name are deliberately present in the input and must not
        # survive into the aggregate response.
        return [{"id": "private-account", "name": "Private", "moneyAmount": {"value": 999999},
                 "currency": {"name": "RUB"}}]

    def list_operations(self, account_id, start, end):
        operations = []
        for day in ("2026-08-01", "2026-08-08", "2026-08-15", "2026-08-22"):
            operations.append({
                "id": f"spend-{day}", "type": "Debit",
                "operationTime": {"milliseconds": milliseconds(day + "T14:00:00+03:00")},
                "amount": {"value": 2000, "currency": {"name": "RUB"}},
                "category": {"name": "Рестораны"}, "description": "Кафе",
            })
        operations.append({
            "id": "transfer", "type": "Debit",
            "operationTime": {"milliseconds": milliseconds("2026-08-22T15:00:00+03:00")},
            "amount": {"value": 500000, "currency": {"name": "RUB"}},
            "category": {"name": "Переводы"}, "description": "Перевод между счетами",
        })
        return operations


NOW = datetime(2026, 8, 28, 12, tzinfo=timezone.utc)


def test_history_budget_weekends_and_event_preferences():
    profile = build_personalization_profile(
        Stub(), transport_mode="flight", trip_nights=2, is_weekend=True,
        spending_lookback_days=30, now=NOW)
    assert profile.transport.recommended_rub == 14000
    assert profile.transport.sample_size == 2
    assert profile.hotel_per_night.recommended_rub == 8500
    assert profile.hotel_per_night.sample_size == 2
    assert profile.onsite.recommended_rub == 2000
    assert profile.onsite.sample_size == 4
    prefs = profile.event_preferences
    assert prefs.personalization_basis == "order_history" and prefs.sample_size == 2
    assert prefs.top_genres[:2] == ["рок", "инди"]
    assert prefs.preferred_venues == ["Тестовый клуб"]
    score, reason = score_event_candidate({
        "genres": ["рок"], "kind": "concert", "venue": "Тестовый клуб",
        "startsAt": "2026-09-19T20:00:00+03:00", "priceFromRub": 4000,
    }, prefs)
    assert score > 85 and "жанр" in reason
    serialized = json.dumps(profile.model_dump(mode="json"), ensure_ascii=False)
    assert "private-account" not in serialized and "999999" not in serialized
    assert "spend-2026" not in serialized


def test_explicit_values_win_and_live_offers_are_honest_fallback():
    explicit = build_personalization_profile(
        Stub(), explicit_transport_budget_rub=10000,
        explicit_hotel_budget_per_night_rub=7000,
        explicit_onsite_budget_rub=6000, is_weekend=True,
        spending_lookback_days=30, now=NOW)
    assert explicit.transport.basis == "explicit" and explicit.transport.recommended_rub == 10000
    assert explicit.hotel_per_night.basis == "explicit"
    assert explicit.onsite.basis == "explicit"

    class Empty(Stub):
        def orders(self):
            return []

        def list_operations(self, *args):
            return []

    fallback = build_personalization_profile(
        Empty(), transport_offer_prices_rub=[10000, 12000, 18000],
        hotel_nightly_offer_prices_rub=[5000, 7000, 9000], now=NOW)
    assert fallback.transport.basis == "live_offers" and fallback.transport.recommended_rub == 12000
    assert fallback.hotel_per_night.basis == "live_offers"
    assert fallback.event_preferences.personalization_basis == "no_history"


if __name__ == "__main__":
    test_history_budget_weekends_and_event_preferences()
    test_explicit_values_win_and_live_offers_are_honest_fallback()
    print("trip personalization: budgets, privacy and event scoring OK")
