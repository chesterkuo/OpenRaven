#!/bin/bash
set -e

echo "=== OpenRaven SaaS Deployment ==="

# Check .env
if [ ! -f .env ]; then
    echo "No .env file found. Copying from .env.example..."
    cp .env.example .env
    echo "Please edit .env with your settings, then run this script again."
    exit 1
fi

# Build and start
echo "Building and starting services..."
docker compose up -d --build

# Wait for API to be healthy
echo "Waiting for API to be healthy..."
for i in {1..30}; do
    if curl -sf http://localhost:${PORT:-80}/health > /dev/null 2>&1; then
        echo "API is healthy!"
        break
    fi
    sleep 2
done

# Run migrations
echo "Running database migrations..."
docker compose exec openraven-api alembic -c /app/openraven/alembic.ini upgrade head

echo ""
echo "=== OpenRaven is running ==="
echo "URL: http://localhost:${PORT:-80}"
echo ""
