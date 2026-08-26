# Travel MCP: offline bundle

Этот архив запускает read-only Travel MCP без Node.js, npm Registry, PyPI и
создания виртуального окружения на целевой машине. Внутри уже находятся
relocatable CPython и все Python-зависимости.

Архив платформенный. Сборка `macos-arm64` работает только на Apple Silicon.

## Установка

```bash
tar -xzf travel-nova-mcp-<version>-macos-arm64-py<version>.tar.gz
cd travel-nova-mcp-<version>-macos-arm64-py<version>
./bin/travel-nova-mcp login
```

Номер телефона, SMS-код, пароль и PIN вводятся только в локальном терминале.
Сессия сохраняется с правами `0600` в
`~/.local/share/tbank-mcp/session.json` и в архив не входит.

## MCP-конфигурация

Укажите абсолютный путь к launcher из распакованного каталога:

```json
{
  "mcpServers": {
    "travel": {
      "command": "/absolute/path/travel-nova-mcp/bin/travel-nova-mcp",
      "args": ["serve"]
    }
  }
}
```

Проверить версию и целостность можно до логина:

```bash
./bin/travel-nova-mcp --version
shasum -a 256 -c MANIFEST.sha256
```

Скачивание кода и зависимостей не требуется. Для фактических запросов MCP по-
прежнему нужен HTTPS-доступ к публичным API T-Bank, OpenStreetMap и Open-Meteo.

Playwright и Chromium намеренно не включены: они нужны только grocery checkout
полного банковского сервера, которого нет в read-only Travel allowlist.
