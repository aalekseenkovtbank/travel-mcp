"""T-Bank mobile API client — self-bootstrapping, fully headless after login.

login(phone) + confirm_otp(otp) do a real SSO login (no capture needed): they
mint the mobile sessionid + access_token + refresh_token and capture the
long-lived SSO_SESSION cookie. silent_relogin() re-mints the session from
SSO_SESSION + a built-in device fingerprint (no OTP) ~every 2h, producing a
session valid for BOTH reads and the messenger tmsg.

Reads use builtin endpoint shapes (endpoints.py — static API params, no
device/session/account secrets) + the live session. `pay`/`group_pay` are
HMAC-SHA256 `x-api-signature` (key = sessionid). api/id/*.t-bank-app.ru serve a
cert by the Russian Trusted Root CA, which no OS trust store ships; tls.py builds
ca/bundle.pem from the system store plus that root, shipped in ca/roots/ and pinned
by SHA-256. Certificates are never taken from the network.
"""
from __future__ import annotations

import base64
import binascii
import decimal
import hashlib
import hmac
import json
import os
import re
import threading
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import requests

from .endpoints import BUILTIN_ENDPOINTS, VERTICALS, VERTICAL_ALIASES, APP_VERSION
from .observability import _redact_value

MOBILE_BASE = "https://api.t-bank-app.ru"
ID_BASE = "https://id.t-bank-app.ru"
# Canonical OAuth2 token endpoint for the refresh grant. Used as the dataclass
# default AND normalized again in __post_init__, so a legacy session.json that
# stored an explicit empty "" token_url (the old default) can never make
# refresh() POST to "" (the original MissingSchema('') crash).
DEFAULT_TOKEN_URL = f"{ID_BASE}/auth/token/mobile"
# workflowType the bank puts on a get_requisites candidate that is the recipient's
# own T-Bank account rather than an SBP route to another bank. Such a candidate has
# no bankMemberId — there is no member to route to.
TBANK_INNER_WORKFLOW = "TinkoffInner"
# SBP "pointer type" enum for a phone-number pointer. Verified CONSTANT across all
# phone/SBP transfers in captures.xml (6 different recipients, different bankMemberId,
# always pointerType="8276") — it is NOT the recipient's bank code (that's bankMemberId),
# so it's a fixed protocol constant, analogous to currencyCode "643" for RUB.
# Serialises every path that re-mints the session.
#
# grocery_checkout is the only async tool and it offloads its body to a worker
# thread (asyncio.to_thread), which leaves FastMCP's event loop free to run any
# other sync tool — against the SAME global MobileSession. Two threads entering
# ensure_fresh together each POST the refresh_token; the grant rotates it, so the
# second gets invalid_grant, falls through to silent_relogin (authorize → step →
# token, plus a propagation wait) and both then write their own access_token,
# sessionid and rotated refresh_token over each other. What lands on disk is a mix.
#
# Module-level rather than per-instance because there is exactly one session per
# server process, and because a per-instance lock has to be created somewhere —
# and the tests build sessions without running __post_init__.
_MINT_LOCK = threading.RLock()

# Cookies EVERY bank host receives, and the only ones.
#
# The capture is unambiguous: across seventeen t-bank-app.ru hosts the app sends
# exactly these three, while SSO_SESSION, SSO_SESSION_STATE, SSO_CONVERSATION_CSRF_*
# and sso_uaid appear on id.t-bank-app.ru and nowhere else. SSO_SESSION is the
# host-only, HttpOnly credential that mints a session WITHOUT an SMS — the whole
# point of silent_relogin — and it was going to every host we talk to, because
# cookie_str was assigned the entire login jar.
_WIDE_COOKIES = ("__P__wuid", "api_sso_id", "sso_used")


def wide_cookies(cookie_str: str) -> str:
    """Keep only the cookies every host is supposed to get, in their given order."""
    out = []
    for part in (cookie_str or "").split(";"):
        part = part.strip()
        if part.split("=", 1)[0].strip() in _WIDE_COOKIES:
            out.append(part)
    return "; ".join(out)


def selected_cookies(cookie_str: str, names: tuple[str, ...]) -> str:
    """Return only explicitly allowed cookies, preserving allowlist order."""
    values = {}
    for part in (cookie_str or "").split(";"):
        key, sep, value = part.strip().partition("=")
        if sep and key in names and key not in values:
            values[key] = value
    return "; ".join(f"{name}={values[name]}" for name in names if name in values)


SBP_PHONE_POINTER_TYPE = "8276"


def _need_store(app_id: str, point_id: str) -> tuple[str, str]:
    """Client-layer guard mirroring server._store(): grocery store-scope methods
    require explicit app_id/point_id — no silent 578/700 default."""
    if not app_id or not point_id:
        raise TbankApiError("NO_STORE_CONTEXT",
            "app_id/point_id required (from grocery_stores()) — no silent default store.")
    return app_id, point_id
_CA_BUNDLE = os.environ.get(
    "TBANK_CA_BUNDLE",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ca", "bundle.pem"),
)
if not os.path.exists(_CA_BUNDLE):
    _CA_BUNDLE = None


