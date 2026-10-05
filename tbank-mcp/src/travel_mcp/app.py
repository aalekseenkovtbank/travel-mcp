"""Travel MCP application shell (FastMCP instance, resources, prompt, tool wiring).

Thin by design: the server object, the instruction resources, the one travel
prompt and the tool wiring that binds allowlisted tool bodies from the canonical
implementation module ``src.server`` (single source of truth) onto this
travel-only FastMCP instance with audited descriptions and annotations.
"""
from __future__ import annotations

import asyncio
import functools
from collections.abc import Callable
from typing import Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .. import trace
from ..instructions import InstructionDocument, instruction_documents

READ, WRITE, MONEY = "read", "write", "money"

# Disabled from the travel-only surface. Implementations stay in their
# modules so they can be restored without reconstructing code or contracts.
# The 2026-09 consolidation removed ceremony/catalog tools whose capability
# now lives inside the deep search tools:
#   hotel_search_filters/hotel_filters -> hotel_search(filters) + availableFilters
#   hotel_latest_offers               -> hotel_search enrichment + trip brief
#   hotel_checkout_url                -> checkoutUrl on every rate row
#   flight_price_forecast             -> flight_search priceForecast (auto)
#   compare_flight_prices             -> flight_search(dates=[...])
#   compare_train_prices/compare_hotel_prices/compare_flight_hotel_prices
#                                     -> deep tools + get_trip_report(brief)
# Keep this list in one place: registration decorators consult it below.
DISABLED_TOOL_NAMES = frozenset({
    "nearby_search", "flows", "format_trip_reply",
    "compose_travel_page", "render_trip_page", "render_travel_page",
    "travel_page_schema", "validate_travel_page",
    "hotel_search_filters", "hotel_filters", "hotel_latest_offers",
    "hotel_checkout_url", "flight_price_forecast", "compare_flight_prices",
    "compare_train_prices", "compare_hotel_prices",
    "compare_flight_hotel_prices",
})

# The travel-only surface registers exactly these tools. Bodies come from
# ``src.server`` via _register_travel_tools(); the instruction fallback tools
# are defined locally in this module. Keep this allowlist next to the
# agent-facing metadata so instructions and titles cannot drift from
# tools/list when a module is intentionally not registered.
# Bank-session tools (train_calendar, trip_personalization_profile, …) stay on
# the unified surface only: this surface has no login(), so they could never
# succeed here and would ship a permanent dead end.
ACTIVE_TOOL_NAMES = frozenset({
    "flight_search",
    "flight_price_calendar", "flight_schedule",
    "geodata_by_code", "search_iata_code",
    "hotel_autocomplete", "hotel_search", "hotel_details", "hotel_rates",
    "hotel_reviews", "train_stations", "train_search",
    "weather", "restaurant_search", "get_trip_report",
    # Read-only events surface: catalog, venues and schedule confirmation.
    "afisha_catalog", "afisha_places", "place_info", "place_schedule",
    "cinema_schedule", "concert_schedule",
    "list_instructions", "read_instruction", "get_travel_prompt",
})

_TRAVEL_INSTRUCTION_SLUGS = frozenset({
    "tbank-flight-search",
    "tbank-trip-generation",
    "tbank-hotel-search",
})


def _travel_instruction_documents() -> tuple[InstructionDocument, ...]:
    return tuple(
        document for document in instruction_documents()
        if document.slug in _TRAVEL_INSTRUCTION_SLUGS
    )


