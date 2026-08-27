# Travel-only MCP

`tbank-travel-mcp` запускает тот же Python FastMCP, что и `tbank-mcp`, но
регистрирует только фиксированный read-only allowlist. Исключённые функции не
скрываются подсказкой: их нет в ответе `tools/list`.

## Запуск

```bash
npx -y @travel-growth-inspiration/mcp login
npx -y @travel-growth-inspiration/mcp serve
```

`login` запрашивает номер телефона, SMS-код, пароль и PIN напрямую в терминале.
Секретный ввод скрыт и не проходит через модель. Сессия сохраняется в
`~/.local/share/tbank-mcp/session.json` с правами `0600`.

Конфигурация агента:

```json
{
  "mcpServers": {
    "travel": {
      "command": "npx",
      "args": ["-y", "@travel-growth-inspiration/mcp", "serve"]
    }
  }
}
```

Node.js работает только как npm-bootstrap: создаёт/обновляет Python venv и
делает `exec`. После старта остаётся только Python FastMCP. Bootstrap пишет
диагностику в stderr, поэтому stdout остаётся чистым stdio MCP.

## Готовый prompt template: персональные выходные

MCP публикует шаблон `personalized_weekend_landing`. Он собирает в один безопасный
сценарий анализ трат за заданный период, историю заказов Афиши, живой подбор
событий, проверку отеля и подготовку адаптивного лендинга с постерами.

Аргументы шаблона:

- `city`, `date_from`, `date_to` — город и диапазон поездки;
- `hotel_query` — точное или частичное название отеля, необязательно;
- `adults` — число взрослых, по умолчанию 2;
- `spending_lookback_days` — глубина анализа расходов, по умолчанию 60 дней.

Шаблон не бронирует и не оплачивает билеты. Для отеля он требует сначала
показать тарифы и получить явный выбор конкретного тарифа; только после этого
можно сформировать checkout-ссылку через `hotel_checkout_url`.

## Опубликованные инструменты

- Контекст: `session_status`, `list_accounts`, `list_operations`,
  `spending_categories`, `operations_histogram`, `audience_profile`.
- История: `orders`, `order_details`, `travel_order_details`, `flight_history`.
- Авиа: `flight_search`, `compare_flight_prices`.
- ЖД: `train_stations`, `train_search`, `compare_train_prices`.
- Отели: `hotel_autocomplete`, `hotel_search`, `compare_hotel_prices`,
  `hotel_search_filters`, `hotel_latest_offers`, `hotel_details`, `hotel_rates`,
  `hotel_checkout_url`, `hotel_reviews`, `hotel_filters`.
- Составная цена: `compare_flight_hotel_prices`.
- Афиша: `search_app`, `cinema_search`, `cinema_schedule`, `cinema_seats`,
  `afisha_catalog`, `afisha_places`, `place_schedule`, `place_info`,
  `concert_schedule`, `concert_hall`.
- Публичные источники: `nearby_search`, `weather`.

У каждого инструмента `readOnlyHint=true` и `destructiveHint=false`. Login/PIN,
переводы, оплаты, бронирования, корзины, сообщения, карты, реквизиты, документы,
инвестиции, продукты, `get_data`, ЖД-бронирование и оплата отсутствуют.

`train_stations` резолвит название города или вокзала через публичный fulltext
T-Bank и возвращает числовой `searchCode`. Этот код напрямую используется в
`train_search`, который обращается к публичному T-Bank Railways API и возвращает
расписание, цены и доступные места. Банковская сессия этим двум тулам не нужна.

`nearby_search` использует Nominatim и Overpass/OpenStreetMap, ищет в радиусе
1,8 км и не требует ключа. `weather` использует прогноз Open-Meteo для ближайших
16 дней, а для остальных дат — климатическую оценку ERA5 за 1991–2020. Диапазон
ограничен 30 днями; partial result содержит `warnings`.

Четыре `compare_*`-инструмента выполняют bounded fan-out по датам, фильтрацию,
стабильную сортировку и расчёт абсолютных/процентных дельт внутри Python. Они
возвращают MCP `outputSchema`/`structuredContent`; JSON-текст остаётся fallback
для старых клиентов. `lowest observed` означает минимум только среди реально
полученных вариантов: partial result никогда не выдаётся за глобальный минимум.

`compare_flight_hotel_prices` складывает только перелёт туда, перелёт обратно и
отель. Питание вне тарифа, трансферы, события и ежедневные расходы в сумму не
входят. Сервер не хранит цены, поездки или экспериментальное состояние; между
перезапусками остаётся только банковская сессия.
