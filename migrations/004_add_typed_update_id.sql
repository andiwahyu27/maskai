-- V2-DB-001: Typed telegram_update_id column (replaces JSONB expression in unique index)
-- Run after 002b. Safe to run multiple times.

BEGIN;

-- 1. Add typed column (nullable for backward compat with existing rows)
ALTER TABLE maskai_transactions
ADD COLUMN IF NOT EXISTS telegram_update_id BIGINT;

-- 2. Populate from metadata JSONB for existing rows
UPDATE maskai_transactions
SET telegram_update_id = (metadata->>'telegram_update_id')::BIGINT
WHERE telegram_update_id IS NULL
  AND metadata->>'telegram_update_id' IS NOT NULL;

-- 3. Drop old expression-based index
DROP INDEX IF EXISTS uq_maskai_transactions_user_update;

-- 4. Create composite unique index on typed column
CREATE UNIQUE INDEX IF NOT EXISTS uq_maskai_transactions_user_update
ON maskai_transactions (user_id, telegram_update_id)
WHERE telegram_update_id IS NOT NULL;

COMMIT;

-- Verify:
-- SELECT indexdef FROM pg_indexes
-- WHERE tablename = 'maskai_transactions' AND indexname = 'uq_maskai_transactions_user_update';
-- Expected: USING btree (user_id, telegram_update_id) WHERE telegram_update_id IS NOT NULL
