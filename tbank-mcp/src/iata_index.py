"""Bank-native IATA index for ``search_iata_code``.

Data source: the bank's own airports dictionary, reduced to public fields
(``src/assets/iata_airports.json``: 5k+ active airports with Russian/English
names and a derived integer ``group`` that encodes only which airports share a
city). A small supplement adds multi-airport *city* codes (MOW) that the
airport-level dictionary does not carry.

The module never invents identifiers at runtime: it only ranks candidates;
``search_iata_code`` validates every suggested code against the bank's live
``geodata_by_code`` directory and drops unconfirmed codes with a warning.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

_ASSETS = Path(__file__).resolve().parent / "assets"
_WHITESPACE = re.compile(r"[\s\-_]+")


@dataclass(frozen=True)
class IataEntry:
    ru: str
    en: str
    airports: tuple[str, ...]
    city: str = ""            # multi-airport city code, when one exists
    alt: tuple[str, ...] = field(default_factory=tuple)


def normalize(value: str) -> str:
    return _WHITESPACE.sub(" ", value.strip().lower().replace("ё", "е"))


def _load() -> tuple[dict, dict, dict]:
    """(airports, city_groups, supplement) from the shipped assets."""
    airports: dict[str, dict] = json.loads(
        (_ASSETS / "iata_airports.json").read_text(encoding="utf-8"))
    city_groups: dict[str, list[str]] = {}
    for code, item in airports.items():
        city_groups.setdefault(str(item.get("group")), []).append(code)
    # Some dictionary groups are shared defaults grouping unrelated airports;
    # only real multi-airport cities (small groups) produce sibling listings.
    city_groups = {k: v for k, v in city_groups.items() if 1 < len(v) <= 6}
    supplement_path = _ASSETS / "iata_city_supplement.json"
    supplement = (json.loads(supplement_path.read_text(encoding="utf-8"))
                  if supplement_path.exists() else {})
    return airports, city_groups, supplement


_AIRPORTS, _CITY_GROUPS, _SUPPLEMENT = _load()


def _entry_for(code: str) -> IataEntry | None:
    item = _AIRPORTS.get(code)
    if not item:
        return None
    siblings = [c for c in _CITY_GROUPS.get(str(item.get("group")), []) if c != code]
    city = code if code in _SUPPLEMENT else ""
    return IataEntry(
        ru=str(item.get("ru") or ""),
        en=str(item.get("en") or ""),
        airports=tuple([code, *sorted(siblings)]),
        city=city,
    )


def _city_entry(city_code: str) -> IataEntry | None:
    spec = _SUPPLEMENT.get(city_code)
    if not spec:
        item = _AIRPORTS.get(city_code)
        if not item:
            return None
        return _entry_for(city_code)
    aliases: list[str] = list(spec.get("alt") or ())
    for code in spec.get("airports") or ():
        item = _AIRPORTS.get(code) or {}
        for key in ("ru", "en"):
            name = str(item.get(key) or "")
            if name and name not in (spec.get("ru"), spec.get("en")) and name not in aliases:
                aliases.append(name)
    return IataEntry(
        ru=str(spec.get("ru") or ""),
        en=str(spec.get("en") or ""),
        airports=tuple(spec.get("airports") or ()),
        city=city_code,
        alt=tuple(aliases),
    )


def _score(query: str, entry: IataEntry) -> int:
    best = 0
    for name in (entry.ru, entry.en, *entry.alt):
        normalized = normalize(name)
        if not normalized:
            continue
        if query == normalized:
            best = max(best, 100)
        elif normalized.startswith(query) or query.startswith(normalized):
            best = max(best, 80)
        elif query in normalized or normalized in query:
            best = max(best, 60)
    codes = [c.lower() for c in (*entry.airports, entry.city) if c]
    if query in codes:
        best = max(best, 95)
    return best


def lookup(query: str, limit: int = 10) -> list[IataEntry]:
    """Ranked matches: city supplement, airport names and IATA codes."""
    q = normalize(query)
    if len(q) < 2:
        return []
    entries: list[tuple[int, str, IataEntry]] = []
    seen: set[str] = set()
    for city_code in _SUPPLEMENT:
        entry = _city_entry(city_code)
        if entry is not None:
            entries.append((_score(q, entry), entry.ru, entry))
            seen.update(entry.airports)
            if entry.city:
                seen.add(entry.city)
    for code in _AIRPORTS:
        if code in seen or not code.isalpha() or len(code) != 3:
            continue
        entry = _entry_for(code)
        if entry is None:
            continue
        entries.append((_score(q, entry), entry.ru, entry))
    entries = [item for item in entries if item[0] > 0]
    entries.sort(key=lambda item: (-item[0], item[1]))
    return [entry for _, _, entry in entries[:limit]]


def codes_for(entry: IataEntry) -> list[str]:
    """Codes to validate for one entry: city code first, then airports."""
    ordered: list[str] = []
    for code in ([entry.city] if entry.city else []) + list(entry.airports):
        if code and code not in ordered:
            ordered.append(code)
    return ordered
