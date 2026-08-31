# T-Bank MCP: offline bundle

Этот архив запускает единый T-Bank MCP без Node.js, npm Registry, PyPI и создания
виртуального окружения на целевой машине. Внутри уже находятся relocatable
CPython, все Python-зависимости, Playwright и Chromium.

Архив платформенный. Сборка `macos-arm64` работает только на Apple Silicon.

## Установка

```bash
tar -xzf tbank-mcp-<version>-macos-arm64-py<version>.tar.gz
cd tbank-mcp-<version>-macos-arm64-py<version>
./bin/tbank-mcp login
```

Номер телефона, SMS-код, пароль и PIN вводятся только в локальном терминале.
Сессия сохраняется с правами `0600` в
`~/.local/share/tbank-mcp/session.json` и в архив не входит.

## MCP-конфигурация

Укажите абсолютный путь к launcher из распакованного каталога:

```json
{
  "mcpServers": {
    "tbank": {
      "command": "/absolute/path/tbank-mcp/bin/tbank-mcp",
      "args": ["serve"]
    }
  }
}
```

Проверить версию и целостность можно до логина:

```bash
./bin/tbank-mcp --version
shasum -a 256 -c MANIFEST.sha256
```

Скачивание кода и зависимостей не требуется. Для фактических запросов MCP по-
прежнему нужен HTTPS-доступ к публичным API T-Bank, OpenStreetMap и Open-Meteo.

Все банковские и travel-методы доступны через один сервер. Денежные действия
требуют preview и отдельного явного подтверждения перед confirm.
