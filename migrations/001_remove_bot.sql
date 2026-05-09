-- Migration 001: Remove bot infrastructure
-- Run this on the SQLite DB to drop bot-specific tables.
-- Safe to run multiple times (IF EXISTS / DROP IF EXISTS).

-- Drop bot-specific tables (tg_users, tg_jobs were the bot's state)
DROP TABLE IF EXISTS tg_users;
DROP TABLE IF EXISTS tg_jobs;

-- Verify
SELECT 'Migration 001 complete. Bot tables removed.' AS status;