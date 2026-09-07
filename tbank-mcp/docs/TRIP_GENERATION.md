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

Текущий travel-only MCP не публикует events, Afisha, cinema, nearby-place или
marketplace тулы. Не добавляй такие сущности в request и не выдумывай их.

## Request для get_trip_report

Request содержит brief поездки и фактические результаты narrow flows:

```json
{
  "title": "...",
  "destination": "...",
  "dateFrom": "YYYY-MM-DD",
  "dateTo": "YYYY-MM-DD",
  "travelers": 2,
  "layout": "full",
  "flights": [
    {
      "direction": "outbound|return",
      "fromCode": "<код из flight_search>",
      "toCode": "<код из flight_search>",
      "date": "YYYY-MM-DD",
      "carriers": ["<рейсы из flight_search>"]
    }
  ],
  "flightOptions": [
    {
      "label": "<название альтернативы>",
      "comment": "<фактические плюсы, минусы и сдвиг дат>",
      "directions": ["<полная outbound + return пара>"]
    }
  ],
  "hotels": [
    {
      "hotelId": "<id из hotel_search>",
      "roomId": "<необязательно>",
      "preferBreakfast": true
    }
  ],
  "recommendedHotelId": "<необязательно>"
}
```

`get_trip_report` сам повторно проверяет доступные предложения, тарифы и ссылки,
собирает бюджет и возвращает дайджест. Не передавай `bookHash` в request; rate
flow принадлежит hotel skill.

## Output mode

`output_mode` управляет форматом результата одного и того же тула:

- `html` — JSON с готовой HTML-страницей, warnings и advice; Markdown в этом
  режиме не возвращается;
- `markdown` — только Markdown-дайджест для текстового ответа.

`layout="compact|full"` влияет только на HTML. Для HTML-capable host выбирай
`html`; для plain-text/chat ответа выбирай `markdown`.

## Контроль результата

Перед возвратом проверь:

- цены, даты, номера рейсов, hotelId и URL пришли из инструментов;
- альтернативы содержат обе стороны, если это round-trip;
- warnings/нефинальные цены не потеряны;
- checkout описан как hand-off, а не как бронь;
- при отсутствии точной ссылки написано «Ссылка T-Bank недоступна».

Не создавай отдельный HTML-проект, не пиши файлы, не вызывай скрытые низкоуровневые
renderer/schema/validate tools и не утверждай, что поездка забронирована.
