---
name: tbank
description: |
  Travel router for T-Bank MCP. Use for flights, trains, hotels, Afisha events,
  weather, comparisons and generated trip pages. Travel scenarios stay read-only:
  do not book or pay even when the unified surface exposes those tools.
---

# Travel Nova MCP — router

The current HTTP launcher exposes the unified T-Bank MCP surface. Travel flows
use only read-only search, comparison and report tools and return ready HTML page
markup or Markdown in memory. Do not book, buy or pay within a travel scenario.

## Pick one narrow skill

| Request | Skill |
|---|---|
| Standalone flight search, comparisons, direct alternatives and flight links | `tbank-flight-search` |
| Standalone hotel search, shortlist, rates, reviews, photos | `tbank-hotel-search` |
| Composed trip, document, digest or page | `tbank-trip-generation` |
| Trains, weather or generic travel components | `tbank-travel-search` |

Do not load both narrow skills unless the request genuinely combines their
scenarios. Follow the selected skill and the published Travel Nova instruction
resources.

## Surface boundaries

- Do not call transfer, payment, booking, card, raw-operation or grocery checkout
  tools while executing a travel flow, even if the unified MCP registers them.
- Transport and hotel operations stop at search/comparison; page rendering is in memory.
- For events in a trip, call public `afisha_catalog()` directly with city and
  dates; do not use authenticated `search_app()` as a preliminary step.
- `hotel_checkout_url()` only returns a user hand-off link; it does not reserve or
  pay for a room.
- `get_trip_report()` returns the requested HTML or Markdown digest in memory;
  it writes no files. Local files exist only for developer CLI commands.
- Public hotel, flight, railway, weather and Afisha catalogue search needs no bank login.
  Session-backed history/profile tools may use an existing local `session.json`,
  but missing authorization must not block public inventory searches.
- Never invent prices, ids, schedules, availability, photos or source results.
- Executable tool schemas and validators take precedence over prose examples.
- If the host hides MCP resources and prompts (typical for ChatGPT), call
  `list_instructions()`, `read_instruction(slug)` and `get_travel_prompt()`
  before searching. The Markdown is the same as `travel-nova://instructions/*`.
