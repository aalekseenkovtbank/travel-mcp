"""Grocery catalog, cart and checkout client methods."""
from __future__ import annotations

from typing import Any

from . import client_common as _client_common

globals().update({
    name: getattr(_client_common, name)
    for name in dir(_client_common)
    if not name.startswith("__")
})

class GroceryMixin:
    """Grocery catalog, cart and checkout client methods."""

    def shopping_favorites(self) -> list[dict]:
        return self._as_list(self._call_read("shopping_favorites"))


    def shopping_cart(self) -> list[dict]:
        return self._as_list(self._call_read("shopping_cart"))


    def grocery_cart_get(self, app_id: str = "", point_id: str = "") -> dict:
        """Read the cart for a specific store. Only appId scopes the cart — the
        real app never sends pointId on this endpoint (pointId lives in the
        cart/set body under delivery). point_id is accepted for call-site symmetry."""
        ov = {"appId": app_id} if app_id else None
        return self._call_read("grocery_cart_get", overrides=ov)


    def grocery_cart_set(self, body: dict | None = None,
                         app_id: str = "", point_id: str = "") -> dict:
        """Set the grocery cart (POST). With body=None this CLEARS the store's cart
        (goods: []). The delivery block — address with full details, plus areaId for
        retailers that require it — is resolved by _grocery_delivery."""
        if body is None:
            body = {"goods": [], "cartSetMode": "SINGLE_CART",
                    "delivery": self._grocery_delivery(app_id, point_id)}
        return self._call_read("grocery_cart_set", body=body,
                               overrides={"appId": app_id} if app_id else None)


    def grocery_cart_check(self) -> dict:
        return self._call_read("grocery_cart_check")


    def grocery_order_get(self, order_id: str = "", app_id: str = "") -> dict:
        """Look up a grocery order by orderId (GET /api/grocery/order). For
        reconciliation after an UNKNOWN checkout (#10)."""
        ov = {k: v for k, v in (("orderId", order_id), ("appId", app_id)) if v}
        return self._call_read("grocery_order_get", overrides=ov or None)


    def grocery_order_create(self, body: dict | None = None) -> dict:
        """Create a grocery order (POST, replays the request body or override)."""
        return self._call_read("grocery_order_create", body=body)


    def grocery_deliveries(self, body: dict | None = None) -> list[dict]:
        return self._as_list(self._call_read("grocery_deliveries", body=body))


    def grocery_retailers(self) -> list[dict]:
        return self._as_list(self._call_read("grocery_retailers"))


    def grocery_catalog(self) -> list[dict]:
        return self._as_list(self._call_read("grocery_catalog"))


    def grocery_categories(self) -> list[dict]:
        return self._as_list(self._call_read("grocery_categories"))


    def grocery_unseen_orders(self) -> dict:
        return self._call_read("grocery_unseen_orders")


    def shopping_change_qty(self, body: dict | None = None) -> dict:
        """POST carts/change-items-quantity — add/remove/change qty of a cart
        item (the granular cart-fill op). Replays the request body or override."""
        return self._call_read("shopping_change_qty", body=body)


    def shopping_cart_detail(self, body: dict | None = None) -> dict:
        """POST carts/cart-detail-info — full cart detail (items, prices, delivery)."""
        return self._call_read("shopping_cart_detail", body=body)


    def store_products(self) -> list[dict]:
        """Browse/search store products (to find items to add to the cart)."""
        return self._as_list(self._call_read("store_products"))


    def store_product(self, product_id: str) -> dict:
        """Product details (PDP) by id — use before adding to cart."""
        return self._call_read("store_product",
            path_override=f"/mybank/api/shopping/mobile/v1/product/{product_id}")


    def store_categories(self) -> list[dict]:
        """Store categories (browse the catalog)."""
        return self._as_list(self._call_read("store_categories"))


    def sphere_categories(self) -> list[dict]:
        """Sphere (Город) categories."""
        return self._as_list(self._call_read("sphere_categories"))


    def grocery_goods(self, category_id: str = "",
                      app_id: str = "", point_id: str = "",
                      page: int = 1) -> list[dict]:
        """Grocery goods (Город catalog items). Pass category_id to browse a
        category, page for pagination."""
        return self._as_list(self._call_read("grocery_goods", overrides={
            "appId": app_id, "pointId": point_id, "categoryId": category_id,
            "page": str(page), "count": "50"}))


    def grocery_popular(self) -> list[dict]:
        """Popular grocery items."""
        return self._as_list(self._call_read("grocery_popular"))


    def grocery_stores(self) -> list[dict]:
        """List available grocery stores for the delivery address."""
        base = {"Accept": "application/json", "User-Agent": "okhttp/4.12.0",
                "Authorization": "Bearer " + self.access_token}
        if self._wide_cookie():
            base["Cookie"] = self._wide_cookie()
        # The delivery address, through the shared accessor rather than a second
        # hand-rolled request to the same URL: a cold-start add_to_cart resolves the
        # address here AND in _grocery_delivery, which was two identical calls.
        addrs = ((self.grocery_client_info().get("deliveryInfo") or {})
                 .get("addresses") or [])
        if not addrs:
            raise TbankApiError("NO_DELIVERY_ADDRESS",
                "У аккаунта нет сохранённого адреса доставки. Добавь адрес в приложении "
                "Т-Банка (Город), затем вызови grocery_stores() снова.")
        addr = addrs[0].get("value", "")
        coords = addrs[0].get("coordinates") or {}
        if not coords.get("latitude") or not coords.get("longitude"):
            raise TbankApiError("NO_DELIVERY_ADDRESS",
                "Сохранённый адрес без координат — обнови адрес в приложении Т-Банка (Город).")
        lat = str(coords.get("latitude"))
        lon = str(coords.get("longitude"))
        # retailers needs ALL these params (from capture)
        params = {"appName": self.app_name, "appVersion": self.app_version,
                  "platform": self.platform, "origin": self.origin,
                  "deviceId": self.device_id, "oldDeviceId": self.old_device_id,
                  "sessionid": self.mobile_sessionid, "ccc": self.ccc,
                  "cpswc": self.cpswc, "connectionType": self.connection_type,
                  "inache": self.inache, "includeMultipleRetailers": "true",
                  "includeClosedRetailers": "false", "address": addr,
                  "latitude": lat, "longitude": lon,
                  "tabsBlockType": "RECOMMENDATION", "v": "2"}
        r = self._http.get("https://lifestyle.t-bank-app.ru/api/grocery/retailers",
                          params=params, headers=base, timeout=30)
        payload = self._unwrap(r)
        stores = []
        categories = payload.get("categories", []) if isinstance(payload, dict) else []
        for cat in categories:
            for ret in cat.get("retailers", []):
                app_id = str(ret.get("appId", ""))
                name = (ret.get("info", {}) or {}).get("name", "")
                point_id = str((ret.get("delivery", {}) or {}).get("pointId", ""))
                min_sum = (ret.get("delivery", {}) or {}).get("minOrderSum", 0)
                nearest = (ret.get("delivery", {}) or {}).get("nearestTime", {})
                cashback = (ret.get("info", {}) or {}).get("cashback", {})
                # areaId identifies the retailer's delivery zone for this address.
                # Retailers that have one (ВкусВилл, Лента) REQUIRE it in the
                # cart/set body — omitting it makes the backend reject the cart.
                # This is the only endpoint that ever returns it.
                area_id = str((ret.get("delivery", {}) or {}).get("areaId", "") or "")
                eta, window = delivery_eta(nearest)
                if app_id and name:
                    # address/addressCount: the store list is built for ONE
                    # profile address (the first), and the answer never said
                    # which — with several saved addresses the agent could not
                    # tell what «доставка за 30 мин» was relative to.
                    stores.append({"appId": app_id, "name": name, "areaId": area_id,
                                   "pointId": point_id, "minOrderSum": min_sum,
                                   "etaMin": eta, "deliveryWindow": window,
                                   "deliveryPrice": nearest.get("price", 0),
                                   "cashback": cashback.get("value", ""),
                                   "category": cat.get("name", ""),
                                   "address": addr, "addressCount": len(addrs)})
        # dedupe by (appId, pointId) — the retailers list can repeat a store (#14)
        seen = set()
        uniq = []
        for st in stores:
            key = (st.get("appId"), st.get("pointId"))
            if key in seen:
                continue
            seen.add(key)
            uniq.append(st)
        # Seed _grocery_delivery's areaId memo from what we just fetched — a
        # grocery_stores() call immediately followed by add_to_cart for the same
        # store used to re-download this whole catalogue a second time just to
        # read the one field (areaId) this call already has in hand.
        memo = getattr(self, "_memo", None)
        if memo is not None:
            for st in uniq:
                memo[f"areaId:{st.get('appId')}:{st.get('pointId')}"] = st.get("areaId", "")
        return uniq


    def _resolve_custom_ordered_id(self, app_id: str, point_id: str) -> str:
        """Discover the per-store 'previously ordered' (Вы заказывали) category id.
        The id is store-suffixed (e.g. custom_ordered_<store>) and NOT
        constructible client-side — sibling custom ids carry random/date suffixes.
        The server lists it in GET /api/grocery/catalog?appId=&pointId= (the real
        app calls it with appId/pointId) under blocks[type=='Categories'].list,
        as the item whose id starts with 'custom_ordered' (label 'Вы заказывали').
        Returns '' when the store has no order history (block absent) → caller
        falls back to global search. Verified for appId=578; degrades safely
        for other stores."""
        data = self._call_read("grocery_catalog", overrides={"appId": app_id, "pointId": point_id})
        blocks = []
        if isinstance(data, dict):
            blocks = data.get("blocks") or []
            if not blocks and isinstance(data.get("payload"), dict):
                blocks = data["payload"].get("blocks") or []
        fallback = ""
        for block in blocks:
            items = block.get("list") if isinstance(block, dict) else None
            if not isinstance(items, list):
                continue
            for cat in items:
                if not isinstance(cat, dict):
                    continue
                cid = cat.get("id")
                if isinstance(cid, str) and cid.startswith("custom_ordered"):
                    # prefer the labeled 'Вы заказывали' match; else keep first custom_ordered
                    if "заказывал" in str(cat.get("name") or "").lower():
                        return cid
                    if not fallback:
                        fallback = cid
        return fallback


    def grocery_plan_order(self, ingredients: list[str], store_app_id: str = "",
                           store_point_id: str = "") -> dict:
        """Plan a grocery order. #12: custom_ordered is loaded ONCE per store and
        matched in memory (was re-read per ingredient → N+1, up to ~28 requests for 7
        ingredients). Ingredient queries are normalized (qty/units/stopwords stripped:
        'картофель 1 кг' → 'картофель'). Missing ingredients fall back to global search
        run in parallel (concurrency-capped).

        Returns {store, items, total_sum, missing, substitutions}."""
        import re as _re
        app_id, point_id = _need_store(store_app_id, store_point_id)
        plan = {"store": app_id, "items": [], "total_sum": 0,
                "missing": [], "substitutions": []}

        def norm(s: str) -> str:
            s = s.lower().strip().replace("ё", "е")
            # strip "1 кг", "2 шт", "100 г", "0.5 л" — quantities + common units
            s = _re.sub(r"\b\d+([.,]\d+)?\s*(кг|г|гр|грамм|л|мл|литр|шт|упак|пачк|банк|дол|зубч)?\b", " ", s)
            s = _re.sub(r"\b(сырой|сырая|сырого|свежий|свежая|очищен|вкусн)\S*", " ", s)
            return _re.sub(r"\s+", " ", s).strip()

        # 1. load custom_ordered ONCE (up to 3 pages), match all ingredients in memory
        _custom = None

        def custom_once():
            nonlocal _custom
            if _custom is not None:
                return _custom
            _custom = []
            # Discover the per-store 'previously ordered' category id dynamically
            # (no hardcoded store id — works for any store that has order history;
            # stores without it return '' and we fall through to global search).
            category_id = self._resolve_custom_ordered_id(app_id, point_id)
            if not category_id:
                return _custom
            for page in range(1, 4):
                items = self._as_list(self._call_read("grocery_goods", overrides={
                    "appId": app_id, "pointId": point_id,
                    "categoryId": category_id,
                    "page": str(page), "count": "50"}))
                if not items:
                    break
                _custom.extend(g for g in items if isinstance(g, dict))
            return _custom

        missing = []
        for ingredient in ingredients:
            q = norm(ingredient)
            found = None
            # collect every previously-ordered match, then score them the same way
            # as search hits — taking the first match picked whatever the history
            # happened to list first, tiny packs and dried forms included.
            cands = []
            for g in custom_once():
                gname = g.get("name", "")
                name = gname.lower().replace("ё", "е")
                m = self._name_matches(q, gname) if q else 0.0
                if m > 0:
                    price = g.get("price", {})
                    weight = g.get("weight", {})
                    cands.append({
                        "id": str(g.get("id", "")), "name": gname,
                        "price": price.get("value", 0) if isinstance(price, dict) else 0,
                        "weight": (f"{weight.get('value','')} {weight.get('unit','')}".strip()
                                   if isinstance(weight, dict) else ""),
                        "match": m,
                        "likely_raw": name.startswith(q)})
            best = self._pick_candidate(cands, q)
            if best:
                found = {**best, "source": "custom_ordered", "query": q}
            if found:
                plan["items"].append(found)
                plan["total_sum"] += found.get("price", 0) or 0
            else:
                missing.append((ingredient, q))

        # 2. global search for the rest — in parallel (concurrency-capped), #12
        if missing:
            queries = [q for _, q in missing if q]
            hits = self._parallel_search(queries, app_id, point_id)
            for ingredient, q in missing:
                g = hits.get(q)
                if g:
                    found = {"id": g.get("id", ""), "name": g.get("name", ""),
                             "price": g.get("price", 0), "source": "search", "query": q,
                             "weight": g.get("weight", ""),
                             "match": g.get("match", 0.0),
                             "likely_raw": g.get("likely_raw", False)}
                    plan["items"].append(found)
                    plan["total_sum"] += found.get("price", 0) or 0
                else:
                    plan["missing"].append(ingredient)
        return plan


    def _grams(item: dict) -> float:
        """Package weight in grams, 0 when unknown. weight is like '100 GRM'."""
        raw = (item.get("weight") or "").strip()
        if not raw:
            return 0.0
        parts = raw.split()
        try:
            val = float(parts[0])
        except (ValueError, IndexError):
            return 0.0
        unit = (parts[1] if len(parts) > 1 else "").upper()
        if unit in ("KGRM", "KG", "KGM", "LT", "L"):
            return val * 1000.0
        return val


    def _qualifier_stems(full_query: str, used_query: str) -> list[str]:
        """Stems of the words dropped when falling back to a looser query.

        Falling back from "яйца куриные" to "яйца" throws away the part that says
        WHICH eggs, and the loose query happily matches "Яйца перепелиные копченые".
        Keep the dropped words so scoring can still prefer a name that mentions them."""
        full = set((full_query or "").lower().replace("ё", "е").split())
        used = set((used_query or "").lower().replace("ё", "е").split())
        return [w[:5] for w in (full - used) if len(w) >= 4]


    def _norm_match(s: str) -> str:
        """Canonicalize a string for matching — deterministic hygiene, NO dictionaries.
        Lowercase + ё→е; strip the apostrophe family INCLUDING the backtick (that one
        char is what hid «Чипсы Lay`s» from a `lay's` query); hyphen/slash/punctuation
        → space so word boundaries are honoured. Cross-script and true synonyms are
        NOT handled here — that is the agent's job via the web."""
        s = (s or "").lower().replace("ё", "е")
        for ch in "`'’‘‛´":
            s = s.replace(ch, "")
        for ch in "-/.,:;()\"«»":
            s = s.replace(ch, " ")
        return " ".join(s.split())


    def _tokens(s: str) -> list[str]:
        return [t for t in MobileSession._norm_match(s).split()
                if t and t not in MobileSession._MATCH_STOPWORDS]


    def _tok_match(t: str, w: str) -> bool:
        """Does query token `t` match name word `w`? Short tokens (<6) must match in
        full — so «кола» hits «Кола» but not «колбаса»; long tokens accept a 5-char
        stem — so «сгущенка» hits «сгущённое» while «магнат» does NOT hit «магний»
        (they share only «магн», 4 < 5)."""
        n = 0
        for a, b in zip(t, w):
            if a != b:
                break
            n += 1
        m = min(len(t), len(w))
        need = 5 if m >= 6 else m
        return n >= need


    def _name_matches(query: str, name: str) -> float:
        """Fraction 0..1 of query tokens present in `name` (token-AND, order-free,
        stopword-free, stemmed via _tok_match). 1.0 = every query token found. 0 =
        no match (skip). A partial value (e.g. кетчуп «с помидорами» for «помидоры»
        would still be 1.0 here — the false-positive guard is _pick_candidate's
        scoring plus the confidence flag, not this recall metric)."""
        qt = MobileSession._tokens(query)
        if not qt:
            return 0.0
        nt = MobileSession._tokens(name)
        hit = sum(1 for t in qt if any(MobileSession._tok_match(t, w) for w in nt))
        return hit / len(qt)


    def _pick_candidate(self, results: list[dict], query: str,
                        qualifiers: list[str] | None = None) -> dict | None:
        """Choose the best search hit for an ingredient.

        The planner used to take results[0], and grocery_search sorts by
        (likely_raw, price) — so it always picked the CHEAPEST raw-looking hit.
        That is how "чеснок" became 10 g of dried ground garlic (52₽, beating fresh
        at 118₽) and "сметана" became a 30 g single-serving cup (55₽). Score instead:
        prefer a real, sanely-sized raw ingredient, and only then prefer cheap."""
        if not results:
            return None
        q = (query or "").lower().replace("ё", "е")
        want_spice = any(w in q for w in self._SPICE_QUERIES)

        def score(it: dict) -> tuple:
            name = (it.get("name") or "").lower().replace("ё", "е")
            grams = self._grams(it)
            # spices are legitimately dried and sold in 20 g jars — neither penalty
            # applies when the ingredient itself is a spice
            wrong_form = (not want_spice
                          and any(w in name for w in self._NOT_THE_FRESH_THING))
            too_small = (not want_spice) and 0.0 < grams < self._MIN_SANE_GRAMS
            price = it.get("price")
            price = price if isinstance(price, (int, float)) else 10 ** 6
            # a dropped qualifier ("куриные", "докторская") outranks everything:
            # the right product in the wrong size beats the wrong product
            missed_qualifier = bool(qualifiers) and not any(s in name for s in qualifiers)
            # token-recall FIRST among the soft signals: «lay's краб» must beat
            # «Lay`s Max Куриные» even though куриные is cheaper — a fuller match is a
            # more-right product. Without this the planner picked cheapest-of-anything.
            low_match = -round(it.get("match", 1.0), 3)
            # lower is better, field order = priority
            return (missed_qualifier, wrong_form, too_small, low_match,
                    not it.get("likely_raw", False), not name.startswith(q), price)

        return min(results, key=score)


    def _search_best(self, query: str, app_id: str, point_id: str) -> dict | None:
        """Search an ingredient, loosening the query until something sane matches.

        Accepts a loose-query hit only if it still honours the words that were
        dropped; otherwise it keeps looking and falls back to the best seen."""
        fallback = None
        for variant in self._query_variants(query):
            # limit=0: _pick_candidate must see every match, not the top ten.
            r, _, _ = self.grocery_search(variant, app_id=app_id,
                                          point_id=point_id, limit=0)
            quals = self._qualifier_stems(query, variant)
            best = self._pick_candidate(r, variant, qualifiers=quals)
            if not best:
                continue
            name = (best.get("name") or "").lower().replace("ё", "е")
            if not quals or any(s in name for s in quals):
                return best
            fallback = fallback or best
        return fallback


    def _query_variants(q: str) -> list[str]:
        """Progressively looser queries. The catalog search matches on a literal
        substring of the product name, so a multi-word or inflected request finds
        nothing: "колбаса докторская" misses "Колбаса вареная ... Докторская", and
        "яйца куриные" misses "Яйцо куриное". Fall back to the head noun, then to
        its stem so a plural still matches the singular."""
        out = [q]
        head = q.split()[0] if q.split() else q
        if head != q:
            out.append(head)
        # "яйца" -> "яйц" matches "Яйцо куриное"; keep >=3 chars so the stem stays
        # specific enough not to match arbitrary products
        if len(head) >= 4:
            out.append(head[:-1])
        if len(head) >= 6:
            out.append(head[:-2])
        seen, uniq = set(), []
        for v in out:
            if v and v not in seen:
                seen.add(v)
                uniq.append(v)
        return uniq


    def _parallel_search(self, queries: list[str], app_id: str, point_id: str,
                         max_workers: int = 4) -> dict:
        """Run global grocery searches in parallel (concurrency-capped). Returns
        {normalized_query: best_hit_dict}. #12"""
        from concurrent.futures import ThreadPoolExecutor
        out: dict[str, dict] = {}
        if not queries:
            return out

        def one(q):
            return q, self._search_best(q, app_id, point_id)

        workers = max(1, min(max_workers, len(queries)))
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for q, hit in ex.map(one, queries):
                if hit:
                    out[q] = hit
        return out


    def grocery_fetch_cap(limit: int) -> int:
        floor = MobileSession.GROCERY_SEARCH_FLOOR
        return max(floor, limit) if limit else MobileSession.GROCERY_PROBE_FETCH


    def grocery_search(self, query: str, app_id: str = "", point_id: str = "",
                       limit: int = 10) -> tuple[list[dict], int, int]:
        """Global grocery search via search/fulltext — searches the ENTIRE store
        catalog (not just one category). Uses inStockFilter (only available
        items). Returns (rows, matched, fetched): rows — up to `limit` matches
        (0 = all of them), matched — how many hits matched the query, fetched —
        how many goods the search service returned at all. query = e.g. "свёкла".

        fetched is capped by grocery_fetch_cap(limit): when fetched == that cap the
        network was saturated and `matched` is a lower bound — more matches may sit
        past the object ceiling, unreached. limit=0 does NOT mean "the whole
        catalog", it means "all of the fetched objects".

        The old shape collected matches with a `break` at 10 and SORTED AFTER the
        break: a cheaper match at position 11 of the server page was silently
        unreachable, and «cheapest» meant cheapest of an arbitrary first ten."""
        _need_store(app_id, point_id)
        q = query.lower().strip().replace("ё", "е")
        # POST search/fulltext (global search across the store)
        base = {"Accept": "application/json", "User-Agent": "okhttp/4.12.0"}
        search_body = {
            "searchTypes": ["grocery_goods", "grocery_categories"],
            "filters": [{"name": "inStockFilter", "type": "grocery_goods",
                         "mode": "always", "value": True}],
            "maxObjectsCount": self.grocery_fetch_cap(limit),
            "sortTypes": [{"type": "grocery_goods", "name": "default"}],
            "text": query.replace("ё", "е"),
        }
        params = self._search_params("grocery", context="api",
                                     applicationId=app_id, pointId=point_id)
        r = self._http.post("https://search.t-bank-app.ru/search/fulltext",
                           params=params, json=search_body,
                           headers={**base, "Authorization": "Bearer " + self.access_token},
                           timeout=30)
        payload = self._unwrap(r)
        hits = payload.get("sortedByScoreObjects", []) if isinstance(payload, dict) else []
        results = []
        fetched = 0
        for hit in hits:
            if hit.get("objectType") != "grocery_goods":
                continue
            fetched += 1
            src = hit.get("objectSource", {})
            if not src:
                continue
            name = src.get("name") or ""
            name_norm = name.lower().replace("ё", "е")
            # Token-AND match instead of literal substring: order-free, stopword-free,
            # punctuation-folded — so «фарш из индейки» hits «Фарш индейки» and a
            # `lay's` query hits «Lay`s» (backtick). score is 0..1; 0 = skip.
            score = self._name_matches(query, name)
            if score == 0:
                continue
            # no filter — classify: is this likely a raw ingredient?
            prep_words = ("с ", "соус", "маринован", "квашен", "солен", "тушен",
                           "салат", "суп", "пюре", "запекан", "жарен", "варен",
                           "голубцы", "винегрет", "бифштекс", "котлет", "боул",
                           "пельмен", "рагу", "бутерброд", "нарезка", "зразы",
                           "соусом", "с сыром", "с чесноком", "с яблоком",
                           "с майонез", "от бренд", "шефа", "паст", "пудинг")
            starts = name_norm.startswith(q)
            has_prep = any(pw in name_norm for pw in prep_words)
            likely_raw = starts and not has_prep
            price = src.get("price", {})
            pv = price.get("value", "?") if isinstance(price, dict) else price
            weight = src.get("weight", {})
            wv = weight.get("value", "") if isinstance(weight, dict) else ""
            wu = weight.get("unit", "") if isinstance(weight, dict) else ""
            results.append({
                "id": str(src.get("goodForeignId", src.get("id", ""))),
                "name": name, "price": pv,
                "weight": f"{wv} {wu}".strip(),
                "unit": wu,
                "inStock": True,  # inStockFilter is applied to the search
                "likely_raw": likely_raw,
                "match": score,
                "appId": str(app_id),
                "pointId": str(point_id),
                "store_app_id": str(src.get("applicationId", app_id)),
                "imageUrl": src.get("imageUrl", ""),
            })
        # sort BEFORE the cut: full matches first (score desc), then likely_raw, then
        # price — so `limit` keeps the best matches, not whichever ten arrived first.
        results.sort(key=lambda r: (-r.get("match", 0), not r.get("likely_raw", False), r.get("price", 999) if isinstance(r.get("price"), (int, float)) else 999))
        matched = len(results)
        if limit > 0:
            results = results[:limit]
        return results, matched, fetched


    def grocery_client_info(self) -> dict:
        """GET /api/grocery/client/info — the account's grocery profile. Carries
        payload.deliveryInfo.{address,deliveryType,comment}: the saved delivery block
        the app uses to seed a cart in a store the user has never ordered from.

        Memoised for CLIENT_INFO_TTL seconds because a single cold-start
        grocery_add_to_cart asked for it twice: once through _grocery_delivery to
        seed the address, then again inside grocery_stores() while resolving areaId.
        Same request, same answer, back to back."""
        memo = getattr(self, "_memo", None)
        if memo is not None:
            at, cached = memo.get("client_info", (0.0, None))
            if cached is not None and time.time() - at < self.CLIENT_INFO_TTL:
                return cached
        info = self._call_read("grocery_client_info")
        info = info if isinstance(info, dict) else {}
        if memo is not None and info:
            memo["client_info"] = (time.time(), info)
        return info


    def _grocery_delivery(self, app_id: str, point_id: str, cart: dict | None = None) -> dict:
        """Build the ``delivery`` block that cart/set requires for this store.

        Two things bit us here, both capture-verified:

        * The address cannot come from the store's own cart alone. For a store the
          user has never used there IS no cart, so the address resolves to ``{}`` and
          the cart/set is rejected — which means no cart is ever created, so the next
          attempt finds no cart either. A permanent deadlock, not a transient miss.
          The app seeds from client/info instead; we prefer the store's own cart (it
          may carry a store-specific address) and fall back to client/info.
        * ``areaId`` is per-retailer and REQUIRED by the retailers that publish one
          (ВкусВилл appId=204, Лента appId=246); Азбука Вкуса (578) has none and its
          real cart/set bodies omit the key entirely. Only the retailers list returns
          it, so resolve it from there and omit the key when the store has none.
        """
        delivery: dict = {}
        try:
            if cart is None:
                cart = self._call_read("grocery_cart_get", overrides={"appId": app_id})
            if isinstance(cart, dict):
                inner = cart.get("cart") if isinstance(cart.get("cart"), dict) else cart
                delivery = inner.get("delivery") or {}
        except TbankApiError:
            delivery = {}
        addr = delivery.get("address") or {}
        comment = delivery.get("comment", "")
        # the cart GET spells it deliveryToDoor; cart/set expects deliveryType
        dtype = delivery.get("deliveryType") or delivery.get("deliveryToDoor") or ""
        if not addr:
            di = self.grocery_client_info().get("deliveryInfo") or {}
            addr = di.get("address") or {}
            dtype = dtype or di.get("deliveryType") or ""
            comment = comment or di.get("comment", "")
        if not addr:
            raise TbankApiError("NO_DELIVERY_ADDRESS",
                "У аккаунта нет сохранённого адреса доставки. Добавь адрес в приложении "
                "Т-Банка (Город), затем повтори.")
        # All 14 captured cart/set bodies carry address.details.streetWithType, but no
        # GET we read returns it — the app fills it in client-side. In every captured
        # address the street name already carries its type (both "<name> проезд" and
        # "улица <name>" forms occur), so street is the value to copy.
        details = addr.get("details")
        if isinstance(details, dict) and details.get("street") and not details.get("streetWithType"):
            addr = dict(addr)
            addr["details"] = {**details, "streetWithType": details["street"]}
        out = {"isExpress": bool(delivery.get("isExpress", False)),
               "comment": comment or "", "pointId": str(point_id),
               "deliveryType": dtype or "IN_PERSON", "address": addr}
        # areaId is a property of the retailer + point, not of the cart, so it does
        # not change between calls. Resolving it meant downloading the whole
        # retailers catalogue on EVERY add_to_cart just to read one field.
        memo = getattr(self, "_memo", None)
        memo_key = f"areaId:{app_id}:{point_id}"
        if memo is not None and memo_key in memo:
            area_id = memo[memo_key]
        else:
            area_id = ""
            found = False
            for st in self.grocery_stores():
                if str(st.get("appId")) == str(app_id) and str(st.get("pointId")) == str(point_id):
                    area_id = str(st.get("areaId") or "")
                    found = True
                    break
            # Only a real answer is memoised. A miss means the catalogue did not list
            # this store on this call — a transient read, a store not yet chosen —
            # and caching "" would drop areaId from every later cart write for the
            # whole process. ВкусВилл needs it: without areaId cart/set answers 200
            # and saves nothing, so the failure would be silent and permanent.
            if memo is not None and found:
                memo[memo_key] = area_id
        if area_id:
            out["areaId"] = area_id
        return out


    def grocery_add_to_cart(self, items: list[dict], app_id: str = "", point_id: str = "") -> dict:
        """Add items to cart. items = [{"id": "123", "count": 1}, ...].
        Resolves the delivery block (address + areaId) and merges with what is
        already in the cart.

        An entry whose key is not exactly ``id`` is refused, not skipped: the old
        loop dropped it silently, the cart came back with an unchanged goodsSum, and
        the tool reported "OK, N new items" for zero items added. `goodId`,
        `good_id` and `product_id` are all plausible guesses for a caller reading
        goods ids out of a search result."""
        _need_store(app_id, point_id)
        _reject_unkeyed(items)
        try:
            cart = self.grocery_cart_get(app_id=app_id, point_id=point_id)
        except TbankApiError as e:
            # cart/set is a FULL REPLACE, so this read is load-bearing: whatever it
            # returns becomes the entire cart. Treating a failed read as an empty
            # cart posted only the new items and DELETED everything already there,
            # while the tool printed an ordinary success line. grocery_set_cart
            # already refuses here for the same reason; this path did not.
            raise TbankApiError("CART_READ_FAILED",
                f"не удалось прочитать корзину перед добавлением ({e}). "
                f"Корзина НЕ изменена — запись заменяет её целиком, а нечитаемая "
                f"корзина не то же самое, что пустая. Повтори позже.") from e
        delivery = self._grocery_delivery(app_id, point_id, cart=cart)
        # cart/set REPLACES the whole cart — every captured body resends the full
        # goods list (item [369] posts 6 goods, [375] posts 5 after a removal). Posting
        # only the new items would silently drop everything added earlier, so merge.
        merged: dict[str, float] = {}
        order: list[str] = []
        for g in self._goods_of(cart):
            gid = str(g.get("id", ""))
            if not gid:
                continue
            if gid not in merged:
                order.append(gid)
            merged[gid] = merged.get(gid, 0) + _count_of(g)
        for it in items:
            gid = str(it.get("id", ""))
            if not gid:
                continue
            if gid not in merged:
                order.append(gid)
            merged[gid] = merged.get(gid, 0) + _count_of(it)
        goods = [{"id": gid, "count": _count_out(merged[gid])} for gid in order]
        return self._grocery_cart_write(goods, app_id, delivery)


    def _grocery_cart_write(self, goods: list[dict], app_id: str, delivery: dict) -> dict:
        """POST the FULL goods list. cart/set replaces the cart wholesale — that is
        also how the app removes an item: capture item [369] posts 6 goods, [375]
        posts 5 after a removal. There is no delete endpoint.

        `cartSetMode` escalates exactly the way the app escalates it. `SINGLE_CART`
        is refused with app code 268 — whose text is the generic "Сервис временно
        недоступен", not anything about carts — once a cart exists for a DIFFERENT
        retailer. The app answers that by resending the identical body with
        `SINGLE_CART_WITH_OTHER_CART_RESET`, which succeeds: captures2.xml [1073]
        fails and [1077] succeeds, and the two bodies differ in this field alone.

        Sending the reset mode unconditionally would work too, and would silently
        discard other retailers' carts on every write. So try the narrow mode first
        and escalate only on 268, then flag it: the caller has to be able to tell
        the user their other cart is gone. An empty goods list never escalates —
        clearing a cart is accepted in the narrow mode."""
        from . import observability as obs

        body = {"goods": goods, "cartSetMode": "SINGLE_CART", "delivery": delivery}

        def _write(mode: str) -> dict:
            body["cartSetMode"] = mode
            started = time.time()
            try:
                res = self._call_read("grocery_cart_set", body=body,
                                      overrides={"appId": app_id})
            except TbankApiError as e:
                code = str(getattr(e, "result_code", "") or "")
                obs.emit("cart_set", app_id=app_id, item_count=len(goods),
                         cart_set_mode=mode, app_code=code,
                         blame=obs.blame_of(200, code),
                         duration_ms=int((time.time() - started) * 1000))
                raise
            obs.emit("cart_set", app_id=app_id, item_count=len(goods),
                     cart_set_mode=mode, http_status=200, blame="ok",
                     duration_ms=int((time.time() - started) * 1000))
            return res

        try:
            return _write("SINGLE_CART")
        except TbankApiError as e:
            if str(getattr(e, "result_code", "")) != "268" or not goods:
                raise
            res = _write("SINGLE_CART_WITH_OTHER_CART_RESET")
            if isinstance(res, dict):
                res = dict(res)
                res["otherCartsReset"] = True
            return res


    def grocery_set_cart(self, items: list[dict], app_id: str = "", point_id: str = "",
                         clear: bool = False) -> dict:
        """Set ABSOLUTE counts. `count: 0` removes a good; goods not mentioned keep
        their current count. `clear=True` empties the cart and ignores `items`.

        The counterpart of grocery_add_to_cart, which is relative (+N). Without this
        the cart could only ever grow: re-adding a good to "correct" it added again.

        Entries without an ``id`` key are refused — see grocery_add_to_cart."""
        _need_store(app_id, point_id)
        if not clear:
            _reject_unkeyed(items)
        try:
            cart = self.grocery_cart_get(app_id=app_id, point_id=point_id)
        except TbankApiError as e:
            # cart/set REPLACES the cart, so proceeding on a failed read would post
            # only what the caller named and delete everything else. An empty cart and
            # an unreadable one look identical from here, so refuse rather than guess.
            raise TbankApiError("CART_READ_FAILED",
                f"Не удалось прочитать корзину ({e}), а запись заменяет её целиком — "
                f"продолжать нельзя, иначе остальные товары будут удалены. "
                f"Повтори позже или проверь grocery_cart(app_id, point_id).") from e
        delivery = self._grocery_delivery(app_id, point_id, cart=cart)
        if clear:
            return self._grocery_cart_write([], app_id, delivery)

        wanted = {str(it.get("id", "")): _count_of(it, default=0.0)
                  for it in items if str(it.get("id", ""))}
        goods, seen = [], set()
        for g in self._goods_of(cart):
            gid = str(g.get("id", ""))
            if not gid or gid in seen:
                continue
            seen.add(gid)
            count = wanted.get(gid, _count_of(g))
            if count > 0:
                goods.append({"id": gid, "count": _count_out(count)})
        # Ids the caller named that are not in the cart yet are additions.
        for gid, count in wanted.items():
            if gid not in seen and count > 0:
                goods.append({"id": gid, "count": _count_out(count)})
        return self._grocery_cart_write(goods, app_id, delivery)


    def _goods_of(cart: Any) -> list[dict]:
        """Goods out of a cart GET payload (payload.cart.goods), [] if none."""
        if not isinstance(cart, dict):
            return []
        inner = cart.get("cart") if isinstance(cart.get("cart"), dict) else cart
        goods = inner.get("goods") if isinstance(inner, dict) else None
        return goods if isinstance(goods, list) else []


    def grocery_cart_goods(self, app_id: str = "", point_id: str = "") -> list[dict]:
        """Goods currently in the store's cart. Raises TbankApiError like any other
        read — this used to swallow it and return [], which conflated "the cart is
        really empty" with "the re-read failed", right after a confirmed-successful
        write. Callers that want a fallback (grocery_add_to_cart already does)
        catch it themselves; this method must not decide that for them."""
        return self._goods_of(self.grocery_cart_get(app_id=app_id, point_id=point_id))


    def grocery_checkout(self, app_id: str = "", point_id: str = "",
                         client_email: str = "", account: str = "",
                         sum_val: float = 0, attempt_id: str | None = None,
                         expected_sum: float = 0, dry_run: bool = False) -> dict:
        """Full grocery checkout (web flow): deliveries → order/create → payment_gate_pay.
        `app_id`/`point_id` scope the store; `account` names the account to debit and
        wins over the bank's last-used one when given; `sum_val` is a mobile-cart
        fallback sum (the post-delivery WEB sum is used inside); `expected_sum` is the
        amount the user approved and refuses the checkout, before the order exists, if
        the backend's final number diverges; `dry_run` stops after the delivery step
        and returns the quote without creating or paying for an order; `attempt_id`
        records progress in the journal. Raises checkout.CheckoutError (safe to retry)
        or checkout.CheckoutUnknown (order may exist — retry must be blocked)."""
        from .checkout import checkout as _checkout
        return _checkout(self, app_id=app_id, point_id=point_id, client_email=client_email,
                         sum_val=sum_val, account=account, attempt_id=attempt_id,
                         expected_sum=expected_sum, dry_run=dry_run)


    def grocery_good(self, good_id: str, app_id: str = "", point_id: str = "") -> dict:
        app_id, point_id = _need_store(app_id, point_id)
        data = self._call_read("grocery_good", overrides={
            "appId": str(app_id), "pointId": str(point_id), "goodId": str(good_id)})
        return (data or {}).get("good") or {}


    def nutrition(good: dict) -> dict:
        """КБЖУ per 100 g, plus per-package totals.

        Two shapes in the wild and only one is structured: Самокат (appId 695)
        fills meta.nutritionalValue.{protein,fat,carbohydrate,energy}; ВкусВилл
        (204) leaves all four empty and puts everything in the free-text `value`
        ("белки 3,3 г, жиры 3 г, углеводы 18,4 г; 113,8 ккал"). Parse the text
        whenever a structured field is missing, else half the catalog reads as
        "no data"."""
        meta = (good or {}).get("meta") or {}
        nv = meta.get("nutritionalValue") or {}
        text = str(nv.get("value") or "")

        def num(x):
            try:
                return float(str(x).replace(",", ".").split()[0])
            except (ValueError, IndexError, AttributeError):
                return None

        out = {"protein": num(nv.get("protein")), "fat": num(nv.get("fat")),
               "carb": num(nv.get("carbohydrate")), "kcal": num(nv.get("energy"))}
        if text:
            low = text.lower().replace(",", ".")
            for key, stem in (("protein", "белк"), ("fat", "жир"), ("carb", "углевод")):
                if out[key] is None:
                    m = re.search(stem + r"\w*\D{0,4}?([\d.]+)", low)
                    if m:
                        out[key] = num(m.group(1))
            if out["kcal"] is None:
                m = re.search(r"([\d.]+)\s*ккал", low)
                if m:
                    out["kcal"] = num(m.group(1))
        weight = meta.get("weight") or {}
        grams = weight.get("value") if str(weight.get("unit", "")).upper() == "GRM" else None
        out["grams"] = grams
        # kcal figures are per 100 g by convention; scale to the actual package
        out["kcal_pack"] = (out["kcal"] * grams / 100.0
                            if out["kcal"] is not None and grams else None)
        out["raw"] = text
        return out


    NUTRITION_KEYS = ("kcal", "kcal_pack", "protein", "fat", "carb")


    SORTABLE_KEYS = ("price", "weight") + NUTRITION_KEYS


    def grocery_candidates(self, query: str, app_id: str = "", point_id: str = "",
                           limit: int = 8, with_nutrition: bool = False,
                           ) -> tuple[list[dict], int]:
        """Search `query` and return (candidate rows, how many matched in total).

        This deliberately applies NO selection policy — it is the capability, not
        the strategy. Ranking ("cheapest", "lowest calorie", "most protein") is the
        caller's decision; see grocery_rank in server.py and the grocery skill.
        `limit <= 0` means every match; the matched count is returned so the
        caller's header can say «N из M» instead of presenting N as everything.

        with_nutrition costs one extra /api/grocery/good request per candidate, so
        it is off unless the caller actually needs those fields. A good whose
        nutrition the retailer does not publish keeps None — "not published" is a
        different fact from zero and must not be flattened into one."""
        found, matched, _ = self.grocery_search(query, app_id=app_id,
                                                point_id=point_id, limit=0)
        picked = found if limit <= 0 else found[:limit]
        rows = []
        for item in picked:
            row = dict(item)
            # search returns weight as a display string ("160.0 GRM"); keep that
            # for output and add a numeric grams field to sort on. _grams reports
            # 0.0 for "no weight given" — keep that as None so an unknown weight
            # sorts as unknown rather than as the lightest item.
            row["weight_label"] = item.get("weight") or ""
            row["weight"] = self._grams(item) or None
            rows.append(row)

        if with_nutrition and rows:
            # One /api/grocery/good per candidate, and they do not depend on each
            # other — issued in sequence this was the whole latency of a ranked
            # search (8 round-trips before the first line of output). requests'
            # Session is thread-safe for concurrent requests on separate
            # connections, and the pool is capped, so a small fan-out is safe here.
            from concurrent.futures import ThreadPoolExecutor

            blank = {k: None for k in ("kcal", "kcal_pack", "protein", "fat",
                                       "carb", "grams")}

            def fetch(item):
                try:
                    good = self.grocery_good(item["id"], app_id=app_id, point_id=point_id)
                    return self.nutrition(good)
                except (TbankApiError, KeyError, ValueError):
                    return dict(blank)

            with ThreadPoolExecutor(max_workers=min(8, len(rows))) as pool:
                for row, n in zip(rows, pool.map(fetch, picked)):
                    row.update({k: n.get(k) for k in self.NUTRITION_KEYS})
                    if n.get("grams"):
                        row["weight"] = n["grams"]
        return rows, matched


    def cancel_grocery_order(self, order_id: str) -> dict:
        """Cancel a grocery (Город) order — paid or not. The app's request
        (cancel-grossary.xml) differs from the ticket flavour on both points that
        bit us there: ONLY orderId rides in the query — no paymentId — and the
        body is genuinely EMPTY (Content-Length: 0), still stamped
        Content-Type: application/json.

        The verdict is payload.{status,code}, NOT the outer envelope — the host
        wraps a refused cancellation in "status":"Ok" too. Observed: 605 = the
        order is already cancelled."""
        data = self._call_read("grocery_order_cancel",
                               overrides={"orderId": str(order_id)})
        return data if isinstance(data, dict) else {}
