#!/usr/bin/env bash
# Load .env if exists
set -a
[ -f /home/ubuntu/source/OpenRaven/openraven/.env ] && source /home/ubuntu/source/OpenRaven/openraven/.env
set +a

exec /home/ubuntu/source/OpenRaven/openraven/.venv/bin/uvicorn \
  openraven.api.server:create_app \
  --factory \
  --port 8741 \
  --host 127.0.0.1
