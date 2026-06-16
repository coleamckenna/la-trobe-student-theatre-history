#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export CATALOG_INSTANCE="$ROOT/config/instance.yaml"
PYTHON="${ROOT}/framework/.venv/bin/python"
DATASETTE="${ROOT}/framework/.venv/bin/datasette"

if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3"
fi
if [[ ! -x "$DATASETTE" ]]; then
  DATASETTE="datasette"
fi

HOST="${DATASETTE_HOST:-127.0.0.1}"
PORT="${DATASETTE_PORT:-8001}"
DB="${DATASETTE_DB:-$ROOT/ltst.sqlite}"

if [[ ! -f "$DB" ]]; then
  echo "Error: database not found: $DB (run ./scripts/build.sh or fossil-sync.sh first)" >&2
  exit 1
fi

exec "$DATASETTE" --immutable "$DB" \
  --metadata "$ROOT/config/metadata.public.yaml" \
  --template-dir "$ROOT/framework/templates" \
  --plugins-dir "$ROOT/framework/plugins" \
  --static static:"$ROOT/framework/static" \
  --host "$HOST" \
  --port "$PORT" \
  "$@"