def _builtin_fingerprint(device_id: str) -> str:
    """A static, generic iOS device-attributes blob used as the anti-fraud
    fingerprint at auth/step (and at refresh). It is device attributes only
    (timezone, screen, OS version, the device id) — not a secret, not a
    challenge-response. A real device produces a similar blob; a plausible
    generic one is accepted for scoring."""
    import uuid as _uuid
    blob = {
        "identifierForVendor": device_id,
        "tDeviceId": device_id,
        "mobileDeviceOs": "iOS",
        "systemVersion": "17.5.1",
        "appVersion": APP_VERSION,
        "bundleId": "com.idamob.tinkoff.android",
        "timeZoneName": "Europe/Moscow",
        "language": "ru",
        "root_flag": "false",
        "jailbreak": "false",
        "emulator": 0,
        "debug": 0,
        "lockedDevice": 1,
        "autologinUsed": False,
        "screenWidth": 390,
        "screenHeight": 844,
        "screenResolution": "1170*2532",
        "screenDpi": 3,
        "systemFontSize": 17,
        "labelFontSize": 17,
        "frontCameraAvailable": True,
        "backCameraAvailable": True,
        "userAgent": "iPhone/iOS(17.5.1)/TCSMB",
        "deviceModel": "iPhone",
        "vendor": "t_ios",
        "platform": "ios",
        "randomId": _uuid.uuid4().hex,
    }
    return json.dumps(blob, ensure_ascii=False, separators=(",", ":"))


class TbankApiError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.result_code = code
        self.message = message


class SessionExpired(TbankApiError):
    """refresh_token / session no longer valid -> re-login (login+confirm_otp)."""


class UnreadableResponse(TbankApiError, requests.exceptions.RequestException):
    """The server answered and the answer could not be read.

    Deliberately BOTH a TbankApiError and a RequestException, because on the money
    path those two mean opposite things. The money tools classify a TbankApiError as
    «the bank answered with an error envelope, so nothing moved» and a
    RequestException as «the request may have arrived, the outcome is unknown».

    A body we cannot parse is the second kind, even on HTTP 200 — a proxy or WAF
    interstitial means something processed the request; what it did is exactly what
    we cannot see. Raising a plain TbankApiError here told the user their money was
    safe on the one occasion nobody can know that."""


class PaymentConfirmationRequired(TbankApiError):
    """The bank ACCEPTED a /v1/pay request but is holding it for a second factor
    (resultCode WAITING_CONFIRMATION): an SMS OTP, a push approval or an in-app
    approval. This is neither a refusal nor a completed payment — it is a resumable
    state, and treating it as a terminal `failed` is the bug this class fixes.

    Money has NOT moved yet, but a pending payment now EXISTS on the backend keyed by
    its ``userPaymentId``. A fresh /v1/pay with a NEW userPaymentId would create a
    SECOND pending payment; the same id must be carried into the confirmation instead.
    So this reads as blocking, not as safe-to-retry.

    A plain TbankApiError keeps only (code, message); _unwrap() would raise one and
    let the rest of the envelope fall on the floor. The WAITING_CONFIRMATION envelope
    (capture-verified) carries, at the TOP level, everything /v1/confirm needs to
    continue:

        {"resultCode":"WAITING_CONFIRMATION",
         "operationTicket":"<uuid>",          # -> initialOperationTicket on /v1/confirm
         "initialOperation":"pay",            # -> initialOperation on /v1/confirm
         "confirmations":["SMSBYID"],         # -> confirmationType on /v1/confirm
         "confirmationData":{"SMSBYID":{"codeLength":4,"paymentId":"<id>",...}}}

    All of it is preserved here. ``payload`` is already redacted at construction. The
    OTP is deliberately NOT a field: it is entered later, by the user, into
    confirm_payment(), rides the wire as ``secretValue`` (a 'secret'-keyed field the
    redactor scrubs) and is never logged."""

    def __init__(self, code: str, message: str, *, http_status=None, payload=None,
                 operation_ticket: str = "", initial_operation: str = "pay",
                 confirmation_type: str = "", confirmations=None,
                 code_length: int = 0, payment_id: str = "",
                 user_payment_id: str = "", request_id: str = "",
                 method: str = "POST", url: str = ""):
        super().__init__(code, message)
        self.http_status = http_status
        self.payload = payload if isinstance(payload, dict) else {}
        self.operation_ticket = str(operation_ticket or "")
        self.initial_operation = str(initial_operation or "pay")
        # The LITERAL type the bank wants echoed back (e.g. "SMSBYID"), not a friendly
        # label — /v1/confirm rejects a normalised value.
        self.confirmation_type = str(confirmation_type or "")
        self.confirmations = [str(c) for c in (confirmations
                              or ([confirmation_type] if confirmation_type else []))]
        self.code_length = int(code_length or 0)
        # The bank's own paymentId, embedded in the challenge — the same id the confirm
        # returns, so it is known even before the code is entered (for reconciliation).
        self.payment_id = str(payment_id or "")
        self.user_payment_id = str(user_payment_id or "")
        self.request_id = str(request_id or "")
        self.method = method
        self.url = url


