#!/bin/sh
# Build a ready-to-run, relocatable macOS Apple Silicon archive. Network access
# is used only on the build machine to obtain the pinned Python runtime and
# locked wheels. The resulting archive never invokes npm, pip, uv or a registry.
set -eu

PACKAGE_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
REPOSITORY_ROOT=$(CDPATH= cd -- "$PACKAGE_ROOT/../.." && pwd)
OFFLINE_ROOT="$PACKAGE_ROOT/offline"
REQUIREMENTS="$OFFLINE_ROOT/requirements.lock"
OUTPUT_ROOT=${OFFLINE_OUTPUT_DIR:-"$PACKAGE_ROOT/dist"}
PYTHON_REQUEST=${OFFLINE_PYTHON_VERSION:-3.13}

case "$(uname -s)-$(uname -m)" in
  Darwin-arm64) PLATFORM=macos-arm64 ;;
  *)
    printf '%s\n' \
      'build-offline-bundle: пока поддерживается только macOS arm64' >&2
    exit 1
    ;;
esac

UV_COMMAND=${UV_COMMAND:-$(command -v uv || true)}
[ -n "$UV_COMMAND" ] || {
  printf '%s\n' 'build-offline-bundle: на build-машине нужен uv' >&2
  exit 1
}
[ -f "$REQUIREMENTS" ] || {
  printf '%s\n' "build-offline-bundle: отсутствует $REQUIREMENTS" >&2
  exit 1
}

PACKAGE_VERSION=$(sed -n 's/^[[:space:]]*"version": "\([^"]*\)",*$/\1/p' \
  "$PACKAGE_ROOT/package.json" | sed -n '1p')
[ -n "$PACKAGE_VERSION" ] || {
  printf '%s\n' 'build-offline-bundle: не удалось прочитать version' >&2
  exit 1
}

TEMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/tbank-mcp-offline.XXXXXX")
cleanup() {
  sh "$PACKAGE_ROOT/scripts/stage-vendor.sh" --clean
  if [ -d "$TEMP_ROOT" ]; then
    find "$TEMP_ROOT" -mindepth 1 -delete
    rmdir "$TEMP_ROOT"
  fi
}
trap cleanup EXIT HUP INT TERM

UV_CACHE="$TEMP_ROOT/uv-cache"
PYTHON_INSTALL="$TEMP_ROOT/python-install"
mkdir -p "$UV_CACHE" "$PYTHON_INSTALL" "$OUTPUT_ROOT"

printf '%s\n' "offline bundle: получаю relocatable CPython $PYTHON_REQUEST"
UV_CACHE_DIR="$UV_CACHE" "$UV_COMMAND" python install "$PYTHON_REQUEST" \
  --install-dir "$PYTHON_INSTALL" --no-bin --no-progress --native-tls

PYTHON_SOURCE=$(find "$PYTHON_INSTALL" -type f -path '*/bin/python3.*' \
  -perm -100 | LC_ALL=C sort | sed -n '1p')
[ -n "$PYTHON_SOURCE" ] || {
  printf '%s\n' 'build-offline-bundle: Python runtime не найден после загрузки' >&2
  exit 1
}
PYTHON_SOURCE_ROOT=$(CDPATH= cd -- "$(dirname -- "$PYTHON_SOURCE")/.." && pwd)
PYTHON_VERSION=$(
  "$PYTHON_SOURCE" -c \
    'import sys; print(".".join(map(str, sys.version_info[:3])))'
)
PYTHON_TAG=$(
  "$PYTHON_SOURCE" -c \
    'import sys; print(f"{sys.version_info.major}{sys.version_info.minor}")'
)

BUNDLE_NAME="tbank-mcp-$PACKAGE_VERSION-$PLATFORM-py$PYTHON_VERSION"
BUNDLE_ROOT="$TEMP_ROOT/$BUNDLE_NAME"
mkdir -p "$BUNDLE_ROOT/bin" "$BUNDLE_ROOT/runtime" \
  "$BUNDLE_ROOT/app/tbank-mcp" "$BUNDLE_ROOT/app/site-packages"

cp -R "$PYTHON_SOURCE_ROOT/." "$BUNDLE_ROOT/runtime/"
cp "$OFFLINE_ROOT/bin/tbank-mcp" "$BUNDLE_ROOT/bin/tbank-mcp"
chmod 0755 "$BUNDLE_ROOT/bin/tbank-mcp"

