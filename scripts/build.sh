#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export CATALOG_INSTANCE="$ROOT/config/instance.yaml"
PYTHON="${ROOT}/framework/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3"
fi
exec "$PYTHON" "$ROOT/framework/catalog/build.py" \
  --config "$ROOT/config/instance.yaml" \
  --catalog "$ROOT/catalog"
