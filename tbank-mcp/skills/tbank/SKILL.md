---
name: tbank
description: |
  Travel-only router for the standalone Travel Nova MCP. Use for T-Bank travel,
  flights, trains, hotels, weather, comparisons and generated trip pages.
  Banking, money, cards, venue search and booking/payment actions are unavailable.
---

# Travel Nova MCP — router

This checkout is configured to use only the standalone `travel-mcp` surface.
It searches and compares travel inventory and returns ready HTML page markup
and Markdown replies (in memory, no disk files), but it cannot book, buy or pay
for anything.

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

- No transfer, bill payment, card, account, raw operation, grocery checkout or
  ticket purchase tools are registered.
- Transport and hotel operations stop at search/comparison; page rendering is in memory.
- `hotel_checkout_url()` only returns a user hand-off link; it does not reserve or
  pay for a room.
- `get_trip_report()` returns the requested HTML or Markdown digest in memory;
  it writes no files. Local files exist only for developer CLI commands.
- Public hotel, flight, railway and weather search needs no bank login.
  Session-backed history/profile tools may use an existing local `session.json`,
  but this MCP exposes no login or money operations.
- Never invent prices, ids, schedules, availability, photos or source results.
- Executable tool schemas and validators take precedence over prose examples.
- If the host hides MCP resources and prompts (typical for ChatGPT), call
  `list_instructions()`, `read_instruction(slug)` and `get_travel_prompt()`
  before searching. The Markdown is the same as `travel-nova://instructions/*`.
