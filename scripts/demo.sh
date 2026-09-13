#!/usr/bin/env bash
# 9Bars demo: build the UI, reset demo data, and serve the app.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "→ building the web UI"
if [ ! -d web/out ]; then
  (cd web && npm ci && npm run build)
fi

echo "→ resetting demo data"
rm -f data/nine_bars.duckdb

echo "→ serving 9Bars at http://localhost:9009/ui"
exec uv run nine-bars