def _travel_server_instructions() -> str:
    return (
        "Travel Nova — MCP для планирования путешествий: авиабилеты, отели, ЖД, "
        "выгодные цены. Workflow и карточка поездки: "
        "mcp({instructions:\"travel\"}). "
        "Основной путь — get_trip_report(brief={city, dateFrom, dateTo, adults, "
        "origin?}, output_mode=\"html\" или \"markdown\"): сервер сам подберёт "
        "отели, события, рестораны и перелёт. Полный документ request "
        "используй, когда нужен ручной контроль. "
        "Для деталей читай read_instruction(\"tbank-trip-generation\"), затем "
        "при необходимости \"tbank-flight-search\" и \"tbank-hotel-search\". "
        "Если resources скрыты, вызови list_instructions(), затем "
        "read_instruction(slug). "
        "flight_search умеет туда-обратно (return_date), месяц (date=\"2026-10\") "
        "и сравнение дат (dates=[...]); офферы помечены «самый дешёвый/быстрый/"
        "оптимальный» и содержат bookingUrl. hotel_search принимает "
        "destination=\"город\" и возвращает comparisonMarkdown, map и тарифы с "
        "checkoutUrl; тарифы hotel_rates — checkoutUrl с checkedAt. "
        "Рестораны ищет публичный restaurant_search из Яндекс.Карт; события и "
        "развлечения — read-only afisha_catalog, afisha_places, place_info, "
        "place_schedule, cinema_schedule и concert_schedule; для пустого "
        "venues get_trip_report запускает рестораны автоматически. "
        "Checkout-ссылки только передают управление пользователю: "
        "бронирование и оплата через MCP не выполняются. Не выдумывай цены, id, "
        "расписания, наличие, фотографии или URL; executable schemas имеют "
        "приоритет над Markdown."
    )

mcp = FastMCP(
    "travel-nova",
    instructions=_travel_server_instructions(),
)

@mcp.resource(
    "travel-nova://instructions/index",
    name="travel_nova_instruction_index",
    title="Travel Nova: входная точка инструкций",
    description=(
        "Короткий порядок чтения и каталог всех инструкций, поставляемых "
        "вместе с этой MCP-поверхностью."
    ),
    mime_type="text/markdown",
)
def travel_nova_instruction_index() -> str:
    """Return the travel-only MCP-native instruction entrypoint."""
    documents = _travel_instruction_documents()
    lines = [
        "# Travel Nova: travel-only instructions",
        "",
        "This MCP provides read-only tools for finding hotels, flights and train tickets at competitive prices, plus a trip planner and travel booklet/report generation.",
        "It cannot book or pay for transport or hotels.",
        "",
        "Read only the documents needed for the current task.",
        "If this host does not expose resources/prompts, use tools "
        "list_instructions, read_instruction and get_travel_prompt.",
    ]
    lines.extend(
        f"- `{document.uri}` — **{document.title}**. {document.description}"
        for document in documents
    )
    return "\n".join(lines) + "\n"

def _instruction_reader(document: InstructionDocument) -> Callable[[], str]:
    def read_document() -> str:
        return document.read()

    return read_document

def _register_instruction_resources() -> None:
    """Publish only documents relevant to the travel-only surface."""
    for document in _travel_instruction_documents():
        read_document = _instruction_reader(document)
        read_document.__name__ = f"read_instruction_{document.slug.replace('-', '_')}"
        mcp.resource(
            document.uri,
            name=f"travel_nova_instruction_{document.slug.replace('-', '_')}",
            title=document.title,
            description=document.description,
            mime_type="text/markdown",
        )(read_document)

_register_instruction_resources()

_INSTRUCTION_SERVER_SLUG = "server"
_INSTRUCTION_INDEX_SLUG = "index"


def travel_instruction_catalog() -> list[dict[str, str]]:
    """Slugs for list_instructions / read_instruction (ChatGPT tools fallback)."""
    items = [
        {
            "slug": _INSTRUCTION_SERVER_SLUG,
            "title": "Server instructions",
            "description": "Короткое поле initialize.instructions: границы поверхности и вход в каталог.",
        },
        {
            "slug": _INSTRUCTION_INDEX_SLUG,
            "title": "Каталог инструкций",
            "description": "Порядок чтения и список документов travel-only поверхности.",
        },
    ]
    for document in _travel_instruction_documents():
        items.append(
            {
                "slug": document.slug,
                "title": document.title,
                "description": document.description,
            }
        )
    return items


def travel_instruction_text(slug: str) -> str:
    """Return one instruction document; unknown slugs raise ValueError."""
    key = slug.strip().lower()
    if not key:
        raise ValueError(
            "slug is empty; call list_instructions() or pass a slug from that list"
        )
    if key == _INSTRUCTION_SERVER_SLUG:
        return _travel_server_instructions()
    if key == _INSTRUCTION_INDEX_SLUG:
        return travel_nova_instruction_index()
    for document in _travel_instruction_documents():
        if document.slug == key:
            return document.read()
    known = ", ".join(item["slug"] for item in travel_instruction_catalog())
    raise ValueError(f"unknown instruction slug {slug!r}; known: {known}")


