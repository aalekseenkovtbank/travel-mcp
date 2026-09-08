"""T-Bank messenger (tmsg) client methods."""
from __future__ import annotations

from typing import Any

from . import client_common as _client_common

globals().update({
    name: getattr(_client_common, name)
    for name in dir(_client_common)
    if not name.startswith("__")
})

class MessengerMixin:
    """T-Bank messenger (tmsg) client methods."""

    def _tmsg_expired(self) -> bool:
        """Decode the tmsg JWT exp; True if missing or within 60s of expiry."""
        if not self.tmsg_session_id:
            return True
        try:
            payload = self.tmsg_session_id.split(".")[1]
            payload += "=" * (-len(payload) % 4)
            exp = json.loads(base64.urlsafe_b64decode(payload)).get("exp", 0)
            return exp <= time.time() + 60
        except Exception:
            return True


    def messenger_issue_token(self) -> str:
        """Mint a fresh tmsgSessionID JWT from the current access_token.
        POST /app/bank/api/v1/session/issueTokenBySSO {ssoToken: <access_token>}
        -> result.jwt. Stores + returns it. Lets the messenger work headlessly
        (re-mint whenever the tmsg nears its ~1h expiry)."""
        url = "https://tm.t-bank-app.ru/app/bank/api/v1/session/issueTokenBySSO"
        headers = {"Content-Type": "application/json", "Accept": "application/json",
                   "User-Agent": "okhttp/4.12.0", "x-lang": "ru"}
        if self._wide_cookie():
            headers["Cookie"] = self._wide_cookie()
        r = self._http.post(url, json={"ssoToken": self.access_token},
                           headers=headers, timeout=30)
        data = self._unwrap(r)
        jwt = ""
        if isinstance(data, dict):
            jwt = data.get("jwt", "") if "jwt" in data else (data.get("result", {}) or {}).get("jwt", "")
        if jwt:
            self.tmsg_session_id = jwt
        return jwt


    def _ensure_tmsg(self) -> None:
        """Ensure a valid tmsg for messenger. If missing/expired, do a silent
        gorod-app re-login (SSO_SESSION + fingerprint, NO OTP) to get a fresh
        SSO-valid access_token, then mint the tmsg via issueTokenBySSO."""
        if not self._tmsg_expired():
            return
        # mint tmsg from the current access_token; if it fails (refresh token is
        # SSO-invalid), do a silent re-login to get a fresh auth_code access_token.
        try:
            self.messenger_issue_token()
            if self.tmsg_session_id:
                return
        except TbankApiError:
            pass
        # silent re-login -> fresh SSO-valid access_token, then mint tmsg
        self.silent_relogin()
        self.messenger_issue_token()


    def _safe_id(value: str, what: str) -> str:
        v = str(value or "")
        if not MobileSession._SAFE_ID_RE.match(v):
            raise TbankApiError("BAD_ID", f"{what} содержит недопустимые символы: {v!r}")
        return v


    def _tmsg_auth_error(data) -> str:
        rec = data[0] if isinstance(data, list) and data else data
        if isinstance(rec, dict) and rec.get("errorCode") in MobileSession._TMSG_AUTH_CODES:
            return str(rec.get("errorMessage") or rec["errorCode"])
        return ""


    def _tmsg_error(data) -> tuple[str, str]:
        """(code, message) for ANY messenger error record, ('','') otherwise.

        The auth subset above earns a token re-mint; every other errorCode has to
        surface as an error all the same. _as_list wraps a lone error dict as
        [error], and the renderers do not check that an element looks like a
        message — so a 404 {"errorCode":"CONVERSATION_NOT_FOUND"} was PRINTED as a
        chat message. That is worse than an empty list: there is nothing to retry
        and nothing to read, and the agent believes it read the conversation."""
        rec = data[0] if isinstance(data, list) and data else data
        if isinstance(rec, dict) and rec.get("errorCode"):
            return str(rec["errorCode"]), str(rec.get("errorMessage") or "")
        return "", ""


    def _messenger_read(self, *, path_override=None, overrides=None, key="messenger_base"):
        """One messenger read, re-minting the token if the server says it is dead.

        _tmsg_expired() only decodes the JWT's own `exp`, so a token the SERVER has
        invalidated early still looks fine locally and no re-mint is attempted."""
        data = self._call_read(key, path_override=path_override, overrides=overrides)
        why = self._tmsg_auth_error(data)
        if not why:
            code, msg = self._tmsg_error(data)
            if code:
                raise TbankApiError(code, msg)
            return data
        self.tmsg_session_id = ""             # force a re-mint, then try once more
        self._ensure_tmsg()
        data = self._call_read(key, path_override=path_override, overrides=overrides)
        why = self._tmsg_auth_error(data)
        if why:
            raise SessionExpired("TMSG_AUTH_REQUIRED",
                f"Мессенджер отклонил токен даже после переоформления ({why}). "
                f"Вызови refresh_session() и повтори.")
        return data


    def _messenger_write(self, *, path_override, body, key="messenger_send"):
        """One messenger WRITE (POST/PUT with a body), with the SAME verdict and
        token re-mint the reads get through _messenger_read.

        The writes used to call _call_read directly and skip all of it. The messenger
        signals a dead token with HTTP 200 and [{"errorCode":"AUTH_REQUIRED"}] in the
        body (see _tmsg_auth_error) — for a read that surfaced as an empty list; for a
        SEND it flowed back as a success with no message id and was reported to the
        user as «Отправлено», while nothing reached the support agent. A send is
        irreversible and read by a person: it has to fail loudly, not silently no-op.
        So the auth shape earns one re-mint and retry, every other errorCode raises,
        and only a clean response returns."""
        data = self._call_read(key, body=body, path_override=path_override)
        why = self._tmsg_auth_error(data)
        if not why:
            code, msg = self._tmsg_error(data)
            if code:
                raise TbankApiError(code, msg)
            return data
        self.tmsg_session_id = ""             # force a re-mint, then try once more
        self._ensure_tmsg()
        data = self._call_read(key, body=body, path_override=path_override)
        why = self._tmsg_auth_error(data)
        if why:
            raise SessionExpired("TMSG_AUTH_REQUIRED",
                f"Мессенджер отклонил токен даже после переоформления ({why}). "
                f"Вызови refresh_session() и повтори.")
        code, msg = self._tmsg_error(data)
        if code:
            raise TbankApiError(code, msg)
        return data


    def messenger_conversations(self, archived: bool = False, offset: int = 0) -> list[dict]:
        ov = {"use_is_archived": str(archived).lower(), "offset": str(offset)}
        return self._as_list(self._messenger_read(
            path_override="/app/bank/messenger/conversations/mobile", overrides=ov))


    def messenger_messages(self, conversation_id: str, direction: str = "before",
                           message_id: str = "") -> list[dict]:
        conversation_id = self._safe_id(conversation_id, "conversation_id")
        ov = {"direction": direction}
        if message_id:
            ov["messageId"] = self._safe_id(message_id, "message_id")
        return self._as_list(self._messenger_read(overrides=ov,
            path_override=f"/app/bank/messenger/conversations/{conversation_id}/messages"))


    def messenger_hints(self, conversation_id: str) -> list[dict]:
        conversation_id = self._safe_id(conversation_id, "conversation_id")
        return self._as_list(self._messenger_read(
            path_override=f"/app/bank/messenger/conversations/{conversation_id}/hints"))


    def messenger_faq(self, conversation_id: str) -> list[dict]:
        conversation_id = self._safe_id(conversation_id, "conversation_id")
        return self._as_list(self._messenger_read(
            path_override=f"/app/bank/messenger/conversations/{conversation_id}/faq"))


    def messenger_unread(self) -> dict:
        """Conversations with unread messages. Uses its OWN template, not
        messenger_base: this path content-negotiates and 406s on the generic
        `application/json` header. Returns {groups, conversationIds, screens}."""
        # Through _messenger_read, not _call_read: this path used to skip both the
        # auth detection and the token re-mint, and then coerced anything that was
        # not a dict to {} — so the documented rejection shape (HTTP 200 with
        # [{"errorCode":"AUTH_REQUIRED"}], a LIST) became «Непрочитанных сообщений
        # нет.» with nothing to retry and nothing to read.
        data = self._messenger_read(key="messenger_unread")
        if not isinstance(data, dict):
            raise TbankApiError("MESSENGER_BAD_SHAPE",
                f"мессенджер ответил не объектом: {_excerpt(data)}")
        return data


    def messenger_send_message(self, conversation_id: str, body: dict | None = None) -> dict:
        """POST a message to a conversation (WRITE). Replays the request body or override."""
        conversation_id = self._safe_id(conversation_id, "conversation_id")
        return self._messenger_write(body=body,
            path_override=f"/app/bank/messenger/conversations/{conversation_id}/messages")


    def messenger_mark_read(self, conversation_id: str, message_id: str) -> Any:
        """Mark one message read. Its own template, not messenger_base: the captured
        request is a PUT with markRead's own vendor content types, while
        messenger_base is a GET that would send `application/json` — the same
        content-negotiation mistake that made messenger_unread answer 406."""
        conversation_id = self._safe_id(conversation_id, "conversation_id")
        message_id = self._safe_id(message_id, "message_id")
        return self._messenger_write(key="messenger_mark_read", body=None,
            path_override=f"/app/bank/messenger/conversations/{conversation_id}/messages/{message_id}/markRead")


    def messenger_file(self, conversation_id: str, file_id: str) -> tuple[bytes, str]:
        """(bytes, filename) for one chat attachment — content.fileId of a
        messageType="file" message.

        The name comes from the RESPONSE, not from the caller. The message record
        carries a fileName, but making the agent copy it back in was a round trip
        through the model for a value the server states itself — twice, in fact:
        `x-amz-meta-filename-base64` (exact bytes, no quoting to get wrong) and
        percent-encoded in Content-Disposition. It is still untrusted text: the
        caller sanitises it before it becomes a path.

        The pair is the key: a fileId is scoped to its conversation, and the same
        fileId under another of the user's own conversations answers 401.

        Not through _messenger_read, which parses JSON — this route returns the raw
        document. But it shares the messenger's worst trait: a dead token comes back
        as HTTP 200 with a JSON error envelope in the body. Unchecked, those 119
        bytes are what gets written to disk and reported as the file — a saved error
        that opens as a corrupt document. So the envelope is detected in the bytes,
        and an auth failure earns the same single re-mint as every other messenger
        read before it is called expired."""
        conversation_id = self._safe_id(conversation_id, "conversation_id")
        if not self._SAFE_FILE_ID_RE.match(str(file_id or "")):
            raise TbankApiError("BAD_ID", f"file_id содержит недопустимые символы: {file_id!r}")
        path = f"/app/bank/messenger/conversations/{conversation_id}/files/{file_id}"

        def _get():
            r = self._call_read("messenger_file", path_override=path,
                                return_response=True)
            st = getattr(r, "status_code", 200)
            if st in (401, 403):
                raise TbankApiError("NOT_AUTHORIZED",
                    "Мессенджер не отдал файл: fileId не принадлежит этому чату. "
                    "conversation_id и file_id должны быть из ОДНОГО сообщения "
                    "(messenger_messages).")
            if st == 500:
                raise TbankApiError("FILE_NOT_FOUND",
                    "Мессенджер ответил 500 — так он отвечает на несуществующий "
                    "fileId. Возьми fileId из messenger_messages.")
            if st >= 400:
                raise TbankApiError(f"HTTP_{st}", _excerpt(getattr(r, "text", "")))
            return r

        r = _get()
        if self._tmsg_auth_error(_as_json_envelope(r.content)):
            self.tmsg_session_id = ""
            self._ensure_tmsg()
            r = _get()
            why = self._tmsg_auth_error(_as_json_envelope(r.content))
            if why:
                raise SessionExpired("TMSG_AUTH_REQUIRED",
                    f"Мессенджер отклонил токен даже после переоформления ({why}). "
                    f"Вызови refresh_session() и повтори.")
        blob = r.content or b""
        code, msg = self._tmsg_error(_as_json_envelope(blob))
        if code:
            raise TbankApiError(code, msg)
        if not blob:
            raise TbankApiError("EMPTY_FILE", "Мессенджер отдал пустой файл (0 байт).")
        return blob, _response_filename(r.headers)


    def messenger_send(self, conversation_id: str, text: str) -> dict:
        """Send a text message to a conversation. Encapsulates the vendor
        Content-Type + body format."""
        import uuid as _uuid
        conversation_id = self._safe_id(conversation_id, "conversation_id")
        body = {"content": text, "clientSideId": str(_uuid.uuid4()),
                "assistant": {"inputType": "default"}}
        return self._messenger_write(body=body,
            path_override=f"/app/bank/messenger/conversations/{conversation_id}/messages")