# Result codes that mean "accepted, pending a second factor" — a continuation, not a
# failure. WAITING_CONFIRMATION is the capture-verified money-path code. The others
# are defensive spellings of the same state; none has been seen in a capture, so none
# drives a request shape — they only route a response into the pending branch instead
# of the terminal-failure branch.
_PAYMENT_CONFIRMATION_CODES = {
    "WAITING_CONFIRMATION", "CONFIRMATION_NEEDED", "CONFIRMATION_REQUIRED",
    "NEED_CONFIRMATION", "NEED_CONFIRM",
}


# query/header keys that carry live secrets — substituted fresh at call time.
_LIVE_QUERY = {"sessionid", "wuid"}
_LIVE_HEADERS = {"authorization", "cookie"}


def delivery_eta(nearest: dict | None, now=None) -> tuple[float | None, str]:
    """A store's nearest delivery slot as (minutes_until_it_lands, human_label).

    `nearestTime` comes in two shapes and they are NOT interchangeable — in the
    capture 55 of 80 retailers use one and 25 the other:

      type=Relative — `from`/`to` are MINUTES as strings, and `from` is often ""
        ("Самокат: to=15" means within 15 minutes).
      type=Absolute — `from`/`to` are ISO-8601 TIMESTAMPS of a booked slot
        ("METRO: 2026-07-22T08:00 → 11:00", i.e. tomorrow morning).

    The old code formatted both as f"{from}-{to} min", which turned the majority
    shape into "2026-07-22T08:00:00+03:00-2026-07-22T11:00:00+03:00 min" — an
    absolute date range labelled as minutes. Nothing caught it because
    grocery_stores() never printed the field.

    Minutes are measured to the END of the window: that is the "you will have it by"
    number, and it is the only figure comparable across both shapes. A store with no
    slot, or whose window has already passed (stale data), returns None — which sorts
    LAST in both directions, the same rule the nutrition ranking uses. Unknown is not
    zero, and a stale slot must never win "fastest"."""
    import datetime as _dt

    nearest = nearest or {}
    kind = str(nearest.get("type") or "")
    raw_from, raw_to = nearest.get("from"), nearest.get("to")
    if not raw_to:
        return None, ""

    if kind == "Absolute":
        try:
            end = _dt.datetime.fromisoformat(str(raw_to))
            start = _dt.datetime.fromisoformat(str(raw_from)) if raw_from else None
        except ValueError:
            return None, ""
        ref = (now if isinstance(now, _dt.datetime)
               else _dt.datetime.fromtimestamp(now if now is not None else time.time(),
                                               tz=end.tzinfo or _dt.timezone.utc))
        if end.tzinfo is None:
            end = end.replace(tzinfo=ref.tzinfo)
        if start is not None and start.tzinfo is None:
            start = start.replace(tzinfo=ref.tzinfo)
        ref = ref.astimezone(end.tzinfo)
        days = (end.date() - ref.date()).days
        day = {0: "сегодня", 1: "завтра"}.get(days) or end.strftime("%d.%m")
        span = (f"{start:%H:%M}–{end:%H:%M}" if start else f"до {end:%H:%M}")
        label = f"{day} {span}"
        minutes = (end - ref).total_seconds() / 60.0
        return (minutes if minutes > 0 else None), label

    # Relative (and anything else that carries plain numbers)
    try:
        to_min = float(str(raw_to).strip())
    except ValueError:
        return None, ""
    try:
        from_min = float(str(raw_from).strip()) if str(raw_from or "").strip() else None
    except ValueError:
        from_min = None
    label = (f"{from_min:g}–{to_min:g} мин" if from_min is not None
             else f"до {to_min:g} мин")
    return to_min, label

# iOS device OS version used in the mobile User-Agent, format
# `iPhone/iOS(<ver>)/TCSMB/<appVersion>(<build>)`. Build is derived from
# app_version, e.g. 7.31.6 -> 7*1_000_000 + 31*10_000 + 6*1_000 = 7316000.
#
# Read straight off the wire: 812 captured requests to the bank's hosts carry
# `iPhone/iOS(26.5.2)/TCSMB/7.31.6(7316000)` and none carry any other version, and
# the same string appears 27 times inside request BODIES. It used to say 17.5.1,
# copied from FINGERPRINT["systemVersion"] below — so every call announced a device
# OS the app never announces.
#
# FINGERPRINT is deliberately NOT changed to match. It is sent once, at login, the
# current value demonstrably works, and nothing in any capture shows what the server
# does with it — so there is evidence for this constant and none for that one.
_IOS_VERSION = "26.5.2"

# /v1/confirm carries the device geo in its anti-fraud block. It is a fraud SIGNAL,
# not a validated field (the captures show it varying — Moscow on one, Petersburg on
# another), and this session has no stored location, so a stable neutral default
# (Moscow centre) is sent; TBANK_GEO_LAT/LON override it.
_CONFIRM_GEO = (os.environ.get("TBANK_GEO_LAT", "55.751244"),
                os.environ.get("TBANK_GEO_LON", "37.618423"))

