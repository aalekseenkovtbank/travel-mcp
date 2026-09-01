"""Safe public T-Bank links shared by travel tools and static renderers."""
from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlsplit


_SENSITIVE_QUERY_PARTS = ("session", "token")


def safe_tbank_url(value) -> str:
    """Return a public T-Bank HTTPS URL without credentials or session data."""
    url = str(value or "").strip()
    if not url:
        return ""
    try:
        parsed = urlsplit(url)
    except ValueError:
        return ""
    host = str(parsed.hostname or "").lower()
    if (parsed.scheme.lower() != "https" or not host
            or not (host == "tbank.ru" or host.endswith(".tbank.ru"))
            or parsed.username or parsed.password):
        return ""
    for parameters in (parsed.query, parsed.fragment):
        for key, _ in parse_qsl(parameters, keep_blank_values=True):
            normalized = re.sub(r"[^a-z0-9]", "", key.lower())
            if (any(part in normalized for part in _SENSITIVE_QUERY_PARTS)
                    or normalized.startswith("sso")):
                return ""
    return url


def hotel_details_url(hotel_id) -> str:
    value = str(hotel_id or "").strip()
    if not re.fullmatch(r"[1-9][0-9]*", value):
        return ""
    return safe_tbank_url(
        f"https://www.tbank.ru/travel/hotels/new/hotels/{value}")


_AFISHA_WEB_CITY_SLUGS = {
    "москва": "moscow", "санкт-петербург": "saint-petersburg",
    "казань": "kazan", "калининград": "kaliningrad", "сочи": "sochi",
    "нижний новгород": "nizhny-novgorod", "екатеринбург": "yekaterinburg",
    "мурманск": "murmansk", "иркутск": "irkutsk", "владивосток": "vladivostok",
    "новосибирск": "novosibirsk", "красноярск": "krasnoyarsk", "самара": "samara",
    "уфа": "ufa", "волгоград": "volgograd", "пермь": "perm",
    "тюмень": "tyumen", "махачкала": "makhachkala",
    "минеральные воды": "mineralnye-vody", "архангельск": "arkhangelsk",
}
_AFISHA_WEB_SECTIONS = {
    "movie": "cinema", "кино": "cinema", "cinema": "cinema",
    "concert": "concerts", "концерт": "concerts",
    "spectacle": "theatres", "театр": "theatres", "theatre": "theatres",
    "exhibition": "exhibitions", "выставка": "exhibitions",
}


def afisha_event_url(city: str, kind: str, event_slug: str) -> str:
    city_key = " ".join(str(city or "").lower().replace("ё", "е").split())
    city_slug = _AFISHA_WEB_CITY_SLUGS.get(city_key, "")
    section = _AFISHA_WEB_SECTIONS.get(str(kind or "").lower(), "")
    slug = str(event_slug or "").strip().strip("/")
    if (not city_slug or not section
            or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug)):
        return ""
    return safe_tbank_url(
        f"https://www.tbank.ru/gorod/afisha/{city_slug}/{section}/{slug}/")
