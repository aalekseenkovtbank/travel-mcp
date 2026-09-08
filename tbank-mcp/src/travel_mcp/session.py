"""Travel MCP session lifecycle and credential persistence."""
from __future__ import annotations

import json
import os
import sys
import threading

from ..client import MobileSession, TbankApiError
from ..endpoints import APP_VERSION

_session: MobileSession | None = None

_session_mtime: float | None = None

_public_flight_session: MobileSession | None = None

_RECEIPTS_DIR = os.environ.get(
    "TBANK_RECEIPTS",
    os.path.expanduser("~/.local/share/tbank-mcp/receipts"),
)

_CHAT_FILES_DIR = os.environ.get(
    "TBANK_CHAT_FILES",
    os.path.expanduser("~/.local/share/tbank-mcp/chat-files"),
)

_SESSION_FILE = os.environ.get(
    "TBANK_SESSION",
    os.path.expanduser("~/.local/share/tbank-mcp/session.json"),
)

_CHECKOUT_LOCK = threading.Lock()

def _blank_session():
    return _with_persist(MobileSession(mobile_sessionid="", refresh_token="",
        client_id="gorod-app", client_version="112.0.0",
        vendor="t_ios", origin="mobile,ib5,loyalty,platform",
        platform="ios", app_name="mobile", app_version=APP_VERSION))

def _with_persist(s):
    """Make the session save itself after every re-mint.

    Not an optimisation: refresh() rotates the refresh_token, and ensure_fresh()
    runs on the first call of nearly every tool. A re-mint that never reaches disk
    leaves the next process holding a spent token, which then falls back to
    silent_relogin and degrades the session to ANONYMOUS — see
    MobileSession._persist for the full chain."""
    if s is not None:
        s._on_persist = lambda: _save_session(s)
    return s

