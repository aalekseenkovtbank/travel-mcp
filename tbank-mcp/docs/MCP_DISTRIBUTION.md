# T-Bank MCP: единый сервер и дистрибуция

В репозитории существует одна MCP-поверхность: `src.server`. Она одновременно
публикует банковские операции, заказы, переводы, Афишу, travel-поиск,
персонализацию поездки и локальный renderer. Все методы регистрируются одним
сервером и возвращаются в одном `tools/list`; серверных профилей инструментов нет.

Исполняемый список инструментов возвращает `tools/list`; сигнатуры, схемы,
валидаторы и annotations в `src/server.py` имеют приоритет над перечислениями в
документации.

## Запуск

Из Python checkout:

```bash
python -m src.server
```

Через npm-bootstrap:

```bash
npx -y @travel-growth-inspiration/mcp login
npx -y @travel-growth-inspiration/mcp serve
```

Конфигурация MCP-клиента:

```json
{
  "mcpServers": {
    "tbank": {
      "command": "npx",
      "args": ["-y", "@travel-growth-inspiration/mcp", "serve"]
    }
  }
}
```

`login` запрашивает номер телефона, SMS-код, пароль и PIN напрямую в терминале.
Секретный ввод скрыт и не проходит через модель. Сессия сохраняется в
`~/.local/share/tbank-mcp/session.json` с правами `0600`.

Node.js используется только для доставки: launcher создаёт или обновляет Python
venv и затем делает `exec` единого FastMCP-процесса. Для grocery checkout нужен
Chromium; он не скачивается неявно при старте MCP. Установка выполняется отдельно:

```bash
npx -y @travel-growth-inspiration/mcp install-browser
```

## Инструкции, поставляемые через MCP

При инициализации сервер возвращает короткое поле `instructions`, которое ведёт
в MCP Resource `travel-nova://instructions/index`. Индекс содержит порядок чтения
и URI канонических правил, router-skill, всех task-specific skills,
`TRIP_GENERATION.md`, этого документа и `FLOWS.md`.

Клиент получает список через `resources/list`, а содержимое — через
`resources/read`. Runtime-копии входят в npm-поставку и не требуют checkout
репозитория. Клиент сам решает, добавлять ли server instructions и resources в
контекст модели, поэтому критические ограничения закреплены также в схемах,
валидаторах, tool descriptions и annotations.

## Единая поверхность и безопасность

В одном `tools/list` находятся:

- счета, операции, карты, документы и банковские данные;
- переводы, платежи, второй фактор и чеки;
- продукты, корзина и grocery checkout;
- кино, концерты, Афиша и билеты;
- чаты, инвестиции, заказы и диагностика;
- авиа, ЖД, отели, маркетплейс, погода и OpenStreetMap;
- агрегированная персонализация, совместимый `render_trip_page` и единый
  `render_travel_page` для новых страниц.

Читающие инструменты помечены `readOnlyHint=true`. Восстанавливаемые изменения
не помечаются destructive. Инструменты, которые списывают реальные деньги,
имеют `destructiveHint=true` и `idempotentHint=false`; перед ними агент обязан
получить подтверждение конкретной суммы и назначения.

Travel Nova подключается к этому же единому серверу, а приложение сохраняет
собственный клиентский allowlist read-only методов. Для travel-задач действуют
ограничения `TRIP_GENERATION.md`: не вызывать денежные и бронирующие инструменты,
не публиковать сырые банковские данные и создавать страницу только через
`render_travel_page` (`render_trip_page` сохраняется для `trip-page/v1`).

## Travel-источники

`flight_search`, `flight_price_calendar`, `flight_price_forecast`,
`flight_schedule` и `geodata_by_code` — публичные read-only методы и не требуют
банковской сессии. Календарь возвращает кэш минимальных цен для выбора дат,
расписание описывает выполняемые рейсы без гарантии живого тарифа, а прогноз
принимает `searchId` уже выполненного `flight_search`. `flight_history` остаётся
сессионной историей пользователя.

`train_stations` резолвит город или вокзал через публичный fulltext T-Bank и
возвращает числовой `searchCode`; `train_search` использует его для расписаний,
цен и мест. Банковская сессия этим инструментам не нужна.

`nearby_search` использует Nominatim и Overpass/OpenStreetMap, ищет в радиусе
1,8 км и не требует ключа. `weather` использует Open-Meteo для ближайших 16 дней,
а для остальных дат — климатическую оценку ERA5 за 1991–2020. Диапазон ограничен
30 днями; неполный результат содержит `warnings`.

Четыре `compare_*`-инструмента выполняют bounded fan-out, фильтрацию, стабильную
сортировку и расчёт RUB/%-дельт внутри Python. `lowest observed` означает минимум
только среди полученных вариантов. `compare_flight_hotel_prices` складывает
только два перелёта и отель, без питания вне тарифа, трансферов, событий и
ежедневных расходов.

## Статические страницы Travel Nova

Текущие публичные контракты — `trip-page/v2` для полной поездки и
`hotel-page/v1` для отдельной подборки до пяти отелей. Они используют общий UI,
общий CSS и единый `render_travel_page(document)`. Старый `trip-page/v1` и
`render_trip_page(document)` сохранены без удаления для совместимости.

JSON Schema и готовую пару файлов можно получить через единый launcher:

```bash
tbank-mcp page-schema --kind trip
tbank-mcp page-schema --kind hotels
tbank-mcp render-page page.json -o page.html
```

Совместимые команды `trip-page-schema` и `render-trip` продолжают работать для
v1. Без `overwrite=true` существующие файлы не заменяются. HTML содержит
встроенные CSS и минимальный JS; trip page также содержит Leaflet. Фотографии и
тайлы OpenStreetMap загружаются по HTTPS.

Checkout URL используется только если его вернул источник. Ссылка не означает
бронь или оплату и лишь передаёт пользователя на дальнейшее оформление.