# Hosts where the real app sends X-App-Name/X-App-Version/X-Platform (capture-
# verified per-host header profile). ONLY these — everywhere else (the BFF
# api.t-bank-app.ru, lifestyle grocery, id, api-invest, ...) the app sends just
# x-lang. Injecting X-App-* on those hosts diverges from the app and BREAKS the
# grocery cart (lifestyle segments carts by client context → set "OK" but the
# goods land in a different bucket → cart reads empty). Keep this list capture-tight.
# Rollback switch for the query scoping below. TBANK_QUERY_PROFILE=legacy restores
# the previous behaviour byte-for-byte (wuid everywhere, vendor/client_version
# injected wherever the session has them) without touching session.json, so
# reverting needs no re-login.
_LEGACY_QUERY = os.environ.get("TBANK_QUERY_PROFILE", "").lower() == "legacy"


# The Accept the app really sends, per host class — capture-verified.
#
# `_NATIVE_ACCEPT` is not a choice the app made: it is the Apple URL-loading
# default that appears when no Accept is set, which is why it is identical across
# every native host (api, api-invest*, my-home, ms-loyalty, shortcuts, …). Where
# the app's own SDKs DO set one — the lifestyle Город/Афиша module, search, id —
# it is application/json. WKWebView-originated calls send */*.
#
# The code sent application/json to all of them. That works today, and the captures
# say why it is safe either way: of the 128 templates present in the captures with
# both sides recorded, every response is application/json regardless of what was
# asked for. The two exceptions are already handled by template-level headers
# (payment_receipt_pdf → application/pdf) or parse fine anyway (/v1/ping answers
# Content-Type: text/html with a JSON body, and _unwrap never looks at the header).
#
# So this is fidelity, not a bug fix — and the direction is toward a header ending
# in */*;q=0.8, a strict superset of application/json. It is OFF by default all the
# same: 63 templates live on the one host that changes, there is no staging
# environment, and the only endpoint whose Content-Type demonstrably moves is the
# free one (`keepalive`) — start the rollout there.
#
#   TBANK_ACCEPT_PROFILE unset | "json"  → today's behaviour, byte-for-byte
#                        "auto"          → the captured profile everywhere
#                        "host,host,…"   → the captured profile on those hosts only
_NATIVE_ACCEPT = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
_JSON_ACCEPT = "application/json"

_HOST_ACCEPT = {
    "lifestyle.t-bank-app.ru": _JSON_ACCEPT,
    "id.t-bank-app.ru": _JSON_ACCEPT,
    "www.tbank.ru": "*/*",
    "webview.t-bank-app.ru": "*/*",
    "trains.t-bank-app.ru": "*/*",
}
# Paths whose host says one thing and whose own capture says another: the lifestyle
# superapp shelf is served by the same host as Город but answers the native default.
_PATH_ACCEPT = {
    ("lifestyle.t-bank-app.ru", "/api/orders/list"): _NATIVE_ACCEPT,
    ("lifestyle.t-bank-app.ru", "/api/order"): _NATIVE_ACCEPT,
    ("lifestyle.t-bank-app.ru", "/api/event/movie"): _NATIVE_ACCEPT,
}


def _accept_profile_hosts() -> set[str] | None:
    """None ⇒ profile off (send json, as before). Empty set ⇒ on everywhere."""
    raw = os.environ.get("TBANK_ACCEPT_PROFILE", "").strip().lower()
    if not raw or raw == "json":
        return None
    if raw == "auto":
        return set()
    return {h.strip() for h in raw.split(",") if h.strip()}


def _accept_for(hostname: str, path: str = "") -> str:
    """The Accept for this host+path. Always returns a value, so the session-level
    default (set on requests.Session at construction) never fills the gap — changing
    only this function would otherwise be a no-op."""
    enabled = _accept_profile_hosts()
    if enabled is None or (enabled and hostname not in enabled):
        return _JSON_ACCEPT
    hit = _PATH_ACCEPT.get((hostname, str(path or "")))
    return hit or _HOST_ACCEPT.get(hostname, _NATIVE_ACCEPT)


def _wants_wuid(host: str, path: str) -> bool:
    """Does the real app send `wuid` to this host+path?

    Only www.tbank.ru, and only under /api/common/. It is absent from all 410
    captured api.t-bank-app.ru requests and all 235 lifestyle ones, and from the
    /api/supreme/lifestyle/* checkout paths on www.tbank.ru itself."""
    hn = (urlparse(host).hostname or host or "").lower()
    return hn == "www.tbank.ru" and str(path or "").startswith("/api/common/")


_STRICT_XAPP_HOSTS = {
    "social-api.t-bank-app.ru", "api-invest-gw.t-bank-app.ru",
    "myauto.t-bank-app.ru", "polls.tbank.ru",
    # The app sends X-App-Name/Version here too (captures2.xml #44). It was the one
    # host in either capture that does and was missing from this list.
    "cx-evolution-api.t-bank-app.ru",
}


