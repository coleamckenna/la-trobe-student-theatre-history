#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export CATALOG_INSTANCE="$ROOT/config/instance.yaml"
exec bash "$ROOT/framework/scripts/bundle-datasette-worker.sh"
