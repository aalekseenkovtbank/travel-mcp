"""Accounts, cards, invest, orders and get_data."""
from __future__ import annotations

from typing import Any

from . import client_common as _client_common

globals().update({
    name: getattr(_client_common, name)
    for name in dir(_client_common)
    if not name.startswith("__")
})

class BankingMixin:
    """Accounts, cards, invest, orders and get_data."""

    def operations_histogram(self, account_id: str | None, start_ms: int, end_ms: int,
                             period: str = "day", group_by: str = "category") -> dict:
        # the app scopes this one by "accounts" (plural) and always sends timeZone
        ov = {"start": str(start_ms), "end": str(end_ms), "period": period,
              "groupBy": group_by, "config": "allNotInner", "timeZone": "+03:00"}
        if account_id:
            ov["accounts"] = account_id
        return self._call_read("operations_histogram", overrides=ov)


    def list_regular_payments(self, activity_types: str = "payment") -> list[dict]:
        d = self._call_read("list_regular_payments", overrides={"activityTypes": activity_types})
        return self._as_list(d)


    def active_loans(self) -> list[dict]:
        return self._as_list(self._call_read("active_loans"))


    def credit_accounts_list(self) -> list[dict]:
        return self._as_list(self._call_read("credit_accounts_list"))


    def credit_account_payments(self, account: str) -> list[dict]:
        return self._as_list(self._call_read("payments_credit_accounts", overrides={"accounts": account}))


    def cashback_summary(self, loyalty_id: str, codes: str = "lifestyle,targetCashback") -> list[dict]:
        return self._as_list(self._call_read("bonuses_aggregated",
                                             overrides={"loyaltyId": loyalty_id, "codes": codes}))


    def invest_accounts(self) -> list[dict]:
        """The brokerage and InvestBox accounts, unwrapped from payload.accounts.

        _as_list knows about `list` and `payload`; this endpoint answers
        {"accounts": [...]}, which it therefore returned as ONE element — the whole
        envelope — so the caller printed a single row with no brokerAccountId. That
        id is the only argument invest_portfolio/operations/securities take, so the
        entire investment side was unreachable through its own entry point while
        get_data("invest_accounts") held the same data all along.

        Unwrapped here rather than by teaching _as_list about "accounts": the shape
        belongs to this endpoint, and a generic rule would start guessing at every
        other payload that happens to carry a key by that name."""
        data = self._call_read("investbox_accounts")
        if isinstance(data, dict) and isinstance(data.get("accounts"), list):
            return [a for a in data["accounts"] if isinstance(a, dict)]
        return self._as_list(data)


    def invest_portfolio(self, broker_account_id: str, date_from: str, date_to: str,
                          currency: str = "RUB", resolution: str = "MONTH") -> dict:
        """Portfolio statistics. `date_from`/`date_to` are ISO **DATES** (2026-01-31).

        They used to be passed the millisecond timestamps every other read here
        takes, and /api/v1/user/portfolio/statistics answered 400 «неверный формат
        входных данных» — which _json_out then printed as if it were the portfolio.
        The captured call also carries resolution and include_cash_in_periods; without
        them the response has no `dates` series at all."""
        return self._call_read("ca_portfolio_statistics",
                                overrides={"brokerAccountId": broker_account_id,
                                           "from": date_from, "to": date_to,
                                           "currency": currency,
                                           "resolution": resolution,
                                           "include_cash_in_periods": "true"})


    def invest_operations(self, broker_account_id: str, operation_type: str = "",
                           limit: int = 50) -> tuple[list[dict], bool]:
        """(operations, has_next). has_next comes from the answer's envelope — the
        request itself is untouched (no cursor param: its wire name is not in any
        capture; raising `limit` is the confirmed way to see more).

        limit<=0 sends OPERATIONS_ALL_LIMIT upstream, not a literal 0 — the bank
        does not treat 0 as "no cap", it treats it as "almost nothing" (one
        malformed row instead of the real history, confirmed live)."""
        upstream_limit = limit if limit > 0 else self.OPERATIONS_ALL_LIMIT
        ov = {"brokerAccountId": broker_account_id, "limit": str(upstream_limit)}
        if operation_type:
            ov["operationType"] = operation_type
        data = self._call_read("ca_operations", overrides=ov)
        # {"items": [...], "hasNext": …, "nextCursor": …} — _as_list does not know
        # this key and returned the envelope as a single element, so the caller
        # printed one row reading «- [] ? |». hasNext used to be dropped here too,
        # so the tool could not say the bank was holding more operations back.
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            return ([o for o in data["items"] if isinstance(o, dict)],
                    bool(data.get("hasNext")))
        return self._as_list(data), False


    def invest_securities(self, broker_account_id: str = "") -> list[dict]:
        """Positions, as [{brokerAccountId, name, positions: [...]}, …].

        The endpoint takes NO account filter — the captured call sends only sort
        parameters and returns every portfolio. Passing brokerAccountId to it did not
        error, it just came back with `portfolios: []`, so the tool reported an empty
        portfolio for an account holding millions. Filtering is ours, done here."""
        data = self._call_read("purchased_securities",
                               overrides={"stocksSort": "by_name", "stocksSortOrder": "asc",
                                          "bondsSort": "by_name", "bondsSortOrder": "asc",
                                          "etfSort": "by_name", "etfSortOrder": "asc"})
        out = []
        for p in (data.get("portfolios") or []) if isinstance(data, dict) else []:
            acc = (p.get("brokerAccount") or {}) if isinstance(p, dict) else {}
            if broker_account_id and str(acc.get("brokerAccountId")) != str(broker_account_id):
                continue
            out.append({"brokerAccountId": acc.get("brokerAccountId"),
                        "name": acc.get("name") or acc.get("brokerCyrillic") or "",
                        "positions": [x for x in (p.get("positions") or [])
                                      if isinstance(x, dict)]})
        return out


    def subscription_all(self) -> list[dict]:
        """All subscriptions (recurring services)."""
        return self._as_list(self._call_read("subscription_all"))


    def subscription_all_bills(self) -> list[dict]:
        """All subscription bills."""
        return self._as_list(self._call_read("subscription_all_bills"))


    def account_details(self) -> dict:
        """Account details (full)."""
        return self._call_read("account_details")


    def full_debt_amount(self) -> dict:
        """Full debt amount (credit)."""
        return self._call_read("full_debt_amount")


    def invoices_to_pay(self) -> list[dict]:
        """Invoices/money requests to pay."""
        return self._as_list(self._call_read("invoices_to_pay"))


    def get_invoices(self) -> list[dict]:
        """Get invoices."""
        return self._as_list(self._call_read("get_invoices"))


    def my_invoices(self) -> list[dict]:
        """My invoices (money requests issued)."""
        return self._as_list(self._call_read("my_invoices"))


    def available_cards(self) -> list[dict]:
        """Available cards (issuable)."""
        return self._as_list(self._call_read("available_cards"))


    def statements(self) -> list[dict]:
        """Account statements."""
        return self._as_list(self._call_read("statements"))


    def statement_exist(self) -> dict:
        """Whether a statement exists."""
        return self._call_read("statement_exist")


    def credit_payment_schedule(self) -> list[dict]:
        """Credit payment schedule."""
        return self._as_list(self._call_read("credit_payment_schedule"))


    def credit_rating(self) -> dict:
        """Credit rating."""
        return self._call_read("credit_rating")


    def credit_recommendations(self) -> list[dict]:
        """Credit recommendations."""
        return self._as_list(self._call_read("credit_recommendations"))


    def manager_info(self) -> dict:
        """Personal manager info."""
        return self._call_read("manager_info")


    def bank_info(self) -> dict:
        """Bank info (branches/contacts)."""
        return self._call_read("bank_info")


    def autopayments(self) -> list[dict]:
        """Autopayments."""
        return self._as_list(self._call_read("autopayments"))


    def sbp_subscriptions(self) -> list[dict]:
        """SBP (SBP-by-Phone) subscriptions."""
        return self._as_list(self._call_read("sbp_subscriptions"))


    def client_offers(self) -> list[dict]:
        """Client offers."""
        return self._as_list(self._call_read("client_offers"))


    def gift_for_recipient(self) -> list[dict]:
        """Gifts for recipient."""
        return self._as_list(self._call_read("gift_for_recipient"))


    def finhealth_balance_total(self) -> dict:
        """Finhealth: total balance metric."""
        return self._call_read("finhealth_balance_total")


    def finhealth_balance_turnover(self) -> dict:
        """Finhealth: balance turnover metric."""
        return self._call_read("finhealth_balance_turnover")


    def finhealth_invest_turnover(self) -> dict:
        """Finhealth: invest turnover metric."""
        return self._call_read("finhealth_invest_turnover")


    def p2p_countries(self) -> list[dict]:
        """P2P transfer countries."""
        return self._as_list(self._call_read("p2p_countries"))


    def services(self) -> list[dict]:
        """Connected services."""
        return self._as_list(self._call_read("services"))


    def invest_pension_profile(self) -> dict:
        """Invest pension profile."""
        return self._call_read("invest_pension_profile")


    def investbox_offers(self) -> list[dict]:
        """InvestBox deposit offers."""
        return self._as_list(self._call_read("investbox_offers"))


    def investbox_product_yield(self) -> list[dict]:
        """InvestBox product yield."""
        return self._as_list(self._call_read("investbox_product_yield"))


    def broker_margin(self) -> dict:
        """Broker margin attributes."""
        return self._call_read("broker_margin")


    def invest_offers(self) -> list[dict]:
        """Invest offers (virtual stock)."""
        return self._as_list(self._call_read("invest_offers"))


    def bundles_all(self) -> list[dict]:
        """All bundles (premium service bundles)."""
        return self._as_list(self._call_read("bundles_all"))


    def detected_merchant_subscriptions(self) -> list[dict]:
        """Recurring third-party billing detected from card statements (merchant, price, next payment date)."""
        return self._as_list(self._call_read("detected_merchant_subscriptions"))


    def user_profile(self) -> dict:
        """Canonical bank identity profile (name, phone, email, siebel_id)."""
        return self._call_read("user_profile")


    def broker_portfolio_accounts(self) -> list[dict]:
        """Brokerage accounts with total amount + expected yield (P&L)."""
        return self._as_list(self._call_read("broker_portfolio_accounts"))


    def my_homes(self) -> list[dict]:
        """Linked homes (Мой дом) with address, price, utility providers."""
        return self._as_list(self._call_read("my_homes"))


    def my_home_activities(self) -> list[dict]:
        """Per-home utility bills to pay and subscription bills."""
        return self._as_list(self._call_read("my_home_activities"))


    def my_cars(self) -> list[dict]:
        """Saved vehicles (make, model, reg number, VIN)."""
        return self._as_list(self._call_read("my_cars"))


    def unread_support_requests(self) -> list[dict]:
        """csc.tbank.ru support/tracker realm — uses a WEBSESS/support session, NOT the
        mobile session. The mobile Bearer+cookie auth here will likely be REJECTED
        (401/403). Not wired to any MCP tool / get_data section today (orphan).
        Capture-verify the support-session auth before exposing it."""
        return self._as_list(self._call_read("unread_support_requests"))


    def bank_by_bik(self, bik: str) -> dict:
        """Bank name + correspondent account for a БИК (GET /v1/bank_info?bik=…).

        The app calls this the moment a QR resolves, and it is the reason a payment
        by hand-typed requisites needs only the БИК: the corr account and the bank's
        legal name come back from here rather than from the payer's memory.

        Separate from bank_info(), which takes no argument and answers with the
        bank's own branches/contacts."""
        digits = re.sub(r"\D", "", str(bik or ""))
        if len(digits) != 9:
            raise TbankApiError("INVALID_BIK",
                f"БИК — это 9 цифр, получено {bik!r}")
        return self._call_read("bank_info", overrides={"bik": digits}) or {}


    def merchant_brand(self) -> list[dict]:
        """Merchant brand metadata (logos/colors) by merchant id."""
        return self._as_list(self._call_read("merchant_brand"))


    def money_request_public_page(self) -> list[dict]:
        """Public share link for a money request."""
        return self._as_list(self._call_read("money_request_public_page"))


    def finhealth_account_presets(self) -> dict:
        """Finhealth tracked-account preset (which accounts are in metrics)."""
        return self._call_read("finhealth_account_presets")


    def business_account_info(self) -> list[dict]:
        """Business account info."""
        return self._as_list(self._call_read("business_account_info"))


    def shared_resources_owned(self) -> list[dict]:
        """Shared resources I own."""
        return self._as_list(self._call_read("shared_resources_owned"))


    def shared_resources(self) -> list[dict]:
        """Shared resources (accessed)."""
        return self._as_list(self._call_read("shared_resources"))


    def contact_list(self) -> list[dict]:
        """Contact list (saved recipients)."""
        return self._as_list(self._call_read("contact_list"))


    def atm_withdrawal_qrs(self) -> list[dict]:
        """ATM withdrawal QRs."""
        return self._as_list(self._call_read("atm_withdrawal_qrs"))


    def check_rating(self) -> dict:
        """Check rating."""
        return self._call_read("check_rating")


    def credit_collection_info(self) -> dict:
        """Credit collection info."""
        return self._call_read("credit_collection_info")


    def active_account_options(self) -> list[dict]:
        """Active account options."""
        return self._as_list(self._call_read("active_account_options"))


    def appointment_deliveries(self) -> list[dict]:
        """Active appointment deliveries."""
        return self._as_list(self._call_read("appointment_deliveries"))


    def list_accounts(self) -> list[dict]:
        data = self._call_read("accounts_light")
        if isinstance(data, dict):
            return data.get("payload") or data.get("accounts") or [data]
        return data


    def list_operations(self, account_id: str | None, start_ms: int, end_ms: int) -> list[dict]:
        """Operations for a period, filtered to one account.

        ``isSuspicious`` is a per-operation FIELD, not a filter flag to set: passing
        ``isSuspicious=true`` narrows the result to fraud-flagged operations, which is
        normally none — the capture has one such request (item 105) returning an empty
        list while every request without it returns 273-440 operations. Sending it
        unconditionally made this tool always answer "no operations".

        The real app also does not scope /v1/operations by account (it fetches all and
        filters client-side on the operation's ``account`` field) — so do the same."""
        ov = {"start": str(start_ms), "end": str(end_ms)}
        data = self._call_read("operations", overrides=ov)
        if isinstance(data, dict):
            pl = data.get("payload")
            ops = pl if isinstance(pl, list) else ([pl] if pl else [])
        else:
            ops = data if isinstance(data, list) else []
        if account_id:
            kept = [o for o in ops
                    if isinstance(o, dict) and str(o.get("account", "")) == str(account_id)]
            # The fetch is unscoped and the filter runs here, so an id of the wrong
            # KIND — a card id where an account id belongs — matches nothing and the
            # answer reads as «этот счёт не использовался», not «такого счёта нет».
            # A non-empty fetch that filters to nothing is the one case where those
            # differ, and only this layer can tell them apart.
            if ops and not kept:
                present = sorted({str(o.get("account")) for o in ops
                                  if isinstance(o, dict) and o.get("account")})
                raise TbankApiError("NO_SUCH_ACCOUNT",
                    f"среди {len(ops)} операций за период нет ни одной по счёту "
                    f"{account_id!r}. Счета с операциями: {', '.join(present[:8])}"
                    + (" …" if len(present) > 8 else "")
                    + ". Похоже, передан id не того вида — id счёта берётся из "
                      "list_accounts(), а не из list_cards().")
            ops = kept
        return ops


    def _histogram_side(side: dict | None) -> tuple[float, dict[str, float]]:
        """Sum one side of an operations_histogram payload by category.

        The shape is a TREE, not a list: {summary:{value}, intervals:[{summary,
        aggregated:[{groupBy, amount:{value}, category:{id,name}}], start, end}]}
        — one interval per `period` (31 of them for a 30-day daily request), each
        holding that day's categories. Iterating the side itself yields the two
        dict KEYS, which is what the previous version did: every entry failed the
        isinstance(dict) test, so the tool reported Total 0 and no categories on
        a payload whose summary was 3.87M RUB (captures.xml #52).
        """
        if not isinstance(side, dict):
            return 0.0, {}
        by_cat: dict[str, float] = {}
        for iv in side.get("intervals") or []:
            if not isinstance(iv, dict):
                continue
            for a in iv.get("aggregated") or []:
                if not isinstance(a, dict):
                    continue
                name = ((a.get("category") or {}).get("name")
                        or a.get("groupBy") or a.get("groupByKey") or "?")
                amt = a.get("amount") or {}
                try:
                    val = abs(float(amt.get("value") if isinstance(amt, dict) else amt))
                except (TypeError, ValueError):
                    continue
                by_cat[name] = by_cat.get(name, 0.0) + val
        # The bank's own total is authoritative; summing the tree is the fallback
        # (they agree to the kopeck on the capture, but a partial page would not).
        summary = side.get("summary") or {}
        try:
            total = abs(float(summary.get("value")))
        except (TypeError, ValueError):
            total = sum(by_cat.values())
        return total, by_cat


    def spending_categories(self, account_id: str | None, start_ms: int, end_ms: int) -> dict:
        """operations_histogram?groupBy=category, flattened to per-category totals."""
        ov = {"start": str(start_ms), "end": str(end_ms), "groupBy": "category",
              "period": "day", "config": "allNotInner", "timeZone": "+03:00"}
        if account_id:
            ov["accounts"] = account_id
        data = self._call_read("operations_histogram", overrides=ov)
        payload = data.get("payload", data) if isinstance(data, dict) else {}
        total, by_cat = self._histogram_side(payload.get("spending"))
        earned, _ = self._histogram_side(payload.get("earning"))
        cats = [{"category": name, "amount": round(amount, 2),
                 "share_pct": round(amount / total * 100, 2) if total else 0.0}
                for name, amount in by_cat.items()]
        currency = (((payload.get("spending") or {}).get("summary") or {})
                    .get("currency") or {}).get("name") or "RUB"
        return {
            "period": {"start_ms": start_ms, "end_ms": end_ms},
            "total_spent": round(total, 2), "currency": currency,
            "categories": sorted(cats, key=lambda x: x["amount"], reverse=True),
            "total_earned": round(earned, 2),
        }


    def account_cards(self, account_id: str) -> list[dict]:
        """Cards issued on one account. Each card carries BOTH an `id` and a
        `ucid` — /v1/limits and /v1/card_credentials key off the **ucid**, while
        an operation's `card` field holds the **id**. Mixing them up silently
        returns another card's data."""
        data = self._call_read("account_cards", overrides={"id": str(account_id)})
        return data if isinstance(data, list) else []


    def cards(self) -> list[dict]:
        """Every card across every account, annotated with its account.

        ONE request. accounts_light already embeds the cards under `cards` (and
        `card` for an ExternalAccount), so the old fan-out — one /v1/account_cards
        per account, 12 extra round-trips on this user, most of them 400s for
        deposits and invest accounts — bought nothing. It bought less, in fact:
        the per-account response carries only id/ucid/position/flags, while the
        embedded one also has name, status, paymentSystem, the masked number and
        the expiry, which is what list_cards actually prints.

        account_cards() stays for the fields only it has (availableBalance,
        canBeRemoved); it is just no longer on this path."""
        out: list[dict] = []
        for acc in self.list_accounts():
            aid = str(acc.get("id") or "")
            if not aid:
                continue
            embedded = acc.get("cards")
            if not isinstance(embedded, list):
                one = acc.get("card")
                embedded = [one] if isinstance(one, dict) else []
            money = acc.get("moneyAmount") if isinstance(acc.get("moneyAmount"), dict) else {}
            for c in embedded:
                if not isinstance(c, dict):
                    continue
                c = dict(c)
                c["account"] = aid
                c["accountName"] = acc.get("name") or ""
                c["accountType"] = acc.get("accountType") or ""
                # The per-account endpoint had availableBalance; the embedded card
                # does not. The account's balance is the right number anyway — cards
                # in a multicard cluster all spend from it.
                c.setdefault("availableBalance", money.get("value"))
                c["currency"] = ((money.get("currency") or {}).get("name")
                                 if isinstance(money.get("currency"), dict) else "")
                out.append(c)
        return out


    def card_limits(self, ucid: str) -> list[dict]:
        data = self._call_read("card_limits", overrides={"ucid": str(ucid)})
        return data if isinstance(data, list) else []


    def _credentials_fingerprint(self) -> str:
        """The device blob /v1/card_credentials expects — the ###-delimited UA
        form (NOT the JSON fingerprint used at auth/step).

        The screen and timezone come from PAY_DEVICE_PROFILE, the same source the
        /v1/pay anti-fraud block uses, so TBANK_DEVICE_SCREEN_* reaches both. They
        were hardcoded here as 1170x2532 while all five captured card_credentials
        requests send 1260x2736 — the value already sitting in PAY_DEVICE_DEFAULTS
        a few hundred lines up. One session claiming two different screens is
        exactly the inconsistency the note above PAY_DEVICE_CONSTANTS warns about,
        and this is the endpoint that returns a PAN and a CVV."""
        ua = self._mobile_ua() or "iPhone/iOS/TCSMB"
        p = self.PAY_DEVICE_PROFILE
        w = p.get("device_screen_width", "1260")
        h = p.get("device_screen_height", "2736")
        tz = str(p.get("timezone", "180")).lstrip("+-")
        return f"{ua}###{w}x{h}x32###-{tz}###false###false###"


    def card_credentials(self, ucid: str) -> dict:
        """Full card number + CVV + expiry for one card. Sensitive: the caller
        decides whether to show or mask it."""
        ov = {
            "ucid": str(ucid),
            "fingerprint": self._credentials_fingerprint(),
            "fingerprint_change_date": "0",
            "mobile_device_os": self.platform or "ios",
            "mobile_device_os_version": _IOS_VERSION,
            "mobile_device_model": self.device_model,
        }
        data = self._call_read("card_credentials", overrides=ov)
        return data if isinstance(data, dict) else {}


    def account_requisites(self, account_id: str,
                           currencies: tuple = ("RUB",)) -> list[dict]:
        """Bank details for an account. The `account` param repeats once per
        currency (`<id>;RUB`) — a list value becomes repeated query params."""
        accounts = [f"{account_id};{c}" for c in currencies]
        data = self._call_read("account_group_requisites",
                               overrides={"account": accounts})
        return data if isinstance(data, list) else []


    def prefill_contact_id(self) -> str:
        """The contact id every prefill/profile path is built from.

        Memoised: documents() needs it for BOTH the document list and the holder's
        brief, so one tool call issued the identical request twice."""
        memo = getattr(self, "_memo", None)
        if memo is not None and memo.get("prefill_contact_id"):
            return memo["prefill_contact_id"]
        data = self._call_read("prefill_contact")
        contacts = (data or {}).get("contacts") or []
        if not contacts:
            raise TbankApiError("NO_CONTACT", "prefill profile returned no contact")
        cid = str(contacts[0].get("id") or "")
        if memo is not None:
            memo["prefill_contact_id"] = cid
        return cid


    def identity_documents(self) -> dict:
        """Every document the bank holds, grouped by kind (RusNationalID,
        RusDriversLic, RusInternationalID, RusSNILS, RusINN, RusOSAGO, …).

        Includes RELATIVES' documents the client once entered, so the caller must
        separate them — see documents() in server.py, which matches on birthDate."""
        cid = self.prefill_contact_id()
        data = self._call_read(
            "prefill_documents",
            path_override=f"/api/prefill/profile/contact/{cid}/document/all")
        return (data or {}).get("documents") or {}


    def identity_brief(self) -> dict:
        """The account holder's own birthDate/sex — the key that tells their
        documents apart from a relative's."""
        cid = self.prefill_contact_id()
        data = self._call_read(
            "prefill_userinfo_brief",
            path_override=f"/api/prefill/profile/contact/{cid}/userinfo/brief")
        return (data or {}).get("brief") or {}


    def orders(self) -> list[dict]:
        """All orders across groceries, cinema, concerts, flights, trains and
        hotels — the app's single "Заказы" feed. Newest first is NOT guaranteed;
        sort on `created`."""
        data = self._call_read("orders_list")
        lst = (data or {}).get("list") if isinstance(data, dict) else data
        return lst if isinstance(lst, list) else []


    def order_details(self, order_id: str) -> dict:
        """Full detail for one entertainment order (hall, seats, QR, cast)."""
        data = self._call_read("order_get", overrides={"orderId": str(order_id)})
        return data if isinstance(data, dict) else {}


    def order_cancel_context(self, order_id: str) -> dict:
        """What is worth knowing BEFORE cancelling, from one order_details() call:
        {"available": bool|None, "status": str, "payment_id": str, "found": bool}.

        `available` is the bank's own isCancelAvailable and is the only field that
        predicted the outcome across every observed attempt: the one order flagged
        true cancelled, the seven flagged false were refused and stayed put. None
        means the field was absent — that is not a refusal, just no signal.

        Read `status`, not `paidFor`: an unpaid reservation carries paidFor=true as
        well, so that field says nothing about payment. Unpaid ones sit under the
        same `orderInfo` key and never appear in the orders() feed at all."""
        try:
            data = self.order_details(order_id)
        except TbankApiError:
            return {"available": None, "status": "", "payment_id": "", "found": False}
        info = data.get("orderInfo") if isinstance(data.get("orderInfo"), dict) else data
        cart = data.get("cartInfo") if isinstance(data.get("cartInfo"), dict) else {}
        avail = info.get("isCancelAvailable")
        return {
            "available": avail if isinstance(avail, bool) else None,
            "status": str(info.get("status") or ""),
            "payment_id": str(cart.get("paymentId") or ""),
            "found": bool(info),
        }


    def bank_documents(self) -> list[dict]:
        """Bank-issued certificates (справки). Answers with a BARE list."""
        data = self._call_read("bank_documents")
        return data if isinstance(data, list) else []


    def insurance_policies(self) -> Any:
        """Active insurance policies. This host capitalises its envelope
        (`Payload`/`ResultCode`), so _unwrap passes the whole body through."""
        return self._call_read("insurance_policies")


    _SECTION_ARG = {"providers": "ids", "requisites": "pointer",
                    "statements": "account", "account_details": "id",
                    "full_debt_amount": "account", "statement_exist": "account"}


    _SECTION_NEEDS_CLIENT = {"invoices", "subscription_bills", "subscriptions",
                             "templates", "autopayments", "sbp",
                             "requisites", "manager", "offers"}


    def get_data(self, section: str, arg: str = "", days: int = 30) -> Any:
        """Unified getter for banking data.

        `arg` is required by the sections in _SECTION_ARG (providers → a
        comma-separated id list; requisites → a phone). Passing it for any other
        section is ignored. `days` sets the statements window — it used to be a
        buried literal 30, so older statements were unreachable through any
        argument while the answer read as complete."""
        _SECTIONS = {
            "subscriptions": "subscription_all",
            # NO subscriptionIds. An audit finding said the missing filter was why an
            # unpaid ГИБДД fine read as «счетов нет», and that the app's two-request
            # chain had to be copied. Implementing it returned nothing at all; the
            # live numbers say why:
            #     /v1/subscription/all_bills                   → 2 records, 4 bills
            #     /v1/subscription/all_bills?subscriptionIds=… → 0 records
            #     /v1/subscription/all                         → 0 subscriptions
            # The parameter NARROWS; the app sends it because it is rendering one
            # provider's screen. The bill really was invisible — but because this
            # section validates the sessionid, whose CLIENT window is ~11 minutes,
            # which _SECTION_NEEDS_CLIENT now raises first.
            "subscription_bills": "subscription_all_bills",
            "credit_schedule": "credit_payment_schedule", "credit_rating": "credit_rating",
            "statements": "statements", "requisites": "get_requisites",
            "invoices": "invoices_to_pay", "templates": "payment_templates",
            "contacts": "contact_list", "providers": "providers_compatible",
            "cards": "available_cards", "loans": "active_loans",
            "autopayments": "autopayments", "sbp": "sbp_subscriptions",
            "offers": "client_offers", "gifts": "gift_for_recipient",
            "services": "services", "bundles": "bundles_all",
            "manager": "manager_info", "merchant_subs": "detected_merchant_subscriptions",
            "profile": "user_profile", "homes": "my_homes",
            "cars": "my_cars", "shortcuts": "payment_shortcuts",
            "finhealth_presets": "finhealth_account_presets",
            "finhealth_total": "finhealth_balance_total",
            "finhealth_turnover": "finhealth_balance_turnover",
            "finhealth_invest": "finhealth_invest_turnover",
            "invest_accounts": "investbox_accounts",
            "invest_offers": "investbox_offers", "invest_yield": "investbox_product_yield",
            "broker_margin": "broker_margin", "pension": "invest_pension_profile",
            "shared_owned": "shared_resources_owned", "shared": "shared_resources",
            "business_info": "business_account_info",
            "appointments": "appointment_deliveries",
            "account_details": "account_details",
            "full_debt_amount": "full_debt_amount",
            "statement_exist": "statement_exist",
            # "qr_resolve" НЕ здесь: resolve_payment_qr — это POST, чей единственный
            # вход — тело {barcodeHash, qr, frontendFeatureFlag}, а get_data тела не
            # передаёт. Секция уходила запросом без QR и не могла ничего разрешить.
            # Рабочий путь — payment_qr(qr).
        }
        if section.lower() == "profile":
            # /userinfo/userinfo needs client_id=gorod-app + no mobile-BFF params —
            # route through _call_userinfo, not the generic _call_read (which 401s).
            return self._call_userinfo()
        if section.lower() in self._SECTION_NEEDS_CLIENT:
            # These validate the sessionid, not just the Bearer, and its CLIENT
            # window is ~11 minutes against the token's ~2h. Without this they
            # answer INSUFFICIENT_PRIVILEGES / «Невозможно определить подписчика»
            # once the window lapses — which reads to an agent as "you have no
            # bills", not as "the session needs raising". Costs one ping, and only
            # for the sections that actually check.
            self.ensure_client_session()
        if section.lower() not in _SECTIONS:
            # Раньше неизвестная секция уезжала В ИМЯ ШАБЛОНА: get_data("v1_pay")
            # выполняло POST /v1/pay, get_data("grocery_cart_set") — запись корзины,
            # get_data("order_cancel") — отмену заказа. Тул помечен
            # readOnlyHint=True/idempotentHint=True, то есть хост вправе выполнить
            # его без спроса. Перечень закрыт.
            raise TbankApiError("UNKNOWN_SECTION",
                f"get_data('{section}') — такой секции нет. Доступные: "
                + ", ".join(sorted(_SECTIONS))
                + ". Разобрать платёжный QR — payment_qr(qr).")
        key = _SECTIONS[section.lower()]
        arg_key = self._SECTION_ARG.get(section.lower())
        if arg_key:
            if not arg:
                raise TbankApiError("ARG_REQUIRED",
                    f"get_data('{section}') is a filter endpoint and returns nothing "
                    f"without an argument: pass {arg_key}. "
                    + ("Provider ids look like 'fns-rf', 'gibdd-online-rf' "
                       "(capture-verified) — they cannot be enumerated through this "
                       "endpoint, only looked up."
                       if arg_key == "ids" else
                       "Pass the account id from list_accounts()."
                       if arg_key in ("account", "id") else
                       "For a recipient lookup prefer transfer_sbp_resolve(phone), "
                       "which parses the same response; for YOUR OWN account details "
                       "use account_requisites(account_id) — a different endpoint."))
            ov = {arg_key: arg}
            if section.lower() == "statements":
                # The other two query params the app always sends with the account.
                start, _ = ms_for_period(days)
                ov.update({"dateFrom": str(start), "itemsOrder": "desc"})
            return self._call_read(key, overrides=ov)
        return self._call_read(key)
