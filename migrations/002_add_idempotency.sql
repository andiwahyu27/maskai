-- MASKAI Telegram Idempotency Migration
-- Fixes CR-009: prevent duplicate transactions from retried updates
-- Safe to run multiple times

BEGIN;

-- Add telegram_update_id to metadata or as nullable column
-- Using metadata JSONB is simpler and avoids schema breaking changes
-- If the column doesn't exist, we use metadata field in insert

-- 1. Add unique partial index on metadata->telegram_update_id
-- This prevents insert of duplicate update_id
CREATE UNIQUE INDEX IF NOT EXISTS idx_transactions_update_id 
ON maskai_transactions ((metadata->>'telegram_update_id'))
WHERE (metadata->>'telegram_update_id') IS NOT NULL;

COMMIT;

-- Rollback: DROP INDEX IF EXISTS idx_transactions_update_id;
