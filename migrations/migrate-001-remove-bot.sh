#!/bin/bash
# migrate-001-remove-bot.sh
# Run this AFTER deploying the new API code.
# Deletes the bot directory and applies DB cleanup.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== Phase 2: Remove Bot Infrastructure ==="
echo ""

# 1. Delete bot directory
if [ -d "$PROJECT_ROOT/bot" ]; then
    echo "🗑 Deleting bot/ directory..."
    rm -rf "$PROJECT_ROOT/bot"
    echo "   ✓ bot/ removed"
else
    echo "   bot/ already removed"
fi

# 2. Delete nginx Telegram config
if [ -f "$PROJECT_ROOT/nginx/telegram.conf" ]; then
    echo "🗑 Deleting nginx/telegram.conf..."
    rm "$PROJECT_ROOT/nginx/telegram.conf"
    echo "   ✓ nginx/telegram.conf removed"
else
    echo "   nginx/telegram.conf already removed"
fi

# 3. Remove bot env vars from .env
echo "🔧 Updating .env (removing bot-related vars)..."
ENV_FILE="$PROJECT_ROOT/.env"
if [ -f "$ENV_FILE" ]; then
    # Backup first
    cp "$ENV_FILE" "$ENV_FILE.bak.$(date +%Y%m%d%H%M%S)"
    # Remove bot vars (keep R2, Redis, Gotenberg, API vars)
    python3 -c "
import re
with open('$ENV_FILE', 'r') as f:
    content = f.read()
keys_to_remove = ['BOT_TOKEN', 'WEBHOOK_BASE_URL', 'BOT_WEBHOOK_SECRET', 'ADMIN_TELEGRAM_IDS', 'API_BASE_URL']
for key in keys_to_remove:
    content = re.sub(rf'^{key}=.*\n?', '', content, flags=re.MULTILINE)
with open('$ENV_FILE', 'w') as f:
    f.write(content)
print('   ✓ Bot env vars removed from .env')
"
else
    echo "   .env not found — skipping"
fi

# 4. Run DB migration
echo "🗄 Running DB migration..."
DB_PATH="${DB_PATH:-${PROJECT_ROOT}/data/zenvort.db}"
if [ -f "$DB_PATH" ]; then
    sqlite3 "$DB_PATH" < "$PROJECT_ROOT/migrations/001_remove_bot.sql"
    echo "   ✓ Migration 001 applied (bot tables dropped)"
else
    echo "   ⚠ DB not found at $DB_PATH — run manually: sqlite3 <path> < migrations/001_remove_bot.sql"
fi

echo ""
echo "✅ Bot removal complete!"
echo ""
echo "Next: rebuild and restart services:"
echo "  cd $PROJECT_ROOT"
echo "  docker compose down"
echo "  docker compose up -d --build"
echo ""
echo "To test the new API endpoints:"
echo "  curl http://localhost:3000/formats"
echo "  curl http://localhost:3000/formats/pdf"
echo "  curl -H 'Authorization: Bearer <key>' http://localhost:3000/user/me"