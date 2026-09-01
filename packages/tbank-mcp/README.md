# `@travel-growth-inspiration/mcp`

Единый T-Bank MCP для банковских, платёжных и travel-операций. Node.js нужен
только для дистрибуции через npm: после подготовки Python venv launcher делает
`exec`, и со stdio агента работает непосредственно Python FastMCP.

```bash
npx -y @travel-growth-inspiration/mcp login
npx -y @travel-growth-inspiration/mcp serve
npx -y @travel-growth-inspiration/mcp install-browser
npx -y @travel-growth-inspiration/mcp page-schema --kind hotels > hotel-page.schema.json
npx -y @travel-growth-inspiration/mcp render-page hotels.json -o hotels.html
npx -y @travel-growth-inspiration/mcp trip-page-schema > trip-page.schema.json
npx -y @travel-growth-inspiration/mcp render-trip trip.json -o trip.html
```

`login` запрашивает номер, SMS-код, пароль и PIN в терминале вне модели. Сессия
сохраняется в `~/.local/share/tbank-mcp/session.json` с правами `0600`.

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

Вместе с сервером поставляются агентские инструкции. Короткая входная точка
приходит в MCP `initialize.instructions` и ведёт в resource
`travel-nova://instructions/index`; остальные правила, travel-документы и skills
доступны через `resources/list` и `resources/read`. Для их чтения checkout Travel
Nova не нужен.

Поддерживаются macOS/Linux и Python 3.11+. Один сервер публикует полный набор
инструментов: счета и операции, переводы и платежи, лояльность, grocery checkout,
Афишу, авиа, ЖД, отели, сравнение цен, персонализацию и локальный renderer.
Все travel-методы входят в этот же набор и возвращаются тем же `tools/list`, что
и банковские методы. Денежные действия сохраняют двухшаговую схему preview →
явное подтверждение пользователя → confirm.

Для grocery checkout нужен Chromium. Установить его можно отдельной командой
`install-browser`; обычный запуск сервера браузер автоматически не скачивает.

`render-page` создаёт `hotel-page/v1` и `trip-page/v2` в общем UI Travel Nova;
`render-trip` сохранён для совместимого `trip-page/v1`. Оба режима не требуют
checkout репозитория, React или Vite. Шаблон, фирменные стили и Leaflet входят в
Python wheel; удалёнными остаются фотографии и тайлы OSM.

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

Готовые архив и SHA-256 появляются в `packages/tbank-mcp/dist/`. Сейчас сборщик
явно поддерживает `macOS arm64`. В архив входят Playwright и Chromium, поэтому
офлайн-дистрибутив предоставляет тот же полный MCP, что и npm-пакет.

```bash
tar -xzf packages/tbank-mcp/dist/tbank-mcp-*.tar.gz
./tbank-mcp-*/bin/tbank-mcp login
```
