"""Runtime instruction catalogue published by the MCP server.

The Markdown files remain canonical in the repository.  The npm prepack step
copies the root entrypoint, instruction map and skills under ``docs/`` in the
vendored Python project, so an installed server can expose the same catalogue
without access to the original checkout.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


INSTRUCTION_INDEX_URI = "travel-nova://instructions/index"
INSTRUCTION_URI_PREFIX = "travel-nova://instructions/"

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CHECKOUT_ROOT = _PROJECT_ROOT.parent
_PACKAGED_DOCS_ROOT = Path(
    os.environ.get("TBANK_INSTRUCTION_ROOT", str(_PROJECT_ROOT / "docs"))
).resolve()


@dataclass(frozen=True)
class InstructionDocument:
    slug: str
    title: str
    description: str
    checkout_path: Path
    packaged_path: Path

    @property
    def uri(self) -> str:
        return f"{INSTRUCTION_URI_PREFIX}{self.slug}"

    def read(self) -> str:
        for path in (self.checkout_path, self.packaged_path):
            if path.is_file():
                return path.read_text(encoding="utf-8")
        raise FileNotFoundError(
            f"Instruction document {self.slug!r} was not packaged; checked "
            f"{self.checkout_path} and {self.packaged_path}"
        )


def _root_document(
    slug: str,
    filename: str,
    title: str,
    description: str,
) -> InstructionDocument:
    return InstructionDocument(
        slug=slug,
        title=title,
        description=description,
        checkout_path=_CHECKOUT_ROOT / filename,
        packaged_path=_PACKAGED_DOCS_ROOT / Path(filename).name,
    )


def _mcp_document(
    slug: str,
    filename: str,
    title: str,
    description: str,
) -> InstructionDocument:
    return InstructionDocument(
        slug=slug,
        title=title,
        description=description,
        checkout_path=_PROJECT_ROOT / "docs" / filename,
        packaged_path=_PACKAGED_DOCS_ROOT / filename,
    )


def _skill_document(
    slug: str,
    skill_name: str,
    title: str,
    description: str,
) -> InstructionDocument:
    relative_path = Path(skill_name) / "SKILL.md"
    return InstructionDocument(
        slug=slug,
        title=title,
        description=description,
        checkout_path=_PROJECT_ROOT / "skills" / relative_path,
        packaged_path=_PACKAGED_DOCS_ROOT / "skills" / relative_path,
    )


_DOCUMENTS = (
    _root_document(
        "agents",
        "AGENTS.md",
        "Travel Nova: корневая инструкция",
        "Общие правила репозитория и обязательная маршрутизация.",
    ),
    _root_document(
        "agent-rules",
        "docs/AGENT_RULES.md",
        "Карта агентских инструкций",
        "Приоритеты, канонические источники и выбор нужного "
        "документа.",
    ),
    _skill_document(
        "tbank-router",
        "tbank",
        "T-Bank MCP: router-skill",
        "Короткая предметная входная точка и общие правила "
        "безопасности.",
    ),
    _mcp_document(
        "mcp-distribution",
        "MCP_DISTRIBUTION.md",
        "T-Bank MCP: единый сервер и дистрибуция",
        "Общая поверхность инструментов, способы установки и renderer.",
    ),
    _mcp_document(
        "trip-generation",
        "TRIP_GENERATION.md",
        "Генерация страницы поездки",
        "Обязательный flow поиска и создания TripPageDocumentV1.",
    ),
    _skill_document(
        "tbank-travel-search",
        "tbank-travel-search",
        "Поиск транспорта и составной поездки",
        "Авиа, ЖД, отели в составе поездки, погода и места — "
        "без оформления.",
    ),
    _skill_document(
        "tbank-hotel-search",
        "tbank-hotel-search",
        "Самостоятельный поиск отелей",
        "Отдельный hotel-flow с актуальными тарифами и фотографиями.",
    ),
    _mcp_document(
        "flows",
        "FLOWS.md",
        "Operational flows T-Bank MCP",
        "Точные последовательности вызовов по предметным "
        "сценариям.",
    ),
    _skill_document(
        "tbank-grocery-order",
        "tbank-grocery-order",
        "Заказ продуктов",
        "Поиск товаров, корзина, подтверждение и оформление.",
    ),
    _skill_document(
        "tbank-tickets",
        "tbank-tickets",
        "Билеты и Афиша",
        "Кино, концерты, места, бронирование и оплата.",
    ),
    _skill_document(
        "tbank-transfer-money",
        "tbank-transfer-money",
        "Переводы",
        "Переводы людям, по СБП, реквизитам и QR.",
    ),
    _skill_document(
        "tbank-bill-pay",
        "tbank-bill-pay",
        "Оплата счетов",
        "ЖКХ, налоги, штрафы, связь и другие провайдеры.",
    ),
    _skill_document(
        "tbank-budget-analyzer",
        "tbank-budget-analyzer",
        "Анализ бюджета",
        "Траты, подписки и агрегированные рекомендации.",
    ),
    _skill_document(
        "tbank-invest-advisor",
        "tbank-invest-advisor",
        "Инвестиционный портфель",
        "Позиции, доходность и безопасный анализ портфеля.",
    ),
    _skill_document(
        "tbank-cards-documents",
        "tbank-cards-documents",
        "Карты и документы",
        "Карты, лимиты, реквизиты и документы клиента.",
    ),
    _skill_document(
        "tbank-messenger",
        "tbank-messenger",
        "Чаты и поддержка",
        "Чтение чатов и отправка сообщений.",
    ),
    _skill_document(
        "tbank-login",
        "tbank-login",
        "Вход и сессия",
        "Авторизация и восстановление банковской сессии.",
    ),
)


def instruction_documents() -> tuple[InstructionDocument, ...]:
    """Return the stable, ordered catalogue for the single MCP surface."""
    return _DOCUMENTS


def instruction_index() -> str:
    """Build the short MCP-native entrypoint with resource URIs."""
    documents = instruction_documents()
    lines = [
        "# Travel Nova: входная точка инструкций",
        "",
        "Эти документы поставляются вместе с MCP и не зависят "
        "от текущей рабочей папки.",
        "Читай их через MCP `resources/read` по URI ниже.",
        "",
        "## Порядок чтения",
        "",
        f"1. `{INSTRUCTION_URI_PREFIX}agents` — общие правила.",
        f"2. `{INSTRUCTION_URI_PREFIX}agent-rules` — выбери область задачи.",
        f"3. `{INSTRUCTION_URI_PREFIX}tbank-router` — выбери один узкий skill.",
        "4. Прочитай ровно один подходящий task-specific skill из каталога ниже.",
        "5. Для составной поездки и HTML + JSON дополнительно прочитай "
        "`trip-generation` и `mcp-distribution`.",
        "",
        "Все банковские и travel-операции находятся в одном MCP. Инструменты, "
        "двигающие реальные деньги, вызывай только после подтверждения конкретной "
        "суммы и получателя или состава заказа.",
    ]
    lines.extend(
        [
            "",
            "Исполняемые схемы, валидаторы, сигнатуры и tool "
            "annotations имеют "
            "приоритет над описательным Markdown.",
            "Не загружай все документы без необходимости: выбери "
            "маршрут по задаче.",
            "",
            "## Доступные документы",
            "",
        ]
    )
    lines.extend(
        f"- `{document.uri}` — **{document.title}**. {document.description}"
        for document in documents
    )
    return "\n".join(lines) + "\n"


def server_instructions() -> str:
    """Return the compact initialize-result instructions for an MCP host."""
    return (
        "T-Bank MCP. Это единый сервер для банковских и travel-операций. "
        "Каноническая входная точка инструкций: "
        f"{INSTRUCTION_INDEX_URI}. До первого предметного вызова "
        "прочитай этот MCP resource, затем общие правила и только "
        "подходящие документы из указанного маршрута. Документы "
        "поставляются вместе с сервером; не рассчитывай на AGENTS.md "
        "в текущей папке. Не выдумывай цены, идентификаторы, "
        "расписания, возможности инструментов или результаты. "
        "Инструменты могут двигать реальные деньги: перед денежным вызовом "
        "обязательно получи подтверждение конкретной суммы и назначения. "
        "Для travel-задач не бронируй и не оплачивай билеты, отели или события; "
        "checkout-ссылки только передают управление пользователю. "
        "Исполняемый контракт инструментов имеет приоритет "
        "над описательными примерами."
    )
