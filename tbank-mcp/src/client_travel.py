"""Flights, trains, geodata and marketplace search."""
from __future__ import annotations

from typing import Any

from . import client_common as _client_common

globals().update({
    name: getattr(_client_common, name)
    for name in dir(_client_common)
    if not name.startswith("__")
})

class TravelMixin:
    """Flights, trains, geodata and marketplace search."""

    def train_search(self, origin: str, destination: str, date: str,
                     adults: int = 1, children: int = 0) -> tuple[list[dict], str]:
        """Trains for one direction on one date, as (ways, trainSearchId).

        origin/destination are the bank's NUMERIC station codes (2000000 is
        Moscow). Nothing in the captures turns a city name into one, so the code
        is the caller's to supply — guessing it would send someone to the wrong
        city with a plausible-looking answer."""
        body = {"directions": [{"origin": str(origin),
                                "destination": str(destination),
                                "departureDate": date}],
                "adultsCount": adults, "childrenCount": children}
        data = self._call_read("train_search", body=body) or {}
        dirs = data.get("directions") or []
        ways = (dirs[0] or {}).get("ways") if dirs else []
        return ([w for w in (ways or []) if isinstance(w, dict)],
                str(data.get("trainSearchId") or ""))


    def train_calendar(self, origin: str, destination: str) -> list[dict]:
        """Which dates are on sale for a direction — a cheap way to check a pair
        of station codes is valid before searching a date that has no trains."""
        data = self._call_read("train_calendar", overrides={
            "origin": str(origin), "destination": str(destination)}) or {}
        return [d for d in (data.get("dates") or []) if isinstance(d, dict)]


    def flight_history(self) -> list[dict]:
        """Past flight searches. Also the only place an airport code comes back
        WITH its name — nothing in the captures resolves a name to an IATA code,
        so this is where an agent can learn that Москва is MOW."""
        data = self._call_read("flight_history")
        return [h for h in (data or []) if isinstance(h, dict)]


    def flight_search(self, from_code: str, to_code: str, date: str,
                      adults: int = 1, children: int = 0, infants: int = 0,
                      cabin: str = "Y", only_bookable: bool = False,
                      deadline_s: float = 45.0) -> dict:
        """Flights, as {searchId, flights, offers, complete, info}.

        ONE ndjson connection (Zubat's `/flight/search/stream`), PUBLIC —
        verified live against prod with no Bearer/Cookie/sessionid at all
        (its `@useAuth` in the spec is merely PublicAuthOptions, optional,
        and no observed field differed between an authenticated and an
        anonymous call).

        The server writes a `Direct` frame (Tinkoff's own inventory) and zero
        or more `Tpo` frames (Travelpayouts partners) as they complete, then
        `Finished`. Measured live: `Direct` is NOT reliably first — one
        request came back Tpo, Tpo, Direct, Tpo, Finished. only_bookable does
        not chase frame order for that reason; it sets `aviasales: false` on
        the request itself, which measured live returns ONLY `Direct` +
        `Finished` (~7s, no partner search even started server-side) — so the
        read is naturally short without ever truncating it client-side. Every
        call runs to `Finished`; `complete` is always true on a normal return.
        `deadline_s` is the one remaining safety bound, against a connection
        that never sends `Finished` at all.

        offers[].flights index the CONCATENATION of every frame's flights, not
        the one frame they arrived in, so nothing can be resolved until the
        stream is stitched — which is why a `deadline_s` timeout (the one way
        this can still return early) is reported via `complete`, not
        silently."""
        return self.flight_search_multi(
            segments=[{"from": from_code.upper(), "to": to_code.upper(), "date": date}],
            adults=adults, children=children, infants=infants,
            cabin=cabin, only_bookable=only_bookable, deadline_s=deadline_s)

    def flight_search_multi(self, segments: list, *, adults: int = 1,
                            children: int = 0, infants: int = 0,
                            cabin: str = "Y", only_bookable: bool = False,
                            deadline_s: float = 45.0) -> dict:
        """Search several segments (one-way or round trip) on Zubat stream.

        Public like flight_search. segments: [{from,to,date}, ...]; a round
        trip = outbound + return legs in one request, and each returned offer
        may cover BOTH legs with a single offerId and a total price.
        """
        body = {"segments": list(segments),
                "passengers": {"adults": adults, "children": children,
                               "infants": infants},
                "cabin": cabin, "composite": 0, "groupsLimit": 4000,
                "aviasales": not only_bookable}
        search_id, flights, offers, info = "", [], [], {}
        complete = False
        started = time.monotonic()
        stream = self._call_stream("flight_search_stream", body=body)
        try:
            for frame in stream:
                ftype = frame.get("type")
                if ftype == "Finished":
                    complete = True
                    break
                if ftype not in ("Direct", "Tpo"):
                    continue
                batch = frame.get("batch") or {}
                search_id = search_id or str(batch.get("searchId") or "")
                flights.extend(batch.get("flights") or [])
                offers.extend(batch.get("offers") or [])
                for key, value in (batch.get("info") or {}).items():
                    if isinstance(value, dict):
                        info.setdefault(key, {}).update(value)
                if batch.get("isOver"):
                    complete = True
                if complete:
                    break
                if time.monotonic() - started > deadline_s:
                    break
        finally:
            stream.close()
        return {"searchId": search_id, "flights": flights, "offers": offers,
                "complete": complete, "info": info}

    def flight_price_calendar(self, from_codes: str | list[str],
                              to_codes: str | list[str], *,
                              from_kind: str = "city", to_kind: str = "city",
                              adults: int = 1, children: int = 0, infants: int = 0,
                              direct: bool | None = None,
                              returning: bool | None = None,
                              baggage: bool | None = None,
                              return_from: str | None = None,
                              return_to: str | None = None,
                              total_days_from: int | None = None,
                              total_days_to: int | None = None) -> list[dict]:
        """Cheapest prices per departure date (Zubat cache, read-only).

        One or more from_codes/to_codes as a group; departure window in
        departure_from/departure_to; an optional return window in
        return_from/return_to. Empty means "not in the cache", not "no
        flights"."""

        # The spec's plurals are not a bare `+ "s"` — "city" -> "cities", not
        # "citys" — so the group variant is looked up, not derived.
        _plural = {"airport": "airports", "city": "cities", "country": "countries"}

        def point(codes: str | list[str], kind: str) -> dict:
            values = [codes] if isinstance(codes, str) else list(codes)
            values = [str(c).upper() for c in values if c]
            if not values:
                raise ValueError("flight_price_calendar: at least one IATA code is required")
            if len(values) == 1:
                return {"type": kind, "code": values[0]}
            plural = _plural.get(kind)
            if not plural:
                raise ValueError(f"flight_price_calendar: unknown point kind {kind!r}")
            return {"type": plural, "codes": values}

        body: dict[str, Any] = {
            "from": point(from_codes, from_kind),
            "to": point(to_codes, to_kind),
            "adults": max(1, adults),
        }
        if children:
            body["children"] = children
        if infants:
            body["infants"] = infants
        if baggage is not None:
            body["baggage"] = baggage
        if direct is not None:
            body["direct"] = direct
        if returning is not None:
            body["returning"] = returning
        # Verified live: the KEY has to be present even with nothing in it — a
        # body with no `departureDate` at all 400s ("Bad Request", no JSON
        # body), but `"departureDate": {}` (or with only one side filled) is
        # accepted. So this is unconditional, not `if departure_from or
        # departure_to:` as the request shape alone would suggest.
        body["departureDate"] = {k: v for k, v in
                                 (("from", departure_from), ("to", departure_to)) if v}
        if return_from or return_to:
            body["returnDate"] = {k: v for k, v in
                                  (("from", return_from), ("to", return_to)) if v}
        if total_days_from is not None and total_days_to is not None:
            body["totalDays"] = {"from": total_days_from, "to": total_days_to}
        data = self._call_read("flight_price_calendar", body=body) or {}
        return [p for p in (data.get("prices") or []) if isinstance(p, dict)]


    def flight_price_forecast(self, search_id: str) -> bool:
        """Will the cheapest price on a search rise before departure — Zubat's
        `GET /flight/search/priceForecast`. Takes the `searchId` flight_search()
        already returns; it does not start a new search."""
        data = self._call_read("flight_price_forecast",
                               overrides={"searchId": search_id}) or {}
        return bool(data.get("willPriceIncrease"))


    def flight_schedule(self, from_code: str, to_code: str,
                        date: str | None = None) -> list[dict]:
        """Scheduled flights on a route — Zubat's `POST /flight/schedule/
        getSchedule`. Verified live against prod, no session required
        (`@useAuth(NoAuth)` in the spec).

        This is a timetable, not a fare search: `minPrice` on each entry is
        only meaningful when `date` is given (a specific day), and `dates`
        lists every day in the schedule's window the flight actually
        operates — without `date` there is no single fare to attach, so
        callers wanting a real price for one day should follow up with
        flight_search. Raises TbankApiError (e.g.
        `schedule.geodata_code_not_found`) for an unknown IATA code."""
        body: dict[str, Any] = {"from": from_code.upper(), "to": to_code.upper()}
        if date:
            body["date"] = date
        data = self._call_read("flight_schedule", body=body) or {}
        return [f for f in (data.get("flights") or []) if isinstance(f, dict)]


    def geodata_by_code(self, codes: str | list[str]) -> list[dict]:
        """Geo records (city or airport) for IATA codes — Zubat's `POST
        /geodata/geoDataByCode`. Verified live, no session required
        (`@useAuth(NoAuth)` in the spec).

        Each entry has code/city_code/country_code, three localized names
        (ru/en/synonyms; city_name also carries Russian case forms), lat/
        lon, IANA timezone and `type` ("city" or "airport"). The order of
        returned records matches the order of input codes; if a code maps
        to both a city and an airport the city wins. Unknown codes raise
        TbankApiError (`geodata.geodata_not_found`)."""
        values = [codes] if isinstance(codes, str) else list(codes)
        values = [str(c).strip().upper() for c in values if str(c).strip()]
        data = self._call_read("geodata_by_code", body=values)
        return [g for g in (data or []) if isinstance(g, dict)]


    def shop_geo(self) -> dict:
        """The delivery address, memoised. Search wants its lat/lon, and asking
        for it per search would double the cost of every query."""
        memo = getattr(self, "_memo", None)
        if memo is None:
            memo = self._memo = {}
        if "shop_geo" not in memo:
            memo["shop_geo"] = self._call_read("shop_address") or {}
        return memo["shop_geo"]


    def shop_search(self, query: str, offset: int = 0,
                    size: int = 20) -> tuple[list[dict], list[dict], int]:
        """Marketplace products, as (products, partners, total_hits).

        Paging is the server's here — offset/size are real — unlike the afisha
        listings where a name has to be matched locally.

        The seller lives in a separate `partners` list, keyed by the product's
        dolyameShopId; the product itself only carries the id."""
        geo = self.shop_geo()
        ov = {"search": query, "offset": str(max(0, offset)), "size": str(size)}
        if geo.get("latitude") and geo.get("longitude"):
            ov["latitude"] = str(geo["latitude"])
            ov["longitude"] = str(geo["longitude"])
        data = self._call_read("shop_search", overrides=ov) or {}
        return ([p for p in (data.get("products") or []) if isinstance(p, dict)],
                [p for p in (data.get("partners") or []) if isinstance(p, dict)],
                int(data.get("totalHits") or 0))


    def shop_carts(self) -> list[dict]:
        """Carts, one per seller. body=None: the captured call sends
        Content-Length: 0, and body={} would put a literal `{}` on the wire."""
        data = self._call_read("shop_carts") or {}
        return [c for c in (data.get("carts") or []) if isinstance(c, dict)]
