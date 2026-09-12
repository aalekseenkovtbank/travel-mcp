"""Travel MCP application shell (FastMCP instance, resources, prompt, tool wiring).

Thin by design: the server object, the instruction resources, the one travel
prompt and the tool-decorator that attaches title/annotations. Tool bodies live
in ``tools/*``; session/format helpers in ``runtime``.
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

# Disabled from the travel-only surface for now. Implementations stay in their
# modules so they can be restored without reconstructing code or contracts.
# Keep this list in one place: registration decorators consult it below.
DISABLED_TOOL_NAMES = frozenset({
    "nearby_search", "flows", "format_trip_reply",
    "compose_travel_page", "render_travel_page", "travel_page_schema",
    "validate_travel_page",
})

# The travel-only import surface currently registers exactly these tools. Keep
# this allowlist next to the agent-facing metadata so instructions and titles
# cannot drift from tools/list when a module is intentionally not imported.
ACTIVE_TOOL_NAMES = frozenset({
    "compare_flight_prices", "compare_train_prices", "compare_hotel_prices",
    "compare_flight_hotel_prices", "compose_travel_page", "flight_search",
    "flight_price_calendar", "flight_price_forecast", "flight_schedule",
    "geodata_by_code", "flight_checkout_url", "search_iata_code",
    "hotel_autocomplete", "hotel_search", "hotel_search_filters",
    "hotel_latest_offers", "hotel_details", "hotel_rates", "hotel_checkout_url",
    "hotel_reviews", "hotel_filters", "train_stations", "train_search",
    "train_calendar", "weather", "restaurant_search", "get_trip_report",
    "trip_personalization_profile",
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
        "Начни с read_instruction(\"tbank-trip-generation\") — это общий workflow "
        "составной поездки. Затем при необходимости загрузи "
        "read_instruction(\"tbank-flight-search\") для авиа или "
        "read_instruction(\"tbank-hotel-search\") для отелей. HTML и Markdown-режим "
        "задаются output_mode у get_trip_report. "
        "Если resources скрыты, вызови list_instructions(), затем "
        "read_instruction(slug). "
        "Рестораны ищет публичный restaurant_search из Яндекс.Карт; для пустого "
        "venues get_trip_report запускает его автоматически. Основной путь "
        "сборки: get_trip_report(request, output_mode=\"html\" или "
        "\"markdown\"). HTML или Markdown возвращаются из одного тула. "
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
    spending_lookback_days: int = 60,
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
Период анализа трат: последние {spending_lookback_days} дней.
{hotel_part}

Работай по этому сценарию:
1. Вызови trip_personalization_profile() и используй только агрегированные рекомендации. Если профиль недоступен, продолжай по живым предложениям и добавь предупреждение.
2. Подбери транспорт туда и обратно через flight_search или train_search. Для гибких дат используй соответствующий compare_*; для прогноза передай searchId из flight_search в flight_price_forecast(). Это только поиск: не утверждай, что билет куплен. Сохрани только URL и идентификаторы, которые вернул источник.
3. Подбери отели через hotel_autocomplete, hotel_search, hotel_latest_offers, hotel_details, hotel_rates и hotel_reviews. Для финальной поездки собери до трёх выбранных вариантов с возрастающими полными ценами; конкретные условия подтверждай только финальной ценой. Для каждого варианта передай facilities, room, meal, cancellation, payment, reviewCount и reviewDigest. Если источник не вернул часть сведений, добавь warning с названием и id отеля. После hotel_rates() можно сразу получить hand-off URL через hotel_checkout_url() с неизменённым bookHash.
4. Вызови restaurant_search() с координатами выбранного отеля или оставь venues пустым: get_trip_report() выполнит тот же публичный поиск Яндекс.Карт автоматически.
5. Собери request только из фактических данных и передай его в get_trip_report(). Не добавляй необязательные данные без источника и не вызывай report до завершения обязательного hotel enrichment.
6. {output_part} Не создавай отдельный HTML-проект и не пиши файлы. Checkout-ссылка не означает бронь или оплату.
7. Не выдумывай цены, id, расписания, наличие, фотографии или URL. Цены снабжай временем проверки."""

_untraced_tool = mcp.tool

