# Travel Nova API

Express API для компиляции персональных путешествий. Сервис объединяет
read-only методы `tbank-mcp`, OpenStreetMap, Open-Meteo и внутренний LLM Proxy, проверяет
бюджет и хранит поездки, ревизии и чат в SQLite.

## Запуск

```bash
cp travel-api/.env.example travel-api/.env
npm install
npm run dev -w travel-nova-api
```

Опционально добавьте `TWOGIS_API_KEY` из
[Менеджера Платформы 2ГИС](https://platform.2gis.ru/). Тогда рестораны будут
искаться через 2ГИС с рейтингом, адресом, расписанием и доступными атрибутами;
при ошибке или пустой выдаче API автоматически вернётся к OpenStreetMap.

После запуска:

- `GET /` — информация о сервисе;
- `GET /health` — короткая проверка доступности;
- `GET /api/v1/health` — версионированная проверка доступности;
- `GET /api/v1/catalog/cities` — каталог городов;
- `GET /api/v1/system/readiness` — безопасное состояние локальных источников;
- `POST /api/v1/trip-runs` — новый подбор;
- `GET /api/v1/jobs/:jobId/events` — прогресс по SSE;
- `GET /api/v1/trips/:tripId` — сохранённая поездка;
- `POST /api/v1/trips/:tripId/messages` — изменение через чат.

## Команды

```bash
npm run dev        # разработка с автоматическим перезапуском
npm run typecheck  # проверка TypeScript
npm run build      # сборка в dist/
npm start          # запуск собранного приложения
```

## Структура

```text
src/
  config/       переменные окружения
  http/         общие HTTP middleware и ошибки
  modules/      каталог, провайдеры, planner, SQLite и редактор
  app.ts        сборка Express-приложения
  server.ts     запуск и корректное завершение процесса
```

Публичные DTO находятся в workspace `@travel-growth-inspiration/contracts`. Все ответы
провайдеров нормализуются до этих контрактов до сохранения или передачи в UI.
Режимы `auto` и `live` не используют демонстрационный fallback; `demo` включается
только явно.

Для фиксированного города три окна гибких дат проверяются параллельно. Лимиты
задаются через `MCP_FLIGHT_MAX_CONCURRENCY` (по умолчанию 6) и
`MCP_HOTEL_MAX_CONCURRENCY` (по умолчанию 3); таймауты отдельных запросов при
этом остаются `FLIGHT_PROVIDER_TIMEOUT_MS` и `HOTEL_PROVIDER_TIMEOUT_MS`.