@mcp.prompt(
    name="personalized_weekend_landing",
    title="Персональная поездка: транспорт, отели и готовая страница",
    description=(
        "Безопасный сценарий: получить агрегированный профиль, подобрать транспорт "
        "и отели, затем вернуть страницу или чат-ответ."
    ),
)
def personalized_weekend_landing(
    city: str,
    date_from: str,
    date_to: str,
    hotel_query: str = "",
    adults: int = 2,
    output_mode: Literal["html", "chat"] = "html",
) -> str:
    """Build the agent prompt for a personalized travel landing page."""
    hotel_part = (
        f"Пользователь назвал отель: {hotel_query}. Включи его в тройку и отметь рекомендуемым."
        if hotel_query.strip()
        else "Отель не задан: подбери ровно три варианта и выбери средний по цене как рекомендуемый."
    )
    output_part = (
        "Собери trip-page/v2 (или hotel-page/v1) и вызови "
        "get_trip_report(request, output_mode=\"html\"): верни его ГОТОВЫЙ "
        "HTML целиком — в Canvas/превью HTML хоста, если доступно. Не пиши "
        "файлы и не ссылайся на пути к файлам."
        if output_mode == "html"
        else "Отвечай только в чате (пользователь явно попросил): вызови "
             "get_trip_report(request, output_mode=\"markdown\") и покажи "
             "его Markdown-дайджест со ссылками T-Bank."
    )
    return f"""Подготовь персональный лендинг для поездки в {city} с {date_from} по {date_to}.
Состав поездки: {adults} взрослых; транспорт и отели ищи с adults={adults}.
{hotel_part}

Работай по этому сценарию:
1. Основной путь — один вызов get_trip_report(brief={{city: "{city}", dateFrom: "{date_from}", dateTo: "{date_to}", adults: {adults}, origin: "<город вылета, если известен>"}}, output_mode="html"): сервер сам подберёт транспорт, отели, события и рестораны. Проверь его warnings и при неполных данных дострой вручную.
2. Транспорт вручную: flight_search(from_code, to_code, date, return_date=...) — там-обратно одним вызовом; для месяца передай date="YYYY-MM", для сравнения дат dates=[...]. Каждый бронируемый оффер уже содержит bookingUrl и метки «самый дешёвый/быстрый/оптимальный». Это только поиск: не утверждай, что билет куплен.
3. Отели вручную: hotel_search(destination="{city}", ...) — первые карточки уже enriched (details, тариф с checkoutUrl, фото, отзывы); hotel_rates/hotel_reviews — для отдельного отеля. Карточки передавай как есть: get_trip_report сам смаппит details/imageUrls/confirmedRate/pluses и догрузит фотографии.
4. restaurant_search() с координатами выбранного отеля необязателен: для пустого venues get_trip_report() выполнит тот же публичный поиск Яндекс.Карт автоматически.
5. Собери request только из фактических данных и передай его в get_trip_report(). Неполный enrichment не блокирует страницу: недостающие поля превращаются в warnings, а фотографии догружаются на сервере; strict=true возвращает жёсткий режим. Фактические сбои источников документируй в request.warnings.
6. {output_part} Не создавай отдельный HTML-проект и не пиши файлы. Checkout-ссылка не означает бронь или оплату.
7. Не выдумывай цены, id, расписания, наличие, фотографии или URL. Цены снабжай временем проверки."""

_untraced_tool = mcp.tool

