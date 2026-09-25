---
name: tbank-hotel-search
description: |
  Read-only skill for finding hotels, filtering availability, checking current
  rates and building a factual shortlist. It does not render pages, write files,
  book rooms or make payments.
---

# Hotel search skill

This skill covers only the hotel-search workflow. Use the active hotel tools in
this order and keep the same destination, dates and guest composition throughout.
Do not call page renderers from this skill; a caller that needs a trip page owns
that separate step. A visible hotel answer is not complete after autocomplete or
inventory search: enrich every hotel in the final shortlist before replying.

## 1. Normalize the request

Determine:

- destination or a specific hotel;
- check-in/check-out dates in `YYYY-MM-DD`;
- adults and children ages (`adults=2`, no children only when the user did not
  specify another composition);
- explicit constraints: budget, stars, area, meal, room, cancellation and
  other preferences.

Ask one short clarification only when a required value cannot be obtained from
 the request or a safe default. Never infer a city, hotel id, dates or budget
from unrelated searches.

## 2. Search the inventory (destination resolves itself)

Pass the city straight to the search:

```text
hotel_search(
  destination="Париж", checkin_date=..., checkout_date=...,
  adults=..., children_ages=..., response_format="json"
)
```

The server resolves the name via autocomplete internally and returns
`resolvedDestination` (plus a warning listing alternatives when ambiguous).
For an exact location id or a repeat search use `destination_id` from
`hotel_autocomplete()`; when the user named a specific property, resolve it
with `hotel_autocomplete()` and use its hotel id with `hotel_rates()`/`hotel_reviews()`.
Do not invent an id from a name.

When the user specifies stars, price, area or asks how many hotels match, use
the `availableFilters` block returned by `hotel_search()` and report the count;
a preliminary filter call is no longer part of the flow.

Keep `limit` within the tool's limit (maximum 50). Treat the returned cards as an
inventory snapshot, not as a reservation. Check `isLoadingCompleted`, `pricesFinal`,
`meta.complete` and warnings; do not call a preliminary price final when the
source marked it non-final.

`hotel_search()` also returns `enrichedShortlist` for the first
`comparison_limit` cards (default 3, maximum 5). Each item already contains the
freshly reloaded `details`, current `confirmedRate` **with a ready
`checkoutUrl`** and a ten-review
`reviewDigest` with **Плюсы**, **Минусы** and **Кому подходит**, in addition to
real photos. A
normal hotel-only answer should select from this block so the result is complete
without redundant calls.

The JSON projection starts with ready-to-render `comparisonMarkdown` — a
complete markdown table (price, nightly price, room/meal, cancellation, pros,
cons) followed by per-hotel detail blocks — plus a `map` block with an
OpenStreetMap link and per-hotel coordinates. It does not publish incomplete
raw catalogue cards. Every enriched item also carries the flat
`primaryPhotoUrl`, `photoUrls`, `pluses`, `minuses`, `suitableFor` and
`nights`. For every hotel included in the visible
answer, render at least one of those photos and all three explicitly labelled
review fields — the simplest way is to reuse `comparisonMarkdown` verbatim.
Use `total` and `catalogSampleCount` only as numeric catalogue
context; they do not describe additional selectable cards.
`hotel_search` also attaches one bounded native MCP image block for every
enriched card, using only trusted T-Bank image CDNs (`cdn.tbank.ru`,
`cdn.t-static.ru`). Preserve those images in
the visible result even when the host summarizes the JSON text.

Every hotel-returning tool includes `details` for each hotel: static name/address,
description, check-in/out, coordinates, facilities, exact T-Bank URL and up to
three real source photos. Single-hotel `hotel_rates` and `hotel_reviews` expose
the same projection as `hotelDetails`. Preserve it in downstream results; an
empty `imageUrls` plus warning means the source returned no usable photo.

Build a shortlist from actual returned hotel ids. For a normal comparison use up
to three strong candidates with meaningfully different trade-offs; for a broad
hotel-only request, the tool contract permits up to five. Do not force a number
when fewer suitable properties are available.

## 3. Refresh current offers before comparing

For a separately obtained hotel outside the enriched shortlist, re-run
`hotel_search(destination=..., comparison_limit=...)` or call
`hotel_rates(hotel_id=..., ...)` directly — its rate rows are the current
offer. If `price.isFinalPrice` is not explicitly true, do not claim that meal,
cancellation, payment or availability is confirmed.

## 4. Inspect each final hotel and its rates

For every separately obtained hotel that replaces a complete shortlist card, call:

```text
hotel_rates(hotel_id=..., checkin_date=..., checkout_date=...,
           adults=..., children_ages=..., response_format="json")
```

Use the embedded `details` for static facts and up to three photo URLs. Call
`hotel_details(hotel_id=..., max_images=3, response_format="json")` only to retry
or request an expanded standalone card. Use `hotel_rates` for current rooms,
prices, meal, payment, cancellation, availability and `bookHash`. Keep the dates
and guests equal to the original search.

Each hotel may expose at most three photo URLs in embedded output. A direct
`hotel_details` call may request a different supported limit; review/search
projections stay capped server-side per hotel. A response containing several
hotels may therefore contain up to three URLs for each hotel.
`hotel_rates` may return up to three room-photo URLs for each room type. Do not
fetch or invent more photos to fill a visual layout.

For every separately obtained hotel that replaces a complete shortlist card, call one comparable review page:

```text
hotel_reviews(hotel_id=..., sort="date", sort_type="desc",
              page_size=30, response_format="json")
```

Reviews are mandatory for the final hotel shortlist. A review page is a sample,
not all reviews. Use only facts in the returned sample; do not calculate
percentages or generalize beyond it. If reviews fail, keep the hotel data but add
a visible warning that the review sample is unavailable. For a composed trip,
summarize the sample as `reviewDigest` and pass it with the hotel item to
`tbank-trip-generation`; the report composer does not call reviews itself.

## 5. Checkout hand-off

Each `hotel_rates()` rate row and each enriched `confirmedRate` already carries
a pre-attached `checkoutUrl` (the T-Bank hand-off link for that `bookHash`) —
surface it directly when the user picks a rate. The response also carries
`checkedAt`: a `bookHash` ages with availability, so if the checkout page shows
a different price or the rate is gone, re-run `hotel_rates()` and surface the
fresh links.

The result is only a user hand-off URL. It does not create a booking or payment.

## 6. Return the result

Return a concise shortlist with, for each hotel:

- name and exact T-Bank hotel link when available;
- factual card details: stars, rating and review count, address, description,
  check-in/out and relevant facilities when the sources returned them;
- at least the first available real photo from `details.imageUrls`; additional
  source photos may be shown up to the documented limit;
- dates, total price and nightly price only when the source labels them clearly;
- meal, room, cancellation and payment only when confirmed by the final rate;
- the review sample size and a separate comparison block with exactly these
  labels: **Плюсы**, **Минусы**, **Кому подходит**. Repeated themes require at
  least two reviews; otherwise write «недостаточно данных»;
- the applied filters and result count when filters were requested;
- a short factual reason it fits;
- warnings for incomplete, missing or non-final data.

Never invent prices, ratings, photos, availability, ids or URLs. If a source
failed, keep the available facts and show the hotel-specific warning instead of
silently omitting details, photos or reviews. This skill does not render HTML,
create files or produce a trip-page document.
