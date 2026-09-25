---
name: tbank
description: |
  Travel router for T-Bank MCP. Use for flights, trains, hotels, Afisha events,
  weather, comparisons and generated trip pages. Travel scenarios stay read-only:
  do not book or pay even when the unified surface exposes those tools.
---

# Travel Nova MCP — router

The current HTTP launcher exposes the travel-only `travel-nova` surface
(24 read-only tools). Travel flows use only read-only search and report tools
and return ready HTML page markup or Markdown in memory. Do not book, buy or
pay within a travel scenario.

## Pick one narrow skill

| Request | Skill |
|---|---|
| Standalone flight search (incl. round-trip, month, date comparison) and flight links | `tbank-flight-search` |
| Standalone hotel search, shortlist, rates, reviews, photos | `tbank-hotel-search` |
| Composed trip, document, digest or page | `tbank-trip-generation` |
| Trains, weather or generic travel components | `tbank-travel-search` |

Do not load both narrow skills unless the request genuinely combines their
scenarios. Follow the selected skill and the published Travel Nova instruction
resources.

## Surface boundaries

- Do not call transfer, payment, booking, card, raw-operation or grocery checkout
  tools while executing a travel flow, even if the unified MCP registers them.
  The default travel-nova surface registers none of them at all.
- Transport and hotel operations stop at search/comparison; page rendering is in memory.
- For events — "what to do", concerts, theatre, cinema — use the read-only
  events tools: `afisha_catalog()` with city and dates (cards carry `url` and
  `imageUrl`), `afisha_places()`/`place_info()`/`place_schedule()` for venues,
  `cinema_schedule()`/`concert_schedule()` to confirm sessions. Do not use
  authenticated `search_app()` as a preliminary step.
- Checkout URLs are user hand-off links; they never reserve or pay. Every
  `hotel_rates()` row and every enriched `confirmedRate` already includes its
  `checkoutUrl` (with `checkedAt` — if the page shows a different price, re-run
  `hotel_rates()` for fresh links); `flight_search()` offers include
  `bookingUrl`.
- Prefer the deep tools over chains: `get_trip_report(brief={city, dateFrom,
  dateTo, adults, origin?})` composes the whole page server-side in one call;
  `flight_search(return_date=...)` builds round-trips, `flight_search(dates=
  [...])` compares dates, `flight_search(date="YYYY-MM")` returns the month
  calendar; `hotel_search(destination="Сочи")` resolves the city itself and
  returns enriched cards plus `comparisonMarkdown` and `map`.
- `get_trip_report()` returns the requested HTML or Markdown digest in memory;
  it writes no files. For an empty trip `venues` block it performs a public
  Yandex Maps `restaurant_search()` around the selected hotel. Local files
  exist only for developer CLI commands.
- Every hotel-returning tool includes a `details` block with static facts,
  facilities and up to three source photos (`hotelDetails` for single-hotel
  rates/reviews). Enriched `hotel_search()` cards (default `comparison_limit=3`)
  already carry `confirmedRate` (with `checkoutUrl`), `reviewDigest` and photos;
  call `hotel_rates()`/`hotel_reviews()` only for a hotel outside the enriched
  shortlist or for a re-check.
- Public hotel, flight, railway, weather, Afisha catalogue, cinema schedule and
  concert/theatre schedule search needs no bank login.
  Session-backed history/profile tools may use an existing local `session.json`,
  but missing authorization must not block public inventory searches.
- Never invent prices, ids, schedules, availability, photos or source results.
- Executable tool schemas and validators take precedence over prose examples.
- If the host hides MCP resources and prompts (typical for ChatGPT), call
  `list_instructions()`, `read_instruction(slug)` and `get_travel_prompt()`
  before searching. The Markdown is the same as `travel-nova://instructions/*`.
