#!/bin/bash
set -e

echo "=== Pulling latest code ==="
cd /root/Zenvort
git pull origin main

echo "=== Rebuilding frontend ==="
cd zenvort-dashboard
npm install
npm run build
cp -r dist/* /var/www/zenvort/
chown -R www-data:www-data /var/www/zenvort

echo "=== Rebuilding backend ==="
cd /root/Zenvort
docker compose up --build -d api worker

echo "=== Running migrations ==="
docker compose run --rm migrate alembic upgrade head

echo "=== Done ==="
curl -s https://zenvort.devbrid.in/api/health