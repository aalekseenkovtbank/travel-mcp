from __future__ import annotations

from copy import deepcopy


def trip_document() -> dict:
    document = {
        "schemaVersion": "trip-page/v1",
        "trip": {
            "title": "Выходные <в Казани>", "destination": "Казань",
            "dateFrom": "2026-09-18", "dateTo": "2026-09-20",
            "travelers": 2, "subtitle": "Архитектура, кухня и вечерний концерт",
        },
        "transport": [
            {
                "id": "flight-out", "direction": "outbound", "mode": "flight",
                "origin": "Москва", "destination": "Казань",
                "departureAt": "2026-09-18T08:00:00+03:00",
                "arrivalAt": "2026-09-18T09:30:00+03:00",
                "carrier": "Пример Авиа", "serviceNumber": "EX 101",
                "priceRub": 6500, "bookingUrl": "https://example.com/flight-out",
            },
            {
                "id": "flight-back", "direction": "return", "mode": "flight",
                "origin": "Казань", "destination": "Москва",
                "departureAt": "2026-09-20T20:00:00+03:00",
                "arrivalAt": "2026-09-20T21:30:00+03:00",
                "carrier": "Пример Авиа", "serviceNumber": "EX 102",
                "priceRub": 7200, "bookingUrl": "https://example.com/flight-back",
            },
        ],
        "hotels": [
            {
                "id": "hotel-value", "name": "Дом на Баумана", "address": "Улица Баумана",
                "coordinates": {"latitude": 55.790, "longitude": 49.113},
                "stars": 3, "rating": 8.7, "reviewCount": 315,
                "imageUrl": "https://example.com/hotel-value.jpg", "nightlyPriceRub": 7000,
                "totalPriceRub": 14000, "room": "Стандарт", "meal": "Без питания",
                "bookingUrl": "https://example.com/hotel-value",
            },
            {
                "id": "hotel-main", "name": "Отель у Кремля", "address": "Центр",
                "coordinates": {"latitude": 55.798, "longitude": 49.106},
                "stars": 4, "rating": 9.1, "reviewCount": 430,
                "imageUrl": "https://example.com/hotel.jpg", "nightlyPriceRub": 9000,
                "totalPriceRub": 18000, "room": "Улучшенный номер", "meal": "Завтрак",
                "bookingUrl": "https://example.com/hotel",
            },
            {
                "id": "hotel-comfort", "name": "Казанский Палас", "address": "Исторический центр",
                "coordinates": {"latitude": 55.781, "longitude": 49.124},
                "stars": 5, "rating": 9.4, "reviewCount": 620,
                "imageUrl": "https://example.com/hotel-comfort.jpg", "nightlyPriceRub": 12000,
                "totalPriceRub": 24000, "room": "Делюкс", "meal": "Завтрак и спа",
                "bookingUrl": "https://example.com/hotel-comfort",
            },
        ],
        "selectedHotelId": "hotel-main",
        "budget": [
            {"component": "transport", "recommendedRub": 14000,
             "rangeMinRub": 12000, "rangeMaxRub": 17000,
             "basis": "comparable_trips", "sampleSize": 4, "confidence": "medium",
             "explanation": "По завершённым поездкам."},
            {"component": "hotel", "recommendedRub": 18000,
             "rangeMinRub": 16000, "rangeMaxRub": 22000,
             "basis": "live_offers", "sampleSize": 3, "confidence": "medium",
             "explanation": "По актуальным предложениям."},
            {"component": "onsite", "recommendedRub": 12000,
             "rangeMinRub": 9000, "rangeMaxRub": 15000,
             "basis": "weekend_spend", "sampleSize": 8, "confidence": "high",
             "explanation": "По полным выходным."},
            {"component": "total", "recommendedRub": 44000,
             "rangeMinRub": 37000, "rangeMaxRub": 54000,
             "basis": "mixed", "sampleSize": 15, "confidence": "medium",
             "explanation": "Сумма дороги, проживания и расходов на месте."},
        ],
        "personalization": {
            "budgetBasis": "История поездок и выходных",
            "eventBasis": "order_history",
            "explanation": "Бюджет рассчитан по агрегатам без публикации операций.",
            "travelSampleSize": 4, "eventSampleSize": 3,
        },
        "events": [{
            "id": "event-1", "name": "Вечерний концерт", "kind": "concert",
            "venue": "Новый зал", "address": "Центр",
            "coordinates": {"latitude": 55.795, "longitude": 49.112},
            "startsAt": "2026-09-19T19:00:00+03:00",
            "endsAt": "2026-09-19T21:00:00+03:00", "priceFromRub": 2500,
            "imageUrl": "https://example.com/event.jpg",
            "sourceUrl": "https://example.com/event", "genres": ["инди"],
            "personalizationScore": 86, "matchReason": "Совпал любимый жанр.",
            "personalizationBasis": "order_history",
        }],
        "venues": [],
        "mapPoints": [
            {"refId": "hotel-main", "kind": "hotel"},
            {"refId": "event-1", "kind": "event"},
        ],
        "plans": [],
        "sources": [
            {"name": "T-Bank Travel", "url": "https://www.tbank.ru/travel/",
             "checkedAt": "2026-08-28T12:00:00+03:00"},
            {"name": "Яндекс Карты", "url": "https://yandex.ru/maps/",
             "checkedAt": "2026-08-28T12:00:00+03:00"},
        ],
        "warnings": ["Цены и доступность могут измениться до оформления."],
        "checkedAt": "2026-08-28T12:00:00+03:00",
    }
    venue_rows = [
        ("restaurant-1", "restaurant", "Ресторан Один", 55.796, 49.108),
        ("restaurant-2", "restaurant", "Ресторан Два", 55.792, 49.115),
        ("bar-1", "bar", "Бар Один", 55.794, 49.104),
        ("bar-2", "bar", "Бар Два", 55.791, 49.118),
    ]
    for index, (venue_id, kind, name, latitude, longitude) in enumerate(venue_rows):
        document["venues"].append({
            "id": venue_id, "kind": kind, "name": name, "address": "Центр",
            "coordinates": {"latitude": latitude, "longitude": longitude},
            "photos": [{
                "url": f"https://example.com/venue-{index}.jpg",
                "attribution": "Яндекс Карты",
                "sourceUrl": f"https://yandex.ru/maps/org/{venue_id}",
            }],
            "rating": 4.7 - index / 10, "ratingScale": 5,
            "reviewCount": 210 + index, "yandexMapsUrl": f"https://yandex.ru/maps/org/{venue_id}",
            "categories": ["Авторская кухня" if kind == "restaurant" else "Коктейльный бар"],
            "openingHours": "ежедневно, 12:00–00:00", "priceLevel": "₽₽",
        })
        document["mapPoints"].append({"refId": venue_id, "kind": kind})

    plan_specs = [
        ("balanced", "Сбалансированный", "Главное без спешки", "restaurant-1"),
        ("culture", "Культура и события", "Больше архитектуры и музыки", "event-1"),
        ("food_nightlife", "Кухня и вечер", "Заведения и ночной город", "bar-1"),
    ]
    for style, title, summary, last_ref in plan_specs:
        document["plans"].append({
            "style": style, "title": title, "summary": summary,
            "days": [{
                "date": "2026-09-19", "title": "Главный день",
                "stops": [
                    {"startsAt": "2026-09-19T10:00:00+03:00",
                     "endsAt": "2026-09-19T11:30:00+03:00", "refId": "hotel-main",
                     "note": "Неспешное начало."},
                    {"startsAt": "2026-09-19T19:00:00+03:00",
                     "endsAt": "2026-09-19T21:00:00+03:00", "refId": last_ref,
                     "note": "Главная точка дня."},
                ],
            }],
        })
    return deepcopy(document)
