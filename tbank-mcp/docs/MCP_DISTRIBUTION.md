# Travel Nova MCP: поверхности и дистрибуция

В репозитории остаются две поверхности:

- `src.server` / `tbank-mcp` — полный совместимый сервер с исходной банковской и
  travel-функциональностью;
- `src.travel_mcp.server` / `travel-mcp` — отдельная travel-only поверхность,
  описанная ниже.

## Travel-only allowlist

`travel-mcp` регистрирует ровно 29 read-only инструментов:

```text
compare_flight_prices
compare_train_prices
compare_hotel_prices
compare_flight_hotel_prices
get_trip_report
flight_search
flight_price_calendar
flight_price_forecast
flight_schedule
geodata_by_code
flight_checkout_url
search_iata_code
hotel_autocomplete
hotel_search
hotel_search_filters
hotel_latest_offers
hotel_details
hotel_rates
hotel_checkout_url
hotel_reviews
hotel_filters
train_stations
train_search
train_calendar
weather
trip_personalization_profile
list_instructions
read_instruction
get_travel_prompt
```

Авторитетный источник списка — server-side import и `tools/list`; allowlist и
короткие descriptions поддерживаются в `src/travel_mcp/app.py`. Реализации
отключённых модулей не удаляются, но их импорт не является частью этой
поверхности.

Все активные инструменты read-only. Поисковые методы, сравнение, персонализация
и рендер не бронируют и не оплачивают; `hotel_checkout_url()` и
`flight_checkout_url()` только возвращают hand-off URL, который пользователь
открывает и проверяет самостоятельно.

## Запуск

```bash
python -m src.travel_mcp.server
# или
./bin/travel-mcp
```

По умолчанию используется stdio. Streamable HTTP на loopback:

```bash
./bin/travel-mcp --http --host 127.0.0.1 --port 8765
```

MCP-клиент указывает `http://127.0.0.1:8765/mcp`. Удалённый HTTP с per-user auth
остаётся отдельной задачей. npm launcher может подготовить Python окружение и
запустить тот же `src.travel_mcp.server`.

## Инструкции MCP

При инициализации travel-only сервер возвращает короткое `instructions` и ресурс
`travel-nova://instructions/index`. Через `resources/list`/`resources/read` или
fallback-инструменты `list_instructions()`, `read_instruction(slug)` и
`get_travel_prompt()` доступны только travel-документы.

Критические ограничения также закреплены в схемах, валидаторах, descriptions и
annotations. Клиент сам решает, добавлять ли instructions/resources в контекст.

## Источники и фактические границы

`search_iata_code`, `flight_search`, `flight_price_calendar`,
`flight_price_forecast`, `flight_schedule` и `geodata_by_code` используются для
публичного авиа-поиска. Прогноз принимает `searchId` уже выполненного
`flight_search`; календарь читает кэш и не заменяет живой поиск.

`train_stations` резолвит пользовательский текст в числовой `searchCode`, а
`train_search` использует его для расписаний, цен и мест. `train_calendar` сообщает
доступные даты, но не заменяет резолвер.

Hotel-инструменты работают с публичной выдачей: autocomplete, search,
availability-aware filters, latest offers, details, rates, reviews и общий
каталог фильтров. При `price.isFinalPrice=false` условия не считаются
подтверждёнными. `hotel_checkout_url` принимает `bookHash` из `hotel_rates()` и может сразу вернуть
hand-off URL; бронь и оплату он не создаёт.

`compare_*` выполняют bounded fan-out и возвращают метаданные полноты. `lowest
observed` означает минимум среди фактически полученных вариантов. Сумма
`compare_flight_hotel_prices` включает только два плеча перелёта и отель.

`weather` возвращает прогноз Open-Meteo для ближайших 16 дней либо климатическую
оценку ERA5 для более дальних дат; диапазон ограничен 30 днями.

## Дайджест поездки

`get_trip_report(request, output_mode="html"|"markdown")` принимает brief,
выбранный транспорт, варианты и hotel ids, повторно проверяет предложения и
возвращает готовый дайджест. `html` — JSON с HTML и metadata, `markdown` —
текстовый дайджест. Файлы, бронирование и оплата не создаются.

Ссылка на объект или checkout не означает бронь или оплату. Не публикуй сырые
персональные записи, credentials или токены и не выдумывай значения, которые не
вернул источник.
