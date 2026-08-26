# `@travel-growth-inspiration/mcp`

POSIX-launcher для read-only Travel MCP. Node.js используется только для
дистрибуции через npm: после подготовки Python venv launcher делает `exec`, и со
stdio агента работает непосредственно Python FastMCP.

```bash
npx -y @travel-growth-inspiration/mcp login
npx -y @travel-growth-inspiration/mcp serve
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

Поддерживаются macOS/Linux и Python 3.11+. В read-only набор входят резолвер
ЖД-станций и поиск поездов T-Bank, а также OpenStreetMap и Open-Meteo; API-ключи
не нужны.

Сервер публикует 33 read-only инструмента. Четыре сценарных метода
`compare_flight_prices`, `compare_train_prices`, `compare_hotel_prices` и
`compare_flight_hotel_prices` параллельно проверяют несколько дат, сортируют
варианты и возвращают готовые RUB/%-дельты в `structuredContent` с JSON fallback.

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
