"""Transfers, bills, QR and provider payments."""
from __future__ import annotations

from typing import Any

from . import client_common as _client_common

globals().update({
    name: getattr(_client_common, name)
    for name in dir(_client_common)
    if not name.startswith("__")
})

class MoneyMixin:
    """Transfers, bills, QR and provider payments."""

    def payment_methods(self) -> list[dict]:
        """Available payment methods for a checkout."""
        return self._as_list(self._call_read("payment_methods"))


    def payment_gate_pay(self, body: dict | None = None) -> dict:
        """Pay for a marketplace order (cookie-only, NO signature). MONEY OP.
        Replays the payment body or uses the override. Default
        dry_run=False — pass a fresh body (orderId/amount/account) for a new pay."""
        return self._call_read("payment_gate_pay", body=body)


    def payment_commission(self, body: dict | None = None) -> dict:
        """Commission preview (POST /v1/payment_commission), no money moved.

        The real app sends application/x-www-form-urlencoded with a single
        ``payParameters`` field holding the JSON-encoded parameters — NOT a JSON
        body (capture item 1469). Posting JSON returns INVALID_REQUEST_DATA.
        ``isTransferStatus``/``isUrgentTransfer`` are string "false" in every
        captured request; default them so callers need not know."""
        p = (body or {}).get("payParameters") or body or {}
        p = dict(p)
        p.setdefault("isTransferStatus", "false")
        p.setdefault("isUrgentTransfer", "false")
        return self._call_read("payment_commission", body={"payParameters": p})


    def checkout_process_order(self, body: dict | None = None) -> dict:
        return self._call_read("checkout_process_order", body=body)


    def get_requisites(self) -> list[dict]:
        """Account requisites (account number / corr / bank — for transfers)."""
        return self._as_list(self._call_read("get_requisites"))


    def payment_templates(self) -> list[dict]:
        """Saved payment templates (favorite recipients)."""
        return self._as_list(self._call_read("payment_templates"))


    def providers_compatible(self) -> list[dict]:
        """Compatible payment providers (for bill payments)."""
        return self._as_list(self._call_read("providers_compatible"))


    def payment_shortcuts(self) -> list[dict]:
        """Payment shortcuts (favorite recipients / autopay deeplinks)."""
        return self._as_list(self._call_read("payment_shortcuts"))


    def resolve_payment_qr(self, body: dict | None = None) -> dict:
        """Resolve a QR payload to a payment provider (no money moved)."""
        return self._call_read("resolve_payment_qr", body=body)


    def qr_providers(self, qr: str) -> list[dict]:
        """Ask the bank what a scanned QR means. Read-only, no money.

        Answers with the provider records that can pay it — for an invoice QR that
        is `transfer-legal`, with every field carrying the `defaultValue` the bank
        itself read out of the QR. That is worth having even though parse_payment_qr
        reads the same string locally: the bank's answer is what proves the QR is
        payable at all, and it names the provider for QRs that are not invoices.

        The app sends the same three values in the query AND as the JSON body
        (captures_payreq.xml #538); both are reproduced rather than picking the one
        that happens to work, because which one the gate reads is not observable."""
        params = {"barcodeHash": payment_qr_hash(qr), "qr": str(qr),
                  "frontendFeatureFlag": "SHAWithSubs"}
        res = self._call_read("resolve_payment_qr", body=dict(params),
                              overrides=dict(params))
        # _unwrap already peels the `payload` envelope; keep the .get for the shape
        # where it does not (a bare providersList).
        data = res if isinstance(res, dict) else {}
        data = data.get("payload", data) if isinstance(data.get("payload"), dict) else data
        providers = (data.get("providersList") or {}).get("providers")
        return [p for p in (providers or []) if isinstance(p, dict)]


    def providers_groups(self) -> list[dict]:
        """Payment provider groups — 19 of them live («ЖКХ», «Мобильная связь»,
        «Госуслуги», …).

        The payload nests them: the endpoint answers a LIST whose single element is
        {"groups": [...]}, so `_as_list` alone handed back that wrapper and every
        caller read zero groups. Verified live 2026-07-26."""
        data = self._call_read("providers_groups")
        for item in self._as_list(data):
            if isinstance(item, dict) and isinstance(item.get("groups"), list):
                return [g for g in item["groups"] if isinstance(g, dict)]
        # Already flat (or an unexpected shape) — return what is usable.
        return [g for g in self._as_list(data)
                if isinstance(g, dict) and (g.get("name") or g.get("id"))]


    def providers_compatible_page(self, group: str = "", page: int = 1,
                                  page_size: int = 100) -> dict:
        """One page of the provider catalogue, with each provider's FIELD SCHEMA.

        `group` is a group NAME as `providers_groups()` prints it («Переводы»,
        «ЖКХ», …), not an id. Returns the raw providersPage:
        {page, providers[], totalPages, totalProviders, storageId, updateTime}.

        Each provider carries `fields[]`, and every field has `id`, `name`,
        `regexp`, `hint`, `keyboard`, `type` and `usageTypes[]` — the last one is
        what says whether the field is required for a payment (`code: "Pay"`) or
        only for saving a template. That schema is the only thing that makes a
        composed payment checkable before it is sent."""
        ov = {"page": str(page), "pageSize": str(page_size)}
        if group:
            ov["groups"] = self.GROUP_ALIASES.get(group.strip(), group.strip())
        data = self._call_read("providers_compatible_page", overrides=ov)
        if isinstance(data, dict):
            return data.get("providersPage") or data
        return {}


    def provider_pay_fields(provider: dict) -> list[dict]:
        """The fields THIS provider needs for a payment, in the app's own order.

        A field counts when its usageTypes carry a `Pay` entry; `required` and
        `editable` come from that same entry, not from the field record."""
        out = []
        for f in (provider.get("fields") or []):
            if not isinstance(f, dict):
                continue
            pay = next((u for u in (f.get("usageTypes") or [])
                        if isinstance(u, dict) and u.get("code") == "Pay"), None)
            if pay is None or not pay.get("visible", True):
                continue
            out.append({"id": f.get("id"), "name": f.get("name"),
                        "regexp": f.get("regexp") or "", "hint": f.get("hint") or "",
                        "type": f.get("type") or "", "required": bool(pay.get("required")),
                        "editable": bool(pay.get("editable", True)),
                        "order": pay.get("order", 0)})
        out.sort(key=lambda x: (x["order"], str(x["id"])))
        return out


    def ruble_source_accounts(self) -> list[dict]:
        """Every Current RUB account with a positive balance — the debit candidates,
        in the bank's order. [{id, name, balance}]. `_source_account` returns the
        first; a picker offers all of them."""
        out = []
        for a in (self.list_accounts() or []):
            if not isinstance(a, dict) or (a.get("accountType") or "") != "Current":
                continue
            money = a.get("moneyAmount") or {}
            bal = money.get("value", 0) if isinstance(money, dict) else 0
            try:
                bal = float(bal)
            except (TypeError, ValueError):
                bal = 0.0
            if bal <= 0:
                continue
            cur = a.get("currency")
            cn = cur.get("name") if isinstance(cur, dict) else cur
            if cn and str(cn).upper() not in ("RUB", "RUBLES", "РОССИЙСКИЙ РУБЛЬ", "₽"):
                continue
            if a.get("id"):
                out.append({"id": str(a["id"]), "name": str(a.get("name") or ""),
                            "balance": bal})
        return out


    def _source_account(self) -> str:
        """First Current RUB account id with a positive balance — the payer/source
        for transfers (capture: payParameters.account = 10-char source id)."""
        accts = self.ruble_source_accounts()
        if accts:
            return accts[0]["id"]
        # Names the way out. This is a guess the caller can always override, and the
        # override is documented on the tools but was absent from the one message the
        # agent actually reads when the guess fails.
        raise TbankApiError("NO_SOURCE_ACCOUNT",
            "не нашёл рублёвый счёт Current с положительным балансом для списания. "
            "Посмотри list_accounts() и укажи счёт явно: "
            "transfer(..., from_account=\"…\") или ticket_pay(..., account_id=\"…\").")


    def _requisites(self, ptr: str, source: str) -> list[dict]:
        """One GET /v1/get_requisites for one pointerSource, parsed into candidates.

        The app sends the two sources with DIFFERENT query params — the internal
        lookup carries neither withTinkoff nor gapBanks — and both shapes are in
        captures.xml, so neither is guessed."""
        extra = ({"withTinkoff": "true", "gapBanks": "true"}
                 if source == "external" else {})
        r = self._call_read("get_requisites", overrides={
            "pointerType": "phone", "pointer": ptr,
            "pointerSource": source, **extra,
        })
        items = r if isinstance(r, list) else (
            (r.get("payload") if isinstance(r, dict) else None) or [])
        out: list[dict] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            df = {d.get("name"): d.get("value")
                  for d in (it.get("displayFields") or []) if isinstance(d, dict)}
            brand = it.get("brand") or {}
            bmi, mfio, plid = (str(df.get("bankMemberId", "")),
                               str(df.get("maskedFIO", "")),
                               str(it.get("pointerLinkId", "")))
            # ready providerFields — paste into payment_commission() so the agent
            # never hand-writes the 8276 pointer-type code. bankMemberId is OMITTED,
            # not blanked, when the bank did not send one: the T-Bank-internal
            # commission body in captures.xml has no such key, and an empty string
            # there is a value we have never seen the app send.
            pf = {"pointerType": SBP_PHONE_POINTER_TYPE, "pointer": ptr,
                  "maskedFIO": mfio, "pointerLinkId": plid}
            if bmi:
                pf["bankMemberId"] = bmi
            out.append({
                "bank_member_id": bmi,
                "masked_fio": mfio,
                "pointer_link_id": plid,
                "bank_name": str(brand.get("name", "")),
                "bank_id": str(brand.get("id", "")),
                "is_default_bank": bool(it.get("isDefaultBank")),
                "workflow_type": str(it.get("workflowType", "")),
                "is_tbank": str(it.get("workflowType", "")) == TBANK_INNER_WORKFLOW,
                "provider_fields": pf,
            })
        return out


    def resolve_recipient(self, phone: str) -> list[dict]:
        """Resolve a phone to every account it can be paid to (GET
        /v1/get_requisites, capture-verified). READ-ONLY — no money moves.

        TWO requests, because the bank answers two different questions and the app
        asks both, in this order:

          pointerSource=internal → the recipient's T-BANK account, if they are a
            T-Bank client. workflowType='TinkoffInner', maskedFIO and pointerLinkId,
            and NO bankMemberId — an internal transfer is not routed through SBP.
          pointerSource=external → the recipient's SBP banks.
            workflowType='SBPTransfer', each with its own bankMemberId.

        Asking only the second one is why a recipient the user could plainly see in
        the app came back as «Sber and VTB, no T-Bank»: `withTinkoff=true` on the
        external call does NOT fold the internal answer in — measured on the same
        phone in captures.xml, the external list is Sber+VTB and the internal one is
        the T-Bank account, and nothing about the external response hints that a
        second list exists.

        A phone can therefore map to SEVERAL candidates, so the caller picks one
        (prefer isDefaultBank=True). Returns [{bank_member_id, masked_fio,
        pointer_link_id, bank_name, bank_id, is_default_bank, workflow_type,
        is_tbank, provider_fields}], T-Bank first. Empty list = neither a T-Bank
        client nor registered in SBP (or the number is wrong).

        RAISES THE SESSION LEVEL FIRST. This endpoint validates the mobile sessionid,
        not just the Bearer, and its CLIENT window is ~11 minutes against the token's
        ~2h — so ensure_fresh(), which re-mints on a ~100-minute schedule, leaves it
        being called with an ANONYMOUS session for most of that interval. The bank's
        answer to that is `REQUEST_RATE_LIMIT_EXCEEDED — Слишком много попыток
        проверить банки получателя`, which reads as a volume limit and is nothing of
        the sort: measured live, it fires on the FIRST call in 14 minutes, with the
        same deviceId and IP, and the identical call succeeds seconds after a re-mint.

        Here rather than in the tools: transfer() resolves a second time on its own
        (for the display name), so a guard on the tool layer would miss that path."""
        self.ensure_client_session()
        ptr = _normalize_phone(phone)
        # The internal lookup is the cheap one and the one whose absence caused the
        # bug, so it goes first and its failure is NOT swallowed: a T-Bank recipient
        # silently missing from the list is exactly the state this method exists to
        # end. Both calls hit the same endpoint with the same session, so there is no
        # failure mode where one is reachable and the other is not.
        return self._requisites(ptr, "internal") + self._requisites(ptr, "external")


    def transfer(self, amount: float, to_account: str, description: str = "",
                 provider: str = "p2p-anybank", pointer_type: str = SBP_PHONE_POINTER_TYPE,
                 bank_member_id: str = "", masked_fio: str = "",
                 pointer_link_id: str = "", account: str = "",
                 user_payment_id: str = "") -> Any:
        """Transfer via signed /v1/pay (REAL money). Body shape is capture-verified
        (the old body invented pointerType='ACCOUNT' and was rejected). The signing
        mechanism (_signed_parts) is unchanged — it was proven byte-exact.

        phone/SBP (default: provider='p2p-anybank', pointer_type='8276'):
          to_account = recipient phone. If pointer_link_id is NOT passed, the
          recipient is AUTO-RESOLVED via resolve_recipient() (GET
          /v1/get_requisites, both pointerSources): the default is picked, or the
          single match; if several with no default → RECIPIENT_MULTIPLE_BANKS
          (surface list, never silently pick). For a NEW recipient, call
          transfer_sbp_resolve(phone) first to show the user the candidates, then
          pass the chosen fields. A candidate that is the recipient's own T-BANK
          account has no bankMemberId — pass its pointer_link_id and leave
          bank_member_id empty, and the key is omitted from providerFields.
          pay body is capture-verified (providerFields.pointerType='8276', pointer
          '+7XXXXXXXXXX'). paymentType='Transfer' belongs to payment_commission,
          NOT to pay — no real pay body carries it.

          Both flavours are pinned to a real signed /v1/pay that the bank answered
          200 to: the SBP one to captures.xml #1477, the T-Bank-internal one to
          captures-pay.xml (same provider and envelope, providerFields WITHOUT
          bankMemberId). Neither is an inference from a commission preview.
        between own accounts (provider='transfer-inner'): NOT supported for the
          PAYMENT. providerFields = {'bankContract': to_account} is a plausible
          envelope, but unlike p2p-anybank (capture-verified) there is no captured
          /v1/pay for this provider to check it against — refused until one exists.
          Transfer between own accounts in the app in the meantime.
        by details (provider='transfer-legal'): use transfer_legal() instead — the
          payment is implemented, but it needs nine requisite fields this signature
          has nowhere to put. Calling transfer() with it raises WRONG_METHOD.

        `account` = the payer account id (from list_accounts). Empty falls back to the
        first Current RUB with a positive balance — which is a GUESS, and was
        previously the only behaviour: the user could be asked which account to debit,
        answer, and be debited from a different one anyway.

        `user_payment_id` is the client-generated id the app sends on every payment
        (a millisecond timestamp). Pass the SAME value to retry a transfer whose
        outcome you did not see — that is what stops a timeout from becoming two
        payments. A fresh value per call provides no idempotency at all.

        `description` becomes providerFields.message (capture: captures2.xml #595) —
        it used to be accepted, documented and then silently dropped.

        For commission preview, call payment_commission() separately before this.
        ALWAYS confirm with the user.

        Returns (payload, recipient): the bank's payload (paymentId, commissionInfo)
        and the masked recipient name that actually went into the signed body.

        The second half exists because it used to be thrown away. When the caller
        passes the two routing ids but no name, this method looks the name up — one
        request to /v1/get_requisites — puts it in providerFields.maskedFIO, and
        used to let it die with the local variable. server.transfer then built its
        confirmation line from its OWN masked_fio argument, still empty, so the one
        line a person reads before money moves showed a phone number and no name —
        while the bank had told us «Мария П.» and we had paid a request for it.

        A tuple rather than an extra key in the payload: that dict is the bank's,
        it is printed verbatim when no paymentId comes back, and inventing a field
        in it would show the user something the bank never sent."""
        src = account or self._source_account()
        if provider == "transfer-inner":
            # providerFields={'bankContract': to_account} would be the plausible
            # envelope, but no captured /v1/pay exists for this provider to check
            # it against — unlike p2p-anybank, which has direct capture references.
            # Refused rather than sent unverified against real money.
            raise TbankApiError("NOT_SUPPORTED",
                "Перевод между своими счетами (provider='transfer-inner') через "
                "MCP не реализован. Тело providerFields={'bankContract': "
                "to_account} выглядит правдоподобно, но ни разу не сверено с "
                "реальным перехваченным /v1/pay для этого провайдера — угадывать "
                "конверт на платеже нельзя. Перевод между своими счетами — в "
                "приложении.")
        elif provider == "transfer-legal":
            # No longer a refusal for want of a capture — captures_payreq.xml #578 is
            # a real signed /v1/pay for this provider. It is a refusal because this
            # signature cannot carry the payment: transfer() routes by ONE recipient
            # id, and a payment to a legal entity needs nine (account, БИК, corr
            # account, bank name, payee, ИНН, КПП, purpose, VAT mark), each with its
            # own format the bank enforces. transfer_legal() takes them.
            raise TbankApiError("WRONG_METHOD",
                "Перевод по банковским реквизитам делается не через transfer(), а "
                "через transfer_legal(amount, fields=…) — у него девять полей "
                "(bankAcnt/bankBik/bankCorrAcnt/bankName/addressee/inn/kpp/comment/"
                "nds), которые в сигнатуру transfer() не помещаются. Тул: "
                "transfer_requisites(...), а прочитать QR со счёта — payment_qr(qr).")
        else:  # p2p-anybank (phone / SBP)
            # The caller's CHOICE is the two ids. maskedFIO is a display name the
            # bank echoes back, not part of the routing — and requiring it here meant
            # an agent that followed the docs (which promise "bank_member_id +
            # pointer_link_id") left it empty, the gate opened, and auto-resolution
            # silently replaced the bank the user had picked and confirmed. Same
            # person, different account, and invisible: the result line prints the
            # recipient only when masked_fio is set.
            # pointer_link_id ALONE is the caller's explicit choice — the gate used to
            # demand bank_member_id too, and a T-Bank-internal recipient does not have
            # one. With the old gate, picking the recipient's T-Bank account was not
            # expressible: passing its link id with an empty member id looked like
            # "nothing chosen" and re-resolved to some SBP bank instead.
            if not pointer_link_id:
                # Auto-resolve the recipient via get_requisites (read-only). Pick the
                # default bank if any, else the single match; if several with NO
                # default, refuse + surface the list — money safety: never silently
                # pick a bank (could send to the wrong bank/account).
                resolved = self.resolve_recipient(to_account)
                if not resolved:
                    raise TbankApiError("RECIPIENT_NOT_RESOLVED",
                        f"{to_account} has no T-Bank account and is not registered in "
                        "SBP (or the number is wrong). "
                        "Call transfer_sbp_resolve(phone) to check.")
                pick = next((x for x in resolved if x["is_default_bank"]), None)
                if pick is None and len(resolved) == 1:
                    pick = resolved[0]
                if pick is None:
                    raise TbankApiError("RECIPIENT_MULTIPLE_BANKS",
                        f"{to_account} maps to {len(resolved)} accounts — pick one:\n" +
                        "\n".join(f"  - {x['masked_fio']} | {x['bank_name']}"
                                  + (" (счёт в Т-Банке, перевод внутри банка)"
                                     if x["is_tbank"] else "")
                                  + f" | bankMemberId={x['bank_member_id'] or '—'}"
                                  f" | pointerLinkId={x['pointer_link_id']}"
                                  for x in resolved) +
                        "\nPass the chosen pointer_link_id (+ bank_member_id for an "
                        "SBP bank; a T-Bank account has none) to transfer().")
                bank_member_id = pick["bank_member_id"]
                masked_fio = pick["masked_fio"]
                pointer_link_id = pick["pointer_link_id"]
            elif not masked_fio:
                # The ids came from the caller, so the routing is already decided.
                # Look up the display name only — never let this overwrite the choice.
                #
                # This lookup IS load-bearing, contrary to a first reading of it: the
                # value goes into pf["maskedFIO"], i.e. into the SIGNED body. What it
                # does NOT reach is the confirmation line the user reads —
                # server.transfer builds that from
                # its own masked_fio argument, so a name resolved here at the cost of
                # a request is still absent from the sentence a person checks before
                # the money moves.
                try:
                    # An empty bank_member_id means the caller chose the recipient's
                    # T-Bank account, and that candidate is the one with no member id
                    # — so the same comparison selects it, deliberately.
                    match = next((x for x in self.resolve_recipient(to_account)
                                  if str(x.get("bank_member_id")) == str(bank_member_id)), None)
                    masked_fio = (match or {}).get("masked_fio", "")
                except TbankApiError:
                    # Left EMPTY, not filled with a placeholder: this goes into the
                    # signed body, and inventing a name there is telling the bank
                    # something untrue. The routing is unaffected — it is the two ids.
                    masked_fio = ""

            pf = {"pointerType": pointer_type, "pointer": _normalize_phone(to_account),
                  "maskedFIO": masked_fio, "pointerLinkId": pointer_link_id}
            if bank_member_id:
                # Present for an SBP route (captures.xml #1477), ABSENT for a T-Bank
                # -internal one: the captured internal commission body has no such
                # key, and the bank answers a bodiless bankMemberId with
                # unfinishedFlag=true — "recipient not fully identified" — which is
                # exactly what a blank string would reproduce.
                pf["bankMemberId"] = bank_member_id
        if description:
            # The app carries the note here, not as a top-level field
            # (captures2.xml #595: providerFields.message = "Hi").
            pf["message"] = description
        pay_params = {"provider": provider, "currency": "RUB", "account": src,
                      "moneyAmount": money_amount(amount), "providerFields": pf,
                      "isTransferStatus": "false", "isUrgentTransfer": "false",
                      # Present in every real pay body; absent from ours until now.
                      "cellularService": "WiFi", "frontCamera": "true",
                      "userPaymentId": user_payment_id or str(int(time.time() * 1000))}
        # NOTE: no paymentType here. `paymentType: "Transfer"` was added from a
        # capture — but of /v1/payment_commission, where it IS required. No real
        # /v1/pay body in either capture carries it (checked all three: captures.xml
        # #1423 and #1477, captures2.xml #595). Sending it is an invention.
        body = "payParameters=" + urllib.parse.quote(json.dumps(pay_params))
        return self.pay(body), masked_fio


    def find_provider(self, provider_id: str, group: str = "",
                      max_pages: int = 7) -> dict:
        """One provider record from the catalogue, {} if not found.

        Walks the pages of `group` when given (cheap: the group filter narrows
        63 889 utility providers to one page), otherwise searches the ungrouped
        catalogue, which is 100k+ providers — so a group is strongly preferred.

        Memoised for PROVIDER_TTL seconds, keyed by (group, provider_id): the
        typical flow calls payment_providers(provider_id=…) to show the fields,
        then pay_bill(provider_id) moments later — same scan, same answer."""
        pid = str(provider_id)
        key = f"provider:{group}:{pid}"
        memo = getattr(self, "_memo", None)
        if memo is not None:
            at, cached = memo.get(key, (0.0, None))
            if cached is not None and time.time() - at < self.PROVIDER_TTL:
                return cached
        # The app looks a provider up by id with ONE filtered request; the page
        # walk downloads up to seven pages of 362 KB (~2.5 MB) to find the same
        # record. Same host, same shape — /providers/compatible/filter?ids= answers
        # with the full fields[] schema (captures: 4 providers, 15 KB).
        try:
            got = self._call_read("providers_compatible", overrides={"ids": pid})
            # `providers`, read by name. _as_list understands `list` and `payload`
            # only, so it wrapped this envelope as ONE element and the id never
            # matched — the same shape mismatch that made four other tools print a
            # single useless row.
            found = (got or {}).get("providers") if isinstance(got, dict) else got
            for prov in (found or []):
                if isinstance(prov, dict) and str(prov.get("id")) == pid:
                    if memo is not None:
                        memo[key] = (time.time(), prov)
                    return prov
        except TbankApiError:
            # The filter is an optimisation, not the contract: if it is unavailable
            # or answers something unexpected, the page walk below still finds it.
            pass
        for page in range(1, max(1, int(max_pages or 7)) + 1):
            pg = self.providers_compatible_page(group=group, page=page)
            for prov in (pg.get("providers") or []):
                if str(prov.get("id")) == pid:
                    if memo is not None:
                        memo[key] = (time.time(), prov)
                    return prov
            if page >= int(pg.get("totalPages") or 1):
                break
        return {}


    def validate_provider_fields(self, provider: dict, fields: dict) -> list[str]:
        """Complaints about `fields` against the provider's own schema, [] if clean.

        The catalogue publishes a `regexp` per field and a `required` flag per usage,
        and this is the only thing standing between a typo and a stranger's utility
        account being paid. Checked BEFORE the request, so a bad value costs nothing."""
        problems: list[str] = []
        schema = self.provider_pay_fields(provider)
        known = {f["id"]: f for f in schema}
        for f in schema:
            val = fields.get(f["id"])
            if val in (None, ""):
                if f["required"]:
                    problems.append(
                        f"нет обязательного поля {f['id']} ({f['name']})"
                        + (f" — {f['hint']}" if f["hint"] else ""))
                continue
            rx = f["regexp"]
            if rx:
                try:
                    if not re.fullmatch(rx, str(val)):
                        problems.append(
                            f"{f['id']} ({f['name']}) не подходит под формат {rx}"
                            + (f" — {f['hint']}" if f["hint"] else ""))
                except re.error:
                    # A schema we cannot compile is not the caller's fault; say so
                    # rather than letting a broken pattern block a valid payment.
                    problems.append(f"{f['id']}: регулярку провайдера не удалось "
                                    f"разобрать ({rx!r}) — проверь значение сам")
        for k in fields:
            if k not in known:
                problems.append(f"поле {k!r} провайдер не принимает; допустимые: "
                                + ", ".join(sorted(known)))
        return problems


    def pay_bill(self, provider_id: str, fields: dict, amount: float,
                 account: str = "", user_payment_id: str = "") -> Any:
        """Pay a service bill (utilities, fines, taxes, internet…). REAL MONEY.

        Same signed /v1/pay envelope transfer() uses — capture-verified for the
        transfer providers — with this provider's own providerFields. `paymentType`
        is deliberately absent: it belongs to payment_commission, and no captured
        pay body carries it.

        The caller is expected to have validated `fields` against the catalogue and
        previewed the commission; this method does neither, so that the server layer
        can report each failure with its own message."""
        src = account or self._source_account()
        pay_params = {"provider": str(provider_id), "currency": "RUB", "account": src,
                      "moneyAmount": money_amount(amount), "providerFields": dict(fields),
                      "cellularService": "WiFi", "frontCamera": "true",
                      "userPaymentId": user_payment_id or str(int(time.time() * 1000))}
        body = "payParameters=" + urllib.parse.quote(json.dumps(pay_params, ensure_ascii=False))
        return self.pay(body)


    def transfer_legal(self, amount: float, fields: dict, account: str = "",
                       user_payment_id: str = "", from_qr: bool = False) -> Any:
        """Pay a legal entity / sole trader by bank requisites. REAL MONEY.

        Body is capture-verified against captures_payreq.xml #578 — a real signed
        /v1/pay for provider `transfer-legal`, 23 600 ₽ from an invoice QR, answered
        200 with a paymentId. Relative to the p2p envelope it keeps isTransferStatus
        and isUrgentTransfer, and adds `paidByPhoto: "QR"` when the requisites were
        scanned rather than typed. `paymentType` stays out, as on every other pay.

        `fields` are the providerFields ids, not human names: bankAcnt (20 digits),
        bankBik (9), bankCorrAcnt, bankName, addressee, inn (10 or 12), kpp (9),
        comment (назначение платежа — the bank requires it) and nds (NDS_EXEMPT /
        NDS_INCLUDED). parse_payment_qr() produces this dict directly.

        This method does NOT validate: the server layer checks the values against
        the provider's own published regexps first, so each complaint can name the
        field. `user_payment_id` is the retry key — same semantics as transfer()."""
        src = account or self._source_account()
        vals = {k: str(v) for k, v in dict(fields or {}).items() if str(v).strip()}
        vals.setdefault("nds", NDS_EXEMPT)
        pay_params = {"moneyAmount": money_amount(amount), "currency": "RUB",
                      "frontCamera": "true", "cellularService": "WiFi",
                      "provider": "transfer-legal",
                      "isTransferStatus": "false", "isUrgentTransfer": "false",
                      "account": src,
                      "userPaymentId": user_payment_id or str(int(time.time() * 1000)),
                      "providerFields": vals}
        if from_qr:
            # The app marks a scanned payment; the bank echoes it into the operation.
            # Only set when the requisites really came from a QR — claiming a scan
            # that did not happen is telling the fraud engine something false.
            pay_params["paidByPhoto"] = "QR"
        # ensure_ascii=False: the captured body carries the payee's name and purpose
        # as percent-encoded utf-8 (%D0%9E%D0%9E%D0%9E), never as \uXXXX escapes.
        body = "payParameters=" + urllib.parse.quote(
            json.dumps(pay_params, ensure_ascii=False))
        return self.pay(body)


    def confirm_payment(self, *, operation_ticket: str, otp: str,
                        initial_operation: str = "pay",
                        confirmation_type: str = "SMSBYID") -> Any:
        """Submit the second-factor code for a /v1/pay held at WAITING_CONFIRMATION.

        Capture-verified: a real POST /v1/confirm that completes a held legal-entity
        transfer and answers 200 with the payload's paymentId.

        Two things make this UNLIKE every other money call and unlike the login OTP:

          * It is NOT signed and NOT Bearer-authorised. The captured /v1/confirm
            carried neither `x-api-signature` nor an `Authorization` header — it
            authorises on the session COOKIE plus the `sessionid` query param. So it
            goes out through a bare POST, not _call_signed and not _call_read (which
            would add the Bearer this endpoint does not want).
          * The OTP rides as `secretValue`, alongside the ticket from the pay
            response (`initialOperationTicket`), the operation (`initialOperation`,
            "pay") and the literal type (`confirmationType`, e.g. "SMSBYID"). The
            rest of the body is the app's standard device/anti-fraud block.

        `secretValue` carries 'secret', so the observability redactor scrubs it; the
        OTP is passed straight to the bank and written nowhere else. On success the
        resultCode-OK envelope unwraps to {paymentId, commissionInfo, extraFields}."""
        if not operation_ticket:
            raise TbankApiError("NO_TICKET", "confirm_payment needs the operationTicket "
                                "from the WAITING_CONFIRMATION response")
        p = self.PAY_DEVICE_PROFILE
        lat, lon = _CONFIRM_GEO
        # Field order mirrors the captured body (fidelity; the server ignores order).
        fields = {
            "deviceId": self.device_id,
            "initialOperation": initial_operation or "pay",
            "confirmationType": confirmation_type or "SMSBYID",
            "appVersion": self.app_version or APP_VERSION,
            "mobile_device_model": self.device_model,
            "mobile_device_os_version": _IOS_VERSION,
            "secretValue": str(otp),
            "root_flag": "false",
            "screen_height": p.get("device_screen_height", "2736"),
            "appName": self.app_name,
            "fingerprint": self._credentials_fingerprint(),
            "connectionType": self.connection_type,
            "device_type": "phone",
            "origin": self.origin,
            "screen_dpi": "3",
            "device_location_availability": "when_user",
            "mobile_device_os": "iOS",
            "longitude": str(lon),
            "latitude": str(lat),
            "platform": self.platform,
            "initialOperationTicket": operation_ticket,
            "screen_width": p.get("device_screen_width", "1260"),
        }
        query = urllib.parse.urlencode({"sessionid": self.mobile_sessionid,
                                        "ccc": self.ccc, "cpswc": self.cpswc})
        host = (self._tpl("v1_pay") or {}).get("host") or self.base_url
        url = f"{host.rstrip('/')}/v1/confirm?{query}"
        headers = {"Content-Type": "application/x-www-form-urlencoded; charset=utf-8;",
                   "Accept": _NATIVE_ACCEPT, "X-Lang": "ru", "Accept-Language": "ru",
                   "User-Agent": self._mobile_ua()}
        if self._wide_cookie():
            headers["Cookie"] = self._wide_cookie()
        r = self._http.post(url, data=urllib.parse.urlencode(fields),
                            headers=headers, timeout=30)
        return self._unwrap(r)


    def payment_id_for_order(self, order_id: str) -> str:
        """paymentId of one order, "" if it has none.

        The order's own cartInfo carries it and is one request; the orders() feed
        is the fallback, because a record there can hold a paymentId the card does
        not return. An unpaid reservation has neither."""
        try:
            cart = self.order_details(order_id).get("cartInfo") or {}
            if isinstance(cart, dict) and cart.get("paymentId"):
                return str(cart["paymentId"])
        except TbankApiError:
            pass
        return next((str(o.get("paymentId")) for o in self.orders()
                     if str(o.get("orderId")) == str(order_id) and o.get("paymentId")),
                    "")


    def payment_receipt_pdf(self, payment_id: str) -> bytes:
        data = self._call_read("payment_receipt_pdf",
                               overrides={"paymentId": str(payment_id)})
        return data if isinstance(data, bytes) else bytes(data or b"")