# Explicit descriptions are the stable MCP contract. Function docstrings remain
# useful for developers, but hosts receive these short, audited descriptions.
TOOL_DESCRIPTIONS: dict[str, str] = {
    "flight_search": "Поиск авиабилетов: одна дата, месяц (date=\"2026-10\" — календарь цен и лучшие даты), список дат dates (сравнение дат за один вызов) и туда-обратно (return_date — сервер ищет оба плеча и собирает roundTripOptions с суммарной ценой). from_code/to_code — IATA, flexible_days расширяет окно priceCalendarNearby. Офферы содержат bookingUrl и labels («самый дешёвый», «самый быстрый», «оптимальный», блок best); при свежем searchId прикладывается priceForecast. Бронирования и оплаты нет.",
    "search_iata_code": "Разрешает название города или аэропорта в IATA-коды (словарь банка: 5k+ аэропортов, группировка городов). query — не менее 2 символов, limit ограничен 20; результат содержит code, name, city, country, type и airports-соседей, подтверждённые справочником банка. Read-only резолвер.",
    "flight_price_calendar": "Возвращает кэш минимальных цен по датам вылета. Коды IATA и типы from_kind/to_kind задают направление; диапазоны дат, обратные даты, длительность и фильтры ограничивают выборку. Это не живой тариф; пустой кэш не означает отсутствие рейсов. Для конкретной даты используй flight_search.",
    "flight_schedule": "Возвращает расписание выполняемых рейсов по IATA-направлению. date необязателен и сужает расписание до дня; minPrice — ориентир, не гарантия тарифа. limit ограничивает число рейсов; по умолчанию json, text доступен явным параметром response_format.",
    "geodata_by_code": "Проверяет IATA-коды и возвращает названия, координаты, country/city codes и timezone. codes — один код или список, limit ограничивает записи; неизвестный код даёт ошибку. Метод только читает справочник.",
    "train_stations": "Разрешает название города или станции в числовой searchCode для train_search. search_text — произвольный запрос, limit ограничивает подсказки; по умолчанию json (stations и warnings), text доступен явным параметром response_format. Бронирование не выполняется.",
    "train_search": "Ищет поезда по числовым кодам origin/destination и дате. date — YYYY-MM-DD, adults/children задают пассажиров, limit — 0 или до 100; результат содержит расписание, минимальные цены и места. MCP не бронирует и не оплачивает.",
    "hotel_autocomplete": "Находит локации и отели с id для следующих hotel-вызовов. Каждая hotel-подсказка содержит details с адресом, описанием, удобствами и до 3 фото. query должен содержать не менее 3 символов, limit ограничивает подсказки; для hotel_search используй id локации или просто destination=название. Бронь и оплата не выполняются.",
    "hotel_search": "Ищет доступные отели: передай destination=\"Сочи\" (сервер сам разрешит город) или destination_id из hotel_autocomplete, даты YYYY-MM-DD и взрослых. Для первых comparison_limit карточек (1–5, по умолчанию 3) сразу загружает полные details, подтверждённый тариф (включая checkoutUrl) и выборку свежих отзывов с цитатами: enrichedShortlist + comparisonMarkdown (готовая таблица) + map (OpenStreetMap с точками отелей). Карточка содержит url, rating, фото, плюсы/минусы. MCP не бронирует.",
    "hotel_details": "Возвращает статическую карточку отеля: адрес, описание, часы, удобства и HTTPS-фото из источника. hotel_id — числовой id, max_images — 1–12 (по умолчанию 3); по умолчанию json со структурированными полями для страницы, text доступен явным параметром. Наличие тарифа и бронь не проверяются.",
    "hotel_rates": "Возвращает hotelDetails с детальной карточкой и до 3 фото, а также комнаты и актуальные тарифы с bookHash, ценой, питанием, оплатой, отменой и готовым checkoutUrl у каждой tariff-строки. checkedAt фиксирует время проверки: если страница показывает другую цену — повтори вызов, строки придут со свежими ссылками. hotel_id и даты обязательны, проживание 1–30 ночей, adults 1–6. Запрос read-only.",
    "hotel_reviews": "Возвращает hotelDetails с детальной карточкой и до 3 фото, а также страницу отзывов с сортировкой и cursor-пагинацией. hotel_id обязателен, page_size 1–50; cursor следующей страницы передавай без изменений, search_text поддерживает фильтр onlyPhotos. Отзывы не подтверждают условия тарифа.",
    "weather": "Возвращает forecast или climate по координатам и диапазону дат. city — подпись, latitude/longitude — координаты, date_from/date_to — YYYY-MM-DD с диапазоном до 30 дней; kind в результате различает прогноз и ERA5-оценку. Частичный ответ сопровождается warnings.",
    "restaurant_search": "Ищет рестораны в публичной выдаче Яндекс.Карт рядом с координатами или адресом. Возвращает report-ready карточки с рейтингом, числом отзывов, фото, часами и sourceUrl; банковская сессия не используется.",
    "get_trip_report": "Готовая страница поездки: html или markdown по output_mode. Краткая форма — brief={city, dateFrom, dateTo, adults, origin?}: сервер сам подберёт 3 enriched-отеля (тариф с checkoutUrl, фото, отзывы), события Афиши, рестораны и, при origin, перелёт туда-обратно — один вызов вместо цепочки из 15+. Полный request (trip-page/v2 / hotel-page/v1) принимается как раньше: карточки отелей в форме hotel-инструментов, включая bare-id; маппинг и догрузка фотографий на сервере. Вместо встроенной карты — ссылка на Яндекс.Карты с отметками мест с известными координатами. Неполный enrichment превращается в warnings; strict=true — жёсткий режим. Файлов, бронирования и оплаты нет.",
    "list_instructions": "Возвращает каталог travel-only инструкций, если клиент не показывает resources. Результат содержит доступные slug и порядок чтения; банковские и отключённые вертикали в каталог не входят.",
    "read_instruction": "Возвращает один travel-only документ по slug из list_instructions. Передай server, index или slug из каталога; неизвестный slug возвращает ошибку и каталог. Внешних действий нет.",
    "get_travel_prompt": "Возвращает параметризованный prompt для поиска транспорта, отелей и страницы поездки. city/date_from/date_to обязательны, adults 1–6, output_mode — html или chat; prompt только инструктирует агента и ничего не бронирует.",
    "afisha_catalog": "События и развлечения города по датам: кино, концерты, спектакли, выставки. kind задаёт категорию (movie по умолчанию, concert, theatre, exhibition), city — название города, date_from/date_to — YYYY-MM-DD. Карточки содержат название, даты, цены от, url (ссылка на событие) и imageUrl (постер). Read-only, без брони и оплаты.",
    "afisha_places": "Площадки города: кинотеатры, театры, концертные залы. kind задаёт тип, query ищет по названию, city ограничивает город; возвращает place_id, название, адрес и координаты для place_info и place_schedule. Только чтение.",
    "place_info": "Детальная карточка площадки по object_id из afisha_places или search: адрес, координаты, описание. Read-only справочник.",
    "place_schedule": "Сеансы и события площадки по object_id и датам. Возвращает расписание залов; подтверждение сеансов для финального ответа делай через cinema_schedule/concert_schedule. Только чтение.",
    "cinema_schedule": "Сеансы кино по event_id из afisha_catalog и датам; cinema — objectId кинотеатра из afisha_places. Подтверждает время сеансов и цены. Бронирование мест не выполняется.",
    "concert_schedule": "Сеансы концертов и спектаклей по event_id из afisha_catalog. kind — concert или spectacle; возвращает даты, площадки и цены от. Read-only подтверждение расписания.",
}

