#!/bin/sh
set -eu

PACKAGE_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
REPOSITORY_ROOT=$(CDPATH= cd -- "$PACKAGE_ROOT/../.." && pwd)
SOURCE_ROOT="$REPOSITORY_ROOT/tbank-mcp"
TARGET_ROOT="$PACKAGE_ROOT/vendor/tbank-mcp"

clean_generated_vendor() {
  if [ -d "$PACKAGE_ROOT/vendor" ]; then
    find "$PACKAGE_ROOT/vendor" -mindepth 1 -delete
    rmdir "$PACKAGE_ROOT/vendor"
  fi
}

case "${1:-}" in
  "") ;;
  --clean)
    clean_generated_vendor
    exit 0
    ;;
  *)
    printf '%s\n' 'usage: stage-vendor.sh [--clean]' >&2
    exit 2
    ;;
esac

[ -f "$SOURCE_ROOT/pyproject.toml" ] || {
  printf '%s\n' "stage-vendor: tbank-mcp not found at $SOURCE_ROOT" >&2
  exit 1
}
[ -f "$REPOSITORY_ROOT/AGENTS.md" ] || {
  printf '%s\n' "stage-vendor: AGENTS.md not found at $REPOSITORY_ROOT" >&2
  exit 1
}
[ -f "$REPOSITORY_ROOT/docs/AGENT_RULES.md" ] || {
  printf '%s\n' "stage-vendor: docs/AGENT_RULES.md not found" >&2
  exit 1
}
[ -d "$SOURCE_ROOT/skills" ] || {
  printf '%s\n' "stage-vendor: tbank-mcp skills not found" >&2
  exit 1
}

clean_generated_vendor
mkdir -p "$TARGET_ROOT"
cp "$SOURCE_ROOT/pyproject.toml" "$SOURCE_ROOT/login_cli.py" \
  "$SOURCE_ROOT/README.md" "$SOURCE_ROOT/LICENSE" "$TARGET_ROOT/"
cp -R "$SOURCE_ROOT/src" "$SOURCE_ROOT/docs" "$TARGET_ROOT/"
# Runtime copies derived from the canonical repository entrypoint and skills.
# They let MCP resources resolve after npm installation, outside this checkout.
cp "$REPOSITORY_ROOT/AGENTS.md" "$TARGET_ROOT/docs/AGENTS.md"
cp "$REPOSITORY_ROOT/docs/AGENT_RULES.md" "$TARGET_ROOT/docs/AGENT_RULES.md"
mkdir -p "$TARGET_ROOT/docs/skills"
for SKILL_FILE in "$SOURCE_ROOT"/skills/*/SKILL.md
do
  SKILL_NAME=$(basename -- "$(dirname -- "$SKILL_FILE")")
  mkdir -p "$TARGET_ROOT/docs/skills/$SKILL_NAME"
  cp "$SKILL_FILE" "$TARGET_ROOT/docs/skills/$SKILL_NAME/SKILL.md"
done
# bundle.pem is generated from the TARGET machine's system trust store. Never
# package a developer's generated bundle or ignored *.local.pem certificate.
mkdir -p "$TARGET_ROOT/ca/roots"
cp "$SOURCE_ROOT/ca/roots/russian-trusted-root-ca.crt" "$TARGET_ROOT/ca/roots/"
find "$TARGET_ROOT" -name '__pycache__' -type d -prune -exec rm -rf {} \;
find "$TARGET_ROOT" -name '*.pyc' -type f -delete
