"""Safe public T-Bank links shared by travel tools and static renderers."""
from __future__ import annotations

import ipaddress
import re
from urllib.parse import parse_qsl, urlencode, urlsplit


_SENSITIVE_QUERY_PARTS = ("session", "token")


def _has_sensitive_query(url: str) -> bool:
    try:
        parsed = urlsplit(url)
    except ValueError:
        return True
    for parameters in (parsed.query, parsed.fragment):
        for key, _ in parse_qsl(parameters, keep_blank_values=True):
            normalized = re.sub(r"[^a-z0-9]", "", key.lower())
            if (any(part in normalized for part in _SENSITIVE_QUERY_PARTS)
                    or normalized.startswith("sso")):
                return True
    return False


def _is_non_public_host(host: str) -> bool:
    """True for loopback/private/link-local hosts a chat link should not use."""
    host = str(host or "").strip().lower()
    if host == "localhost" or host.endswith(".local") or host.endswith(".localhost"):
        return True
    try:
        ip = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return False
    return (ip.is_private or ip.is_loopback or ip.is_link_local
            or ip.is_reserved or ip.is_multicast or ip.is_unspecified)


def safe_public_https_url(value) -> str:
    """Return a public HTTPS URL without credentials or session data.

    Used for EVENT source links (Afisha may be unavailable and the match lives
    on an external sports site). Hotels and avia links stay T-Bank-only via
    safe_tbank_url. Checks: https, real host, no user:pass, no sensitive query
    keys (session/token/sso), no loopback/private/link-local hosts.
    """
    url = str(value or "").strip()
    if not url:
        return ""
    try:
        parsed = urlsplit(url)
    except ValueError:
        return ""
    host = str(parsed.hostname or "").lower()
    if (parsed.scheme.lower() != "https" or not host
            or parsed.username or parsed.password
            or _is_non_public_host(host)):
        return ""
    if _has_sensitive_query(url):
        return ""
    return url


def safe_tbank_url(value) -> str:
    """Return a public T-Bank HTTPS URL without credentials or session data."""
    url = safe_public_https_url(value)
    if not url:
        return ""
    host = str(urlsplit(url).hostname or "").lower()
    if not (host == "tbank.ru" or host.endswith(".tbank.ru")):
        return ""
    return url


def with_leading_tbank_url(row: dict, url=None) -> dict:
    """Put ``tbankUrl`` first so hosts copy it instead of burying it in JSON."""
    rest = {key: value for key, value in row.items() if key != "tbankUrl"}
    if url is None:
        url = row.get("tbankUrl")
    cleaned = safe_tbank_url(url) or None
    return {"tbankUrl": cleaned, **rest}


def hotel_details_url(hotel_id) -> str:
    value = str(hotel_id or "").strip()
    if not re.fullmatch(r"[1-9][0-9]*", value):
        return ""
    return safe_tbank_url(
        f"https://www.tbank.ru/travel/hotels/new/hotels/{value}")


def avia_checkout_url(offer_id) -> str:
    """T-Bank avia checkout link for one bookable offer (by its offerId).

    Confirmed shape: https://www.tbank.ru/travel/flights/checkout/?offerId=…
    Only used for bookable (vendor=Tinkoff) offers; a partner offer has no
    bank checkout. Empty when the id looks wrong — never guess.
    """
    value = str(offer_id or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9._:-]{6,128}", value):
        return ""
    return safe_tbank_url(
        "https://www.tbank.ru/travel/flights/checkout/?"
        + urlencode({"offerId": value}))


# ── Avia share deep link (no UTM) ────────────────────────────────────────────
# The web „share“ URL opens the flight search prefilled with the exact flights
# and dates of the found itinerary. It is NOT a per-offer purchase page and it
# does not carry a price or a booking; it hands the user to the booking flow.
# We assemble it ONLY from fields the source returned (search codes, per-segment
# date, marketing carrier code and flight number); nothing is guessed. UTM and
# internal_* parameters are deliberately not added.
#
# Real shape (direct flights):
#   https://www.tbank.ru/travel/flights/multi-way/OVB-MOW/10-13/MOW-OVB/11-11/
#     ?...&flights=10-13-S7-2502~11-11-S7-2505&...
# Real shape (transfer, e.g. OVB→KZN via SVO out, KZN→OVB ret):
#   https://www.tbank.ru/travel/flights/multi-way/OVB-KZN/10-13/KZN-OVB/11-11/
#     ?...&flights=10-13-S7-7001_10-14-N4-758~11-11-N4-759_11-11-S7-5344&...
# Path lists one city pair + departure date per DIRECTION (not per segment);
# flights lists per-direction groups joined by "~", segments inside a direction
# joined by "_", each segment as MM-DD-CARRIER-NUMBER (segments may span dates).

