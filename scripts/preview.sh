#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="${HOME}/.local/bin:${PATH}"
export CATALOG_INSTANCE="$ROOT/config/instance.yaml"
"$ROOT/framework/scripts/bundle-datasette-worker.sh"
PYWRANGLER="${ROOT}/framework/.venv/bin/pywrangler"
if [[ ! -x "$PYWRANGLER" ]]; then
  echo "Install workers-py in framework/.venv first"
  exit 1
fi
cd "$ROOT/framework/datasette-worker"
exec "$PYWRANGLER" dev "$@"