def _count_of(good: dict, default: float = 1.0) -> float:
    """A cart line's quantity, kept NUMERIC.

    Goods sold by weight carry a fractional count — captures2.xml #1005 posts
    {"id":"606","count":0.57} alongside 0.63 and 1.35. Coercing with int() turned
    every such line into 0, and a 0 count is how this API removes a good: rebuilding
    the cart to add one item silently deleted every vegetable, fruit and meat line
    in it, while cart/set answered 200."""
    try:
        return float(good.get("count", default) if good.get("count") is not None else default)
    except (TypeError, ValueError):
        return default


def _count_out(count: float):
    """Send an int when the quantity is whole, a float when it is not — matching the
    app, which posts 2 for two packs and 0.57 for 570 g."""
    return int(count) if float(count) == int(count) else round(float(count), 3)


def _reject_unkeyed(items: Any) -> None:
    """Refuse a cart write whose entries carry no ``id``, BEFORE anything is posted.

    The cart loops skipped such an entry silently. cart/set then replaced the cart
    with the unchanged goods list and answered 200 with a goodsSum, so the server
    layer reported success and counted the caller's INPUT — "OK: 3 новых позиций"
    for zero items added. Nothing about that told the caller its key name was wrong.
    Refusing here costs nothing: no request has been made yet."""
    if not isinstance(items, list):
        raise TbankApiError("BAD_ITEMS",
            f"items должен быть списком объектов [{{\"id\": \"123\", \"count\": 1}}], "
            f"а пришло {type(items).__name__}.")
    bad = [it for it in items
           if not isinstance(it, dict) or not str(it.get("id", "") or "").strip()]
    if bad:
        keys = sorted({k for it in bad if isinstance(it, dict) for k in it})
        raise TbankApiError("BAD_ITEMS",
            f"{len(bad)} из {len(items)} позиций без ключа \"id\" — они были бы "
            f"молча пропущены, а корзина осталась бы прежней. "
            f"Нужно [{{\"id\": \"123\", \"count\": 1}}]"
            + (f"; пришли ключи: {', '.join(keys)}." if keys else ".")
            + " id товара берётся из grocery_search / grocery_rank.")


def _next_step_hint(resp: dict) -> str:
    """What the caller must do next, from the `step` the bank names in an
    /auth/step response. Shared by login() and confirm_step() — the latter used to
    dump the raw JSON instead, so the normal otp → password hop surfaced to the
    agent as «API error (NO_CODE): {…}» with the answer inside the blob."""
    step = str((resp or {}).get("step", "") or "")
    tool = {"otp": "confirm_otp(<код из СМС>)",
            "password": "confirm_password(<пароль от аккаунта>)",
            "pin": "confirm_pin(<PIN приложения>)"}.get(step)
    if tool:
        return f"Следующий шаг — {step}. Вызови {tool}."
    return (f"Следующий шаг — '{step or 'неизвестен'}'. Подходящий тул: confirm_otp / "
            f"confirm_password / confirm_pin. Ответ: "
            f"{json.dumps(resp, ensure_ascii=False)[:200]}")


def _wait_for_propagation(probe, *, timeout_s: float = 8.0, interval_s: float = 0.3) -> None:
    """Poll `probe` until it stops raising, or the deadline passes.

    A freshly-minted session needs a moment before mobile reads accept it
    (else INSUFFICIENT_PRIVILEGES) — a blind sleep either waits when it
    didn't need to, or not long enough. This degrades to "waited the full
    deadline and proceeded anyway" on timeout, so it is never worse than the
    blind sleep it replaces."""
    deadline = time.monotonic() + timeout_s
    while True:
        try:
            probe()
            return
        except Exception:
            pass
        if time.monotonic() >= deadline:
            return
        time.sleep(interval_s)


def money_amount(amount) -> float | int:
    """The value that goes into `moneyAmount`, in the form the app sends it.

    Three things happen here, and each has a way of going wrong quietly:

    * NOT FINITE is refused. json.dumps writes NaN and Infinity as bare `NaN` /
      `Infinity` — not JSON at all — and it would go into a SIGNED payment body.
      An amount that came out of arithmetic can be either.
    * QUANTISED to kopecks. A computed amount arrives as 7866.666666666667 and was
      sent verbatim; the duplicate-guard key is built from that string too, so two
      attempts at «the same» payment could stop recognising each other.
    * WHOLE amounts stay integers. All eleven captured bodies — /v1/pay and
      /v1/payment_commission across four capture files — carry
      `"moneyAmount":23600`, never `23600.0`. float(amount) produced the second form.

    Non-positive is left to the callers: each has a better message for it, and
    refusing here would replace «Сумма должна быть больше нуля» with a type error."""
    try:
        value = float(amount)
    except (TypeError, ValueError):
        raise TbankApiError("INVALID_AMOUNT",
                            f"сумма должна быть числом, получено {amount!r}") from None
    if value != value or value in (float("inf"), float("-inf")):
        raise TbankApiError("INVALID_AMOUNT",
                            f"сумма не является конечным числом: {amount!r}")
    # Decimal, not round(). round(100.005, 2) is 100.0, because 100.005 is really
    # 100.00499999999999545 in binary — half a kopeck lost, silently, on money.
    # Quantising the DECIMAL text of the value rounds what the caller meant.
    kopecks = decimal.Decimal(str(value)).quantize(decimal.Decimal("0.01"),
                                                   rounding=decimal.ROUND_HALF_UP)
    return int(kopecks) if kopecks == kopecks.to_integral_value() else float(kopecks)