printf '%s\n' 'offline bundle: устанавливаю locked-зависимости в архив'
UV_CACHE_DIR="$UV_CACHE" UV_LINK_MODE=copy "$UV_COMMAND" pip install \
  --python "$BUNDLE_ROOT/runtime/bin/python3" \
  --target "$BUNDLE_ROOT/app/site-packages" \
  --requirements "$REQUIREMENTS" \
  --require-hashes \
  --no-deps \
  --only-binary :all: \
  --no-progress \
  --no-config \
  --native-tls

printf '%s\n' 'offline bundle: добавляю Chromium для grocery checkout'
PYTHONPATH="$BUNDLE_ROOT/app/site-packages" \
PLAYWRIGHT_BROWSERS_PATH="$BUNDLE_ROOT/app/ms-playwright" \
  "$BUNDLE_ROOT/runtime/bin/python3" -m playwright install chromium

sh "$PACKAGE_ROOT/scripts/stage-vendor.sh"
cp -R "$PACKAGE_ROOT/vendor/tbank-mcp/." "$BUNDLE_ROOT/app/tbank-mcp/"
sh "$PACKAGE_ROOT/scripts/stage-vendor.sh" --clean
cp "$OFFLINE_ROOT/README.md" "$BUNDLE_ROOT/README.md"
cp "$REQUIREMENTS" "$BUNDLE_ROOT/requirements.lock"
cp "$REPOSITORY_ROOT/tbank-mcp/LICENSE" "$BUNDLE_ROOT/LICENSE"

printf '%s\n' \
  "tbank-mcp $PACKAGE_VERSION" \
  "platform $PLATFORM" \
  "python $PYTHON_VERSION" >"$BUNDLE_ROOT/VERSION"

LOCK_SHA=$(shasum -a 256 "$REQUIREMENTS" | awk '{print $1}')
printf '%s\n' \
  "package_version=$PACKAGE_VERSION" \
  "platform=$PLATFORM" \
  "python_version=$PYTHON_VERSION" \
  "python_tag=cp$PYTHON_TAG" \
  "requirements_sha256=$LOCK_SHA" \
  "built_utc=$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
  >"$BUNDLE_ROOT/BUILD-INFO"

# Ensure no credential or generated machine-specific trust bundle crossed the
# packaging boundary.
if find "$BUNDLE_ROOT" -type f \( \
  -name 'session.json' -o -name '*.har' -o -name 'bundle.pem' \
  \) | grep . >/dev/null 2>&1; then
  printf '%s\n' 'build-offline-bundle: найден запрещённый credential/runtime файл' >&2
  exit 1
fi

(
  cd "$BUNDLE_ROOT"
  find . -type f ! -name MANIFEST.sha256 | LC_ALL=C sort | while IFS= read -r FILE
  do
    shasum -a 256 "$FILE"
  done >MANIFEST.sha256
)

ARCHIVE="$OUTPUT_ROOT/$BUNDLE_NAME.tar.gz"
ARCHIVE_SHA="$ARCHIVE.sha256"
printf '%s\n' "offline bundle: создаю $ARCHIVE"
COPYFILE_DISABLE=1 tar -czf "$ARCHIVE" -C "$TEMP_ROOT" "$BUNDLE_NAME"

# Verify the archive after a second extraction, not only the staging directory.
# This catches absolute symlinks and other accidental assumptions about the
# build path before the artifact is handed to an offline machine.
VERIFY_ROOT="$TEMP_ROOT/verify"
mkdir -p "$VERIFY_ROOT"
COPYFILE_DISABLE=1 tar -xzf "$ARCHIVE" -C "$VERIFY_ROOT"
(
  cd "$VERIFY_ROOT/$BUNDLE_NAME"
  shasum -a 256 -c MANIFEST.sha256 >/dev/null
)
if find "$VERIFY_ROOT/$BUNDLE_NAME" -type l -exec readlink {} \; \
  | grep '^/' >/dev/null 2>&1; then
  printf '%s\n' 'build-offline-bundle: в архив попал абсолютный symlink' >&2
  exit 1
fi
# Store only the basename so the checksum remains usable after transfer to a
# different machine or directory.
(
  cd "$OUTPUT_ROOT"
  shasum -a 256 "$(basename -- "$ARCHIVE")" \
    >"$(basename -- "$ARCHIVE_SHA")"
)

printf '%s\n' \
  "offline bundle: готово" \
  "  $ARCHIVE" \
  "  $ARCHIVE_SHA"
