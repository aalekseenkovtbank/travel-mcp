# Travel Nova MCP: локальный runbook деплоя в Timeweb Cloud

Этот файл содержит привязку к конкретному облачному приложению и общий порядок
его публикации из любого checkout репозитория.

## Текущее окружение

- Репозиторий: `aalekseenkovtbank/travel-mcp`.
- Ветка деплоя: `codex/timeweb-mcp`.
- Timeweb Cloud project ID: `2904963`.
- Timeweb App Platform app ID: `250685`.
- Имя приложения: `Travel Nova MCP`.
- Настройки сборки: `https://timeweb.cloud/my/apps/250685/settings`.
- Статус и логи: `https://timeweb.cloud/my/apps/250685/deploy`.
- Директория проекта в Timeweb: `/tbank-mcp`.
- Окружение сборки: `Dockerfile`.
- Публичный MCP: `https://aalekseenkovtbank-travel-mcp-c1cc.twc1.net/mcp`.
- Health endpoint: `https://aalekseenkovtbank-travel-mcp-c1cc.twc1.net/health`.
- MCP опубликован без Bearer-авторизации. Переменная `MCP_AUTH_TOKEN` в Timeweb
  не нужна.

Timeweb закрепляет приложение на выбранном коммите. Обычного `git push`
недостаточно: после push нужно выбрать новый коммит в настройках и вручную
запустить деплой.

## Перед публикацией

1. Прочитай корневой `AGENTS.md` и `docs/AGENT_RULES.md`.
2. Сохрани пользовательские незакоммиченные изменения. Не откатывай их.
3. Проверь текущую ветку и diff:

   ```bash
   git status --short --branch
   git diff --check
   git diff
   ```

4. Не запускай автоматические тесты: это запрещено корневым `AGENTS.md`.
   Используй подходящие проверки импорта, `py_compile`, lint, typecheck или
   ручную проверку конкретного контракта.
5. Зафиксируй только относящиеся к задаче файлы и отправь ветку:

   ```bash
   git add <точные пути>
   git commit -m '<сообщение>'
   git push origin codex/timeweb-mcp
   ```

## Деплой в Timeweb

1. Открой страницу настроек приложения:
   `https://timeweb.cloud/my/apps/250685/settings`.
2. Проверь значения:
   - окружение — `Dockerfile`;
   - путь до директории проекта — `/tbank-mcp`;
   - ветка — `codex/timeweb-mcp`;
   - путь проверки состояния оставлен пустым;
   - `MCP_AUTH_TOKEN` отсутствует.
3. В блоке «Коммит» выбери только что отправленный commit SHA.
4. Нажми «Сохранить данные».
5. В диалоге «Запустить деплой?» нажми «Запустить».
6. Перейди на `https://timeweb.cloud/my/apps/250685/deploy` и дождись одновременно:
   - статуса «В сети»;
   - нужного commit SHA в шапке;
   - статуса «Успешно» у деплоя;
   - строки `Deploy succeeded` в логах.
7. При ошибке не откатывай пользовательские изменения. Прочитай последние логи,
   исправь причину в репозитории, сделай новый коммит и повтори процедуру.

## Проверка после деплоя

Сначала проверь health endpoint:

```bash
curl -sS -i \
  https://aalekseenkovtbank-travel-mcp-c1cc.twc1.net/health
```

Ожидается `HTTP 200` и JSON:

```json
{"ok":true,"service":"tbank-mcp"}
```

Затем выполни MCP `initialize` без заголовка `Authorization`:

```bash
curl -sS -i -X POST \
  https://aalekseenkovtbank-travel-mcp-c1cc.twc1.net/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"deploy-check","version":"1.0"}}}'
```

Ожидается `HTTP 200`, `content-type: text/event-stream`, заголовок
`mcp-session-id` и результат `initialize` с `serverInfo.name = "tbank"`.

Если задача меняла конкретный read-only tool, заверши MCP handshake и вызови
этот tool через `tools/call` с безопасными аргументами. Проверяй не только HTTP
статус, но и отсутствие прежней ошибки в payload. Не вызывай денежные,
бронирующие или иные изменяющие состояние tools ради smoke-check.

## Финальный отчёт

Сообщи пользователю:

- commit SHA и ветку;
- успешность push;
- статус Timeweb и развернутый SHA;
- результаты `/health`, `initialize` и проверки изменённого tool;
- состояние рабочего дерева.