TOOL_KINDS: dict[str, tuple[str, str]] = {
    name: (name.replace("_", " "), READ) for name in ACTIVE_TOOL_NAMES
}
TOOL_KINDS.update({
    "flight_search": ("Поиск авиабилетов", READ),
    "search_iata_code": ("Резолвер IATA-кодов", READ),
    "flight_price_calendar": ("Календарь цен", READ),
    "flight_schedule": ("Расписание рейсов", READ),
    "geodata_by_code": ("Геоданные по IATA-коду", READ),
    "train_stations": ("Резолвер ЖД-станций", READ),
    "train_search": ("Поиск поездов", READ),
    "hotel_autocomplete": ("Поиск направления или отеля", READ),
    "hotel_search": ("Поиск доступных отелей", READ),
    "hotel_details": ("Карточка отеля", READ),
    "hotel_rates": ("Тарифы отеля", READ),
    "hotel_reviews": ("Отзывы об отеле", READ),
    "weather": ("Погода и климат", READ),
    "restaurant_search": ("Рестораны Яндекс.Карт", READ),
    "get_trip_report": ("Готовый дайджест поездки", READ),
    "list_instructions": ("Каталог инструкций", READ),
    "read_instruction": ("Текст инструкции", READ),
    "get_travel_prompt": ("Prompt поездки", READ),
    "afisha_catalog": ("Афиша событий и развлечений", READ),
    "afisha_places": ("Площадки города", READ),
    "place_info": ("Карточка площадки", READ),
    "place_schedule": ("Сеансы площадки", READ),
    "cinema_schedule": ("Сеансы кино", READ),
    "concert_schedule": ("Сеансы концертов и спектаклей", READ),
})