# Explicit descriptions are the stable MCP contract. Function docstrings remain
# useful for developers, but hosts receive these short, audited descriptions.
TOOL_DESCRIPTIONS: dict[str, str] = {
    "flight_search": "Ищет авиапредложения и возвращает цены, сегменты, offerId и searchId. from_code/to_code — IATA, date — YYYY-MM-DD; adults/children/infants задают состав, only_bookable ограничивает предложения T-Bank, limit — размер выдачи. response_format=json возвращает структурированный результат; поиска брони и оплаты нет.",
    "search_iata_code": "Разрешает название города или аэропорта в IATA-коды. query — не менее 2 символов, limit ограничен 20; результат содержит code, name, city, country и type. Это read-only резолвер без бронирования и оплаты.",
    "flight_price_calendar": "Возвращает кэш минимальных цен по датам вылета. Коды IATA и типы from_kind/to_kind задают направление; диапазоны дат, обратные даты, длительность и фильтры ограничивают выборку. Это не живой тариф; пустой кэш не означает отсутствие рейсов.",
    "flight_price_forecast": "Читает сигнал изменения цены для уже выполненного flight_search. Передай search_id из ответа поиска; новый поиск не запускается, сигнал не гарантирует изменение тарифа. Метод read-only и не бронирует билет.",
    "flight_schedule": "Возвращает расписание выполняемых рейсов по IATA-направлению. date необязателен и сужает расписание до дня; minPrice — ориентир, не гарантия тарифа. limit ограничивает число рейсов, response_format=json возвращает структуру.",
    "geodata_by_code": "Проверяет IATA-коды и возвращает названия, координаты, country/city codes и timezone. codes — один код или список, limit ограничивает записи; неизвестный код даёт ошибку. Метод только читает справочник.",
    "flight_checkout_url": "Строит ссылку T-Bank на выбранный маршрут по фактическим кодам, датам и номерам сегментов. request содержит adults и directions с fromCode/toCode/date/flights; URL — только передача управления, бронь и оплата не создаются.",
    "compare_flight_prices": "Сравнивает живые авиапредложения максимум по 7 датам и возвращает варианты и дельты цен. dates — YYYY-MM-DD; max_stops, max_duration_minutes, baggage_required, refundable_required, sort_by и limit ограничивают результат. Неполные даты и lowest observed помечаются в warnings.",
    "train_stations": "Разрешает название города или станции в числовой searchCode для train_search. search_text — произвольный запрос, limit ограничивает подсказки; response_format=json возвращает stations и warnings. Бронирование не выполняется.",
    "train_search": "Ищет поезда по числовым кодам origin/destination и дате. date — YYYY-MM-DD, adults/children задают пассажиров, limit — 0 или до 100; результат содержит расписание, минимальные цены и места. MCP не бронирует и не оплачивает.",
    "train_calendar": "Возвращает доступные даты продажи по паре числовых searchCode станций. origin и destination обязательны, limit ограничивает выдачу; пустой результат не доказывает причину отсутствия данных. Метод read-only.",
    "compare_train_prices": "Сравнивает поезда по 1–5 датам и возвращает группы, тарифы и дельты. origin/destination — searchCode из train_stations; limit и max_duration_minutes фильтруют выдачу. Неполные даты и lowest observed отражаются в warnings.",
    "hotel_autocomplete": "Находит локации и отели с id для следующих hotel-вызовов. query должен содержать не менее 3 символов, limit ограничивает подсказки; для hotel_search используй id локации. Бронь и оплата не выполняются.",
    "hotel_search": "Ищет доступные отели и предварительные цены на даты. destination_id берётся из autocomplete, даты — YYYY-MM-DD, adults 1–6, limit 1–50; children_ages принимает CSV или JSON-массив. В JSON выдаётся не более 3 фото-ссылок на ответ; нефинальные цены и неполная выдача отмечаются; MCP не бронирует.",
    "hotel_search_filters": "Возвращает доступные фильтры и filteredHotelsCount для локации, дат и состава гостей. filters — объекты filterId/value, limit отсутствует; метод не возвращает карточки, после него вызови hotel_search. Только чтение.",
    "hotel_latest_offers": "Перепроверяет цены и условия shortlist отелей одним запросом. hotel_ids — 1–1000 id, даты и adults должны совпадать с поиском; filters ограничивают запрос. Фото-ссылки в ответе ограничены тремя; при price.isFinalPrice=false питание, оплату, отмену и наличие не считай подтверждёнными.",
    "hotel_details": "Возвращает статическую карточку отеля: адрес, описание, часы, удобства и до 3 HTTPS-фото из источника. hotel_id — числовой id, max_images — 0–3; response_format=json даёт структурированные поля для страницы. Наличие тарифа и бронь не проверяются.",
    "hotel_rates": "Возвращает комнаты и актуальные тарифы выбранного отеля с bookHash, ценой, питанием, оплатой и отменой. hotel_id и даты обязательны, проживание 1–30 ночей, adults 1–6, limit 1–100; filters берутся из hotel_filters. В compact JSON возвращается до трёх HTTPS-фото для каждого типа комнаты. Запрос read-only.",
    "hotel_checkout_url": "Строит hand-off ссылку T-Bank для тарифа из hotel_rates(). Можно вызвать сразу после поиска тарифов; передай book_hash без изменений, совпадающие hotel_id/даты/guests. rate_confirmed оставлен для совместимости и не является обязательным финальным подтверждением; ссылка не создаёт бронь и не списывает деньги.",
    "hotel_reviews": "Возвращает страницу отзывов одного отеля с сортировкой и cursor-пагинацией. hotel_id обязателен, page_size 1–50; cursor следующей страницы передавай без изменений, search_text поддерживает фильтр onlyPhotos. Фото-ссылки для этого отеля ограничены тремя; отзывы не подтверждают условия тарифа.",
    "hotel_filters": "Возвращает общий каталог фильтров для UI и hotel_rates. max_chars ограничивает текст, 0 возвращает весь ответ; доступность на конкретные даты этот метод не проверяет.",
    "compare_hotel_prices": "Сравнивает отели по 1–7 окнам проживания и возвращает цены, группы и дельты. windows задают даты, destination_id — локацию, фильтры и limit ограничивают результат. На каждое окно выполняется один bounded search; неполные данные отмечаются, автоматических повторов нет.",
    "compare_flight_hotel_prices": "Сравнивает два перелёта и отель по 1–3 окнам и возвращает bundleTotal с дельтами. Сумма включает только outbound, return и отель; фильтры и budget_rub ограничивают варианты. Дополнительные расходы поездки в сумму не входят.",
    "weather": "Возвращает forecast или climate по координатам и диапазону дат. city — подпись, latitude/longitude — координаты, date_from/date_to — YYYY-MM-DD с диапазоном до 30 дней; kind в результате различает прогноз и ERA5-оценку. Частичный ответ сопровождается warnings.",
    "trip_personalization_profile": "Считает агрегированные бюджетные ориентиры и предпочтения поездки без сырых операций. Вход задаёт транспорт, ночи, период и явные бюджеты; актуальные цены можно передать как fallback. Ответ содержит агрегаты и warnings, а не банковские записи.",
    "restaurant_search": "Ищет рестораны в публичной выдаче Яндекс.Карт рядом с координатами или адресом. Возвращает report-ready карточки с рейтингом, числом отзывов, фото, часами и sourceUrl; банковская сессия не используется.",
    "get_trip_report": "Валидирует готовый request trip-page/v2 или hotel-page/v1 и возвращает html или markdown по output_mode. До вызова для каждого финального отеля обязательны hotel_latest_offers, hotel_details, hotel_rates и hotel_reviews; передай facilities, тарифные условия, reviewCount и reviewDigest. Пропущенный enrichment становится явным warning/advice. События получи прямым afisha_catalog и передай в request.events. Для пустого venues report автоматически ищет рестораны Яндекс.Карт вокруг выбранного отеля; файлов, бронирования и оплаты нет.",
    "list_instructions": "Возвращает каталог travel-only инструкций, если клиент не показывает resources. Результат содержит доступные slug и порядок чтения; банковские и отключённые вертикали в каталог не входят.",
    "read_instruction": "Возвращает один travel-only документ по slug из list_instructions. Передай server, index или slug из каталога; неизвестный slug возвращает ошибку и каталог. Внешних действий нет.",
    "get_travel_prompt": "Возвращает параметризованный prompt для поиска транспорта, отелей и страницы поездки. city/date_from/date_to обязательны, adults 1–6, output_mode — html или chat; prompt только инструктирует агента и ничего не бронирует.",
}

