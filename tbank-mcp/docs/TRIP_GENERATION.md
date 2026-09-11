# Travel Nova: составление поездки

Это orchestration-flow для complete trip. Он не ищет каждую сущность вместо
узких skills и не бронирует/оплачивает. Выбирай skill по потребности:

- `tbank-flight-search` — авиа, round-trip, даты, прямые альтернативы и ссылки;
- `tbank-hotel-search` — destination/hotel, shortlist, фильтры, offers, rates и
  ссылки;
- `tbank-travel-search` — ЖД, погода и общие travel-компоненты.

Для составной поездки координатор собирает фактические результаты этих flows в
один request и вызывает единственный публичный тул:

```text
get_trip_report(request, output_mode="html" | "markdown")
```

## Нормализация brief

До поиска зафиксируй destination, даты, ночи, adults/children/infants,
транспорт, явные фильтры отелей, бюджет и важные ограничения. Один и тот же
состав гостей передавай в авиа и отельные тулы. Не угадывай города, IATA-коды,
даты, ids или бюджет.

Если нужны билеты — сначала следуй `tbank-flight-search`. Основной маршрут и
полные альтернативы сохраняй с реальными кодами, датами, номерами рейсов,
offerId/searchId и полученными ссылками.

Если нужны отели — сначала следуй `tbank-hotel-search`. Передай в итоговый
request реальные hotelId и выбранные параметры rate/room, если они есть.

Если нужен досуг, перед сборкой request получи события из Афиши по flow
ниже. Не добавляй события, если их не вернул источник.

## Подбор событий в поездке

1. Сразу вызови `afisha_catalog(city=destination, kind=...,
   date_from=..., date_to=..., response_format="json")` на даты поездки.
   Банковская авторизация для каталога необязательна; не вызывай
   `search_app` для предварительного поиска или проверки доступности.
   Для конкретного названия передай `query` в тот же вызов.
2. Поддерживаются `кино`, `концерт`, `театр`; выбирай категории
   по интересам. У выставок каталога по датам нет: сообщи об ограничении,
   не подменяй каталог `search_app`.
3. Сохрани warnings и `meta.complete`. Если выдача неполна, не выдавай
   просмотренную часть за весь каталог.
4. Для выбранных концертов и спектаклей вызови
   `concert_schedule(event_id=..., kind=..., response_format="json")` и оставь
   только сеансы нужного города и дат. Для кино вызови
   `cinema_schedule(event_id=..., city=destination, date=...)` на выбранный день.
   `cinema_schedule` не требует банковской авторизации. Если расписание всё же
   недоступно из-за ошибки источника, а для концерта или спектакля — также из-за
   отсутствия авторизации, не делай fallback на `search_app`: сохрани кандидата
   в текстовой выдаче, но не включай его в `request.events` без подтверждённого
   `startsAt`.
5. Включи выбранные сеансы в `request.events`: `id`, `name`, `kind`,
   `startsAt`, `venue`, `address`, `priceFromRub`, `sourceUrl`, `genres`,
   `ageRestriction`, `matchReason`. Для `id` используй реальный eventId;
   при нескольких сеансах одного события добавь реальный slotId для
   уникальности. Покупку, бронь и оплату выполняет только пользователь.

## Request для get_trip_report

`request` — документ `trip-page/v2` (для отдельной подборки отелей —
`hotel-page/v1`), соответствующий опубликованной JSON Schema инструмента.
Основные поля поездки: `schemaVersion`, `trip`, `transport`,
`flightOptions`, `hotels`, `selectedHotelId`, `events`, `sources`, `warnings`,
`checkedAt`. Обязательные вложенные поля бери из схемы, а значения — из
результатов поиска.

`get_trip_report` валидирует готовый документ и формирует результат
встроенным renderer. Он не выполняет повторный поиск: перепроверь цены,
тарифы и расписания до вызова. Не передавай `bookHash` в request.

Для каждого финального отеля до вызова обязательны `hotel_latest_offers`,
`hotel_details`, `hotel_rates` и `hotel_reviews`. Передай `reviewCount`,
`facilities`, `room`, `meal`, `cancellation`, `payment` и структурированный
`reviewDigest`. Если источник не вернул часть сведений, сохрани конкретный
warning для этого отеля. Renderer также добавляет такой warning и actionable
`advice`, если enrichment был пропущен, поэтому неполная страница не выглядит
полной молча. В HTML-ответе верхнеуровневое поле `schemaVersion` позволяет
сверить опубликованный контракт с версией клиента.

Ниже — структурные примеры с полным hotel enrichment. Значения
`replace-with-*`, числа, даты, цены и координаты — только JSON-заглушки: перед
вызовом замени их фактическими значениями из инструментов. Не копируй их в
пользовательский отчёт как данные поиска.

### Структурный `trip-page/v2`

Событие в `events` должно быть получено через `afisha_catalog` и подтверждено
расписанием согласно flow выше.