def _annotations_for(name: str) -> ToolAnnotations:
    if name not in TOOL_KINDS:
        raise RuntimeError(
            f"tool {name!r} has no entry in TOOL_KINDS. Classify it as READ "
            f"(nothing changes), WRITE (changes something, costs nothing) or "
            f"MONEY (debits an account) — see the note above the table.")
    title, kind = TOOL_KINDS[name]
    local_renderers: set[str] = set()
    ann = {"title": title, "openWorldHint": name not in local_renderers}
    if kind == READ:
        ann.update(readOnlyHint=True, destructiveHint=False, idempotentHint=True)
    elif kind == WRITE:
        # Modifies something, destroys nothing. destructiveHint defaults to TRUE
        # when readOnlyHint is false, so saying false here is what actually takes
        # the confirmation dialog off these.
        ann.update(readOnlyHint=False, destructiveHint=False)
    else:
        ann.update(readOnlyHint=False, destructiveHint=True, idempotentHint=False)
    return ToolAnnotations(**ann)

def _traced_tool(*a, **kw):
    def register(fn):
        if fn.__name__ in DISABLED_TOOL_NAMES:
            return fn
        annotations = _annotations_for(fn.__name__)
        title, _ = TOOL_KINDS[fn.__name__]
        opts = {
            "title": title,
            "description": TOOL_DESCRIPTIONS[fn.__name__],
            "annotations": annotations,
            **kw,
        }
        return _untraced_tool(*a, **opts)(trace.wrap(fn))
    return register

mcp.tool = _traced_tool

def _threaded_tool(fn):
    """Register a blocking read tool without blocking FastMCP's event loop.

    Travel searches spend most of their time inside synchronous ``requests``
    calls. Running those bodies in worker threads lets independent MCP requests
    make progress and, crucially, lets FastMCP flush each completed response
    while slower searches are still running.

    Disabled names remain importable but are deliberately not registered on the
    public travel-only surface.
    """
    if fn.__name__ in DISABLED_TOOL_NAMES:
        return fn
    @functools.wraps(fn)
    async def offloaded(*args, **kwargs):
        return await asyncio.to_thread(fn, *args, **kwargs)

    return mcp.tool()(offloaded)


# --- Local fallback tools (for hosts that hide resources/prompts) ----------

@_traced_tool()
def list_instructions() -> list[dict[str, str]]:
    """Catalogue of travel-only instruction documents: slug, title, description."""
    return travel_instruction_catalog()


@_traced_tool()
def read_instruction(slug: str) -> str:
    """One travel-only instruction document by slug from list_instructions()."""
    return travel_instruction_text(slug)


@_traced_tool()
def get_travel_prompt(
    city: str,
    date_from: str,
    date_to: str,
    hotel_query: str = "",
    adults: int = 2,
    output_mode: Literal["html", "chat"] = "html",
) -> str:
    """Parameterized agent prompt for a personalized trip landing page."""
    return personalized_weekend_landing(
        city, date_from, date_to, hotel_query, adults, output_mode,
    )


_LOCAL_TOOL_NAMES = frozenset({
    "list_instructions", "read_instruction", "get_travel_prompt",
})


def _register_travel_tools() -> None:
    """Bind allowlisted tool bodies from the canonical implementation module.

    Tool bodies live exactly once in ``src.server`` (plus its helper modules);
    this travel-only surface re-registers the allowlisted subset with the
    audited descriptions, titles and annotations maintained here. A name that
    is allowlisted but missing from ``src.server`` fails loudly at import time
    instead of silently disappearing from tools/list.
    """
    from .. import server as _server_module
    for name in sorted(ACTIVE_TOOL_NAMES - _LOCAL_TOOL_NAMES):
        fn = getattr(_server_module, name, None)
        if fn is None:
            raise RuntimeError(
                f"travel surface: tool {name!r} is allowlisted but has no "
                f"implementation in src.server")
        _traced_tool()(fn)


_register_travel_tools()