def _excerpt(text, limit: int = 200) -> str:
    """A cut that says how much it dropped.

    `s[:200]` is indistinguishable from the whole thing, which is the entire
    complaint the truncation audit made about the rest of the codebase — and these
    are DIAGNOSTIC strings, where the missing part is often the interesting part: a
    proxy interstitial cut at 200 characters looks like the server said nothing.
    server._cut marks with a bare «…»; here the size is worth naming, because the
    reader is deciding whether to go and look at the full response."""
    s = str(text or "")
    if len(s) <= limit:
        return s
    return f"{s[:limit]}… (+{len(s) - limit} симв.)"


def _response_filename(headers) -> str:
    """The filename the SERVER states for a download, or ''.

    Three spellings, most reliable first:
      * `x-amz-meta-filename-base64` — the object store's own copy, exact bytes,
        with no quoting or encoding left to interpret. This is what the messenger
        actually sends;
      * `Content-Disposition: …filename*=UTF-8''…` (RFC 5987);
      * `Content-Disposition: …filename="…"`, whose value the messenger
        percent-encodes ("Otchet_%D0%BE%D1%82…"), so it is unquoted either way — a
        name that was NOT encoded contains no '%' and survives unchanged.

    The result is untrusted text like any other bank string: it names nothing on
    disk until the caller has scrubbed it."""
    # requests hands over a case-insensitive mapping, but this must not depend on
    # that: a plain dict from a test or another transport spells its keys however
    # it likes, and a header lookup that misses simply returns no name at all.
    lower = {str(k).lower(): v for k, v in (headers or {}).items()}
    try:
        raw = lower.get("x-amz-meta-filename-base64") or ""
        if raw:
            return base64.b64decode(raw + "=" * (-len(raw) % 4)).decode("utf-8")
    except (ValueError, UnicodeDecodeError, binascii.Error):
        pass
    cd = lower.get("content-disposition") or ""
    m = re.search(r"filename\*\s*=\s*[^']*''([^;]+)", cd, re.I)
    if not m:
        m = re.search(r'filename\s*=\s*"([^"]*)"', cd, re.I) or \
            re.search(r"filename\s*=\s*([^;]+)", cd, re.I)
    if not m:
        return ""
    try:
        return urllib.parse.unquote(m.group(1).strip(), errors="strict")
    except (UnicodeDecodeError, ValueError):
        return m.group(1).strip()