```json
{
  "schemaVersion": "trip-page/v2",
  "trip": {
    "title": "Поездка в replace-with-destination",
    "destination": "replace-with-destination",
    "dateFrom": "2030-01-01",
    "dateTo": "2030-01-03",
    "travelers": 2
  },
  "transport": [],
  "flightOptions": [],
  "hotels": [
    {
      "id": "replace-with-hotel-id",
      "name": "replace-with-hotel-name",
      "address": "replace-with-hotel-address",
      "reviewCount": 10,
      "coordinates": {
        "latitude": 0,
        "longitude": 0
      },
      "nightlyPriceRub": 0,
      "totalPriceRub": 0,
      "room": "replace-with-room-from-hotel-rates",
      "meal": "replace-with-meal-from-hotel-rates",
      "cancellation": "replace-with-cancellation-from-hotel-rates",
      "payment": "replace-with-payment-from-hotel-rates",
      "facilities": ["replace-with-facility-from-hotel-details"],
      "reviewDigest": {
        "sampleSize": 10,
        "sort": "date",
        "sortType": "desc",
        "pros": ["replace-with-repeated-pro-from-loaded-reviews"],
        "cons": ["replace-with-repeated-con-or-insufficient-data"],
        "suitableFor": "replace-with-source-backed-fit",
        "summary": "replace-with-review-sample-summary"
      }
    }
  ],
  "selectedHotelId": "replace-with-hotel-id",
  "events": [
    {
      "id": "replace-with-event-or-slot-id",
      "name": "replace-with-event-name",
      "kind": "concert",
      "startsAt": "2030-01-02T19:00:00+03:00",
      "venue": "replace-with-venue",
      "address": "replace-with-event-address",
      "genres": [],
      "ageRestriction": "",
      "matchReason": "replace-with-source-backed-reason"
    }
  ],
  "sources": [
    {
      "name": "hotel_latest_offers",
      "checkedAt": "2030-01-01T12:00:00+03:00"
    },
    {
      "name": "hotel_details",
      "checkedAt": "2030-01-01T12:00:00+03:00"
    },
    {
      "name": "hotel_rates",
      "checkedAt": "2030-01-01T12:00:00+03:00"
    },
    {
      "name": "hotel_reviews",
      "checkedAt": "2030-01-01T12:00:00+03:00"
    },
    {
      "name": "afisha_catalog",
      "checkedAt": "2030-01-01T12:00:00+03:00"
    }
  ],
  "warnings": [],
  "checkedAt": "2030-01-01T12:00:00+03:00"
}
```

Если транспорт, ссылки, цены, фото или другие блоки получены от инструментов,
добавь их по опубликованной JSON Schema. Пустой `transport` допустим только
когда транспорт не входит в задачу или подтверждённых вариантов нет.

### Структурный `hotel-page/v1`

Используй эту модель только для отдельной подборки отелей без полной поездки.

```json
{
  "schemaVersion": "hotel-page/v1",
  "search": {
    "title": "Отели в replace-with-destination",
    "destination": "replace-with-destination",
    "dateFrom": "2030-01-01",
    "dateTo": "2030-01-03",
    "adults": 2,
    "childrenAges": []
  },
  "hotels": [
    {
      "id": "replace-with-hotel-id",
      "name": "replace-with-hotel-name",
      "address": "replace-with-hotel-address",
      "reviewCount": 10,
      "coordinates": {
        "latitude": 0,
        "longitude": 0
      },
      "nightlyPriceRub": 0,
      "totalPriceRub": 0,
      "room": "replace-with-room-from-hotel-rates",
      "meal": "replace-with-meal-from-hotel-rates",
      "cancellation": "replace-with-cancellation-from-hotel-rates",
      "payment": "replace-with-payment-from-hotel-rates",
      "facilities": ["replace-with-facility-from-hotel-details"],
      "reviewDigest": {
        "sampleSize": 10,
        "sort": "date",
        "sortType": "desc",
        "pros": ["replace-with-repeated-pro-from-loaded-reviews"],
        "cons": ["replace-with-repeated-con-or-insufficient-data"],
        "suitableFor": "replace-with-source-backed-fit",
        "summary": "replace-with-review-sample-summary"
      }
    }
  ],
  "selectedHotelId": "replace-with-hotel-id",
  "sources": [
    {
      "name": "hotel_latest_offers",
      "checkedAt": "2030-01-01T12:00:00+03:00"
    },
    {
      "name": "hotel_details",
      "checkedAt": "2030-01-01T12:00:00+03:00"
    },
    {
      "name": "hotel_rates",
      "checkedAt": "2030-01-01T12:00:00+03:00"
    },
    {
      "name": "hotel_reviews",
      "checkedAt": "2030-01-01T12:00:00+03:00"
    }
  ],
  "warnings": [],
  "checkedAt": "2030-01-01T12:00:00+03:00"
}
```

При подборке короче пяти отелей валидатор добавит warning о неполном shortlist.

## Output mode

`output_mode` управляет форматом результата одного и того же тула:

- `html` — JSON с готовой HTML-страницей, warnings и advice; Markdown в этом
  режиме не возвращается;
- `markdown` — только Markdown-дайджест для текстового ответа.

Для HTML-capable host выбирай `html`; для plain-text/chat ответа
выбирай `markdown`. Параметра `layout` в текущем контракте нет.

## Контроль результата

Перед возвратом проверь:

- цены, даты, номера рейсов, hotelId и URL пришли из инструментов;
- альтернативы содержат обе стороны, если это round-trip;
- warnings/нефинальные цены не потеряны;
- checkout описан как hand-off, а не как бронь;
- при отсутствии точной ссылки написано «Ссылка T-Bank недоступна».

Не создавай отдельный HTML-проект, не пиши файлы, не вызывай скрытые низкоуровневые
renderer/schema/validate tools и не утверждай, что поездка забронирована.
