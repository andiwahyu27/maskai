-- MASKAI Telegram Idempotency Migration v2
-- CR-009: Composite unique index on (user_id, telegram_update_id)
-- Safe to run multiple times (IF NOT EXISTS)

BEGIN;

-- 1. Drop old single-column index if it exists
DROP INDEX IF EXISTS idx_transactions_update_id;

-- 2. Create composite partial unique index
CREATE UNIQUE INDEX IF NOT EXISTS uq_maskai_transactions_user_update
ON maskai_transactions (user_id, (metadata->>'telegram_update_id'))
WHERE (metadata->>'telegram_update_id') IS NOT NULL;

COMMIT;

-- Audit duplicate (run manually after):
-- SELECT user_id, metadata->>'telegram_update_id' as uid, COUNT(*)
-- FROM maskai_transactions
-- WHERE metadata->>'telegram_update_id' IS NOT NULL
-- GROUP BY user_id, metadata->>'telegram_update_id'
-- HAVING COUNT(*) > 1;
