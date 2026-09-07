"""Cinema, concerts, venues and ticket orders."""
from __future__ import annotations

from typing import Any

from . import client_common as _client_common

globals().update({
    name: getattr(_client_common, name)
    for name in dir(_client_common)
    if not name.startswith("__")
})

class AfishaMixin:
    """Cinema, concerts, venues and ticket orders."""

    PAGE = 30                      # what the collection endpoint returns per page


    def afisha_collection_code(self, prefix: str, kind: str = "movie",
                               city: str = "", city_id: int | str = 0) -> str:
        """The server's own collectionCode for a shelf, e.g. "Segodnya-v_kino_".

        This used to be built by transliterating the city name, which is a guess
        that happens to be right for Moscow. The server publishes the codes, and
        its own spelling is not consistent — the same city appears as Moskva,
        moscow and msk across different shelves — so nothing derived from the name
        could have covered them all."""
        cid = city_id_of(city, city_id)
        # `getattr(...) or {}` would be a bug here: an EMPTY memo is falsy, so the
        # fallback would hand back a fresh dict every call and cache nothing.
        memo = getattr(self, "_memo", None)
        if memo is None:
            memo = self._memo = {}
        shelves = memo.setdefault("afisha_shelves", {})
        key = (vertical(kind)["service"], cid)
        if key not in shelves:
            data = self._call_read("events_by_service", overrides={
                "service": key[0], "cityId": cid})
            shelves[key] = [c for c in ((data or {}).get("collections") or [])
                            if isinstance(c, dict)]
        found = next((str(c.get("code")) for c in shelves[key]
                      if str(c.get("code") or "").startswith(prefix)), "")
        if found:
            return found
        # An empty shelf list is a live condition, not a contract: Moscow's came
        # back empty while Petersburg's was full. Fall back to the convention the
        # server itself uses for this family rather than reporting no cinema.
        name = city or CITY_IDS.get(int(cid) if str(cid).isdigit() else -1, "")
        return prefix + translit_city(name) if name else ""


    def cinema_movies(self, city: str = "", query: str = "",
                      max_pages: int = 8,
                      city_id: int | str = 0) -> tuple[list[dict], int, int]:
        """Movies playing today in `city`, as (matches, scanned, listing_total).

        The collection code comes from the server's own shelf list; it is only a
        way to reach an eventId, which is itself city-independent and is what the
        schedule endpoint wants.

        The listing has no server-side search, so matching is ours and every page has
        to be seen. A previous version stopped as soon as ONE page held a match,
        which made a named search cheap and wrong: matches on later pages vanished,
        and the caller then reported the survivors as the complete count. Pages after
        the first are fetched concurrently instead — page 1 states the true total, so
        the page count is known after one request and the rest cost one round trip.

        `scanned` is returned so the caller can tell "these are all of them" from
        "these are all of them among the first N" when max_pages binds."""
        code = self.afisha_collection_code("Segodnya-v_kino_", "movie",
                                           city=city, city_id=city_id)
        if not code:
            raise TbankApiError(
                "NO_TODAY_SHELF",
                f"у города {city or city_id} нет полки «сегодня в кино» — "
                "возможно, в нём нет проката")
        q = query.lower().replace("ё", "е") if query else ""

        def matches(e):
            return not q or q in str(e.get("name", "")).lower().replace("ё", "е")

        def fetch(page: int) -> tuple[list, int]:
            data = self._call_read("events_collection", body={"genres": []},
                                   overrides={"collectionCode": code,
                                              "page": str(page), "count": str(self.PAGE)})
            coll = (data or {}).get("collection") or {}
            return [e for e in (coll.get("events") or []) if isinstance(e, dict)], \
                   int(coll.get("amount") or 0)

        out, total = fetch(1)
        pages = min(max(1, max_pages), -(-total // self.PAGE) if total else 1)
        if pages > 1 and len(out) < total:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=min(4, pages - 1)) as pool:
                for events, _ in pool.map(fetch, range(2, pages + 1)):
                    out.extend(events)
        return [e for e in out if matches(e)], len(out), total


    def cinema_schedule(self, event_id: str = "", date: str = "", city: str = "",
                        latitude: float = 0.0, longitude: float = 0.0,
                        object_id: str = "") -> list[dict]:
        """Showtimes on one date (YYYY-MM-DD). Three shapes, all capture-shaped:

        * object_id alone — EVERYTHING that cinema plays that day, in one request.
          This is the only way to a cinema's repertoire: no other endpoint answers
          «what is on at this venue» for film, and the alternative is asking the
          schedule of every film in the city one by one. Verified live against Каро
          11: 24 films, 48 showings, one call — and one of those films was missing
          from the city listing entirely, because that listing is today's and the
          film only ran the next day.
        * event_id + object_id — one film at one cinema.
        * event_id + city — that film across the city, sorted by distance.

        The city rides as a NAME here, not as the numeric cityId the rest of the
        afisha uses; the captured bodies carry "city": "Москва". It is not
        defaulted, because a Moscow listing is a plausible-looking answer to a
        question about somewhere else. With object_id the city is not sent at all —
        the venue already fixes it.

        The location only sorts by distance — the whole city is returned either way.
        Pass latitude/longitude to sort around a real point; omitted, the centre of
        `city` is used, and for a city not in CITY_CENTRES the distance sort is
        dropped rather than anchored somewhere arbitrary."""
        if not (event_id or object_id):
            raise TbankApiError("NO_TARGET",
                                "нужен event_id (фильм) или object_id (кинотеатр)")
        body: dict = {"date": date}
        if object_id:
            body["objectId"] = str(object_id)
            if event_id:
                body["eventId"] = str(event_id)
            data = self._call_read("schedule_movie", body=body)
            lst = (data or {}).get("list") if isinstance(data, dict) else data
            return lst if isinstance(lst, list) else []
        if not str(city).strip():
            raise TbankApiError("CITY_REQUIRED",
                                "не назван город; cinema_schedule требует city "
                                "или object_id кинотеатра")
        body["eventId"] = str(event_id)
        body["city"] = city
        if not (latitude or longitude):
            latitude, longitude = self.CITY_CENTRES.get(city, (0.0, 0.0))
        if latitude or longitude:
            body["sort"] = {"by": "distance"}
            body["location"] = {"latitude": latitude, "longitude": longitude}
        data = self._call_read("schedule_movie", body=body)
        lst = (data or {}).get("list") if isinstance(data, dict) else data
        return lst if isinstance(lst, list) else []


    def _date_bounds(date_from: str, date_to: str) -> dict:
        """{from, to} covering whole days. The +03:00 is a literal: the afisha runs
        on Moscow time and the captured bodies say so, so deriving it from the host
        clock would move the window on a machine in another zone."""
        a = str(date_from or date_to or "").strip()
        b = str(date_to or date_from or "").strip()
        if not a:
            raise TbankApiError("DATE_REQUIRED", "нужна дата: date_from (и date_to)")
        return {"from": f"{a}T00:00:00+03:00", "to": f"{b}T23:59:59+03:00"}


    def afisha_catalog(self, kind: str = "movie", city: str = "",
                       date_from: str = "", date_to: str = "",
                       city_id: int | str = 0, query: str = "",
                       count: int = 0, max_pages: int = 8) -> tuple[list[dict], int]:
        """Everything of one vertical playing in a date RANGE, as (events, amount).

        The app only asks for one day because its calendar picks one, but the
        server takes a range — an eight-day window in Moscow answers with 197
        unique films against 83 for a single day, and the extra titles are real
        one-off screenings. An event repeats across the days it runs, so results
        are deduplicated on eventId, first occurrence winning.

        Two shapes hide behind one call. movie ignores count/page and hands back
        the vertical whole, with EMPTY slots — the showings live in
        cinema_schedule. concert and spectacle paginate for real and do carry
        slots. Exhibitions have no catalogue at all; nothing in the captures posts
        to /api/events/exhibition, so this refuses rather than inventing a path.

        `query` is matched here, not by the server, which is why the pages are all
        read before filtering."""
        v = vertical(kind)
        if not v["catalog_key"]:
            raise TbankApiError(
                "NO_CATALOG",
                f"у вертикали «{kind}» нет каталога по датам; смотри "
                "search_app(screen=\"afisha\") или place_schedule()")
        cid = city_id_of(city, city_id)
        window = self._date_bounds(date_from, date_to)
        size = count if count > 0 else self.CATALOG_PAGE

        def fetch(page: int) -> tuple[list, int]:
            data = self._call_read(v["catalog_key"], body={
                "cityId": cid, "count": size, "page": page, "date": window})
            lst = [e for e in ((data or {}).get("list") or []) if isinstance(e, dict)]
            return lst, int((data or {}).get("amount") or 0)

        out, amount = fetch(1)
        if v["catalog_paged"] and len(out) < amount:
            pages = min(max(1, max_pages), -(-amount // size))
            if pages > 1:
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=min(4, pages - 1)) as pool:
                    for events, _ in pool.map(fetch, range(2, pages + 1)):
                        out.extend(events)
        seen, uniq = set(), []
        for e in out:
            key = str(e.get("eventId") or id(e))
            if key not in seen:
                seen.add(key)
                uniq.append(e)
        scanned = len(uniq)
        if query:
            q = _norm_city(query)
            uniq = [e for e in uniq if q in _norm_city(e.get("eventName") or "")]
        # `scanned` alongside `amount`, the way cinema_movies already reports it.
        # Without it the caller cannot tell «these are all of them» from «these are
        # the first max_pages×count of them» — and the `query` above filters the
        # SCANNED slice, so «ничего не найдено» was also being said about events the
        # scan never reached.
        return uniq, scanned, amount


    def ticket_artifacts(self, order_id: str) -> dict:
        """What is actually presented at the door, for one order.

        It lives in the ORDERS FEED, in the order's `fields` — not in
        order_details, which carries the booking code and nothing else. The
        obvious-looking /api/tickets/get is dead: four calls, four code=228, so no
        template exists for it and none should be added.

        Coverage is partial and the caller has to say so: across 75 afisha orders
        every one carried a reservationCode but only 53 carried a `qr`, and the
        partners differ in what they hand out — Рамблер gives a pdfUrl, Ticketland
        gives neither. An unpaid reservation is not in this feed at all, so an
        empty answer means «no ticket yet», not «no such order»."""
        row = next((o for o in self.orders()
                    if str(o.get("orderId")) == str(order_id)), None)
        if row is None:
            return {}
        f = row.get("fields") or {}
        return {
            "found": True,
            "status": str(row.get("status") or ""),
            "event": str(f.get("eventName") or row.get("title") or ""),
            "venue": str(f.get("objectName") or f.get("objectForeignName") or ""),
            "hall": str(f.get("hallName") or ""),
            "partner": str(f.get("partnerName") or ""),
            "reservation_code": str(f.get("reservationCode") or ""),
            # A short payload string ("QQ1AB2C"), not an image: it is what the
            # scanner reads, and rendering it as a barcode is the client's job.
            "qr": str(f.get("qr") or ""),
            "barcode_type": str(f.get("barcodeType") or ""),
            "pdf_url": str(f.get("pdfUrl") or ""),
            "ticket_url": str(f.get("ticketUrl") or ""),
        }


    def afisha_places(self, kind: str = "movie", city: str = "",
                      city_id: int | str = 0, query: str = "",
                      max_pages: int = 4) -> tuple[list[dict], int]:
        """Venues of one vertical in one city, as (matches, total).

        There is no server-side search here — no captured request carries a name
        parameter of any kind — so `query` is matched locally, which means every
        page has to be read before filtering, exactly as with the film listing.

        A 204 from this endpoint means the vertical is not serving, NOT that the
        city has no venues: live, cinema answers while concert, theatre and
        exhibition all return 204. The distinction matters — «нет площадок» and
        «раздел не отвечает» are different answers to the user.

        Pages after the first are fetched concurrently, same as cinema_movies()/
        afisha_catalog() and for the same reason: page 1 states the true total, so
        the page count is known after one request and the rest cost one round trip."""
        cid = city_id_of(city, city_id)
        service = vertical(kind)["service"]

        def fetch(page: int) -> tuple[list, int]:
            data = self._call_read("events_places", overrides={
                "service": service, "cityId": cid, "page": str(page),
                "count": str(self.PLACES_PAGE)})
            objs = [o for o in ((data or {}).get("objects") or [])
                    if isinstance(o, dict)]
            return objs, int(((data or {}).get("pagination") or {}).get("totalItems") or 0)

        out, total = fetch(1)
        pages = min(max(1, max_pages), -(-total // self.PLACES_PAGE) if total else 1)
        if pages > 1 and len(out) < total:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=min(4, pages - 1)) as pool:
                for objs, _ in pool.map(fetch, range(2, pages + 1)):
                    out.extend(objs)
        q = _norm_city(query) if query else ""
        if q:
            out = [o for o in out if q in _norm_city(o.get("name") or "")]
        return out, total


    def place_schedule(self, object_id: str, page: int = 1,
                       count: int = 50) -> tuple[list[dict], int]:
        """What is on at one venue, as (events, total).

        Concerts, theatre and exhibitions only — a cinema's repertoire lives in
        cinema_schedule(object_id=…, date=…) instead."""
        data = self._call_read("place_schedule", overrides={
            "objectId": str(object_id), "page": str(page), "count": str(count)})
        payload = data or {}
        lst = payload.get("list") or payload.get("events") or []
        return ([e for e in lst if isinstance(e, dict)],
                int(payload.get("amount") or 0))


    def place_info(self, object_id: str, with_halls: bool = False) -> dict:
        """Venue card. `geo.address` came back empty in every captured call, so
        with_halls stitches in the halls answer, which does carry addresses."""
        data = self._call_read("place_info", overrides={"objectId": str(object_id)})
        out = data if isinstance(data, dict) else {}
        if with_halls:
            try:
                halls = self._call_read("place_halls",
                                        overrides={"objectId": str(object_id)})
                out = dict(out)
                out["halls"] = (halls or {}).get("list") or (halls or {}).get("halls") or []
            except TbankApiError:
                pass
        return out


    def event_seats(self, event_id: str, slot_id: str, object_id: str,
                    kind: str = "movie", sector_id: str = "") -> list[dict]:
        """Hall layout for one showing: every seat with status and price.

        Cinemas key seats as "row:number". The other three verticals use a
        composite string ("Фанзона|5000§~§54093386|default") that must be passed
        back to order/create verbatim — it encodes sector, price and ticket id.

        sector_id narrows the answer to one sector; the app sends it when the
        buyer has already picked one off the hall map."""
        key = vertical(kind)["sectors_key"]
        params = {"eventId": str(event_id), "slotId": str(slot_id),
                  "objectId": str(object_id)}
        if sector_id:
            params["sectorId"] = str(sector_id)
        data = self._call_read(key, overrides=params)
        lst = (data or {}).get("list") if isinstance(data, dict) else data
        return lst if isinstance(lst, list) else []


    def concert_hall(self, event_id: str, slot_id: str, object_id: str,
                     kind: str = "concert") -> dict:
        """Free-seating venues answer here instead of /sectors: sectors with
        `freeSeating: true` and a ticket count rather than a seat grid.

        Only concerts and theatre have this screen — the captures hold no
        /api/scheme/hall/exhibition at all, and cinemas number their seats.

        READ ONLY on purpose — the capture has no order/create example for this
        purchase screen, so the request body for it is unknown and this client
        will not invent one."""
        key = vertical(kind)["hall_key"]
        if not key:
            raise TbankApiError(
                "NO_FREE_SEATING",
                f"{kind}: у этой вертикали нет схемы со свободной рассадкой — "
                "места смотри в event_seats()")
        data = self._call_read(key, overrides={
            "eventId": str(event_id), "slotId": str(slot_id),
            "objectId": str(object_id)})
        return data if isinstance(data, dict) else {}


    def event_showings(self, event_id: str, kind: str = "concert",
                       object_id: str = "") -> list[dict]:
        """Showings of one concert, play or exhibition.

        Unlike movies these carry no date in the request and the answer covers
        everything scheduled ahead, so filtering by day is the caller's job.
        object_id narrows it to a single venue."""
        body: dict = {"eventId": str(event_id)}
        if object_id:
            body["objectId"] = str(object_id)
        data = self._call_read(vertical(kind)["schedule_key"], body=body)
        lst = (data or {}).get("list") if isinstance(data, dict) else data
        return lst if isinstance(lst, list) else []


    def create_ticket_order(self, event_id: str, slot_id: str, object_id: str,
                            seats: list[dict], kind: str = "movie") -> dict:
        """Reserve seats. Creates an order and moves NO money — payment is a
        separate call. An order left unpaid expires by itself.

        seats: [{"id": "7:10", "type": "basic"}] for cinemas; concerts take the
        composite seatId and no type."""
        key = vertical(kind)["create_key"]
        body = {"eventId": str(event_id), "slotId": str(slot_id),
                "objectId": str(object_id), "seats": seats}
        data = self._call_read(key, body=body)
        return data if isinstance(data, dict) else {}


    def pay_marketplace_order(self, order_id: str, amount: float,
                              account: str, nfs_payment_token: str) -> dict:
        """MONEY OPERATION. Pay for a marketplace order (cinema/concert ticket).

        Cookie/Bearer only — no HMAC signature, unlike /v1/pay. `nfs_payment_token`
        and the amount both come from the create_ticket_order response; passing an
        amount that disagrees with the order is how you get a stuck payment."""
        body = {
            "amount": {"amount": amount, "type": "simple", "currencyCode": "643"},
            "paymentMethod": {"type": "agreement", "agreement": str(account)},
            "flow": {"orderId": str(order_id), "type": "marketplace",
                     "nfsPaymentToken": str(nfs_payment_token)},
        }
        data = self._call_read("payment_gate_pay_mobile", body=body)
        return data if isinstance(data, dict) else {}


    def cancel_ticket_order(self, order_id: str, kind: str = "movie",
                            payment_id: str = "") -> Any:
        """Cancel a ticket order. `orderId` rides in the query, `paymentId` next to
        it when the order has one, and the body stays empty.

        What decides the outcome is the order's own `isCancelAvailable`. The single
        captured success (delete-order.xml) cancelled a PAID order the bank had
        flagged cancelable: 200 {"status":"Success"}, and it moved to
        PARTIALLY_CANCELED — tickets refunded, service fee not. Seven live attempts
        on orders flagged `isCancelAvailable: false` answered 200 with a business
        refusal ({"status":"Failed","code":…}) and changed nothing; sending the same
        request as form-urlencoded made no difference.

        Read the verdict from the payload, not from the transport: this returns
        normally for a business refusal (the outer envelope is "Ok") and only raises
        when the request itself failed.

        payment_id is looked up from the order when the caller hasn't got it. An
        unpaid reservation has none, and does not need cancelling — it expires."""
        if not payment_id:
            payment_id = self.payment_id_for_order(order_id)
        key = vertical(kind)["cancel_key"]
        params = {"orderId": str(order_id)}
        if payment_id:
            params["paymentId"] = str(payment_id)
        # body=None, not {}: `json={}` puts a literal two-byte body on the wire and
        # both captured cancels send Content-Length: 0. The grocery flavour already
        # gets this right (grocery_order_cancel) — this one never got the same fix.
        return self._call_read(key, overrides=params)
