---
name: tbank-flight-search
description: |
  Skill for finding, comparing and linking flight offers. Covers IATA resolution,
  live search, date comparison, round trips, direct alternatives, price signals
  and T-Bank hand-off links.
---

# Flight search skill

Use this skill for aviation search requests. It returns factual flight shortlists
and T-Bank hand-off links. For a complete trip, start with the general
`tbank-trip-generation` skill and use this skill for every aviation search.

## 1. Normalize the request

Determine:

- origin and destination;
- outbound and return dates, or an explicitly flexible date window;
- adults, children ages and infants;
- cabin, baggage, direct-flight, duration, carrier and refundability constraints;
- whether the user wants one-way, round-trip, alternatives or a price comparison.

Use the same passenger composition in every flight call. Ask one short clarification
only when a required value cannot be obtained safely from the request.

## 2. Resolve IATA codes

For city or airport names call:

```text
search_iata_code(query="Париж", response_format="json")
```

Use only returned codes. If several airports/cities are plausible, ask the user or
choose only when the request makes the choice unambiguous. `geodata_by_code()` can
validate already-known codes and return coordinates/timezone; it does not resolve a
name into a code. Do not guess IATA codes from memory.

## 3. Choose the search sequence

### Exact one-way

Call:

```text
flight_search(
  from_code=..., to_code=..., date=..., adults=...,
  children=..., infants=..., only_bookable=true,
  response_format="json"
)
```

### Exact round trip

Use `return_date` in the same `flight_search` request when a combined round-trip
offer is useful. Preserve the returned offerId/searchId and the direction/segment
structure; do not add a second price or invent a second checkout URL.

### Several dates

- `flight_price_calendar()` is a cached date-selection aid, not a live fare;
- `flight_schedule()` describes operating flights, not current availability or price;
- `compare_flight_prices()` performs bounded live comparisons for multiple dates;
- `flight_price_forecast(search_id=...)` reads a signal for an already completed
  search and does not start a new search.

For any candidate that will be shown as a current offer, use live
`flight_search()` before the final answer.

## 4. Mandatory neighbouring-window comparison

Every round-trip goes through two search phases:

1. Search the requested outbound and return dates.
2. Unless the user explicitly says that dates are immutable, inspect a reasonable
   neighbouring window around both dates. The default window is ±1–2 days, but
   use a wider/narrower range when the trip constraints make that appropriate.

The second phase is mandatory because a nearby date may materially improve the
itinerary even when the user did not name a specific alternative. Compare:

- total price;
- departure/arrival times;
- duration and connection count;
- direct versus connecting itinerary;
- alignment with the user's event or stay.

Use this sequence for the neighbouring window:

1. `flight_price_calendar()` and/or `compare_flight_prices()` to select candidate
   dates;
2. `flight_schedule()` to check operating/direct services;
3. live `flight_search()` for each candidate worth showing;
4. pair outbound and return into complete itineraries before comparing them with
   the requested dates.

Hard dates remain hard: an adjacent date must never silently replace the requested
itinerary. If a nearby itinerary is materially better or satisfies a useful
constraint (price, time, fewer stops or direct service), add it to `flightOptions`
with a factual `label` and `comment`. The comment must include the date shift,
extra/missing nights, price trade-off and connection risk.

If no useful complete alternative is found, record the checked date window and say
so explicitly in the final result. Do not turn a one-way direct segment into a
direct round-trip claim.

## 5. Links and output

For each displayed offer include, when available:

- offerId/searchId from the live result;
- carrier, flight number, date, local departure/arrival and connection count;
- price and passenger composition;
- baggage/refundability only when returned by the source;
- the exact T-Bank `tbankUrl` returned by the source.

For selected real segments without a per-offer URL, call
`flight_checkout_url(request)` with the actual codes, dates and flight numbers from
`flight_search`. It creates a user hand-off route URL, not a booking. Never build a
URL by guessing an offerId, flight number, date or airline.

Return a compact shortlist with a recommendation and warnings about incomplete
results, partner links, non-final availability, date shifts and timezone details.
Prices and availability must come from tool responses and should be checked again
before a final composed page.

## 6. Errors and boundaries

- `NO_SESSION`/history errors do not block public search;
- an empty calendar is not proof that no flight exists;
- a partial compare result is not a global cheapest-price claim;
- `only_bookable=false` may return offers that leave T-Bank;
- MCP never books, pays, fills forms or guarantees inventory.
