#!/bin/bash
# deploy.sh — Deploy Zenvort to production
# Usage: ./deploy.sh

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "=== Pulling latest code ==="
git pull origin main

echo "=== Running DB migration ==="
# Migration 001: remove bot tables (safe to run multiple times)
docker compose exec api sqlite3 /data/zenvort.db < migrations/001_remove_bot.sql || true

echo "=== Rebuilding and restarting services ==="
docker compose up -d --build

echo "=== Checking health ==="
sleep 3
curl -sf http://localhost:3000/health && echo " ✅ API is up" || echo " ❌ API health check failed"

echo ""
echo "Services:"
docker compose ps --format "  {{.Name}}: {{.Status}}"