def _as_json_envelope(blob: bytes):
    """Parse `blob` as JSON if it plausibly IS one, else None.

    For routes that answer with a document but report failure as JSON. A real
    .xlsx/.pdf/.png starts with its own magic and never parses, so the guards are
    cheap; the size cap keeps a 60MB attachment from being decoded just to find
    out it is not an error object."""
    if not blob or len(blob) > 65536 or blob[:1] not in (b"{", b"["):
        return None
    try:
        return json.loads(blob.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _normalize_phone(phone: str) -> str:
    """Normalize a RU mobile number to the SBP `pointer` format ``+7XXXXXXXXXX``
    (the form the real app sends). Accepts +7 / 8 / 7 / bare-9… forms."""
    d = re.sub(r"\D", "", phone or "")
    if d.startswith("8") and len(d) == 11:
        d = "7" + d[1:]          # 8904… → 7904…
    elif len(d) == 10 and d[:1] == "9":
        d = "7" + d              # 904… → 7904…
    if not (len(d) == 11 and d.startswith("7")):
        raise TbankApiError("INVALID_PHONE", f"not a valid RU mobile number: {phone}")
    return "+" + d


# ---- payment QR (ГОСТ Р 56042-2014) --------------------------------------
#
# The QR printed on every Russian invoice. Header is "ST0001" + one digit naming
# the encoding of the rest (1 = win-1251, 2 = utf-8, 3 = koi8-r), then Key=Value
# pairs joined by "|". `Sum` is in KOPECKS; every other value is text.
#
# The app does not parse it locally — it posts the string untouched to
# /providers/providers/qr/resolve and gets back the `transfer-legal` provider with
# every field pre-filled (captures_payreq.xml #538). We parse it anyway, for two
# reasons: the tool can show the recipient before spending a request, and a QR the
# bank does not recognise still has a readable payee.
QR_PAYMENT_PREFIX = "ST0001"

# QR key (lowercased) → the providerFields id transfer-legal wants. The first seven
# are the bank's OWN mapping, not a reading of the standard: the QR in
# captures_payreq.xml #538 carries exactly Name/PersonalAcc/BankName/BIC/CorrespAcc/
# PayeeINN/KPP/Sum, and the bank echoed each one back as the defaultValue of the
# field named here.
#
# `purpose` is the exception and is marked so on purpose: that QR carried no Purpose
# (the payer typed «За товар» by hand afterwards), so the pairing comes from the
# standard, where Purpose IS назначение платежа, and not from an observed response.
# Nothing rests on it being right — a missing or misread purpose is refused before
# the payment by the provider's own `required` flag, never silently paid.
QR_TO_PROVIDER_FIELD = {
    "name": "addressee",
    "personalacc": "bankAcnt",
    "bankname": "bankName",
    "bic": "bankBik",
    "correspacc": "bankCorrAcnt",
    "payeeinn": "inn",
    "kpp": "kpp",
    "purpose": "comment",       # from the standard; the capture has no Purpose
    # ЖКХ block. The provider publishes `account` («Номер лицевого счета», optional)
    # and the standard puts the payer's personal account in PersAcc — a утилита QR
    # carries it and it was being dropped, so the payment went out with the field
    # the receiving side uses to match the payer left empty.
    "persacc": "account",
}

# The two values the `nds` List field accepts. Not cosmetic: this is the VAT mark
# that goes on the payment order the recipient's bank shows their accountant.
NDS_INCLUDED = "323"      # «НДС включен»
NDS_EXEMPT = "322"        # «НДС не облагается» — the provider's own defaultValue
NDS_LABELS = {NDS_INCLUDED: "НДС включен", NDS_EXEMPT: "НДС не облагается"}


def payment_qr_hash(qr: str) -> str:
    """`barcodeHash` as the app computes it: sha1 over the QR string's utf-8 bytes.

    Verified: sha1(qr.encode("utf-8")).hexdigest() reproduces the hash the app sent
    alongside the QR in captures_payreq.xml #538, byte for byte."""
    return hashlib.sha1(str(qr).encode("utf-8")).hexdigest()


def parse_payment_qr(qr: str) -> dict:
    """Split a ГОСТ Р 56042-2014 payment QR into requisites, WITHOUT the network.

    Returns {"format", "fields", "requisites", "amount", "hash"} where `requisites`
    is already keyed by transfer-legal's own field ids and `amount` is in RUBLES
    (the QR carries kopecks) or None when the QR names no sum — an open invoice the
    payer fills in.

    Raises QR_NOT_PAYMENT for anything that is not this format; a link, a loyalty
    card or an SBP QR would otherwise be silently read as a set of blank requisites."""
    text = (qr or "").strip()
    if not text.upper().startswith(QR_PAYMENT_PREFIX):
        raise TbankApiError("QR_NOT_PAYMENT",
            "это не платёжный QR по ГОСТ Р 56042-2014 — такая строка должна "
            f"начинаться с {QR_PAYMENT_PREFIX} (например ST00012|Name=…|"
            "PersonalAcc=…|BIC=…). Получено: " + (_excerpt(text, 60) or "пусто"))
    head, _, rest = text.partition("|")
    fields: dict[str, str] = {}
    for chunk in rest.split("|"):
        key, sep, value = chunk.partition("=")
        if sep and key.strip():
            fields[key.strip()] = value
    requisites: dict[str, str] = {}
    for key, value in fields.items():
        dst = QR_TO_PROVIDER_FIELD.get(key.lower())
        if dst and value.strip():
            requisites[dst] = value.strip()
    amount = None
    raw_sum = next((v for k, v in fields.items() if k.lower() == "sum"), "")
    # isdecimal, not isdigit: isdigit admits superscripts and circled digits, which
    # int() then refuses — a ValueError out of a parser whose whole job is to refuse
    # cleanly. The kopeck conversion below is only valid for decimal digits anyway.
    if str(raw_sum).strip().isdecimal():
        # Kopecks. Read as rubles this would pay 100× the invoice — worth the
        # explicit conversion and the round(), which keeps 2360000 → 23600.0 and
        # not 23599.999999999996.
        amount = round(int(raw_sum) / 100.0, 2)
    return {"format": head, "fields": fields, "requisites": requisites,
            "amount": amount, "hash": payment_qr_hash(text)}


# Every afisha listing is scoped by a numeric cityId, and the bank publishes no
# directory for it — the app has the mapping compiled in. This table was walked
# live: cityId 1..70 against the venue directory, each id resolved to a name
# through a venue's own schedule. 65 answered; 20, 41, 48, 65 and 68 are holes,
# and the run stopped at 70 with the list continuing alphabetically, so this is
# the popular head rather than everything the bank knows.
#
# It is code, not a data file, so it ships inside the wheel. Anything outside it
# is still reachable — the tools take an explicit city_id — but nothing here is
# guessed from a name.
CITY_IDS = {
    1: "Москва", 2: "Санкт-Петербург", 3: "Краснодар", 4: "Новосибирск",
    5: "Томск", 6: "Вологда", 7: "Чебоксары", 8: "Тольятти", 9: "Пермь",
    10: "Екатеринбург", 11: "Красноярск", 12: "Ростов-на-Дону", 13: "Сочи",
    14: "Ижевск", 15: "Тула", 16: "Набережные Челны", 17: "Казань",
    18: "Хабаровск", 19: "Ульяновск", 21: "Улан-Удэ", 22: "Иркутск", 23: "Уфа",
    24: "Белгород", 25: "Волгоград", 26: "Тюмень", 27: "Ейск", 28: "Кемерово",
    29: "Севастополь", 30: "Нижний Новгород", 31: "Самара", 32: "Челябинск",
    33: "Омск", 34: "Воронеж", 35: "Саратов", 36: "Химки", 37: "Зеленоград",
    38: "Балашиха", 39: "Домодедово", 40: "Красногорск", 42: "Сергиев Посад",
    43: "Люберцы", 44: "Наро-Фоминск", 45: "Мытищи", 46: "Щелково",
    47: "Гатчина", 49: "Барнаул", 50: "Абакан", 51: "Альметьевск",
    52: "Армавир", 53: "Архангельск", 54: "Астрахань", 55: "Балаково",
    56: "Бийск", 57: "Биробиджан", 58: "Брянск", 59: "Великий Новгород",
    60: "Владивосток", 61: "Владикавказ", 62: "Владимир", 63: "Волгодонск",
    64: "Грозный", 66: "Иваново", 67: "Йошкар-Ола", 69: "Калининград",
    70: "Калуга",
}


def _norm_city(s: str) -> str:
    return str(s).strip().lower().replace("ё", "е")


_CITY_BY_NAME = {_norm_city(n): i for i, n in CITY_IDS.items()}
# What people actually type.
_CITY_BY_NAME.update({"спб": 2, "питер": 2, "санкт петербург": 2, "мск": 1,
                      "екб": 10, "нижний": 30, "ростов": 12, "н.новгород": 30})


def city_id_of(city: str = "", city_id: int | str = 0) -> str:
    """Numeric cityId for an afisha call, as the string the bodies carry.

    An explicit city_id always wins — it is the escape hatch for a city outside
    the table. A name that is not in the table RAISES rather than falling back to
    Moscow: a Moscow listing answering a question about Kazan looks entirely
    plausible and is entirely wrong, which is the one failure mode worth an error."""
    if str(city_id).strip() not in ("", "0"):
        return str(city_id).strip()
    if not str(city).strip():
        raise TbankApiError("CITY_REQUIRED",
                            "не назван город; передай city или city_id")
    found = _CITY_BY_NAME.get(_norm_city(city))
    if found:
        return str(found)
    near = [n for n in CITY_IDS.values()
            if _norm_city(city)[:4] and _norm_city(city)[:4] in _norm_city(n)]
    raise TbankApiError(
        "UNKNOWN_CITY",
        f"города {city!r} нет в таблице cityId"
        + (f"; похожие: {', '.join(near[:5])}" if near else "")
        + ". Если он есть в банке, передай city_id числом.")


_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya", " ": "_",
    "-": "-",
}


