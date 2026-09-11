# Глоссарий и карта инструкций для агентов

Этот документ — единый каталог агентских правил Travel Nova. Он объясняет, какой
источник читать для конкретной задачи и где находится каноническая версия каждого
правила. Корневая точка входа — [`AGENTS.md`](../AGENTS.md).

## Как пользоваться картой

1. Всегда начинай с `AGENTS.md`.
2. Найди тип задачи в таблице маршрутизации ниже.
3. Прочитай все источники, отмеченные как обязательные, до выполнения задачи.
4. Не загружай все skills подряд: router-skill выбирает узкую инструкцию.
5. Документы, помеченные как справочные, не переопределяют обязательный flow или
   исполняемый контракт.

## Порядок приоритетов

При конфликте используй первый применимый источник сверху вниз:

1. Явные инструкции пользователя для текущей задачи.
2. [`AGENTS.md`](../AGENTS.md) — общие правила всего репозитория.
3. Исполняемый контракт: JSON Schema, валидаторы, сигнатуры и annotations MCP
   tools, в частности [`trip_page.py`](../tbank-mcp/src/trip_page.py), полный
   [`server.py`](../tbank-mcp/src/server.py) и модульные travel-регистрации
   [`travel_mcp/tools`](../tbank-mcp/src/travel_mcp/tools).
4. Обязательный предметный flow или выбранный task-specific skill.
5. Справочные документы, README и примеры.

Если исполняемый контракт не поддерживает обязательное продуктовое требование,
не обходи контракт: сначала обнови схему и реализацию либо остановись и опиши
расхождение.

## Маршрутизация по типу задачи

| Задача | Обязательно прочитать | Дополнительный источник |
|---|---|---|
| Любое изменение репозитория | [`AGENTS.md`](../AGENTS.md) | README соответствующего пакета |
| Отдельный поиск отелей | [`TRAVEL_OUTPUT_MODES.md`](../tbank-mcp/docs/TRAVEL_OUTPUT_MODES.md), [`tbank-hotel-search`](../tbank-mcp/skills/tbank-hotel-search/SKILL.md) | Раздел Hotels в [`FLOWS.md`](../tbank-mcp/docs/FLOWS.md) |
| Поиск транспорта, отелей и досуга с готовой страницей поездки | [`TRIP_GENERATION.md`](../tbank-mcp/docs/TRIP_GENERATION.md), [`TRAVEL_OUTPUT_MODES.md`](../tbank-mcp/docs/TRAVEL_OUTPUT_MODES.md) | [`MCP_DISTRIBUTION.md`](../tbank-mcp/docs/MCP_DISTRIBUTION.md) |
| Изменение полного или travel-only MCP, их дистрибуции или renderer | [`MCP_DISTRIBUTION.md`](../tbank-mcp/docs/MCP_DISTRIBUTION.md), [`TRIP_GENERATION.md`](../tbank-mcp/docs/TRIP_GENERATION.md), [`TRAVEL_OUTPUT_MODES.md`](../tbank-mcp/docs/TRAVEL_OUTPUT_MODES.md) | [`server.py`](../tbank-mcp/src/server.py), [`travel_mcp`](../tbank-mcp/src/travel_mcp), [`trip_page.py`](../tbank-mcp/src/trip_page.py) |
| Любая задача T-Bank MCP | router-skill [`tbank`](../tbank-mcp/skills/tbank/SKILL.md), затем один узкий skill | Нужный раздел [`FLOWS.md`](../tbank-mcp/docs/FLOWS.md) |
| Точная цепочка MCP-вызовов или диагностика flow | Соответствующий skill | Нужный раздел [`FLOWS.md`](../tbank-mcp/docs/FLOWS.md), не весь документ |
| Изменение MCP tool или prompt | Сигнатура, docstring и annotations в [`server.py`](../tbank-mcp/src/server.py) | Связанный skill и `FLOWS.md` |
| Изменение формата страницы поездки | [`TRIP_GENERATION.md`](../tbank-mcp/docs/TRIP_GENERATION.md), [`trip_page.py`](../tbank-mcp/src/trip_page.py) | [`trip_personalization.py`](../tbank-mcp/src/trip_personalization.py) |
| Выгрузка корпоративной API-документации из Confluence | Локальный skill [`confluence-doc-extract`](../.nessy/skills/auto-skill-confluence-doc-extract/SKILL.md) | Правила корпоративной wiki |

## Skills Travel MCP

Travel-router [`tbank`](../tbank-mcp/skills/tbank/SKILL.md) выбирает активный
предметный skill по сценарию. Только перечисленные ниже travel-каталоги остаются
под `tbank-mcp/skills/` и могут индексироваться агентом.

