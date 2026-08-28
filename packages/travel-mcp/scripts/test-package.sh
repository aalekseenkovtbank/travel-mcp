#!/bin/sh
set -eu

PACKAGE_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PACKAGE_ROOT"
sh scripts/stage-vendor.sh

test -x bin/travel-nova-mcp
test -f vendor/tbank-mcp/src/travel_server.py
test -f vendor/tbank-mcp/src/trip_page.py
test -f vendor/tbank-mcp/src/assets/leaflet-1.9.4.js.txt
test -f vendor/tbank-mcp/ca/roots/russian-trusted-root-ca.crt
test ! -f vendor/tbank-mcp/ca/bundle.pem
test ! -f vendor/tbank-mcp/ca/roots/tinkoffbank-root-ca.local.pem
test -f vendor/tbank-mcp/docs/FLOWS.md
test -x offline/bin/travel-nova-mcp
test -x scripts/build-offline-bundle.sh
test -x scripts/test-offline-bundle.sh
test -f offline/requirements.in
test -f offline/requirements.lock
if grep -i 'playwright' offline/requirements.in | grep -v 'intentionally absent' >/dev/null 2>&1; then
  printf '%s\n' 'offline packaging: Playwright must not enter the travel bundle' >&2
  exit 1
fi

TEMP_ROOT=${TMPDIR:-/tmp}/travel-nova-launcher-test-$$
mkdir -p "$TEMP_ROOT/node_modules/.bin"
ln -s "$PACKAGE_ROOT/bin/travel-nova-mcp" "$TEMP_ROOT/node_modules/.bin/travel-nova-mcp"
HELP_OUTPUT=$("$TEMP_ROOT/node_modules/.bin/travel-nova-mcp" --help)
find "$TEMP_ROOT" -mindepth 1 -delete
rmdir "$TEMP_ROOT"
printf '%s' "$HELP_OUTPUT" | grep 'local trip pages' >/dev/null
python3 scripts/test-interactive-login.py "$PACKAGE_ROOT/bin/travel-nova-mcp"
python3 scripts/test-login-cli-input.py "$PACKAGE_ROOT/vendor/tbank-mcp/login_cli.py"
PYTHONPATH="$PACKAGE_ROOT/vendor/tbank-mcp" python3 -m src.trip_cli trip-page-schema |
  grep 'trip-page/v1' >/dev/null

if grep -R -i -E '2gis|2gis\.ru|api\.2gis|sqlite|openai|travel-api|travel-web' \
  vendor/tbank-mcp/src \
  vendor/tbank-mcp/login_cli.py >/dev/null 2>&1; then
  printf '%s\n' 'packaging security: forbidden provider/runtime reference found' >&2
  exit 1
fi
if find vendor/tbank-mcp -type f \( -name '*.js' -o -name '*.ts' \
  -o -name '*.sqlite' -o -name '*.db' \) | grep . >/dev/null 2>&1; then
  printf '%s\n' 'packaging security: Node or SQLite artifact found' >&2
  exit 1
fi

printf '%s\n' 'Travel MCP package layout: OK'
