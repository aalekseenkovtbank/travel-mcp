# Travel Nova eval runner

`eval_live.py` — детерминированный (без LLM-судей) раннер проверок контракта MCP.
Ничего не бронирует и не оплачивает: только read-only поиск/валидация/рендер и
оффлайн-проверки билдеров. Основан на stdlib (`http.client`), pytest не нужен.

## Запуск

```bash
# оффлайн: билдеры ссылок + контракт документа (без сети)
./.venv/bin/python evals/eval_live.py --offline

# live: боевой эндпоинт
./.venv/bin/python evals/eval_live.py \
  --url https://quexungixgeetus.beget.app/tn-.../mcp

# live + медленный сценарий compose_travel_page (перезапрашивает рейсы/отели)
./.venv/bin/python evals/eval_live.py --url "$TRAVEL_MCP_URL" --scenario

# JSON-отчёт
./.venv/bin/python evals/eval_live.py --url "$TRAVEL_MCP_URL" --report /tmp/eval.json
```

URL можно не передавать, если задан `TRAVEL_MCP_URL`. Exit-код: `0` — всё прошло,
`1` — есть FAIL (удобно для cron/CI).

## Что проверяется

Оффлайн:
- `avia_share_url` воспроизводит реальные образцы (прямые рейсы и пересадки `_`/`~`);
- `avia_checkout_url` по `offerId` (формат `/travel/flights/checkout/?offerId=…`), мусор отклоняется;
- событие принимает внешний HTTPS `sourceUrl`, отель остаётся T-Bank-only;
- минимальный документ без budget/personalization/events/venues/mapPoints/plans валиден;
- JSON Schema: есть `travelers`, нет устаревшего `transportAdults`.

Live:
- `initialize` отвечает `travel-nova`; в `tools/list` есть все ключевые тулы (46), нет `flight_history`;
- `validate_travel_page`: минимальный документ ok; битый — читаемые ошибки с путями и «частые причины»;
- `render_travel_page` толерантный: частичный документ → HTML + `advice`;
- инструкция `trip-generation` чистая (без orders()/audience_profile()/python/путей);
- `flight_search`: у bookable-офферов есть чекаут `tbankUrl` по `offerId`, на плечах `hops`/`flightNumber`;
- `hotel_rates`: компактные карточки (bookHash/price/meal/…, без кредитных полей, < 15 КБ);
- `flight_checkout_url` собирает ссылку 1-в-1 с образцом пересадки;
- (при `--scenario`) `compose_travel_page` возвращает страницу+advice.

## Автоматизация

Подходит для cron/CI: `eval_live.py --offline && eval_live.py --url "$TRAVEL_MCP_URL" --report …`.
Пример (VPS, cron hourly → результат в лог/файл):

```bash
0 * * * * cd /opt/travel-mcp && /usr/bin/python3 evals/eval_live.py \
  --url https://…/mcp --report /opt/travel-mcp/eval-last.json >> /var/log/travel-eval.log 2>&1 \
  && echo ok || echo FAIL
```

Если нужен именно прогон «слабой модели» (как ChatGPT) — это отдельно через
агентский прогон (например, DeepSeek Flash в изолированной папке), см.
`~/.local/share/muxbay/envs/tbank-travel-live-probe`; детерминированный eval его не заменяет.