| Область | Канонический skill |
|---|---|
| Отдельный поиск и сравнение авиабилетов | [`tbank-flight-search`](../tbank-mcp/skills/tbank-flight-search/SKILL.md) |
| Отдельный поиск отелей, shortlist и тарифы | [`tbank-hotel-search`](../tbank-mcp/skills/tbank-hotel-search/SKILL.md) |
| Составная поездка и итоговый дайджест | [`tbank-trip-generation`](../tbank-mcp/skills/tbank-trip-generation/SKILL.md) |
| ЖД, погода и общие travel-компоненты | [`tbank-travel-search`](../tbank-mcp/skills/tbank-travel-search/SKILL.md) |

Банковские skills сохранены без потери содержимого в
`tbank-mcp/archive/banking-guidance/`. Их файлы называются `SKILL.md.disabled`,
поэтому skill-сканеры их не индексируют; это архив, а не действующая инструкция.

## Карта хранилищ

| Хранилище | Роль | Статус |
|---|---|---|
| [`AGENTS.md`](../AGENTS.md) | Автоматически обнаруживаемая корневая инструкция | Каноническая входная точка |
| [`docs/AGENT_RULES.md`](AGENT_RULES.md) | Навигация, глоссарий и приоритеты | Канонический каталог |
| [`tbank-mcp/docs`](../tbank-mcp/docs) | Предметные flows и документация MCP | Читать по маршруту |
| [`tbank-mcp/skills`](../tbank-mcp/skills) | Только активные travel-инструкции | Выбирать через travel-router |
| `tbank-mcp/archive/banking-guidance` | Отключённый архив банковских skills (`SKILL.md.disabled`) | Не индексировать и не применять |
| MCP Resources `travel-nova://instructions/*` | Производная runtime-поставка канонических инструкций вне checkout | Вход через `travel-nova://instructions/index` |
| [`.cursor/rules`](../.cursor/rules) | Адаптер правил для Cursor | Должен ссылаться на `AGENTS.md` |
| [`.nessy/skills`](../.nessy/skills) | Локальные автоматически извлечённые skills | Не хранится в Git |
| [`tbank-mcp/.claude-plugin`](../tbank-mcp/.claude-plugin) | Манифесты публикации MCP и skills | Метаданные, не источник правил |

## Глоссарий

**Корневая инструкция** — `AGENTS.md`, автоматически обнаруживаемый файл общих
правил репозитория.

**Router-skill** — короткая точка выбора предметного skill. В текущей
travel-only конфигурации `tbank-mcp/skills/tbank/SKILL.md` направляет только в
hotel-search или общий travel-search.

**Task-specific skill** — инструкция для одной области: переводов, отелей,
билетов, продуктов и так далее. Загружается только когда задача соответствует её
триггерам.

**Operational flow** — точная последовательность действий и MCP-вызовов.
Общий источник — `FLOWS.md`; для готовой страницы поездки —
`TRIP_GENERATION.md`.

**Исполняемый контракт** — схема и код, реально определяющие допустимые поля,
значения и поведение инструмента. Он сильнее описательного примера в Markdown.

**MCP prompt** — опубликованный сервером шаблон задачи. Prompt
`personalized_weekend_landing` определён в полном `tbank-mcp/src/server.py` и в
travel-only `tbank-mcp/src/travel_mcp/app.py`; действует только при явном выборе
клиентом.

**MCP instruction resource** — поставляемая сервером производная копия
канонического документа. Короткое поле `initialize.instructions` ведёт в
`travel-nova://instructions/index`, а индекс маршрутизирует к отдельным ресурсам;
клиент сам решает, добавлять ли их в контекст модели.

**Полный T-Bank MCP** — поверхность банковских и travel-операций в
`src.server`, сохранённая для банковских сценариев и обратной совместимости.

**Travel MCP** — отдельная поверхность `src.travel_mcp.server`. Её allowlist
задаётся server-side регистрацией `src/travel_mcp/tools/*.py`; денежные,
карточные и бронирующие инструменты в ней отсутствуют. Запуск и дистрибуция обеих
поверхностей описаны в `MCP_DISTRIBUTION.md`.

**Checkout-ссылка** — переход к дальнейшему оформлению пользователем; она сама
не означает бронь или оплату.

**`trip-page/v1`** — версия JSON-контракта статической страницы поездки.

**`trip-page/v2`** — расширенная страница поездки с галереями, структурированным
обзором отзывов и сравнением трёх отелей.

**`hotel-page/v1`** — самостоятельная HTML + JSON подборка до пяти отелей в
общем UI Travel Nova.

## Правила сопровождения документации

- Одно правило должно иметь один канонический источник.
- В других документах оставляй краткое назначение и ссылку, а не копию flow.
- Если дублирование необходимо для runtime prompt или tool safety, пометь текст
  как производный и укажи канонический источник рядом с кодом.
- Новый agent-facing документ или skill обязательно добавляй в эту карту.
- Изменение tool signature требует проверки связанного skill, раздела `FLOWS.md`
  и опубликованного MCP prompt.
- Не удаляй документ или содержательное правило без явного разрешения
  пользователя и предварительного списка последствий.
