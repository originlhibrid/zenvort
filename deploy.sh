#!/bin/bash
# deploy.sh — Deploy Zenvort to production
# Usage: ./deploy.sh

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "=== Pulling latest code ==="
git pull origin main

echo "=== Running DB migrations ==="
# Run all pending migrations using the migration runner
# The runner tracks which migrations have been applied
docker compose exec api python3 run_migrations.py

echo "=== Rebuilding and restarting services ==="
docker compose up -d --build

echo "=== Checking health ==="
sleep 3
curl -sf http://localhost:8000/v1/health && echo " ✅ API is up" || echo " ❌ API health check failed"

echo ""
echo "Services:"
docker compose ps --format "  {{.Name}}: {{.Status}}"