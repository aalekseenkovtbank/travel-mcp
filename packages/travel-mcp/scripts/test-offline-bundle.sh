#!/bin/sh
set -eu

[ "$#" -eq 1 ] || {
  printf '%s\n' 'usage: test-offline-bundle.sh <extracted-bundle-root>' >&2
  exit 2
}

BUNDLE_ROOT=$(CDPATH= cd -- "$1" && pwd)
LAUNCHER="$BUNDLE_ROOT/bin/travel-nova-mcp"
PYTHON_COMMAND="$BUNDLE_ROOT/runtime/bin/python3"
APP_ROOT="$BUNDLE_ROOT/app/tbank-mcp"
SITE_PACKAGES="$BUNDLE_ROOT/app/site-packages"

test -x "$LAUNCHER"
test -x "$PYTHON_COMMAND"
test -f "$APP_ROOT/login_cli.py"
test -f "$APP_ROOT/ca/roots/russian-trusted-root-ca.crt"
test -d "$SITE_PACKAGES/mcp"
test ! -d "$SITE_PACKAGES/playwright"
test ! -f "$APP_ROOT/ca/bundle.pem"

HELP_OUTPUT=$(env -i HOME="$BUNDLE_ROOT/.test-home" PATH=/usr/bin:/bin \
  "$LAUNCHER" --help)
printf '%s' "$HELP_OUTPUT" | grep 'Travel MCP offline bundle' >/dev/null

# Import and inspect the exact registry using only the bundled interpreter and
# dependencies. Invalid proxies make an accidental build-time network call fail
# immediately instead of silently making the smoke test depend on connectivity.
env -i \
  HOME="$BUNDLE_ROOT/.test-home" \
  PATH=/usr/bin:/bin \
  PYTHONNOUSERSITE=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH="$APP_ROOT:$SITE_PACKAGES" \
  TBANK_TOOLSET=travel \
  TBANK_TRACE=0 \
  HTTP_PROXY=http://127.0.0.1:9 \
  HTTPS_PROXY=http://127.0.0.1:9 \
  ALL_PROXY=http://127.0.0.1:9 \
  NO_PROXY= \
  "$PYTHON_COMMAND" -c '
from src import server
expected = {
    "session_status", "list_accounts", "list_operations",
    "spending_categories", "operations_histogram", "audience_profile",
    "orders", "order_details", "travel_order_details", "flight_history",
    "flight_search", "hotel_autocomplete", "hotel_search", "hotel_details",
    "hotel_filters", "hotel_rates", "hotel_reviews", "hotel_search_filters",
    "hotel_latest_offers", "hotel_checkout_url",
    "compare_flight_prices", "compare_train_prices", "compare_hotel_prices",
    "compare_flight_hotel_prices", "train_stations", "train_search", "search_app",
    "cinema_search", "cinema_schedule", "cinema_seats", "afisha_catalog",
    "afisha_places", "place_schedule", "place_info", "concert_schedule",
    "concert_hall", "nearby_search", "weather",
}
tools = server.mcp._tool_manager.list_tools()
assert {tool.name for tool in tools} == expected
assert all(tool.annotations.readOnlyHint is True for tool in tools)
assert all(tool.annotations.destructiveHint is False for tool in tools)
print(f"offline Travel MCP registry: {len(tools)} read-only tools")
'

printf '%s\n' 'Travel MCP offline bundle: OK'
