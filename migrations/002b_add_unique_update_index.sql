-- CR-009: Create composite unique index on (user_id, telegram_update_id)
-- Run ONLY after 002a returns 0 rows.

BEGIN;

DROP INDEX IF EXISTS idx_transactions_update_id;
DROP INDEX IF EXISTS uq_maskai_transactions_user_update;

CREATE UNIQUE INDEX IF NOT EXISTS uq_maskai_transactions_user_update
ON maskai_transactions (user_id, (metadata->>'telegram_update_id'))
WHERE (metadata->>'telegram_update_id') IS NOT NULL;

COMMIT;
