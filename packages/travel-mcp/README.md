# `@travel-growth-inspiration/mcp`

POSIX-launcher для Travel MCP и локального генератора страниц. Node.js используется только для
дистрибуции через npm: после подготовки Python venv launcher делает `exec`, и со
stdio агента работает непосредственно Python FastMCP.

```bash
npx -y @travel-growth-inspiration/mcp login
npx -y @travel-growth-inspiration/mcp serve
npx -y @travel-growth-inspiration/mcp trip-page-schema > trip-page.schema.json
npx -y @travel-growth-inspiration/mcp render-trip trip.json -o trip.html
```

`login` запрашивает номер, SMS-код, пароль и PIN в терминале вне модели. Сессия
сохраняется в `~/.local/share/tbank-mcp/session.json` с правами `0600`.

Конфигурация MCP-клиента:

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

Поддерживаются macOS/Linux и Python 3.11+. Банковские и поисковые инструменты
остаются read-only. Единственная локальная запись — `render_trip_page`, создающий
HTML и JSON с правами `0600`.

Сервер публикует 41 инструмент: 40 read-only и локальный renderer. `hotel_search_filters` возвращает
доступные фильтры конкретного поиска, `hotel_latest_offers` перепроверяет цены и
условия шорт-листа, `hotel_rates` возвращает комнаты и живые тарифы выбранного
отеля, `hotel_checkout_url` после явного выбора тарифа создаёт ссылку на его
оформление в T-Bank, а `hotel_reviews` — отзывы с сортировкой, фильтрацией и
cursor-пагинацией.
Четыре сценарных метода
`compare_flight_prices`, `compare_train_prices`, `compare_hotel_prices` и
`compare_flight_hotel_prices` параллельно проверяют несколько дат, сортируют
варианты и возвращают готовые RUB/%-дельты в `structuredContent` с JSON fallback.

`trip_personalization_profile` агрегирует завершённые поездки, траты полных
выходных и заказы Афиши, не возвращая счета, балансы и отдельные операции.
`yandex_venue_search` принимает только полные договорные карточки с фото,
рейтингом и количеством отзывов. Для него нужны `YANDEX_MAPS_API_KEY` и
`YANDEX_VENUE_STORAGE_ALLOWED=1`; последний флаг означает, что оператор проверил
право сохранять данные в итоговом HTML. Ключ никогда не записывается в артефакты.

`render-trip` не требует checkout репозитория, React или Vite. Шаблон, фирменные
стили и Leaflet входят в Python wheel; удалёнными остаются фотографии и тайлы OSM.

На macOS Python автоматически добавляет в свой CA bundle сертификаты, явно
разрешённые в user/admin Keychain trust settings. Это позволяет работать в
корпоративной сети без `verify=false`: сертификат, полученный от удалённого
сервера, никогда не добавляется в доверенные. Для нестандартного локального CA
можно явно задать `TBANK_EXTRA_CA=/path/to/root.pem`.

Инструкция для сопровождающих по выпуску новой версии через PVM находится в
[`PUBLISHING.md`](PUBLISHING.md).

## Полностью офлайн-архив

Для переноса в контур без npm Registry и PyPI можно собрать платформенный
архив. В него входят relocatable CPython и уже установленные зависимости;
на целевой машине не нужны Node.js, Python, `pip` или `uv`:

```bash
npm run build:offline -w @travel-growth-inspiration/mcp
```

Готовые архив и SHA-256 появляются в `packages/travel-mcp/dist/`. Сейчас сборщик
явно поддерживает `macOS arm64`. Playwright не включается, потому что checkout
полного банковского MCP отсутствует в read-only Travel allowlist.

```bash
tar -xzf packages/travel-mcp/dist/travel-nova-mcp-*.tar.gz
./travel-nova-mcp-*/bin/travel-nova-mcp login
```
