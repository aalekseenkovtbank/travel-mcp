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

Offers carry `labels` («самый дешёвый», «самый быстрый», «оптимальный») and a
`best` block; a fresh searchId also yields an automatic `priceForecast`
(price likely to rise or not).

### Exact round trip

Pass `return_date=...` in the SAME call: the server searches both legs and
returns `roundTripOptions` — complete pairs with a total price and each leg's
`bookingUrl`. Preserve the returned offerId/searchId structure; do not invent
a second checkout URL. A second standalone `flight_search` for the return leg
is only needed when the dates or passenger composition differ.

### Vague or month-level request («подешевле в октябре»)

Pass `date="YYYY-MM"`: the server answers with `monthCalendar` (cached minimum
prices for the whole month) and `cheapestDates` without starting a live
search. Pick a concrete date with the user, then run a live `flight_search`.

### Several explicit dates

Pass `dates=["2026-10-02", "2026-10-09", ...]` (up to 7): the server compares
them in one call and returns `byDate` plus `cheapestDate`.

### Supporting reads

- `flight_price_calendar()` is a cached date-selection aid, not a live fare;
- `flight_schedule()` describes operating flights, not current availability or price;
- `flight_search(flexible_days=0..14)` widens the automatic
  `priceCalendarNearby` window beyond the default ±3 days.

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

1. `flight_price_calendar()` (or `flight_search(date="YYYY-MM")` for a whole
   month) to select candidate dates;
2. `flight_schedule()` to check operating/direct services;
3. live `flight_search()` for each candidate worth showing — `dates=[...]`
   compares several candidates in one call;
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
- the «самый дешёвый / самый быстрый / оптимальный» labels from `best`;
- baggage/refundability only when returned by the source;
- the exact T-Bank `bookingUrl` returned by the source: `flight_search()`
  embeds it per bookable offer (checkout hand-off) together with a
  `priceCalendarNearby` cache block (±`flexible_days`, default 3).

For selected real segments without a per-offer URL, preserve the actual `offerId`,
codes, dates, carrier codes and flight numbers from `flight_search` in the report
request; the page renderer also builds `avia_checkout_url(offerId)` and
`avia_share_url(...)` links. These URLs only hand the user off to T-Bank; they do not
create a booking. Never build a URL in the agent or guess an offerId, flight number,
date or airline.

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