_AVIA_CITY_RE = re.compile(r"^[A-Z]{3}$")
_AVIA_CARRIER_RE = re.compile(r"^[A-Z0-9]{1,3}$")
_AVIA_FLIGHT_RE = re.compile(r"^[0-9]{1,5}[A-Z]?$", re.IGNORECASE)


def _avia_mmdd(date_value) -> str:
    """YYYY-MM-DD → the MM-DD the web share URL uses; empty when unparsable."""
    text = str(date_value or "").strip()
    match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", text)
    if not match:
        return ""
    year, month, day = (int(part) for part in match.groups())
    if not (2000 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31):
        return ""
    return f"{month:02d}-{day:02d}"


def _avia_segment_mmdd(segment) -> str:
    """Direction segment date: own date if present, else its empty string."""
    if isinstance(segment, dict) and segment.get("date"):
        return _avia_mmdd(segment.get("date"))
    return ""


def avia_share_url(legs, *, adults: int = 1, cabin: str = "Y",
                   baggage: int = 0) -> str:
    """Build a T-Bank avia share URL from source-verified flight directions.

    ``legs``: chronological list of direction dicts, each with:
      - origin / destination: 3-letter search codes of the DIRECTION pair
        (e.g. OVB → KZN), not per-segment airports;
      - date: YYYY-MM-DD departure date of the direction;
      - segments: list of real flight segments within that direction, each
        {date (YYYY-MM-DD, may differ from the direction date), carrier, flight}.
        When segments is empty, a single segment is derived from the direction's
        own ``carrier``/``flight``/``date``.

    Returns "" when anything is missing or malformed — callers must show
    «Ссылка T-Bank недоступна» then.
    """
    try:
        adults = int(adults)
    except (TypeError, ValueError):
        return ""
    if not 1 <= adults <= 9:
        return ""
    cabin = str(cabin or "Y").strip().upper()[:1] or "Y"
    route_parts: list[str] = []
    direction_groups: list[str] = []
    for leg in legs or []:
        origin = str(leg.get("origin") or "").strip().upper()
        destination = str(leg.get("destination") or "").strip().upper()
        mmdd = _avia_mmdd(leg.get("date"))
        if not (re.fullmatch(_AVIA_CITY_RE.pattern, origin)
                and re.fullmatch(_AVIA_CITY_RE.pattern, destination)
                and mmdd):
            return ""
        segments = leg.get("segments") or []
        if not segments:
            carrier = str(leg.get("carrier") or "").strip().upper()
            flight = str(leg.get("flight") or "").strip().upper()
            if not (re.fullmatch(_AVIA_CARRIER_RE.pattern, carrier)
                    and re.fullmatch(_AVIA_FLIGHT_RE.pattern, flight)):
                return ""
            segments = [{"date": leg.get("date"),
                         "carrier": carrier, "flight": flight}]
        flight_parts: list[str] = []
        for segment in segments:
            seg_date = _avia_segment_mmdd(segment)
            carrier = str(segment.get("carrier") or "").strip().upper()
            flight = str(segment.get("flight") or "").strip().upper()
            if not (seg_date
                    and re.fullmatch(_AVIA_CARRIER_RE.pattern, carrier)
                    and re.fullmatch(_AVIA_FLIGHT_RE.pattern, flight)):
                return ""
            flight_parts.append(f"{seg_date}-{carrier}-{flight}")
        route_parts.append(f"{origin}-{destination}/{mmdd}")
        direction_groups.append("_".join(flight_parts))
    if not route_parts:
        return ""
    query = urlencode({
        "children": 0,
        "source": "share",
        "infants": 0,
        "cabin": cabin,
        "flights": "~".join(direction_groups),
        "adults": adults,
        "baggage": baggage,
        "composite": 0,
    })
    return safe_tbank_url(
        "https://www.tbank.ru/travel/flights/multi-way/"
        + "/".join(route_parts) + "/?" + query)


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
