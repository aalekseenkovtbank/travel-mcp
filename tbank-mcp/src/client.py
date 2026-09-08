"""T-Bank mobile API client — self-bootstrapping, fully headless after login.

Public façade: ``MobileSession`` and error types. Implementation is split by
domain into ``client_common`` plus mixins.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import requests

from . import client_common as _client_common
from .client_afisha import AfishaMixin
from .client_banking import BankingMixin
from .client_grocery import GroceryMixin
from .client_hotels import HotelMixin
from .client_messenger import MessengerMixin
from .client_money import MoneyMixin
from .client_travel import TravelMixin

# Mixin and core methods historically resolved module globals in client.py.
globals().update({
    name: getattr(_client_common, name)
    for name in dir(_client_common)
    if not name.startswith("__")
})

__all__ = [
    "MobileSession", "TbankApiError", "SessionExpired",
    "UnreadableResponse", "PaymentConfirmationRequired",
    "ms_for_period", "MOBILE_BASE",
]


@dataclass
class MobileSession(
    HotelMixin, GroceryMixin, MessengerMixin, TravelMixin,
    AfishaMixin, MoneyMixin, BankingMixin,
):
    mobile_sessionid: str
    refresh_token: str
    access_token: str = ""
    expires_in: int = 7199
    device_id: str = ""
    old_device_id: str = ""
    fingerprint: str = ""           # the static anti-fraud JSON blob
    client_id: str = ""             # from Basic auth (e.g. "gorod-app")
    basic_auth: str = ""            # full "Basic ..." header value
    client_version: str = ""
    vendor: str = ""
    origin: str = ""
    platform: str = ""
    app_name: str = ""
    app_version: str = ""
    connection_type: str = "WiFi"
    ccc: str = "true"
    cpswc: str = "true"
    inache: str = "drivetransitt"  # app routing/feature flag (constant) — sent on every request
    cookie_str: str = ""            # the cookie header to replay on reads/refresh
    sso_login_cookie: str = ""      # the LOGIN (auth_code) cookie set incl. SSO_SESSION (long-lived) — for silent re-login
    sso_id: str = ""                # public web ssoId, learned from session_status and used only by allowlisted facades
    auth_step_fingerprint: str = "" # the static fingerprint blob sent at auth/step (silent re-login)
    tmsg_session_id: str = ""       # messenger JWT cookie (tm.t-bank-app.ru)
    trains_cookie: str = ""         # rail host cookie (trains.t-bank-app.ru)
    trains_cookie_at: float = 0.0   # when it was minted (unix seconds)
    hotels_cookie: str = ""         # isolated cookies learned from Hotels web SSO
    hotels_cookie_at: float = 0.0   # when the Hotels cookie set was last updated
    token_url: str = DEFAULT_TOKEN_URL
    read_templates: dict = field(default_factory=dict)
    base_url: str = MOBILE_BASE
    proxy: str | None = None
    _http: requests.Session = field(default_factory=requests.Session, repr=False)
    _minted_at: float = 0.0  # persisted to session.json (not just runtime)

    def __post_init__(self) -> None:
        # self-bootstrap defaults: a fresh device_id + a built-in device
        # fingerprint blob (no capture needed). login()/confirm_otp() populate
        # the SSO_SESSION + session from a real phone+OTP login.
        import uuid as _uuid
        # Persistence hook, set by the owner (server._require). Every re-mint
        # rotates the refresh_token, so a re-mint that is not written to disk
        # burns the token for the NEXT process — see _persist().
        self._on_persist = None
        # If _minted_at is 0 (loaded from legacy session without timestamp),
        # don't set it to now — that would make an old token look fresh.
        # Leave it 0 — ensure_fresh will refresh before first use.
        # Per-PROCESS memo for values that are stable for the life of a session and
        # were being re-fetched on every call: the prefill contact id (documents()
        # asked for it twice in one invocation) and the per-store areaId (a full
        # retailers download per add_to_cart, to read one field). A plain attribute,
        # not a dataclass field — _save_session serializes fields, and this must
        # never reach session.json.
        self._memo: dict = {}
        # Device facts for the payment anti-fraud block, from the environment.
        # A plain attribute for the same reason as _memo: it is machine-local
        # configuration, not session state, and must not be written to session.json
        # (nor restored from an old one, which would outlive the machine it
        # described). Unset keys fall back to PAY_DEVICE_DEFAULTS.
        self.device_profile: dict = {
            k: v for k, v in (
                ("device_screen_height", os.environ.get("TBANK_DEVICE_SCREEN_HEIGHT")),
                ("device_screen_width", os.environ.get("TBANK_DEVICE_SCREEN_WIDTH")),
                ("language", os.environ.get("TBANK_DEVICE_LANGUAGE")),
                ("timezone", os.environ.get("TBANK_DEVICE_TIMEZONE")),
                ("model", os.environ.get("TBANK_DEVICE_MODEL")),
            ) if v}
        if not self.device_id:
            self.device_id = str(_uuid.uuid4()).upper()
        if not self.old_device_id:
            self.old_device_id = self.device_id
        if not self.fingerprint:
            self.fingerprint = _builtin_fingerprint(self.device_id)
        if not self.auth_step_fingerprint:
            self.auth_step_fingerprint = _builtin_fingerprint(self.device_id)
        safe_headers = {
            "User-Agent": "okhttp/4.12.0",
            "Accept": "application/json",
            "x-lang": "ru",
        }
        self._http.headers.update(safe_headers)
        # Public facades must not share requests.Session's implicit cookie jar
        # with banking calls.  Merely omitting an explicit Cookie header is not
        # enough: requests can attach a Domain=.tbank.ru cookie stored from an
        # earlier www.tbank.ru response.  This isolated jar starts credential-free
        # and can only ever learn cookies from the public facade itself.
        self._public_http = requests.Session()
        self._public_http.headers.update(safe_headers)
        if self.proxy:
            self._http.proxies = {"http": self.proxy, "https": self.proxy}
            self._public_http.proxies = {"http": self.proxy, "https": self.proxy}
        # Build the CA bundle on startup = system store + the pinned roots in
        # ca/roots/. Cheap and offline (no openssl, no network), so it is safe to
        # do every time and it keeps a fresh clone working: ca/bundle.pem is
        # generated and gitignored, so it does not exist until this runs.
        # The adapter retries once on an SSL failure by rebuilding from the SAME
        # trusted material — it never learns a certificate from the peer.
        _bundle_path = _CA_BUNDLE  # latched at import; may be None on a fresh machine
        try:
            from . import tls as _tls
            _tls.rebuild_bundle()
            self._http.mount("https://", _tls.RobustTLSAdapter())
            self._public_http.mount("https://", _tls.RobustTLSAdapter())
            _bundle_path = _tls.BUNDLE  # canonical path — now exists (rebuild built it)
        except Exception:
            pass
        # Set verify AFTER rebuild_bundle, re-checked at runtime. The module-level
        # _CA_BUNDLE is evaluated ONCE at import: on a fresh machine where ca/bundle.pem
        # didn't exist yet, it latches to None and the old `if _CA_BUNDLE: verify=...`
        # (run BEFORE rebuild) never set verify → requests fell back to system CAs (no
        # Russian Trusted Root CA) → SSL CERTIFICATE_VERIFY_FAILED. (#latch-bug)
        if _bundle_path and os.path.exists(_bundle_path):
            self._http.verify = _bundle_path
            self._public_http.verify = _bundle_path
        # Normalize token_url: a legacy session.json may have stored an explicit
        # "" (the old default). An empty value would make refresh() POST to "",
        # so force the canonical default. The dataclass default alone can't
        # override an explicit empty string passed at construction time.
        if not self.token_url:
            self.token_url = DEFAULT_TOKEN_URL
        # DON'T set _minted_at = time.time() here — it would make old tokens
        # look fresh on reload. _minted_at is set by login/refresh/renew,
        # or stays 0 (from legacy session) → ensure_fresh will refresh before use.
        if not self._minted_at:
            self._minted_at = 0  # explicit: 0 means "unknown age → refresh before first use"
        # login state (cid + otp token persisted between login() and confirm_otp())
        self._login_cid: str = ""
        self._login_token: str = ""
        self._login_cookie: str = ""


    def _persist(self) -> None:
        """Write the session out after a re-mint, if the owner installed a hook.

        This is not an optimisation — it is required for correctness. `refresh()`
        rotates the refresh_token, so a process that re-mints and exits without
        saving leaves the NEXT process holding a spent token; that one then has to
        fall back to the slower silent_relogin, and if the SSO cookie has also
        lapsed it fails outright and every tool starts answering SESSION EXPIRED.
        """
        hook = getattr(self, "_on_persist", None)
        if hook is None:
            return
        try:
            hook()
        except Exception:
            # Persisting is best-effort: a read-only HOME must not break reads.
            pass


    def _refresh_body(self) -> dict:
        # EXACT fields of the refresh grant (10 fields). client_id is
        # in the Basic header, not the body. No client_assertion, no redirect_uri.
        return {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "device_id": self.device_id,
            "appName": self.app_name,
            "appVersion": self.app_version,
            "origin": self.origin,
            "platform": self.platform,
            "vendor": self.vendor,
            "client_version": self.client_version,
            "fingerprint": self.fingerprint,
        }


    def refresh(self) -> dict:
        """Re-mint the mobile sessionid headlessly (proven to work). Stores the
        rotated refresh_token + new sessionid + access_token."""
        headers = {
            "Authorization": self.basic_auth or self._basic_auth(),
            "Accept": "application/json",
            "X-SSO-No-Adapter": "true",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "okhttp/4.12.0",
            "x-lang": "ru",
        }
        if self._wide_cookie():
            headers["Cookie"] = self._wide_cookie()
        r = self._http.post(self.token_url, data=self._refresh_body(),
                            headers=headers, timeout=30)
        tok = self._unwrap(r)
        if not isinstance(tok, dict) or (
            "access_token" not in tok and "mobile" not in tok
        ):
            err = tok.get("error") if isinstance(tok, dict) else None
            msg = (tok.get("error_description") or tok.get("status")
                   or "(no token in response)") if isinstance(tok, dict) else str(tok)[:200]
            if str(err).lower() in ("invalid_grant", "invalid token"):
                raise SessionExpired(str(err), str(msg))
            raise TbankApiError(str(err) if err else "NOT_A_TOKEN_RESPONSE", str(msg)[:300])
        self.access_token = tok.get("access_token", self.access_token)
        self.refresh_token = tok.get("refresh_token", self.refresh_token)
        self.expires_in = tok.get("expires_in", self.expires_in) or self.expires_in
        mobile = tok.get("mobile") or {}
        self.mobile_sessionid = mobile.get("sessionid", self.mobile_sessionid)
        self._minted_at = time.time()
        self._persist()          # the refresh_token just rotated — never lose it
        return tok


    def _basic_auth(self) -> str:
        return "Basic " + base64.b64encode(f"{self.client_id}:".encode()).decode()


    def ensure_fresh(self, max_age_s: int = 6000) -> None:
        """Re-mint the session before the access_token expires (~2h).

        Prefers refresh() — the refresh_token grant — simply because it is ONE
        request, against silent_relogin's authorize → step → token dance plus a 3 s
        propagation sleep. silent_relogin stays as the fallback for a dead or
        rotated refresh_token.

        Both grants mint an equally privileged sessionid (measured: CLIENT with
        portalSessionExpiresInSeconds 659 vs 656). An earlier version of this
        comment claimed only refresh() yielded CLIENT — that was a misreading of
        ensure_client_session's ~11-minute window, see there.

        This only tracks the ~2h access_token. Tools that need a CLIENT-level
        SESSION must call ensure_client_session() instead — that window is ~11
        minutes and lapses long before the token does.
        _minted_at == 0 means unknown age (legacy session) → always re-mint."""
        if not self._needs_mint(max_age_s):
            return
        with _MINT_LOCK:
            # Checked again INSIDE the lock. Without this the lock only queues the
            # threads: each would take its turn and re-mint, rotating the
            # refresh_token once per waiter instead of once in total.
            if not self._needs_mint(max_age_s):
                return
            try:
                self.refresh()
            except Exception:
                if not (self.sso_login_cookie and self.auth_step_fingerprint):
                    raise
                self.silent_relogin()


    def _needs_mint(self, max_age_s: int = 6000) -> bool:
        return (self._minted_at == 0
                or time.time() - self._minted_at
                > min(max_age_s, max(60, self.expires_in - 600)))


    def ensure_client_session(self) -> str:
        """Guarantee a CLIENT-level sessionid, for the few endpoints that check it.

        The sessionid's CLIENT window is MUCH shorter than the access_token that
        ensure_fresh() tracks: /v1/ping reports `portalSessionExpiresInSeconds`
        ≈ 659 right after a re-mint — about 11 minutes — against the token's ~2h.
        Once it lapses the same sessionid reads back as accessLevel ANONYMOUS /
        userId 1111, and only the handful of session-validating endpoints notice
        (card_credentials, prefill/profile documents, session_status); everything
        else keeps working on the Bearer, which is why the lapse looks like a
        random failure rather than an expiry.

        So: ping, and re-mint if the window has closed. Costs one extra request,
        and only the tools that actually need CLIENT should call it."""
        self.ensure_fresh()
        def level():
            try:
                return (self.keepalive() or {}).get("accessLevel")
            except TbankApiError:
                return None
        current = level()
        if current == "CLIENT":
            return current
        self.refresh()
        return level() or "UNKNOWN"


    def _tpl(self, key: str) -> dict:
        """Resolve a read template: builtin endpoint shape first (capture-free),
        then any capture-loaded template (legacy)."""
        tpl = BUILTIN_ENDPOINTS.get(key) or self.read_templates.get(key)
        if not tpl:
            raise TbankApiError("NO_TEMPLATE", f"no endpoint shape for '{key}'")
        return tpl


    def _mobile_ua(self) -> str:
        """The mobile User-Agent derived from the session (NOT hardcoded):
        ``iPhone/iOS(<ver>)/TCSMB/<appVersion>(<build>)``. The numeric build is
        derived from app_version (7.31.6 -> 7316000); the iOS device version is the
        constant ``_IOS_VERSION``. Returns '' for non-iOS / unknown app_version."""
        if self.platform != "ios" or not self.app_version:
            return ""
        try:
            a, b, c = (int(x) for x in self.app_version.split("."))
            build = a * 1_000_000 + b * 10_000 + c * 1_000
        except ValueError:
            return ""
        return f"iPhone/iOS({_IOS_VERSION})/TCSMB/{self.app_version}({build})"


    def _mobile_headers(self, host_url: str = "", path: str = "") -> dict:
        """Mobile-client headers the real app sends, derived from session attrs.
        ``X-Lang``/``Accept-Language``/``Accept``/mobile ``User-Agent`` are sent on
        basically every API host → injected always. But ``X-App-Name``/``Version``/
        ``Platform`` are sent ONLY on ``_STRICT_XAPP_HOSTS`` (capture-verified
        per-host profile). Injecting them elsewhere diverges from the app and breaks
        the grocery cart on lifestyle. An explicit template header still wins
        (setdefault below)."""
        hn = (urlparse(host_url).hostname or host_url or "").lower()
        h: dict[str, str] = {"X-Lang": "ru", "Accept-Language": "ru",
                             "Accept": _accept_for(hn, path)}
        if hn in _STRICT_XAPP_HOSTS:
            if self.app_name:
                h["X-App-Name"] = self.app_name
            if self.app_version:
                h["X-App-Version"] = self.app_version
            if self.platform:
                h["X-Platform"] = self.platform
        ua = self._mobile_ua()
        if ua:
            h["User-Agent"] = ua
        # The messenger host has its own UA header, and it is NOT the same string:
        # bundle:appVersion; sdk; iOS:version; device:model. Derived here so it
        # cannot drift from _IOS_VERSION the way the frozen template literal did
        # (it claimed iOS 17.5.1 and carried no device segment at all).
        if hn == "tm.t-bank-app.ru" and self.app_version:
            h["Tmsg-User-Agent"] = (
                f"com.idamob.tinkoff.android:{self.app_version}; "
                f"tmsg-sdk-iOS:1.0.0; iOS:{_IOS_VERSION}; device:{self.device_model}")
        return h


    def _prepare_request(self, template_key: str, *, overrides: dict | None = None,
                        body: dict | list | None = None,
                        path_override: str | None = None,
                        headers_override: dict[str, str] | None = None):
        """Build (method, url, params, headers, http, body_kwargs, tpl) for a
        builtin endpoint template.

        Shared by _call_read (buffered, JSON-enveloped) and _call_stream
        (unbuffered, ndjson): the session/param/header/cookie assembly below
        is the one place that knows how a request gets authorised, and a fix
        made there for one path must not silently miss the other."""
        tpl = self._tpl(template_key)
        params = {k: v for k, v in tpl.get("params", {}).items()
                  if k not in _LIVE_QUERY}
        # Most hosts read the mobile sessionid from `sessionid`; the prefill-profile
        # and insurance hosts spell it `sessionId` and reject the lowercase form.
        # Some hosts want none of the native client context. The webview-served
        # ones carry only appName/appVersion/platform and answer 400 to the rest,
        # which is the same class of divergence that once broke the lifestyle cart:
        # sending what the app does not send is not free.
        lean = bool(tpl.get("no_base_params"))
        if not lean:
            params[tpl.get("session_param") or "sessionid"] = self.mobile_sessionid
            params["deviceId"] = self.device_id
            params["oldDeviceId"] = self.old_device_id or self.device_id
        elif tpl.get("session_param"):
            # A lean host may still key its session off ONE named query param.
            params[tpl["session_param"]] = self.mobile_sessionid
        host = tpl.get("host") or self.base_url
        path = path_override or tpl["path"]
        # wuid is the WEB portal's device identifier. It went on every request to
        # every host; the app sends it only to www.tbank.ru, and only under
        # /api/common/ (never on the /api/supreme/lifestyle/* checkout paths). On a
        # native call it is a value the app never puts there — the same reasoning
        # that already removed it from /v1/pay.
        if _LEGACY_QUERY or _wants_wuid(host, path):
            params["wuid"] = self.device_id
        # inject the common base params from the session if not in the template
        # (so builtin endpoints with minimal params still send appName/origin/etc.)
        # inache is the app's routing/feature flag (constant "drivetransitt") — the
        # real client sends it on EVERY request; centralizing it here (default in the
        # dataclass) closes the gap for the ~8 templates that had empty params and
        # omitted it (cars, finhealth presets, my_home, payment_shortcuts, ...).
        # vendor/client_version are NOT here: they belong to the OIDC authorize call,
        # which builds its own query and never reaches _call_read, so injecting them
        # was pure divergence on every other host.
        base = [("appName", self.app_name), ("appVersion", self.app_version),
                ("origin", self.origin), ("platform", self.platform),
                ("ccc", self.ccc), ("cpswc", self.cpswc),
                ("connectionType", self.connection_type),
                ("inache", self.inache)]
        if _LEGACY_QUERY:
            base += [("vendor", self.vendor), ("client_version", self.client_version)]
        for k, v in base:
            if v and k not in params and not lean:
                params[k] = v
        if overrides:
            params.update(overrides)
        headers = {k: v for k, v in tpl.get("headers", {}).items()
                   if k.lower() not in _LIVE_HEADERS}
        # Inject the mobile-client headers the real app sends on this host:
        # x-lang/Accept-Language/Accept/UA always; X-App-Name/Version/Platform ONLY
        # on _STRICT_XAPP_HOSTS (elsewhere the app sends just x-lang — injecting
        # X-App-* there breaks the lifestyle grocery cart). setdefault ⇒ an explicit
        # template header or Authorization/Cookie below still wins.
        for k, v in self._mobile_headers(host, path).items():
            headers.setdefault(k, v)
        if headers_override:
            headers.update({str(k): str(v) for k, v in headers_override.items()})
        # A few hosts are authorised by cookie alone and the app sends no Bearer to
        # them at all; carrying one there is another silent divergence.
        if not tpl.get("no_bearer"):
            headers["Authorization"] = "Bearer " + self.access_token
        # Public facades must never inherit the normal bank/session cookie set.
        # A template may explicitly allow a small optional subset. Public Hotels
        # reads use only ssoId; authenticated favorites opts into its separate,
        # narrowly-built web SSO cookie profile. No implicit credential is sent.
        if tpl.get("no_cookie"):
            if tpl.get("hotels_sso_session"):
                cookie = self._hotels_sso_cookie()
                if self.sso_id:
                    headers.setdefault("x-tcs-sso-id", self.sso_id)
            elif tpl.get("optional_hotels_sso_session"):
                cookie = ""
                if self.access_token or self.refresh_token:
                    try:
                        cookie = self._hotels_sso_cookie()
                    except (TbankApiError, requests.RequestException):
                        # Search is public: failed optional auth only removes
                        # personalization and must not fail the search itself.
                        cookie = ""
                if cookie and self.sso_id:
                    headers.setdefault("x-tcs-sso-id", self.sso_id)
            else:
                allowed = tuple(tpl.get("optional_cookie_names") or ())
                cookie = self._optional_cookies(allowed) if allowed else ""
        else:
            cookie = self._cookie_for(host)
        if cookie:
            headers["Cookie"] = cookie
        # `no_cookie` uses a physically separate cookie jar. The getattr fallback
        # keeps lightweight test doubles made with MobileSession.__new__ working;
        # every normally constructed/loaded session has _public_http above.
        http = (getattr(self, "_public_http", self._http)
                if tpl.get("no_cookie") else self._http)
        if tpl.get("no_cookie"):
            # Public responses may set analytics/sticky cookies. Drop them before
            # every request so the explicit allowlisted Cookie header above is the
            # only cookie that can go back over the wire.
            http.cookies.clear()
        url = f"{host.rstrip('/')}/{path.lstrip('/')}"
        method = (tpl.get("method") or "GET").upper()
        body_kwargs: dict[str, Any] = {}
        if method == "POST":
            post_body = body
            if post_body is None and tpl.get("body"):
                raw = tpl["body"]
                try:
                    post_body = json.loads(raw) if isinstance(raw, str) else raw
                except json.JSONDecodeError:
                    post_body = raw
            if tpl.get("form"):
                # A few endpoints (payment_commission) take
                # application/x-www-form-urlencoded, not JSON — posting JSON there
                # returns INVALID_REQUEST_DATA. Dict values are JSON-encoded fields.
                data = {k: (json.dumps(v, ensure_ascii=False)
                            if isinstance(v, (dict, list)) else v)
                        for k, v in (post_body or {}).items()}
                body_kwargs = {"data": data}
            else:
                body_kwargs = {"json": post_body}
        return method, url, params, headers, http, body_kwargs, tpl


    def _call_read(self, template_key: str, *, overrides: dict | None = None,
                   body: dict | list | None = None,
                   path_override: str | None = None,
                   headers_override: dict[str, str] | None = None,
                   return_response: bool = False) -> Any:
        """Replay a read endpoint (builtin shape) with fresh sessionid + Bearer.

        path_override replaces the path (for parameterized endpoints like
        messenger conversations/{id}/messages)."""
        method, url, params, headers, http, body_kwargs, tpl = self._prepare_request(
            template_key, overrides=overrides, body=body,
            path_override=path_override, headers_override=headers_override)
        if method == "POST":
            r = http.post(url, params=params, headers=headers, timeout=30, **body_kwargs)
        elif method == "PUT":
            r = http.put(url, params=params, headers=headers, timeout=30)
        else:
            r = http.get(url, params=params, headers=headers, timeout=30)
        if tpl.get("optional_hotels_sso_session") or tpl.get("hotels_sso_session"):
            self._remember_hotels_sso_cookies(http)
        if return_response:
            # The caller wants the response itself, not a parsed body: a download
            # whose FILENAME lives in the headers, not in the bytes. Status handling
            # is theirs too — this returns 401s and 500s unraised.
            return r
        if tpl.get("raw"):
            # A few endpoints answer with bytes, not JSON (payment_receipt_pdf →
            # application/pdf). _unwrap would raise HTTP_200 on the undecodable body.
            r.raise_for_status()
            return r.content
        return self._unwrap(r)


    def _call_stream(self, template_key: str, *, body: dict | list | None = None,
                     overrides: dict | None = None):
        """POST a builtin endpoint that answers `application/x-ndjson` and
        yield each frame as a parsed dict, without buffering the whole
        response first.

        Used for Zubat's flight `/search/stream`, which emits one
        newline-delimited frame per line (`{"type": "Direct"|"Tpo"|"Finished",
        ...}`) over a single connection. Being a generator also means a
        caller that stops iterating early (a `break`, or letting the
        generator get garbage-collected) closes the underlying connection
        instead of reading a response nobody wants — see the `finally: r.close()`
        below, not something callers have to remember to do themselves.

        An error comes back as a single ordinary JSON body (BadRequestError /
        TechError per the Zubat spec), not ndjson — signalled by an HTTP
        status outside 2xx, which `_unwrap` already knows how to turn into
        the right exception."""
        method, url, params, headers, http, body_kwargs, _tpl = self._prepare_request(
            template_key, overrides=overrides, body=body)
        r = http.request(method, url, params=params, headers=headers,
                         timeout=30, stream=True, **body_kwargs)
        if not (200 <= r.status_code < 300):
            self._unwrap(r)
            return
        try:
            for raw_line in r.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue
                try:
                    yield json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
        finally:
            r.close()


    def _sign(self, method: str, path: str, query: str, body: str) -> str:
        """Reproduce the T-Bank x-api-signature (verified against a real capture).

        msg = METHOD + "\\n" + path_tail + ["\\n"+query] + ["\\n"+body]
        path_tail = the path from the v\\d segment onward (e.g. "/v1/pay").
        key = the mobile sessionid. alg = HMAC-SHA256, base64(NO_WRAP).
        """
        m = re.search(r"(/v\d+.*)$", path)
        path_tail = m.group(1) if m else path
        msg = method + "\n" + path_tail
        if query:
            msg += "\n" + query
        if body:
            msg += "\n" + body
        digest = hmac.new(self.mobile_sessionid.encode("utf-8"),
                          msg.encode("utf-8"), hashlib.sha256).digest()
        return base64.b64encode(digest).decode("ascii")


    PAY_DEVICE_CONSTANTS = {
        "colorDepth": "24",
        "debug": "0",
        "emulator": "0",
        "jailbreak": "false",
        "javaEnabled": "false",
        "javaScriptEnabled": "true",
        "notificationUrl": "https://api.t-bank-app.ru/v1/3ds",
    }


    PAY_DEVICE_DEFAULTS = {
        "device_screen_height": "2736",
        "device_screen_width": "1260",
        "language": "ru-CY",
        "timezone": "180",
    }


    DEVICE_MODEL = "iPhone18,4"


    def device_model(self) -> str:
        """Hardware identifier for the endpoints that ask for one (card_credentials,
        the messenger's Tmsg-User-Agent). TBANK_DEVICE_MODEL overrides it."""
        return str((getattr(self, "device_profile", None) or {}).get("model")
                   or self.DEVICE_MODEL)


    def PAY_DEVICE_PROFILE(self) -> dict:
        """The full block: constants + this session's device facts."""
        # getattr, not self.device_profile: __post_init__ sets it, and the test
        # sessions build the object without running it.
        override = getattr(self, "device_profile", None) or {}
        # `model` is filtered out on purpose — it belongs to the device, not to the
        # payment block, and no captured /v1/pay carries it.
        return {**self.PAY_DEVICE_CONSTANTS, **self.PAY_DEVICE_DEFAULTS,
                **{k: str(v) for k, v in override.items() if v and k != "model"}}


    def _call_signed(self, template_key: str, body_str: str,
                     extra_query: dict | None = None) -> Any:
        """POST a signed request (private; only pay_execute/human use)."""
        url, headers, body_str = self._signed_parts(template_key, body_str, extra_query)
        r = self._http.post(url, data=body_str, headers=headers, timeout=30)
        return self._unwrap(r)


    def _signed_parts(self, template_key: str, body_str: str,
                      extra_query: dict | None = None) -> tuple[str, dict, str]:
        """Build the signed POST request parts (url, headers, body)."""
        tpl = self._tpl(template_key)
        if not tpl:
            raise TbankApiError("NO_TEMPLATE", f"no endpoint shape for '{template_key}'")
        params = {k: v for k, v in tpl.get("params", {}).items() if k not in _LIVE_QUERY}
        params["sessionid"] = self.mobile_sessionid
        # The real /v1/pay carries deviceId + oldDeviceId and NO wuid (wuid is the
        # web/portal identifier; it appears on www.tbank.ru calls, not on this one).
        # The signature covers the query string, so what goes here is what gets signed.
        params["deviceId"] = self.device_id
        params["oldDeviceId"] = self.old_device_id or self.device_id
        params.update(self.PAY_DEVICE_PROFILE)
        if extra_query:
            params.update(extra_query)
        # `:` is safe too: both captured /v1/pay requests send the notificationUrl's
        # scheme separator literally in the QUERY (`https://…`), while the copy in
        # the form body is percent-encoded — the app really does differ between the
        # two. The signature covers whatever we send, so this is fidelity, not a fix.
        query = urllib.parse.urlencode(params, safe="%/,:")
        host = tpl.get("host") or self.base_url
        path = tpl["path"]
        url = f"{host.rstrip('/')}/{path.lstrip('/')}?{query}"
        sig = self._sign("POST", path, query, body_str)
        headers = {k: v for k, v in tpl.get("headers", {}).items()
                   if k.lower() not in _LIVE_HEADERS}
        # The signature covers METHOD + path + query + body, never the headers, so
        # these are free to match the app — and they must. The query declares
        # platform=ios and a whole iOS device profile, while the User-Agent came
        # from the requests.Session default and said `okhttp/4.12.0`: an Android
        # HTTP client posting an iPhone's anti-fraud block. The captured native
        # /v1/pay sends the mobile UA together with X-Lang and this Accept.
        for k, v in self._mobile_headers(host, path).items():
            headers.setdefault(k, v)
        # The captured pay asks for the native default. Set explicitly rather than
        # left to _accept_for, because this one is verified against the capture and
        # must not follow the profile switch in either direction.
        headers["Accept"] = _NATIVE_ACCEPT
        headers["Authorization"] = "Bearer " + self.access_token
        headers["x-api-signature"] = sig
        if self._wide_cookie():
            headers["Cookie"] = self._wide_cookie()
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=utf-8;"
        return url, headers, body_str


    def pay(self, body: str | None = None) -> Any:
        """POST v1/pay — REAL signed payment (moves money). body = raw form-encoded
        payParameters=...; None = replay the default pay body. Signed with
        x-api-signature (HMAC-SHA256, key=sessionid).

        The device/anti-fraud fields are prepended here rather than by every caller,
        so no payment can go out without them."""
        tpl = self._tpl("v1_pay")
        if not tpl:
            raise TbankApiError("NO_TEMPLATE", "no v1/pay in capture")
        body_str = body if body is not None else (tpl.get("body") or "")
        if "payParameters=" in body_str and "notificationUrl=" not in body_str:
            prefix = urllib.parse.urlencode(self.PAY_DEVICE_PROFILE)
            body_str = prefix + "&" + body_str
        return self._call_signed("v1_pay", body_str)


    def _wide_cookie(self) -> str:
        """cookie_str, narrowed to what every host is supposed to receive.

        Applied where the value is USED, not only where it is assigned: a
        session.json written before this existed still holds the whole login jar,
        and it is loaded straight into the field."""
        return wide_cookies(self.cookie_str)


    def _optional_cookies(self, names: tuple[str, ...]) -> str:
        """Read an explicit cookie allowlist from saved SSO state, if present."""
        if self.sso_id and "ssoId" in names:
            return selected_cookies(f"ssoId={self.sso_id}", names)
        found = selected_cookies(self.sso_login_cookie, names)
        if found:
            return found
        found = selected_cookies(self.cookie_str, names)
        if found:
            return found
        jar = getattr(getattr(self, "_http", None), "cookies", None)
        if jar is None:
            return ""
        values = jar.get_dict()
        return "; ".join(
            f"{name}={values[name]}" for name in names if values.get(name))


    def _cookie_for(self, host: str) -> str:
        """The Cookie header this host expects, or "".

        Hosts do not agree on how the session reaches them, and the disagreement
        is not a detail: the messenger accepts ONLY its own minted JWT, and
        sending it the SSO cookie instead of that authorises nothing. Keeping the
        per-host answer in one place is what stops a new host from inheriting
        whichever branch happened to be last."""
        if "tm.t-bank-app.ru" in host:
            # Minted on demand from the access_token via issueTokenBySSO.
            self._ensure_tmsg()
            return f"tmsgSessionID={self.tmsg_session_id}" if self.tmsg_session_id else ""
        if "trains.t-bank-app.ru" in host:
            self._ensure_trains()
            return self.trains_cookie
        if "webview.t-bank-app.ru" in host:
            # The shopping webview sends no Authorization at all — 179 captured
            # requests, not one Bearer — and authorises on cookies whose sessionID
            # and sso_api_session both hold the very access_token we already have.
            # deviceId rides uppercase there, as the app writes it.
            return (f"sessionID={self.access_token}; "
                    f"sso_api_session={self.access_token}; "
                    f"deviceId={(self.device_id or '').upper()}")
        return self._wide_cookie()


    TRAINS_TTL = 3600.0     # the Set-Cookie expiry runs ~2h; re-mint well inside it


    def _ensure_trains(self) -> None:
        """Mint the rail host's own cookie, in an ISOLATED jar.

        One request does it: GET https://trains.t-bank-app.ru/ with the ordinary
        mobile Bearer answers with Set-Cookie carrying sessionID and the travel
        session id, and the search API accepts those.

        The isolation is not tidiness. That same response also clears the cookie
        for the tbank.ru domain, so minting this inside the shared jar would race
        every other host mid-flight."""
        if self.trains_cookie and time.time() - self.trains_cookie_at < self.TRAINS_TTL:
            return
        jar = requests.Session()
        try:
            from . import tls as _tls
            _tls.rebuild_bundle()
            jar.mount("https://", _tls.RobustTLSAdapter())
            jar.verify = _tls.BUNDLE
        except Exception:
            pass
        jar.get("https://trains.t-bank-app.ru/",
                params={"iswebview": "true", "os": "ios", "language": "ru",
                        "appName": self.app_name, "appVersion": self.app_version},
                headers={"Authorization": "Bearer " + self.access_token,
                         "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
                         "User-Agent": self._mobile_ua() or "okhttp/4.12.0"},
                timeout=30, allow_redirects=True)
        got = jar.cookies.get_dict()
        wanted = [f"{k}={v}" for k, v in got.items()
                  if k in ("sessionID", "SSO_ID", "_T_travel_session_id",
                           "SSO_ID_TOKEN", "SSO_VALIDATION")]
        if wanted:
            self.trains_cookie = "; ".join(wanted)
            self.trains_cookie_at = time.time()
            self._persist()


    def silent_relogin(self) -> dict:
        """Silent gorod-app re-login (NO OTP): uses the long-lived SSO_SESSION +
        the static fingerprint blob. auth/authorize(gorod-app, SSO_SESSION) ->
        auth/step(fingerprint) -> code -> /auth/token/mobile (auth_code) ->
        fresh SSO-valid access_token + mobile sessionid + refresh_token.

        This is how the phone re-mints a login access_token for the messenger
        tmsg. Persistent as long as the SSO_SESSION cookie is alive (days/weeks).
        """
        if not self.sso_login_cookie or not self.auth_step_fingerprint:
            raise TbankApiError("NO_SSO_SESSION", "no SSO_SESSION cookie / fingerprint "
                                "— call login(phone)+confirm_otp(otp) first to get SSO_SESSION.")
        claims = ('{"id_token":{"given_name":{"essential":true},'
                  '"phone_number":{"essential":true},"picture":{"essential":true},'
                  '"api_sso_id":{"essential":true}}}')
        state = str(__import__("uuid").uuid4()).upper()
        params = {"claims": claims, "client_version": self.client_version,
                  "state": state, "redirect_uri": "mobile://", "response_type": "code",
                  "cpswc": "true", "device_id": self.device_id, "client_id": "gorod-app",
                  "ccc": "true", "response_mode": "json", "display": "json",
                  "vendor": self.vendor}
        # use a session with the SSO cookies in the jar (so SSO_CONVERSATION_CSRF
        # from the authorize Set-Cookie auto-attaches to the step call)
        base = {"Accept": "application/json", "User-Agent": "okhttp/4.12.0"}
        r = self._http.get("https://id.t-bank-app.ru/auth/authorize", params=params,
                          headers={**base, "Cookie": self.sso_login_cookie}, timeout=30)
        rj = self._unwrap(r)
        cid = rj.get("cid")
        if not cid:
            raise TbankApiError("NO_CID", f"authorize: {json.dumps(rj)[:200]}")
        # copy SSO cookies into the session jar so the step auto-sends CSRF
        for c in self.sso_login_cookie.split(";"):
            c = c.strip()
            if "=" in c:
                k, v = c.split("=", 1)
                self._http.cookies.set(k, v, domain="id.t-bank-app.ru")
        body = "step=fingerprint&fingerprint=" + urllib.parse.quote(
            self.auth_step_fingerprint, safe="")
        r2 = self._http.post(
            f"https://id.t-bank-app.ru/auth/step?cid={cid}&ccc=true&cpswc=true",
            data=body,
            headers={**base, "Content-Type": "application/x-www-form-urlencoded"},
            timeout=30)
        r2j = self._unwrap(r2)
        code = r2j.get("code")
        if not code:
            raise TbankApiError("NO_CODE", f"step: {json.dumps(r2j)[:200]}")
        tb = (f"device_id={self.device_id}&client_version={self.client_version}"
              f"&grant_type=authorization_code&appVersion={self.app_version or APP_VERSION}"
              f"&origin={self.origin}&vendor={self.vendor}&code={code}"
              f"&platform={self.platform}&appName={self.app_name}"
              f"&redirect_uri=mobile%3A%2F%2F")
        r3 = self._http.post(
            "https://id.t-bank-app.ru/auth/token/mobile?ccc=true&cpswc=true",
            data=tb,
            headers={**base, "Authorization": self._basic_auth(),
                     "Content-Type": "application/x-www-form-urlencoded",
                     "X-SSO-No-Adapter": "true", "Cookie": self.sso_login_cookie},
            timeout=30)
        tok = self._unwrap(r3)
        if not isinstance(tok, dict) or "access_token" not in tok:
            raise TbankApiError("NO_TOKEN", f"token/mobile: {str(tok)[:200]}")
        # silent_relogin gives a session valid for BOTH reads and the messenger
        # tmsg (unlike the refresh_grant session, which is read-only). Update the
        # unified session: access_token + mobile.sessionid + refresh_token.
        self.access_token = tok["access_token"]
        self.refresh_token = tok.get("refresh_token", self.refresh_token)
        self.expires_in = tok.get("expires_in", self.expires_in) or self.expires_in
        mobile = tok.get("mobile") or {}
        self.mobile_sessionid = mobile.get("sessionid", self.mobile_sessionid)
        self._minted_at = time.time()
        self.tmsg_session_id = ""  # force tmsg re-mint with the fresh access_token
        # the freshly-minted session needs a moment to propagate before mobile
        # reads accept it (else INSUFFICIENT_PRIVILEGES) — poll instead of a
        # blind wait, since most of the time it's ready sooner than 3s.
        _wait_for_propagation(self.keepalive)
        self._persist()          # same reason as in refresh(): the token rotated
        return tok


    def login(self, phone: str) -> str:
        """Start a real SSO login (no capture needed). POSTs the phone number to
        auth/step; the bank sends an SMS OTP. Returns a message asking to call
        confirm_otp(otp) with the code. Stores cid + the otp-step token.
        phone = full international form, e.g. +79991234567."""
        base = {"Accept": "application/json", "User-Agent": "okhttp/4.12.0"}
        claims = ('{"id_token":{"given_name":{"essential":true},'
                  '"phone_number":{"essential":true},"picture":{"essential":true},'
                  '"api_sso_id":{"essential":true}}}')
        state = str(__import__("uuid").uuid4()).upper()
        params = {"claims": claims, "client_version": self.client_version,
                  "state": state, "redirect_uri": "mobile://", "response_type": "code",
                  "cpswc": "true", "device_id": self.device_id, "client_id": "gorod-app",
                  "ccc": "true", "response_mode": "json", "display": "json",
                  "vendor": self.vendor}
        # authorize (no SSO_SESSION) — the jar captures SSO_CONVERSATION_CSRF
        r = self._http.get(f"{ID_BASE}/auth/authorize", params=params, headers=base, timeout=30)
        rj = self._unwrap(r)
        cid = rj.get("cid")
        if not cid:
            raise TbankApiError("NO_CID", f"authorize: {json.dumps(rj)[:200]}")
        self._login_cid = cid
        # step=phone — triggers the SMS OTP
        body = ("step=phone&phone=" + urllib.parse.quote(phone, safe="")
                + "&fingerprint=" + urllib.parse.quote(self.auth_step_fingerprint, safe=""))
        r2 = self._http.post(f"{ID_BASE}/auth/step?cid={cid}&ccc=true&cpswc=true",
                            data=body, headers={**base, "Content-Type": "application/x-www-form-urlencoded"},
                            timeout=30)
        r2j = self._unwrap(r2)
        self._login_token = r2j.get("token", "") or ""
        return _next_step_hint(r2j)


    def confirm_step(self, kind: str, value: str) -> dict:
        """Finish the login: submit the OTP (kind='otp') or PIN (kind='pin') or
        password (kind='password'), get the auth code, exchange it at
        auth/token/mobile -> session. Captures SSO_SESSION. Chains the token
        from each step's response to the next."""
        if not self._login_cid:
            raise TbankApiError("NO_LOGIN", "call login(phone) first")
        base = {"Accept": "application/json", "User-Agent": "okhttp/4.12.0"}
        body = f"step={kind}&{kind}=" + urllib.parse.quote(str(value), safe="")
        if self._login_token:
            body += f"&token={self._login_token}"
        r = self._http.post(f"{ID_BASE}/auth/step?cid={self._login_cid}&ccc=true&cpswc=true",
                           data=body, headers={**base, "Content-Type": "application/x-www-form-urlencoded"},
                           timeout=30)
        # parse the response directly (auth/step doesn't use resultCode envelope)
        try:
            rj = r.json()
        except Exception:
            raise TbankApiError("HTTP_" + str(r.status_code), r.text[:300])
        # chain the token from this response to the next step
        new_token = rj.get("token", "")
        if new_token:
            self._login_token = new_token
        # if error in the response, raise with full detail — redact BEFORE the
        # 300-char cut, not after: a token/phone that lands near the boundary
        # would otherwise survive as a truncated (still readable) fragment.
        if rj.get("error"):
            raise TbankApiError(str(rj.get("error")),
                                json.dumps(_redact_value(rj), ensure_ascii=False)[:300])
        code = rj.get("code")
        if not code:
            # Not an error: the login is alive and the bank named the NEXT step in
            # the response. This used to dump the raw JSON under "NO_CODE", so the
            # ordinary first-device flow (otp → password) read to the agent as a
            # failure, with the tool it needed to call next sitting unread in the
            # blob. login() has parsed the same field all along.
            raise TbankApiError("NEXT_STEP", _next_step_hint(rj))
        # exchange the code for the mobile session
        tb = (f"device_id={self.device_id}&client_version={self.client_version}"
              f"&grant_type=authorization_code&appVersion={self.app_version or APP_VERSION}"
              f"&origin={self.origin}&vendor={self.vendor}&code={code}"
              f"&platform={self.platform}&appName={self.app_name}"
              f"&redirect_uri=mobile%3A%2F%2F")
        r3 = self._http.post(f"{ID_BASE}/auth/token/mobile?ccc=true&cpswc=true",
                           data=tb, headers={**base, "Authorization": self._basic_auth(),
                                             "Content-Type": "application/x-www-form-urlencoded",
                                             "X-SSO-No-Adapter": "true"}, timeout=30)
        tok = self._unwrap(r3)
        if not isinstance(tok, dict) or "access_token" not in tok:
            raise TbankApiError("NO_TOKEN", f"token/mobile: {str(tok)[:200]}")
        self.access_token = tok["access_token"]
        self.refresh_token = tok.get("refresh_token", self.refresh_token)
        self.expires_in = tok.get("expires_in", self.expires_in) or self.expires_in
        mobile = tok.get("mobile") or {}
        self.mobile_sessionid = mobile.get("sessionid", self.mobile_sessionid)
        self._minted_at = time.time()
        # capture the SSO_SESSION cookie from the jar (set during login) for
        # silent re-login + messenger.
        self.sso_login_cookie = "; ".join(
            f"{c.name}={c.value}" for c in self._http.cookies
            if c.domain and "t-bank-app.ru" in c.domain)
        # A full login may switch to another user. Never carry the previous
        # public web identity into the new session; session_status() will learn
        # and persist the matching ssoId on its next call.
        self.sso_id = ""
        self.hotels_cookie = ""
        self.hotels_cookie_at = 0.0
        # NOT the whole jar. sso_login_cookie keeps every cookie because
        # silent_relogin replays it against id.t-bank-app.ru, which is the one host
        # that issued SSO_SESSION and the one host that should ever see it again.
        self.cookie_str = wide_cookies(self.sso_login_cookie)
        self.tmsg_session_id = ""
        self._login_cid = self._login_token = ""
        _wait_for_propagation(self.keepalive)  # propagation, like silent_relogin
        return tok


    _TMSG_AUTH_CODES = {"AUTH_REQUIRED", "TOKEN_EXPIRED", "UNAUTHORIZED"}


    _SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


    _SAFE_FILE_ID_RE = re.compile(r"^[A-Za-z0-9_=-]{1,256}$")


    OPERATIONS_ALL_LIMIT = 200


    def session_status(self) -> dict:
        # www.tbank.ru/api/common/v1/session_status (web gateway) — confirmed WORKING
        # with the mobile session: the SSO cookie in cookie_str authenticates it.
        # (Audit flagged www.tbank.ru as a 'different realm', but live use proves it
        # returns accessLevel/SSO TTL/userId — do NOT reroute or 'fix'.)
        data = self._call_read("session_status")
        sso_id = data.get("ssoId") if isinstance(data, dict) else None
        if (isinstance(sso_id, str) and sso_id and ";" not in sso_id
                and sso_id != self.sso_id):
            self.sso_id = sso_id
            self._persist()
        return data


    def _call_userinfo(self) -> dict:
        """GET /userinfo/userinfo (id.t-bank-app.ru) — the gorod-app SSO IdP OIDC
        UserInfo. Capture-verified shape: client_id=<gorod-app> + ccc/cpswc +
        Authorization: Bearer + the t-bank-app.ru jar cookies (which carry the SSO
        tracking set). The generic _call_read OMITS client_id and adds mobile-BFF
        params, which the IdP rejects with HTTP 401 (research-workflow confirmed
        across 3 captures). Reuses self.client_id (= gorod-app), no new literal."""
        r = self._http.get(
            "https://id.t-bank-app.ru/userinfo/userinfo",
            params={"ccc": "true", "cpswc": "true", "client_id": self.client_id or "gorod-app"},
            headers={"Accept": "*/*",
                     "Authorization": "Bearer " + self.access_token,
                     **({"Cookie": self._wide_cookie()} if self._wide_cookie() else {})},
            timeout=30)
        return self._unwrap(r)


    def keepalive(self) -> Any:
        """POST v1/ping — keep the mobile session alive (unsigned)."""
        return self._call_read("ping")


    def unread_count(self) -> dict:
        return self._call_read("notification_count")


    def profile_lite(self) -> dict:
        return self._call_read("profile_own_lite")


    def get_ip(self) -> dict:
        """Egress IP of the session (connectivity/geo sanity)."""
        return self._call_read("get_ip")


    def push_unread_count(self) -> dict:
        """Unread push-notification count."""
        return self._call_read("push_unread_count")


    GROUP_ALIASES = {
        "ЖКХ": "Коммунальные платежи",
        "Интернет, ТВ и телефония": "Интернет ТВ и телефония",
    }


    _NOT_THE_FRESH_THING = ("сушен", "молот", "приправа", "смесь", "концентрат",
                            "экстракт", "ароматизат", "в горшочке", "семена")


    _SPICE_QUERIES = ("приправ", "перец", "специ", "паприк", "куркум", "зира",
                      "кориц", "лавров", "базилик", "орегано", "хмели")


    _MIN_SANE_GRAMS = 50.0


    _MATCH_STOPWORDS = frozenset(
        "из для со с по и на в от до без вкусом со_вкусом".split())


    def _as_list(d: Any) -> list[dict]:
        if isinstance(d, list):
            return d
        if isinstance(d, dict):
            # grocery API: payload = {"list": [...]} → _unwrap returns {"list": [...]}
            if "list" in d and isinstance(d["list"], list):
                return d["list"]
            pl = d.get("payload")
            if isinstance(pl, list):
                return pl
            if isinstance(pl, dict):
                return [pl]
            if "payload" in d:
                return [d["payload"]]
            return [d]
        return []


    _AUTH_STATUS = (401, 403)


    def _unwrap(self, resp: requests.Response) -> Any:
        ok = 200 <= resp.status_code < 300
        try:
            data = resp.json()
        except ValueError:
            resp.raise_for_status()
            # HTTP 200 and an unparseable body. See UnreadableResponse: the request
            # was processed by SOMETHING, so this is an unknown outcome, not a
            # confirmed non-event.
            raise UnreadableResponse("HTTP_" + str(resp.status_code),
                                     _excerpt(resp.text, 500))
        if isinstance(data, dict):
            # api.tinsurance.ru envelopes with a capital `ResultCode`; matching only
            # the lowercase spelling handed its ERROR envelope back as data, and the
            # tool printed «Действующих полисов нет.» for a failed request.
            code = (data.get("resultCode") or data.get("ResultCode")
                    or data.get("error") or "")
            # Case-insensitive on the VALUE as well as the key. api.tinsurance.ru
            # says {"ResultCode": "Ok"} — capital R, lowercase k — so reading the
            # capital key without also relaxing the value turned that host's every
            # SUCCESS into «API error (Ok)». Caught by a live sweep, not by a test:
            # no fixture carried this host's exact spelling.
            if code and str(code).lower() not in ("ok", "0", "success", ""):
                msg = data.get("errorMessage") or data.get("error_description") or data.get("plainMessage") or ""
                lc = str(code)
                # Accepted-pending-a-second-factor comes back through THIS branch (a
                # non-ok resultCode), but it is not a failure: raise the resumable
                # exception that keeps the envelope instead of the terminal one that
                # discards it. Checked before SessionExpired so a confirmation is
                # never mistaken for a dead session.
                if lc.upper() in _PAYMENT_CONFIRMATION_CODES:
                    raise self._payment_confirmation_error(resp, data, lc, str(msg))
                if lc in _SESSION_EXPIRED or "session" in lc.lower() or "authoriz" in lc.lower() or lc == "invalid_grant":
                    raise SessionExpired(lc, str(msg))
                raise TbankApiError(lc, str(msg))
            # The lifestyle/Город envelope signals failure with HTTP 200 +
            # {"status":"Error","payload":{"message":..,"code":..,"blame":..}} — it uses
            # neither resultCode nor error, so the check above misses it and the ERROR
            # payload gets returned as a success value. That is how a rejected
            # grocery cart/set surfaced as `OK: goodsSum=?`: the caller read goodsSum
            # off an error body. "Ok"/"ok"/"OK" and "Error" are the only status values
            # across all 447 enveloped responses in the capture.
            st = data.get("status")
            if isinstance(st, str) and st.lower() == "error":
                err = data.get("payload") if isinstance(data.get("payload"), dict) else {}
                ec = str(err.get("code") or "Error")
                em = str(err.get("message") or err.get("plainMessage") or "")
                if ec in _SESSION_EXPIRED or "session" in ec.lower() or "authoriz" in ec.lower():
                    raise SessionExpired(ec, em)
                raise TbankApiError(ec, em)
            # The body parsed and claimed nothing was wrong — but the STATUS did.
            #
            # This runs AFTER the envelope checks on purpose. The OIDC token endpoint
            # answers HTTP 400 with {"error":"invalid_grant"}, and that mapping to
            # SessionExpired is what drives the silent re-login; checking the status
            # first would turn it into a generic HTTP_400 and break re-login on the
            # one path that recovers a dead session. So a body that names its own
            # error still produces that error, and the status is the fallback.
            #
            # Before this existed, `_call_read` never looked at the status either, so
            # a 404 whose body was ordinary JSON came back to the caller AS THE
            # PAYLOAD: tm answers 404 {"errorCode":"FAQ_NOT_FOUND",…} and
            # webview 404 {"message":"Not Found"}, and ~40 read tools rendered that as
            # an empty list — «ничего не найдено» for a request that failed.
            if not ok:
                raise self._status_error(resp, data)
            # unwrap envelope: payload (mobile API) or result (messenger)
            if "payload" in data:
                return data["payload"]
            if "result" in data:
                return data["result"]
            return data
        if not ok:
            raise self._status_error(resp, data)
        return data


    def _payment_confirmation_error(self, resp: requests.Response, data: dict,
                                    code: str, msg: str) -> "PaymentConfirmationRequired":
        """Build the resumable error from a WAITING_CONFIRMATION envelope.

        Field names are capture-verified; everything sits at the TOP LEVEL, not under
        ``payload`` —

            operationTicket, initialOperation, confirmations:[<type>],
            confirmationData:{<type>:{codeLength, paymentId, codeType}}

        The confirmation type is kept LITERAL (e.g. "SMSBYID") because /v1/confirm
        echoes it back verbatim. The whole body is still stored redacted under
        ``.payload`` for reconciliation."""
        confirmations = data.get("confirmations")
        confirmations = [str(c) for c in confirmations] if isinstance(confirmations, list) else []
        ctype = confirmations[0] if confirmations else str(data.get("confirmationType") or "")
        cdata = data.get("confirmationData") if isinstance(data.get("confirmationData"), dict) else {}
        detail = cdata.get(ctype) if isinstance(cdata.get(ctype), dict) else {}
        request_id = (resp.headers.get("X-Tracking-Id")
                      or resp.headers.get("x-tracking-id")
                      or str(data.get("trackingId") or "")) or ""
        return PaymentConfirmationRequired(
            code, msg,
            http_status=resp.status_code,
            payload=_redact_value(data) if isinstance(data, dict) else {},
            operation_ticket=str(data.get("operationTicket") or data.get("operation_ticket") or ""),
            initial_operation=str(data.get("initialOperation") or "pay"),
            confirmation_type=ctype,
            confirmations=confirmations,
            code_length=int(detail.get("codeLength") or 0),
            payment_id=str(detail.get("paymentId") or ""),
            request_id=request_id,
            method="POST",
            url="",
        )


    def _status_error(self, resp: requests.Response, data: Any) -> TbankApiError:
        """The error for a non-2xx whose body did not declare one itself."""
        msg = ""
        if isinstance(data, dict):
            for key in ("errorMessage", "message", "error_description",
                        "plainMessage", "detail"):
                if data.get(key):
                    msg = str(data[key])
                    break
            # The server's own code is the machine-readable half and is what an
            # agent can act on ("FAQ_NOT_FOUND" says retrying is pointless, where
            # the prose does not). Keep both when both exist.
            if data.get("errorCode"):
                msg = f"{data['errorCode']}: {msg}" if msg else str(data["errorCode"])
        code = str(resp.status_code)
        if not msg:
            msg = resp.text
        # Excerpted once, here, on the way out — not at each of the branches above.
        # The first version marked only the fallback, so a body carrying a 4 KB
        # `message` field sailed through whole while a raw body was cut: the same
        # defect, one level up, and invisible until a test fed it 4 000 characters.
        msg = _excerpt(msg)
        if resp.status_code in self._AUTH_STATUS:
            return SessionExpired("HTTP_" + code, msg)
        return TbankApiError("HTTP_" + code, msg)


    _GROCERY_CATEGORIES = {
        "свекл": "ОФ", "капуст": "ОФ", "картоф": "ОФ", "морков": "ОФ",
        "лук": "ОФ", "чеснок": "ОФ", "огурц": "ОФ", "помидор": "ОФ",
        "яблок": "ОФ", "банан": "ОФ", "зелён": "ОФ", "салат": "ОФ",
        "говядин": "МК", "свинин": "МК", "куриц": "МК", "колбас": "МК",
        "мяс": "МК", "фарш": "МК", "сосиск": "МК", "сардель": "МК",
        "молок": "МЛ", "сыр": "МЛ", "твор": "МЛ", "сметан": "МЛ",
        "йогурт": "МЛ", "масл": "МЛ", "яйц": "МЛ", "кефир": "МЛ",
        "томатн": "БК", "мук": "БК", "сахар": "БК", "соль": "БК",
        "круп": "БК", "рис": "БК", "греч": "БК", "макарон": "БК",
        "вермиш": "БК", "хлеб": "БК", "уксус": "БК", "перец": "БК",
        "вод": "ВН", "напит": "ВН", "сок": "ВН", "чай": "КЧ",
        "кофе": "КЧ", "морож": "ЗМ",
    }


    _PREPARED_FOOD_WORDS = (
        "готов", "салат", "боул", "зразы", "пельмен", "голубцы", "винегрет",
        "бифштекс", "сельд", "котлет", "суп", "соус", "пюре", "тушен",
        "бульон", "бутерброд", "ролл", "бургер", "пицц", "шаурм", "воки",
        "жарен", "варен", "запекан", "запеч", "гриль", "маринов",
        "нарезка", "ассорти", "боул", "паназиат", "ризотт", "паэл",
        "рагу", "жюльен", "тартар", "карпаччо", "чипс", "снек",
    )


    SEARCH_SCREENS = ("services", "afisha", "movie_main", "grocery",
                      "concerts_main", "spectacle_main", "exhibition_main")


    def _search_params(self, screen: str, **extra) -> dict:
        """Common query string for the search host."""
        params = {
            "screen": screen, "appName": self.app_name,
            "appVersion": self.app_version, "platform": self.platform,
            "origin": self.origin, "deviceId": self.device_id,
            "oldDeviceId": self.old_device_id, "ccc": self.ccc,
            "cpswc": self.cpswc, "connectionType": self.connection_type,
            "inache": self.inache,
        }
        params.update({k: v for k, v in extra.items() if v not in (None, "")})
        return params


    def _search_post(self, params: dict, body: dict) -> dict:
        r = self._http.post("https://search.t-bank-app.ru/search/fulltext",
                            params=params, json=body,
                            headers={"Accept": "application/json",
                                     "User-Agent": "okhttp/4.12.0",
                                     "Authorization": "Bearer " + self.access_token},
                            timeout=30)
        payload = self._unwrap(r)
        return payload if isinstance(payload, dict) else {}


    def app_search(self, text: str, screen: str = "services",
                   limit: int = 20) -> list[dict]:
        """Full-text search across an app section. Returns the raw hits
        (objectType + objectSource) — the caller decides how to render them.

        The body is minimal on purpose: the real app also sends a `toggles` map of
        ~12 feature flags, but the endpoint answers identically without it
        (verified live), so there is nothing to keep in sync."""
        if screen not in self.SEARCH_SCREENS:
            raise TbankApiError("BAD_SEARCH_SCREEN",
                f"unknown screen {screen!r}; valid: {', '.join(self.SEARCH_SCREENS)}")
        payload = self._search_post(
            self._search_params(screen),
            {"text": text, "maxObjectsCount": max(1, limit), "screenContext": {}})
        hits = payload.get("sortedByScoreObjects") or []
        return [h for h in hits if isinstance(h, dict)][:limit]


    GROCERY_SEARCH_FLOOR = 30       # network's natural page — the min ranking pool


    GROCERY_PROBE_FETCH = 100       # the limit=0 ceiling


    GROCERY_MATCH_OK = 0.67         # plan_order: below this the pick is «⚠ проверь», not ✓


    CLIENT_INFO_TTL = 60.0


    PROVIDER_TTL = 60.0


    HOTEL_LIST_PAGE = 50


    HOTEL_SEARCH_RETURN_CAP = 50


    HOTEL_SEARCH_WAIT_S = 18.0


    HOTEL_SEARCH_POLL_S = 0.45


    CITY_CENTRES = {
        "Москва": (55.7558, 37.6173),
        "Санкт-Петербург": (59.9386, 30.3141),
        "Екатеринбург": (56.8389, 60.6057),
        "Новосибирск": (55.0084, 82.9357),
        "Казань": (55.7963, 49.1088),
    }


    CATALOG_PAGE = 20


    PLACES_PAGE = 100              # the endpoint's ceiling: 116 answers 400
