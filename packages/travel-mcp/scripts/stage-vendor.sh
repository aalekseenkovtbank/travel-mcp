#!/bin/sh
set -eu

PACKAGE_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
REPOSITORY_ROOT=$(CDPATH= cd -- "$PACKAGE_ROOT/../.." && pwd)
SOURCE_ROOT="$REPOSITORY_ROOT/tbank-mcp"
TARGET_ROOT="$PACKAGE_ROOT/vendor/tbank-mcp"

[ -f "$SOURCE_ROOT/pyproject.toml" ] || {
  printf '%s\n' "stage-vendor: tbank-mcp not found at $SOURCE_ROOT" >&2
  exit 1
}

mkdir -p "$TARGET_ROOT"
find "$TARGET_ROOT" -mindepth 1 -maxdepth 1 -exec rm -rf {} \;
cp "$SOURCE_ROOT/pyproject.toml" "$SOURCE_ROOT/login_cli.py" \
  "$SOURCE_ROOT/README.md" "$SOURCE_ROOT/LICENSE" "$TARGET_ROOT/"
cp -R "$SOURCE_ROOT/src" "$SOURCE_ROOT/docs" "$TARGET_ROOT/"
# bundle.pem is generated from the TARGET machine's system trust store. Never
# package a developer's generated bundle or ignored *.local.pem certificate.
mkdir -p "$TARGET_ROOT/ca/roots"
cp "$SOURCE_ROOT/ca/roots/russian-trusted-root-ca.crt" "$TARGET_ROOT/ca/roots/"
find "$TARGET_ROOT" -name '__pycache__' -type d -prune -exec rm -rf {} \;
find "$TARGET_ROOT" -name '*.pyc' -type f -delete
