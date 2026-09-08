"""Hotel search and booking-read methods."""
from __future__ import annotations

from typing import Any

from . import client_common as _client_common

globals().update({
    name: getattr(_client_common, name)
    for name in dir(_client_common)
    if not name.startswith("__")
})

class HotelMixin:
    """Hotel search and booking-read methods."""

    def _hotels_sso_cookie(self) -> str:
        """Narrow web session used only by authenticated Hotels endpoints.

        ``ssoId`` identifies the user but is not, on its own, proof of an
        authenticated web session. Prefer the distinct cookies actually issued
        by Hotels; the mobile token aliases remain a compatibility fallback.
        """
        self.ensure_fresh()
        if not self.sso_id:
            self.session_status()
        names = (
            "__P__wuid", "api_sso_id", "sso_used", "ssoId", "sso_user_id",
            "sso_api_session", "sessionID", "SSO_ID_TOKEN", "SSO_VALIDATION",
            "_T_travel_session_id",
        )
        values = {}
        actual = selected_cookies(self.hotels_cookie, names)
        for part in actual.split(";"):
            if "=" in part:
                key, value = part.strip().split("=", 1)
                if key in names and value:
                    values[key] = value

        fallback = {
            "ssoId": self.sso_id,
            "sso_user_id": self.sso_id,
            "sso_api_session": self.access_token,
            "sessionID": self.access_token,
        }
        wide = selected_cookies(self._wide_cookie(), names)
        for part in wide.split(";"):
            if "=" in part:
                key, value = part.strip().split("=", 1)
                if key in names and value:
                    values.setdefault(key, value)
        for key, value in fallback.items():
            if value:
                values.setdefault(key, value)
        return "; ".join(
            f"{name}={values[name]}" for name in names if values.get(name))

    def _remember_hotels_sso_cookies(self, http) -> None:
        """Persist only the allowlisted cookies issued by the Hotels web flow."""
        names = (
            "__P__wuid", "api_sso_id", "sso_used", "ssoId", "sso_user_id",
            "sso_api_session", "sessionID", "SSO_ID_TOKEN", "SSO_VALIDATION",
            "_T_travel_session_id",
        )
        jar = getattr(http, "cookies", None)
        values = {}
        for part in selected_cookies(self.hotels_cookie, names).split(";"):
            if "=" in part:
                key, value = part.strip().split("=", 1)
                if key in names and value:
                    values[key] = value
        if jar is not None:
            values.update({key: value for key, value in jar.get_dict().items()
                           if key in names and value})
        learned = "; ".join(
            f"{name}={values[name]}" for name in names if values.get(name))
        if learned and learned != self.hotels_cookie:
            self.hotels_cookie = learned
            self.hotels_cookie_at = time.time()
            self._persist()

    def hotel_booking(self, booking_id: str) -> dict:
        """Full detail for a hotel booking: dates, hotel, room, guests, meals.

        Unlike the flight and rail hosts, this one accepts the plain mobile Bearer
        — no per-service link token — so it works straight from a mobile session."""
        data = self._call_read(
            "hotel_booking",
            path_override=f"/api/v1/hotels/bookings/{booking_id}")
        return data if isinstance(data, dict) else {}


    def hotel_autocomplete(self, query: str) -> dict:
        """Locations and hotels matching a name on the public hotel facade."""
        data = self._call_read("hotel_autocomplete", body={"input": query})
        return data if isinstance(data, dict) else {}


    def hotel_search(self, destination_id: int, checkin_date: str,
                     checkout_date: str, *, adults: int = 1,
                     children_ages: list[int] | None = None,
                     limit: int = 50) -> dict:
        """Current public v2 hotel availability plus static hotel cards.

        The former ``/api/v1/hotels/search`` route can wait indefinitely. The
        production web app now starts a search through ``searchHotelPoints`` and
        loads list pages through ``listParameters.offset`` in the same 50-item
        steps as the production web app. This method waits until
        ``isLoadingCompleted`` (or ``HOTEL_SEARCH_WAIT_S``), then returns at most
        ``HOTEL_SEARCH_RETURN_CAP`` ranked cards. Offers whose search price is
        not final are refreshed through ``getLatestHotelOffer`` before they are
        joined with ``getHotelStaticInfo``. All calls go through
        www.tbank.ru/api/hotels without bank tokens or session cookies. If the
        SSO login supplied ssoId, that single cookie is forwarded so the Hotels
        API can personalize the response.
        """
        return_limit = self.HOTEL_SEARCH_RETURN_CAP if int(limit) <= 0 else min(
            int(limit), self.HOTEL_SEARCH_RETURN_CAP)
        search_tag = f"mcp-{time.time_ns()}"
        base_body = {
            "searchTag": search_tag,
            "locationId": int(destination_id),
            "checkinDate": checkin_date,
            "checkoutDate": checkout_date,
            "guests": {
                "adultsCount": adults,
                "childrenAge": list(children_ages or []),
            },
            "filters": [],
            # There is no map in the MCP response. pinLimit=0 makes list
            # pagination available even while suppliers are still streaming.
            "mapFrameInput": {"mapParameters": {"pinLimit": 0}},
        }
        sticky_headers = {
            "x-sticky-id": self._hotel_sticky_id(
                destination_id, checkin_date, checkout_date, adults, children_ages),
        }
        last_search: dict = {}
        total_count: int | None = None
        deadline = time.monotonic() + self.HOTEL_SEARCH_WAIT_S

        def fetch_page(offset: int) -> tuple[dict, list, list[dict]]:
            nonlocal last_search, total_count
            body = dict(base_body)
            body["listParameters"] = {"offset": int(offset)}
            search = self._call_read(
                "hotel_search_points", body=body, headers_override=sticky_headers)
            search = search if isinstance(search, dict) else {}
            last_search = search
            offer_rows = [row for row in (search.get("hotelDetails") or [])
                          if isinstance(row, dict)]
            hotel_list = search.get("hotelList") or {}
            if isinstance(hotel_list.get("filteredHotelsCount"), int):
                reported_total = hotel_list["filteredHotelsCount"]
                total_count = max(total_count or 0, reported_total)
            page_ids = [row.get("hotelId") for row in (hotel_list.get("hotels") or [])
                        if isinstance(row, dict) and row.get("hotelId") is not None]
            if not page_ids:
                page_ids = [row.get("hotelId") for row in offer_rows
                            if row.get("hotelId") is not None]
            return search, page_ids, offer_rows

        # Wait for suppliers to finish before paging. Paginating an incomplete
        # first slice used to return a partial ranking as if it were the list.
        while True:
            search, _, _ = fetch_page(0)
            if search.get("isLoadingCompleted") is True:
                break
            if time.monotonic() >= deadline:
                break
            time.sleep(self.HOTEL_SEARCH_POLL_S)

        offer_rows_by_id: dict[str, dict] = {}
        hotel_order: list[int] = []
        seen_hotel_ids: set[str] = set()
        offset = 0
        page_step = self.HOTEL_LIST_PAGE
        while True:
            _, page_ids, offer_rows = fetch_page(offset)
            for row in offer_rows:
                hotel_id = row.get("hotelId")
                if hotel_id is not None:
                    offer_rows_by_id[str(hotel_id)] = row
            for hotel_id in page_ids:
                key = str(hotel_id)
                if key not in seen_hotel_ids:
                    seen_hotel_ids.add(key)
                    hotel_order.append(hotel_id)
            if len(hotel_order) >= return_limit:
                hotel_order = hotel_order[:return_limit]
                break
            offset += page_step
            if total_count is not None and offset >= total_count:
                break
            if not page_ids:
                break

        if not hotel_order:
            return {
                "hotels": [],
                "filteredHotelsCount": total_count or 0,
                "isLoadingCompleted": last_search.get("isLoadingCompleted") is True,
                "pricesFinal": True,
            }

        def offer_is_final(hotel_id) -> bool:
            offer = (offer_rows_by_id.get(str(hotel_id)) or {}).get("offerDetails") or {}
            price = offer.get("price") or {}
            is_final = price.get("isFinalPrice")
            if is_final is None:
                is_final = offer.get("isFinalPrice")
            return is_final is True

        def refresh_non_final() -> None:
            pending = [int(hotel_id) for hotel_id in hotel_order
                       if not offer_is_final(hotel_id)]
            for start in range(0, len(pending), 1000):
                latest = self.hotel_latest_offers(
                    pending[start:start + 1000], checkin_date, checkout_date,
                    location_id=destination_id, adults=adults,
                    children_ages=children_ages)
                for row in (latest.get("hotels") or []):
                    if isinstance(row, dict) and row.get("hotelId") is not None:
                        offer_rows_by_id[str(row["hotelId"])] = row

        refresh_non_final()
        if any(not offer_is_final(hotel_id) for hotel_id in hotel_order):
            time.sleep(self.HOTEL_SEARCH_POLL_S)
            refresh_non_final()

        static_rows = []
        for start in range(0, len(hotel_order), page_step):
            static = self._call_read("hotel_static_info", body={
                "hotelIds": hotel_order[start:start + page_step],
                "searchTag": search_tag,
            })
            if isinstance(static, dict):
                static_rows.extend(row for row in (static.get("hotels") or [])
                                   if isinstance(row, dict))
        static_by_id = {
            str(row.get("hotelId")): row
            for row in static_rows
            if isinstance(row, dict) and row.get("hotelId") is not None
        }
        offers_by_id = {
            str(row.get("hotelId")): row.get("offerDetails") or {}
            for row in offer_rows_by_id.values() if row.get("hotelId") is not None
        }
        hotels = []
        for hotel_id in hotel_order:
            card = dict(static_by_id.get(str(hotel_id)) or {})
            offer = offers_by_id.get(str(hotel_id)) or {}
            price = offer.get("price") or {}
            if not card or not price.get("amount"):
                continue
            location = card.get("location") or {}
            coordinates = location.get("hotelCoordinates") or {}
            card["hotelLocation"] = {
                "address": location.get("hotelAddress") or "",
                "latitude": coordinates.get("latitude"),
                "longitude": coordinates.get("longitude"),
            }
            is_final = (price.get("isFinalPrice") is True
                        or offer.get("isFinalPrice") is True)
            card["rateForHotelsFeed"] = {
                "shownPrice": {
                    "amount": price.get("amount"),
                    "currency": price.get("currency") or "RUB",
                },
                "isFinalPrice": is_final,
            }
            meal = offer.get("mealType")
            if isinstance(meal, dict):
                meal = meal.get("name")
            if meal:
                card["rateForHotelsFeed"]["mealName"] = meal
            if offer.get("availableRoomsCount") is not None:
                card["rateForHotelsFeed"]["availableRoomsCount"] = offer[
                    "availableRoomsCount"]
            hotels.append(card)
        prices_final = bool(hotels) and all(
            (row.get("rateForHotelsFeed") or {}).get("isFinalPrice") is True
            for row in hotels)
        loading_completed = last_search.get("isLoadingCompleted") is True
        return {
            "hotels": hotels,
            "filteredHotelsCount": (total_count if total_count is not None else len(hotels)),
            "isLoadingCompleted": loading_completed,
            "pricesFinal": prices_final,
            "searchId": last_search.get("searchId"),
            "upstreamLoadingCompleted": loading_completed,
        }


    def _hotel_sticky_id(self, location_id: int | None, checkin_date: str,
                         checkout_date: str, adults: int,
                         children_ages: list[int] | None) -> str:
        """Build the optional Hotels Search API affinity key from request data."""
        parts = [
            f"cin={str(checkin_date).replace('-', '')}",
            f"cout={str(checkout_date).replace('-', '')}",
        ]
        if location_id is not None:
            parts.append(f"did={int(location_id)}")
        parts.append(f"adults={int(adults)}")
        ages = list(children_ages or [])
        if ages:
            parts.append("cages=" + ",".join(str(age) for age in ages))
        return "&".join(parts)


    def hotel_search_filters(self, location_id: int, checkin_date: str,
                             checkout_date: str, *, adults: int = 1,
                             children_ages: list[int] | None = None,
                             filters: list[dict] | None = None,
                             map_frame_input: dict | None = None,
                             favorite_hotel_ids: list[int] | None = None,
                             language: str = "RU") -> dict:
        """Availability-aware filters for one hotel search (searchFilters_v3)."""
        body = {
            "locationId": int(location_id),
            "checkinDate": checkin_date,
            "checkoutDate": checkout_date,
            "guests": {
                "adultsCount": int(adults),
                "childrenAge": list(children_ages or []),
            },
        }
        if filters:
            body["filters"] = list(filters)
        if map_frame_input:
            body["mapFrameInput"] = dict(map_frame_input)
        if favorite_hotel_ids:
            body["favoriteHotelIds"] = list(favorite_hotel_ids)
        data = self._call_read(
            "hotel_search_filters", body=body,
            headers_override={
                "x-sticky-id": self._hotel_sticky_id(
                    location_id, checkin_date, checkout_date, adults, children_ages),
                "X-User-Language": language,
            })
        return data if isinstance(data, dict) else {}


    def hotel_latest_offers(self, hotel_ids: list[int], checkin_date: str,
                            checkout_date: str, *, location_id: int | None = None,
                            adults: int = 1,
                            children_ages: list[int] | None = None,
                            filters: list[dict] | None = None) -> dict:
        """Refresh prices and conditions for selected hotels."""
        body = {
            "checkinDate": checkin_date,
            "checkoutDate": checkout_date,
            "hotelIds": list(hotel_ids),
            "guests": {
                "adultsCount": int(adults),
                "childrenAge": list(children_ages or []),
            },
        }
        if location_id is not None:
            body["locationId"] = int(location_id)
        if filters:
            body["filters"] = list(filters)
        data = self._call_read(
            "hotel_latest_offers", body=body,
            headers_override={
                "x-sticky-id": self._hotel_sticky_id(
                    location_id, checkin_date, checkout_date, adults, children_ages),
            })
        return data if isinstance(data, dict) else {}


    def hotel_details(self, hotel_id: str) -> dict:
        """Static hotel card from the current public hotel facade."""
        data = self._call_read("hotel_static_info", body={
            "hotelIds": [int(hotel_id)],
            "searchTag": f"mcp-details-{time.time_ns()}",
        })
        rows = (data or {}).get("hotels") if isinstance(data, dict) else []
        if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
            return {}
        card = dict(rows[0])
        location = card.get("location") or {}
        coordinates = location.get("hotelCoordinates") or {}
        card["hotelLocation"] = {
            "address": location.get("hotelAddress") or "",
            "latitude": coordinates.get("latitude"),
            "longitude": coordinates.get("longitude"),
        }
        return card


    def hotel_filters(self) -> dict:
        """Current search-filter catalogue from the public hotel facade."""
        data = self._call_read("hotel_filters")
        return data if isinstance(data, dict) else {}


    def hotel_rates(self, hotel_id: str, checkin_date: str, checkout_date: str,
                    *, adults: int = 1, children_ages: list[int] | None = None,
                    filters: list[dict] | None = None) -> dict:
        """Available v3 rooms and rates for one hotel and one room.

        This is an availability lookup, despite being an HTTP POST: it creates no
        booking and moves no money. Like the other public hotel calls, it uses an
        isolated cookie jar and sends no bank session or Bearer; only an available
        ssoId cookie is forwarded.
        """
        data = self._call_read(
            "hotel_rates",
            path_override=f"/api/hotels/api/v3/hotels/{hotel_id}/rates",
            body={
                "checkInDate": checkin_date,
                "checkOutDate": checkout_date,
                "guests": [{
                    "adultsCount": int(adults),
                    "childrenAge": list(children_ages or []),
                }],
                "filters": list(filters or []),
            },
        )
        return data if isinstance(data, dict) else {}


    def hotel_reviews(self, hotel_id: str, *, source_code: str = "",
                      sort: str = "date", sort_type: str = "desc",
                      cursor: str = "", page_size: int = 10,
                      search_text: str = "") -> dict:
        """One page of public guest reviews for a hotel (current v2 contract)."""
        query = {
            "Sort": sort,
            "SortType": sort_type,
            "Cursor": cursor,
            "PageSize": str(page_size),
        }
        if source_code:
            query["SourceCode"] = source_code
        if search_text:
            query["SearchText"] = search_text
        data = self._call_read(
            "hotel_reviews", overrides=query,
            path_override=f"/api/hotels/api/v2/review/{hotel_id}/feedback")
        return data if isinstance(data, dict) else {}