TOOL_KINDS: dict[str, tuple[str, str]] = {
    name: (name.replace("_", " "), READ) for name in ACTIVE_TOOL_NAMES
}
TOOL_KINDS.update({
    "flight_search": ("Поиск авиабилетов", READ),
    "search_iata_code": ("Резолвер IATA-кодов", READ),
    "flight_price_calendar": ("Календарь цен", READ),
    "flight_price_forecast": ("Прогноз цены", READ),
    "flight_schedule": ("Расписание рейсов", READ),
    "geodata_by_code": ("Геоданные по IATA-коду", READ),
    "flight_checkout_url": ("Ссылка на маршрут", READ),
    "train_stations": ("Резолвер ЖД-станций", READ),
    "train_search": ("Поиск поездов", READ),
    "train_calendar": ("Календарь ЖД", READ),
    "hotel_autocomplete": ("Поиск направления или отеля", READ),
    "hotel_search": ("Поиск доступных отелей", READ),
    "hotel_search_filters": ("Доступные фильтры отелей", READ),
    "hotel_latest_offers": ("Актуальные предложения отелей", READ),
    "hotel_details": ("Карточка отеля", READ),
    "hotel_rates": ("Тарифы отеля", READ),
    "hotel_checkout_url": ("Ссылка на тариф отеля", READ),
    "hotel_reviews": ("Отзывы об отеле", READ),
    "hotel_filters": ("Каталог фильтров отелей", READ),
    "compare_flight_prices": ("Сравнение авиабилетов", READ),
    "compare_train_prices": ("Сравнение поездов", READ),
    "compare_hotel_prices": ("Сравнение отелей", READ),
    "compare_flight_hotel_prices": ("Сравнение перелёта и отеля", READ),
    "weather": ("Погода и климат", READ),
    "restaurant_search": ("Рестораны Яндекс.Карт", READ),
    "trip_personalization_profile": ("Агрегированный профиль поездки", READ),
    "get_trip_report": ("Готовый дайджест поездки", READ),
    "list_instructions": ("Каталог инструкций", READ),
    "read_instruction": ("Текст инструкции", READ),
    "get_travel_prompt": ("Prompt поездки", READ),
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
