#!/usr/bin/env bash
cd /home/ubuntu/source/OpenRaven/openraven-ui
export PORT="${PORT:-3002}"
export CORE_API_URL="${CORE_API_URL:-http://127.0.0.1:8741}"
exec /home/ubuntu/.bun/bin/bun run server/index.ts