def _write_json_0600(path: str, d: dict, label: str) -> None:
    """Write a credential file atomically, owner-only.

    Written to a temp file and renamed, never truncated in place. O_TRUNC
    empties the real file BEFORE the new bytes exist, so an interruption
    anywhere in between — a crash, a kill, a full disk — left a zero-length or
    half-written session.json, and the next start had no session at all. The
    cost of that is a phone-and-SMS login, which is the one thing this file
    exists to avoid. os.replace is atomic within a filesystem, so a reader
    sees either the old session or the new one.

    A separate function rather than inline code because the next credential file
    somebody adds will otherwise be written the obvious way and inherit the
    truncation bug."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + f".tmp{os.getpid()}"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(d, fh, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())         # rename is atomic; the CONTENT must land too
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    os.chmod(path, 0o600)
    print(f"[tbank] {label} saved: {path} ({os.path.getsize(path)} bytes, 0600)", file=sys.stderr)

def _mtime_or_none(path: str):
    try:
        return os.stat(path).st_mtime
    except OSError:
        return None

def _save_session(s) -> bool:
    """Save session to disk with 0600 permissions. Returns whether it landed.

    Persists _minted_at for correct expiry tracking across restarts.

    The failure is still not raised — a read-only HOME must not break reads, which
    is why MobileSession._persist swallows it too. But «не сломало чтение» и «можно
    отвечать ОК» — разные вещи: тулы, чья ЦЕЛЬ оставить после себя рабочую сессию
    (confirm_*, refresh_session), обязаны знать, что записи не было, иначе они
    рапортуют «Сессия активна» про сессию, которой после перезапуска не будет.
    Отсюда возвращаемое значение вместо голого None."""
    global _session_mtime
    try:
        d = {k: v for k, v in s.__dict__.items() if not k.startswith("_") or k == "_minted_at"}
        _write_json_0600(_SESSION_FILE, d, "session")
        # Our own write must not later read as someone else's re-login.
        _session_mtime = _mtime_or_none(_SESSION_FILE)
        return True
    except OSError as e:
        print(f"[tbank] session save failed: {e}", file=sys.stderr)
        return False

_SAVE_FAILED = ("OK, сессия активна В ЭТОМ ПРОЦЕССЕ, но на диск НЕ записана "
                f"({{}}) — после перезапуска она не поднимется. Проверь права на "
                f"{os.path.dirname(_SESSION_FILE)} и повтори; иначе понадобится "
                f"полный логин.")

def _saved_or_warn(s) -> str:
    return "OK. Сессия активна." if _save_session(s) else _SAVE_FAILED.format(_SESSION_FILE)

def _load_session():
    if not os.path.exists(_SESSION_FILE):
        print(f"[tbank] no session file: {_SESSION_FILE}", file=sys.stderr)
        return None
    try:
        # Explicit encoding and a closed handle: the writer uses utf-8 and
        # ensure_ascii=False, while a bare open() decodes with whatever the process
        # locale happens to be — the two only agreed by accident.
        with open(_SESSION_FILE, encoding="utf-8") as fh:
            d = json.load(fh)
        # keep known non-underscore fields + _minted_at; drop runtime fields (_http,
        # _login_*) and removed fields (e.g. legacy sso_access_token) so an old
        # session.json loads without TypeError.
        fields = MobileSession.__dataclass_fields__
        keep = {k for k in fields if not k.startswith("_")} | {"_minted_at"}
        d = {k: v for k, v in d.items() if k in keep}
        s = MobileSession(**d)
        mode = oct(os.stat(_SESSION_FILE).st_mode & 0o777)
        print(f"[tbank] session loaded: {_SESSION_FILE} ({os.path.getsize(_SESSION_FILE)} bytes, {mode})", file=sys.stderr)
        return s
    except Exception as e:
        print(f"[tbank] session load failed: {e}", file=sys.stderr)
        return None

def _require():
    """The in-memory session — but NOT older than the file on disk.

    The server runs for hours; a re-login happens in another process (login_cli.py),
    which rewrites session.json. Before this check the running server kept its stale
    copy forever (`if _session is None`), so the fresh login only took effect after an
    MCP reconnect — with nothing telling the user that. Now one stat() per call: a
    newer file means someone re-logged in, so re-read it. An unreadable file (mid-write,
    bad JSON) must NOT destroy a working in-memory session, so it is only replaced when
    the read succeeds or there was nothing in memory to begin with."""
    global _session, _session_mtime
    disk = _mtime_or_none(_SESSION_FILE)
    if _session is None or (disk is not None and disk != _session_mtime):
        fresh = _load_session()
        if fresh is not None or _session is None:
            _session = _with_persist(fresh)
            _session_mtime = disk
    if not _session or not _session.mobile_sessionid:
        raise TbankApiError("NO_SESSION",
            "Сначала вызови login(phone).")
    return _session

def _public_session():
    """A MobileSession for public travel reads that need no bank credential.

    This covers Avia and Hotels facades confirmed to send no Bearer, bank Cookie
    or mobile sessionid. A saved session is still preferred because Hotels may
    use its separately allowlisted ssoId; an anonymous shell is enough otherwise.

    Goes through `_require()` FIRST, not a copy of its body: every test in
    this repo stubs a fake session by reassigning `server._require`, and a
    second, independent path to a session here would silently skip that stub
    and hit the real network instead (found by test_response_parsers.py etc.
    actually doing that once — a stub's canned flight_search offer was ignored
    and the tool hit prod, which happened to answer HTTP_400 for the test's
    fixture body instead of returning fixture data). Only the specific
    NO_SESSION failure — nobody has called login() at all — falls back to a
    credential-free session; any other error from `_require()` (a stub
    raising something else on purpose) still propagates."""
    global _public_flight_session
    try:
        return _require()
    except TbankApiError as e:
        if e.result_code != "NO_SESSION":
            raise
    if _public_flight_session is None:
        _public_flight_session = MobileSession(mobile_sessionid="", refresh_token="")
    return _public_flight_session
