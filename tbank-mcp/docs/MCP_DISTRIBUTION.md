# Travel Nova MCP: поверхности и дистрибуция

В репозитории остаются две поверхности:

- `src.server` / `tbank-mcp` — полный совместимый сервер с исходной банковской и
  travel-функциональностью;
- `src.travel_mcp.server` / `travel-mcp` — отдельная travel-only поверхность,
  описанная ниже.

## Актуальная HTTP-поверхность

Текущий HTTP entrypoint `src.travel_mcp.server` по умолчанию serves travel-only
поверхность `travel-nova` (24 read-only инструмента, см. allowlist ниже).
Переменная окружения `TRAVEL_SURFACE=full` (синонимы: `tbank`, `unified`)
возвращает единый `src.server` с банковской вертикалью для обратной
совместимости.

Travel-поверхность содержит `get_trip_report` (включая краткую форму
`brief`), `restaurant_search`, полный read-only events-набор
(`afisha_catalog`, `afisha_places`, `place_info`, `place_schedule`,
`cinema_schedule`, `concert_schedule`) и углублённые transport/hotel-поиск.
Bank-инструменты (`search_app`, платежи, grocery, OTP и остальные), а также
bank-session-зависимые `train_calendar` и `trip_personalization_profile`, на
travel-поверхности отсутствуют: без `login()` они не могли бы завершиться
успешно. Низкоуровневые compatibility helpers `render_trip_page`,
`render_travel_page` и `format_trip_reply` не регистрируются как MCP tools:
единственная публичная точка сборки страницы — `get_trip_report`.
Сценарий событий начинается с прямого `afisha_catalog` и описан в
[TRIP_GENERATION.md](TRIP_GENERATION.md#подбор-событий-в-поездке).

## Travel-only allowlist

Поверхность `travel-nova` регистрирует ровно 24 read-only инструмента
(тела берутся из `src.server`; авторитетный источник списка — server-side
регистрация и `tools/list`, allowlist и короткие descriptions поддерживаются в
`src/travel_mcp/app.py`):

```text
get_trip_report
flight_search
flight_price_calendar
flight_schedule
geodata_by_code
search_iata_code
hotel_autocomplete
hotel_search
hotel_details
hotel_rates
hotel_reviews
train_stations
train_search
weather
afisha_catalog
afisha_places
place_info
place_schedule
cinema_schedule
concert_schedule
restaurant_search
list_instructions
read_instruction
get_travel_prompt
```

Консолидация 2026-09 убрала с travel-поверхности 9 церемониальных
инструментов; их возможности живут внутри глубоких тулов:
`hotel_search_filters`/`hotel_filters` → фильтры `hotel_search` и
`availableFilters`; `hotel_latest_offers` → enriched-карточки `hotel_search`
и brief-режим; `hotel_checkout_url` → `checkoutUrl` в каждой tariff-строке
`hotel_rates` и в `confirmedRate`; `flight_price_forecast` → автоматическое
поле `priceForecast` у `flight_search`; `compare_flight_prices` →
`flight_search(dates=[...])`; `compare_train_prices`, `compare_hotel_prices` и
`compare_flight_hotel_prices` → глубокие тулы плюс `get_trip_report(brief)`.
Реализации отключённых модулей не удаляются (остаются на единой поверхности
`TRAVEL_SURFACE=full`), но их импорт не является частью этой поверхности.

Все активные инструменты read-only. Поисковые методы, сравнение,
персонализация и рендер не бронируют и не оплачивают: hand-off-ссылки
(`bookingUrl`, `checkoutUrl`) пользователь открывает и проверяет
самостоятельно. Авиа-ссылки — share-ссылки, а не checkout: `flight_search()`
строит `bookingUrl` каждого бронируемого оффера через публичный
T-Bank Avia `/flight/search/share/createOneLink` (обычно короткий `l.tbank.ru`, при
недоступности — локально собранный `avia_share_url(...)`). Такая ссылка
открывает страницу поиска с уже выбранным рейсом и актуальной доступностью —
она не устаревает вместе с поисковой сессией, как
`/flights/checkout/?offerId=…`. Renderer страницы строит `avia_share_url(...)`
и для подтверждённого маршрута.

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
`flight_schedule` и `geodata_by_code` используются для публичного авиа-поиска.
`search_iata_code` построен на собственном словаре аэропортов банка
(5k+ активных записей, ru/en названия, группировка городов) и подтверждает
каждый код через `geodata_by_code`. `flight_search` — глубокий тул:
`return_date` ищет оба плеча и возвращает `roundTripOptions` с суммарной
ценой, `date="YYYY-MM"` отдаёт календарь месяца с лучшими датами без живого
поиска, `dates=[...]` сравнивает до 7 дат, `flexible_days` расширяет окно
`priceCalendarNearby`, офферы помечены `labels` («самый дешёвый», «самый
быстрый», «оптимальный») и дополняются автоматическим `priceForecast` при
свежем `searchId`. Календарь читает кэш и не заменяет живой поиск.

`afisha_catalog` публично читает каталоги кино, концертов и театра,
`cinema_schedule` — сеансы кино, а `concert_schedule` — показы концертов,
спектаклей и выставок без обязательной банковской сессии. Эти запросы сохраняют
обязательный app/device-контекст, но не отправляют Bearer, cookie или `sessionid`.

`train_stations` резолвит пользовательский текст в числовой `searchCode`, а
`train_search` использует его для расписаний, цен и мест. `train_calendar` сообщает
доступные даты, но не заменяет резолвер.

Hotel-инструменты работают с публичной выдачей: autocomplete, глубокий search,
details, rates и reviews. `hotel_search` принимает `destination="город"`
(разрешается сервером) или `destination_id`; первые `comparison_limit` карточек
приходят enriched (details, подтверждённый тариф с `checkoutUrl`, фото,
reviewDigest) плюс `comparisonMarkdown` (готовая таблица) и `map`
(OpenStreetMap). При `price.isFinalPrice=false` условия не считаются
подтверждёнными. `hotel_rates` возвращает тарифы с готовым `checkoutUrl` и
`checkedAt`: если страница показывает другую цену, повторный вызов возвращает
свежие ссылки; бронь и оплату это не создаёт.

Каждый инструмент, возвращающий отель, включает его статическую карточку и до
трёх реальных HTTPS-фотографий: `details` у элементов списков и `hotelDetails` у
`hotel_rates`/`hotel_reviews`. Для больших списков static-info загружается
пакетно. Недоступный detail-source не уничтожает цены, тарифы или отзывы: ответ
остаётся частичным и получает warning плюс `meta.detailsComplete=false`.

`compare_*`-инструменты остались только на единой поверхности
(`TRAVEL_SURFACE=full`): travel-сценарии используют глубокие тулы
(`flight_search(dates)`, `hotel_search`) и `get_trip_report(brief)`.

`weather` возвращает прогноз Open-Meteo для ближайших 16 дней либо климатическую
оценку ERA5 для более дальних дат; диапазон ограничен 30 днями.

`restaurant_search` читает публичную серверную выдачу Яндекс.Карт без банковской
сессии и ключей, ограничивает результат заданным радиусом и возвращает
report-ready карточки с прямыми sourceUrl. Данные не сохраняются на сервере.

## Дайджест поездки

`get_trip_report` работает в двух формах. Краткая:
`get_trip_report(brief={city, dateFrom, dateTo, adults, origin?},
output_mode=...)` — сервер сам подбирает три enriched-отеля (тариф с
`checkoutUrl`, фото, отзывы), события Афиши на даты, рестораны вокруг отеля и,
при заданном `origin`, перелёт туда-обратно с `bookingUrl`, затем собирает и
рендерит страницу: один вызов вместо цепочки из 15+. Полная форма:
`get_trip_report(request)` принимает готовый `trip-page/v2` с транспортом,
отелями и `events` либо `hotel-page/v1`; предложения и расписания
перепроверяются до вызова, report валидирует документ и возвращает готовый
дайджест. Для пустого `venues` в trip-page/v2 он автоматически загружает
рестораны Яндекс.Карт рядом с выбранным отелем. `html` — JSON с HTML и
metadata, `markdown` — текстовый дайджест с теми же ресторанами.
Файлы, бронирование и оплата не создаются.
HTML metadata содержит `schemaVersion`. Неполный hotel enrichment по умолчанию
превращается в warnings и фотографии/статика догружаются на сервере;
`strict=true` возвращает жёсткую ошибку `HOTEL_ENRICHMENT_REQUIRED`, а
`allow_incomplete_after_source_failure` документирует фактические сбои
источников в `request.warnings`.
Правила доставки hotel-фотографий внутри HTML, включая server-side встраивание
для sandbox-preview, находятся в
[TRAVEL_OUTPUT_MODES.md](TRAVEL_OUTPUT_MODES.md#фото).

Ссылка на объект или checkout не означает бронь или оплату. Не публикуй сырые
персональные записи, credentials или токены и не выдумывай значения, которые не
вернул источник.

## Формат ответов и карточки

Все travel-инструменты по умолчанию возвращают `response_format="json"`
(структурный envelope `{ok, data, warnings, meta}`); `text` доступен явным
параметром. Карточки presentation-ready: у отеля — `url`, `images`/`photoUrls`,
`rating` и `reviewDigest` с цитатами; у оффера — `bookingUrl`; у тарифа —
`checkoutUrl`; у события — `url` и `imageUrl`. Envelope содержит `hints` —
подсказки следующего шага. `get_trip_report` принимает hotel-карточки в форме
hotel-инструментов (details, imageUrls, confirmedRate, pluses/minuses,
tbankUrl маппятся автоматически) и даже bare-id; неполный enrichment по
умолчанию превращается в warnings, `strict=true` возвращает жёсткий режим
`HOTEL_ENRICHMENT_REQUIRED`.
