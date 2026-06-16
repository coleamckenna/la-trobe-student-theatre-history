#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export CATALOG_INSTANCE="$ROOT/config/instance.yaml"
PYTHON="${ROOT}/framework/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3"
fi

SOURCE_DB="${1:-$ROOT/ltst.sqlite}"
EXPORT_DIR="${EXPORT_DIR:-/tmp/ltst-roundtrip-export}"
REBUILT_DB="${REBUILT_DB:-/tmp/ltst-roundtrip-rebuilt.sqlite}"

if [[ ! -f "$SOURCE_DB" ]]; then
  echo "Error: source database not found: $SOURCE_DB" >&2
  exit 1
fi

rm -rf "$EXPORT_DIR"
mkdir -p "$EXPORT_DIR"

"$PYTHON" "$ROOT/framework/catalog/export.py" \
  --config "$ROOT/config/instance.yaml" \
  --db "$SOURCE_DB" \
  --catalog "$EXPORT_DIR"

"$PYTHON" "$ROOT/framework/catalog/build.py" \
  --config "$ROOT/config/instance.yaml" \
  --catalog "$EXPORT_DIR" \
  --db "$REBUILT_DB"

exec "$PYTHON" "$ROOT/framework/catalog/verify_roundtrip.py" \
  --source "$SOURCE_DB" \
  --rebuilt "$REBUILT_DB"
