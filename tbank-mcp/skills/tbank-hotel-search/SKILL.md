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

## 2. Resolve the destination or hotel

Call:

```text
hotel_autocomplete(query="Париж", response_format="json")
```

Use only ids returned by the tool:

- choose a location/destination id for a city or area search;
- choose a hotel id when the user named a specific property;
- if several same-name locations are returned, ask the user to choose;
- do not turn a hotel id into a destination id or invent an id from a name.

## 3. Inspect filters when constraints are explicit

If the user specifies stars, price, area, room, meal, cancellation or asks how
many hotels match, call `hotel_search_filters()` **before** the card search, with
the same location, dates and guests.

It returns available filter values and `filteredHotelsCount`, not hotel cards.
Use its returned filter ids/values in the subsequent `hotel_search()` and, where
supported, in `hotel_rates()` calls. Report the filters that were applied and the
returned count. A generic filter catalog from `hotel_filters()` is optional; it
is not a substitute for the date-specific `hotel_search_filters()` call.

## 4. Search the inventory

Call:

```text
hotel_search(
  destination_id=..., checkin_date=..., checkout_date=...,
  adults=..., children_ages=..., response_format="json"
)
```

Keep `limit` within the tool's limit (maximum 50). Treat the returned cards as an
inventory snapshot, not as a reservation. Check `isLoadingCompleted`, `pricesFinal`,
`meta.complete` and warnings; do not call a preliminary price final when the
source marked it non-final.

Every hotel-returning tool includes `details` for each hotel: static name/address,
description, check-in/out, coordinates, facilities, exact T-Bank URL and up to
three real source photos. Single-hotel `hotel_rates` and `hotel_reviews` expose
the same projection as `hotelDetails`. Preserve it in downstream results; an
empty `imageUrls` plus warning means the source returned no usable photo.

Build a shortlist from actual returned hotel ids. For a normal comparison use up
to three strong candidates with meaningfully different trade-offs; for a broad
hotel-only request, the tool contract permits up to five. Do not force a number
when fewer suitable properties are available.

## 5. Refresh current offers before comparing

Once the shortlist is selected, call one:

```text
hotel_latest_offers(
  hotel_ids=[...], checkin_date=..., checkout_date=...,
  adults=..., children_ages=..., response_format="json"
)
```

Match the response by `hotelId`. If an id is missing, do not show it as currently
available. If `price.isFinalPrice` is not explicitly true, do not claim that meal,
cancellation, payment or availability is confirmed.

## 6. Inspect each final hotel and its rates

For every hotel that will appear in the final shortlist, call:

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

For every final hotel, call one comparable review page:

```text
hotel_reviews(hotel_id=..., sort="date", sort_type="desc",
              page_size=10, response_format="json")
```

Reviews are mandatory for the final hotel shortlist. A review page is a sample,
not all reviews. Use only facts in the returned sample; do not calculate
percentages or generalize beyond it. If reviews fail, keep the hotel data but add
a visible warning that the review sample is unavailable. For a composed trip,
summarize the sample as `reviewDigest` and pass it with the hotel item to
`tbank-trip-generation`; the report composer does not call reviews itself.

## 7. Checkout hand-off

After `hotel_rates()` you may immediately call `hotel_checkout_url()` for each
rate whose `bookHash` should be shown to the user; this is not required to be the
final step and does not require a separate final confirmation. Pass:

- the unchanged `bookHash` from `hotel_rates`;
- matching hotel id and dates;
- the guest composition used for the rate.

The result is only a user hand-off URL. It does not create a booking or payment.

## 8. Return the result

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
