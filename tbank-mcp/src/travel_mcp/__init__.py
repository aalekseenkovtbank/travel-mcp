"""Standalone, read-only Travel MCP surface.

Splits the single T-Bank MCP into a travel-only server that publishes transport
search, hotels, date/city comparison, read-only events (Afisha catalog, venues
and schedule confirmation), personalization and static trip/hotel page
rendering. Nearby places and marketplace tools remain in the source tree but
are not registered on this surface. No bank credentials, transfers, cards,
grocery or ticket-booking tools are registered here.

Layout (each module stays small so it can be read on its own):

  app.py       — FastMCP instance, instruction resources, one prompt, tool wiring
  server.py    — stdio/HTTP entrypoint, surface selection (TRAVEL_SURFACE)
  runtime.py   — session lifecycle + redaction/format/comparison/hotel helpers
"""