def translit_city(s: str) -> str:
    """City name in the spelling the `Segodnya-v_kino_*` shelf codes use.

    This is a reconstruction of the server's own convention, not a guess at a
    name: the live shelf lists hand back exactly Segodnya-v_kino_Sankt-Peterburg,
    Segodnya-v_kino_Sochi, Skoro-v_kino_Kazan. It stays only as the fallback for
    when the shelf list comes back empty — which the Moscow one does when that
    backend is having a moment, and Moscow is the last city where guessing wrong
    would be noticed late.

    It does NOT generalise to other shelf families: those spell the same city
    Moskva, moscow and msk depending on the shelf, so nothing but the server's
    own list can be trusted for them."""
    out = "".join(_TRANSLIT.get(ch, _TRANSLIT.get(ch.lower(), ch))
                  if not ch.isascii() else ch for ch in s)
    return re.sub(r"(^|[_\-])([a-z])",
                  lambda m: m.group(1) + m.group(2).upper(), out)


def vertical(kind: str) -> dict:
    """The VERTICALS row for `kind`, or an error naming what is accepted.

    Every afisha call used to pick its path with `"concert" if kind == "concert"
    else <movie>`, so a typo — or a vertical nobody had wired up yet — silently
    booked a cinema seat instead of failing. An unknown kind raises here."""
    key = VERTICAL_ALIASES.get(str(kind).strip().lower())
    if not key:
        raise TbankApiError(
            "UNKNOWN_KIND",
            f"unknown kind {kind!r}; use one of: {', '.join(VERTICALS)} "
            f"(кино, концерт, театр, выставка)")
    return VERTICALS[key]


_SESSION_EXPIRED = {
    "NOT_AUTHORIZED", "SESSION_EXPIRED", "SESSION_NOT_FOUND", "NO_SESSION",
    "UNAUTHORIZED", "DEVICE_LINK_REMOVED", "REAUTH", "INVALID_SESSION",
    "invalid_grant", "invalid_token",
}


def ms_for_period(days: int = 30) -> tuple[int, int]:
    end = int(time.time() * 1000)
    return end - days * 86400 * 1000, end
